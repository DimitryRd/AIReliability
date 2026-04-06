#!/usr/bin/env python3
"""
NEWBORN K — Phoenix Cost Alert
Checks token usage per tool and alerts if budget exceeded.
Usage: python3 cost-alert.py [--budget 10000] [--price 0.000003]
"""

import httpx
import os
import sys
import argparse
from collections import defaultdict

PHOENIX_URL = os.getenv("PHOENIX_URL", "http://localhost:6006")
PHOENIX_API_KEY = os.getenv("PHOENIX_API_KEY", "")
PROJECT_NAME = os.getenv("PHOENIX_PROJECT", "newbornk-mcp")

# Claude Sonnet price per token (input+output average)
PRICE_PER_TOKEN = float(os.getenv("PRICE_PER_TOKEN", "0.000003"))  # $3 per 1M tokens


def get_auth_headers():
    if PHOENIX_API_KEY:
        return {"Authorization": f"Bearer {PHOENIX_API_KEY}"}
    return {}


def get_project_id(client: httpx.Client) -> str:
    resp = client.get(f"{PHOENIX_URL}/v1/projects", headers=get_auth_headers())
    resp.raise_for_status()
    projects = resp.json().get("data", [])
    for p in projects:
        if p["name"] == PROJECT_NAME:
            return p["id"]
    raise ValueError(f"Project '{PROJECT_NAME}' not found in Phoenix")


def get_spans(client: httpx.Client, project_id: str, limit: int = 1000) -> list:
    resp = client.get(
        f"{PHOENIX_URL}/v1/projects/{project_id}/spans",
        params={"limit": limit},
        headers=get_auth_headers(),
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json().get("data", [])


def analyze(spans: list, budget: int, price_per_token: float):
    total_tokens = 0
    per_tool: dict = defaultdict(lambda: {"calls": 0, "tokens": 0})

    for span in spans:
        attrs = span.get("attributes", {})
        tokens = attrs.get("llm.token_count.total", 0)
        tool = attrs.get("tool.name", span.get("name", "unknown"))

        total_tokens += tokens
        per_tool[tool]["calls"] += 1
        per_tool[tool]["tokens"] += tokens

    total_cost = total_tokens * price_per_token

    print(f"\n{'='*50}")
    print(f"  NEWBORN K — Phoenix Cost Report")
    print(f"  Project: {PROJECT_NAME}")
    print(f"{'='*50}")
    print(f"\n  Total spans analyzed : {len(spans)}")
    print(f"  Total tokens used    : {total_tokens:,}")
    print(f"  Estimated cost       : ${total_cost:.4f}")
    print(f"  Budget               : {budget:,} tokens (${budget * price_per_token:.4f})")

    print(f"\n  Per-tool breakdown:")
    print(f"  {'Tool':<30} {'Calls':>6} {'Tokens':>10} {'Cost':>10}")
    print(f"  {'-'*60}")
    for tool, data in sorted(per_tool.items(), key=lambda x: x[1]["tokens"], reverse=True):
        cost = data["tokens"] * price_per_token
        print(f"  {tool:<30} {data['calls']:>6} {data['tokens']:>10,} ${cost:>9.4f}")

    print(f"\n{'='*50}")

    if total_tokens > budget:
        print(f"\n  ⚠️  ALERT: Budget exceeded!")
        print(f"  Used {total_tokens:,} tokens — {total_tokens - budget:,} over budget")
        print(f"  Extra cost: ${(total_tokens - budget) * price_per_token:.4f}")
        print()
        return False
    else:
        remaining = budget - total_tokens
        pct = (total_tokens / budget * 100) if budget else 0
        print(f"\n  ✅ Within budget — {pct:.1f}% used ({remaining:,} tokens remaining)")
        print()
        return True


def main():
    parser = argparse.ArgumentParser(description="Phoenix cost alert for newbornk-mcp")
    parser.add_argument("--budget", type=int, default=10000, help="Token budget (default: 10000)")
    parser.add_argument("--price", type=float, default=PRICE_PER_TOKEN, help="Price per token (default: $3/1M)")
    parser.add_argument("--limit", type=int, default=1000, help="Max spans to fetch (default: 1000)")
    args = parser.parse_args()

    with httpx.Client() as client:
        try:
            project_id = get_project_id(client)
            spans = get_spans(client, project_id, limit=args.limit)
            ok = analyze(spans, budget=args.budget, price_per_token=args.price)
            sys.exit(0 if ok else 1)
        except Exception as e:
            print(f"\n  ERROR: {e}")
            print(f"  Make sure Phoenix is running: kubectl port-forward svc/phoenix-svc 6006:6006 -n observability")
            sys.exit(2)


if __name__ == "__main__":
    main()
