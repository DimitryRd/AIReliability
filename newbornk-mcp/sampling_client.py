"""
MCP Sampling Demo — NEWBORN K
==============================
Демонструє справжній MCP Sampling flow:

  MCP Server (newbornk-mcp)
      → ctx.session.create_message()   ← сервер ініціює LLM запит
      → sampling_callback()            ← клієнт обробляє запит
      → Anthropic Claude API           ← реальний LLM
      → відповідь назад до сервера     ← результат

Запуск:
  export ANTHROPIC_API_KEY=sk-ant-...
  export SHOPIFY_ADMIN_TOKEN=shpat_...
  export SHOPIFY_DOMAIN=newbornk-com.myshopify.com
  python sampling_client.py
"""

import asyncio
import os
import anthropic
from mcp import ClientSession, types
from mcp.client.streamable_http import streamablehttp_client


ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:3000/mcp")
PRODUCT_ID = os.getenv("PRODUCT_ID", "12832285360288")  # UVEX Blaze


async def sampling_callback(
    context,
    params: types.CreateMessageRequestParams,
) -> types.CreateMessageResult:
    """
    Клієнтський sampling callback.
    Викликається коли MCP сервер робить ctx.session.create_message().
    Клієнт контролює який LLM використовувати і може показати запит людині.
    """
    print("\n" + "="*60)
    print("📨 MCP SAMPLING REQUEST від сервера:")
    print("="*60)

    # Показуємо що сервер запитує (human-in-the-loop)
    for msg in params.messages:
        if hasattr(msg.content, "text"):
            print(f"\nPrompt:\n{msg.content.text[:200]}...")

    if params.systemPrompt:
        print(f"\nSystem: {params.systemPrompt}")

    print(f"\nMax tokens: {params.maxTokens}")
    print("="*60)

    # Клієнт викликає Anthropic Claude
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    messages = []
    for msg in params.messages:
        content = msg.content.text if hasattr(msg.content, "text") else ""
        messages.append({"role": msg.role, "content": content})

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=params.maxTokens or 300,
        system=params.systemPrompt or "",
        messages=messages,
    )

    generated_text = response.content[0].text

    print(f"\n🤖 LLM відповідь (claude-haiku):\n{generated_text}")
    print("="*60 + "\n")

    return types.CreateMessageResult(
        role="assistant",
        content=types.TextContent(type="text", text=generated_text),
        model=response.model,
        stopReason="endTurn",
    )


async def main():
    print("🚀 MCP Sampling Demo — NEWBORN K")
    print(f"Підключення до: {MCP_SERVER_URL}")
    print(f"Товар ID: {PRODUCT_ID}\n")

    async with streamablehttp_client(MCP_SERVER_URL) as (read, write, _):
        async with ClientSession(
            read,
            write,
            sampling_callback=sampling_callback,
        ) as session:
            await session.initialize()
            print("✅ З'єднання встановлено\n")

            # Виклик tool generate_product_description
            # Сервер всередині зробить ctx.session.create_message()
            # що активує наш sampling_callback
            print("🛍️  Викликаємо generate_product_description...")
            result = await session.call_tool(
                "generate_product_description",
                {"product_id": PRODUCT_ID},
            )

            print("\n" + "="*60)
            print("✅ ФІНАЛЬНИЙ РЕЗУЛЬТАТ:")
            print("="*60)
            if result.content:
                print(result.content[0].text)


if __name__ == "__main__":
    asyncio.run(main())
