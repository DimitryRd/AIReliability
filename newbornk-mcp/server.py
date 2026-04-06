import httpx
import os
import json
from functools import wraps
from mcp.server.fastmcp import FastMCP, Context
from mcp.types import SamplingMessage, TextContent
from phoenix.otel import register
from opentelemetry import trace
from opentelemetry.trace import SpanKind

# Phoenix tracing — відправляємо trace у Phoenix через gRPC OTLP
PHOENIX_ENDPOINT = os.getenv("PHOENIX_COLLECTOR_ENDPOINT", "http://phoenix-svc.observability:4317")
PHOENIX_API_KEY = os.getenv("PHOENIX_API_KEY", "")
register(
    project_name="newbornk-mcp",
    endpoint=PHOENIX_ENDPOINT,
    headers={"authorization": f"Bearer {PHOENIX_API_KEY}"} if PHOENIX_API_KEY else {},
)

tracer = trace.get_tracer("newbornk-mcp")

def traced_tool(func):
    """Wrap MCP tools to capture input/output and token usage in Phoenix"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        with tracer.start_as_current_span(func.__name__, kind=SpanKind.SERVER) as span:
            span.set_attribute("openinference.span.kind", "TOOL")
            span.set_attribute("tool.name", func.__name__)
            safe_kwargs = {k: v for k, v in kwargs.items() if k != "ctx"}
            input_str = json.dumps(safe_kwargs)
            span.set_attribute("input.value", input_str)

            # estimate prompt tokens (4 chars ≈ 1 token)
            prompt_tokens = len(input_str) // 4
            span.set_attribute("llm.token_count.prompt", prompt_tokens)

            try:
                result = await func(*args, **kwargs)
                output_str = str(result)[:2000]
                span.set_attribute("output.value", output_str)

                # estimate completion tokens
                completion_tokens = len(output_str) // 4
                span.set_attribute("llm.token_count.completion", completion_tokens)
                span.set_attribute("llm.token_count.total", prompt_tokens + completion_tokens)

                return result
            except Exception as e:
                span.record_exception(e)
                span.set_attribute("output.value", f"ERROR: {e}")
                raise
    return wrapper

mcp = FastMCP("newbornk-assistant", host="0.0.0.0", port=3000)

SHOPIFY_DOMAIN = os.getenv("SHOPIFY_DOMAIN", "newbornk.myshopify.com")
SHOPIFY_TOKEN = os.getenv("SHOPIFY_ADMIN_TOKEN", "")


async def shopify_get(path: str) -> dict:
    url = f"https://{SHOPIFY_DOMAIN}/admin/api/2024-01/{path}"
    headers = {"X-Shopify-Access-Token": SHOPIFY_TOKEN}
    async with httpx.AsyncClient() as client:
        r = await client.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        return r.json()


async def shopify_put(path: str, payload: dict) -> dict:
    url = f"https://{SHOPIFY_DOMAIN}/admin/api/2024-01/{path}"
    headers = {"X-Shopify-Access-Token": SHOPIFY_TOKEN, "Content-Type": "application/json"}
    async with httpx.AsyncClient() as client:
        r = await client.put(url, headers=headers, json=payload, timeout=10)
        r.raise_for_status()
        return r.json()


@mcp.tool()
@traced_tool
async def get_products(limit: int = 10) -> str:
    """Отримати список товарів з Shopify"""
    data = await shopify_get(f"products.json?limit={limit}&fields=id,title,vendor,product_type,variants,metafields_global_title_tag")
    products = data.get("products", [])
    lines = []
    for p in products:
        price = p["variants"][0]["price"] if p["variants"] else "N/A"
        has_seo = "є" if p.get("metafields_global_title_tag") else "немає"
        lines.append(f"ID:{p['id']} | {p['title']} | {p['vendor']} | {price} грн | SEO: {has_seo}")
    return "\n".join(lines) if lines else "Товари не знайдені"


@mcp.tool()
@traced_tool
async def get_product_details(product_id: str) -> str:
    """Отримати деталі одного товару для генерації SEO"""
    data = await shopify_get(f"products/{product_id}.json")
    p = data.get("product", {})
    if not p:
        return f"Товар {product_id} не знайдений"
    price = p["variants"][0]["price"] if p.get("variants") else "N/A"
    return (
        f"ID: {p['id']}\n"
        f"Назва: {p['title']}\n"
        f"Бренд: {p['vendor']}\n"
        f"Категорія: {p['product_type']}\n"
        f"Ціна: {price} грн\n"
        f"Поточний SEO title: {p.get('metafields_global_title_tag', 'не встановлено')}\n"
        f"Поточний SEO description: {p.get('metafields_global_description_tag', 'не встановлено')}"
    )


@mcp.tool()
@traced_tool
async def find_product_by_name(name: str) -> str:
    """Знайти товар за назвою і повернути його ID та деталі"""
    data = await shopify_get(f"products.json?title={name}&limit=5&fields=id,title,vendor,product_type,variants")
    products = data.get("products", [])
    if not products:
        return f"Товар '{name}' не знайдений"
    lines = []
    for p in products:
        price = p["variants"][0]["price"] if p["variants"] else "N/A"
        lines.append(f"ID:{p['id']} | {p['title']} | {p['vendor']} | {price} грн")
    return "\n".join(lines)


@mcp.tool()
@traced_tool
async def update_product_seo(product_id: str, seo_title: str, seo_description: str) -> str:
    """Оновити SEO title і SEO description товару в Shopify"""
    if len(seo_title) > 70:
        return f"❌ SEO title задовгий ({len(seo_title)} симв). Максимум 70 символів."
    if len(seo_description) > 160:
        return f"❌ SEO description задовгий ({len(seo_description)} симв). Максимум 160 символів."

    data = await shopify_get(f"products/{product_id}.json?fields=id,title")
    p = data.get("product", {})
    if not p:
        return f"Товар {product_id} не знайдений"

    await shopify_put(f"products/{product_id}.json", {
        "product": {
            "id": product_id,
            "metafields_global_title_tag": seo_title,
            "metafields_global_description_tag": seo_description,
        }
    })
    return (
        f"✅ SEO оновлено для '{p['title']}':\n"
        f"Title ({len(seo_title)} симв): {seo_title}\n"
        f"Description ({len(seo_description)} симв): {seo_description}"
    )


@mcp.tool()
@traced_tool
async def get_products_without_seo(limit: int = 20) -> str:
    """Отримати список товарів без SEO title для масового оновлення"""
    data = await shopify_get(f"products.json?limit={limit}&fields=id,title,vendor,product_type,variants,metafields_global_title_tag")
    products = data.get("products", [])
    without_seo = [p for p in products if not p.get("metafields_global_title_tag")]
    if not without_seo:
        return "Всі товари мають SEO title"
    lines = []
    for p in without_seo:
        price = p["variants"][0]["price"] if p["variants"] else "N/A"
        lines.append(f"ID:{p['id']} | {p['title']} | {p['vendor']} | {price} грн")
    return f"Товари без SEO ({len(without_seo)}):\n" + "\n".join(lines)


@mcp.tool()
@traced_tool
async def get_orders_analytics() -> str:
    """Отримати аналітику останніх 50 замовлень"""
    orders_data = await shopify_get("orders.json?status=any&limit=50&fields=id,total_price,created_at,line_items")
    orders = orders_data.get("orders", [])
    if not orders:
        return "Замовлення не знайдені"

    total_revenue = sum(float(o["total_price"]) for o in orders)
    product_counts: dict[str, int] = {}
    for order in orders:
        for item in order.get("line_items", []):
            name = item["title"]
            product_counts[name] = product_counts.get(name, 0) + item["quantity"]

    top = sorted(product_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    top_str = "\n".join(f"  - {name}: {qty} шт" for name, qty in top)

    return (
        f"Замовлень: {len(orders)}\n"
        f"Виручка: {total_revenue:.0f} грн\n"
        f"Середній чек: {total_revenue/len(orders):.0f} грн\n\n"
        f"Топ-5 товарів:\n{top_str}"
    )

@mcp.tool()
@traced_tool
async def get_products_with_stock(limit: int = 20) -> str:
    """Отримати список товарів із залишком більше 0"""
    data = await shopify_get(f"products.json?limit={limit}&fields=id,title,vendor,product_type,variants")
    products = data.get("products", [])

    in_stock = []
    for p in products:
        total_qty = sum(
            v.get("inventory_quantity", 0)
            for v in p.get("variants", [])
            if v.get("inventory_management") == "shopify"  # тільки ті, що tracked
        )
        if total_qty > 0:
            in_stock.append((p, total_qty))

    if not in_stock:
        return "Немає товарів із залишком"

    lines = []
    for p, qty in in_stock:
        price = p["variants"][0]["price"] if p["variants"] else "N/A"
        lines.append(f"ID:{p['id']} | {p['title']} | {p['vendor']} | {price} грн | залишок: {qty}")

    return f"Товари в наявності ({len(in_stock)}):\n" + "\n".join(lines)


@mcp.tool()
@traced_tool
async def generate_product_description(product_id: str, ctx: Context) -> str:
    """[MCP Sampling] Генерує продаючий опис товару — сервер запитує LLM через клієнта"""
    data = await shopify_get(f"products/{product_id}.json")
    p = data.get("product", {})
    if not p:
        return f"Товар {product_id} не знайдений"

    price = p["variants"][0]["price"] if p.get("variants") else "N/A"

    # MCP Sampling: сервер ініціює запит до LLM через клієнта
    result = await ctx.session.create_message(
        messages=[
            SamplingMessage(
                role="user",
                content=TextContent(
                    type="text",
                    text=f"""Напиши продаючий опис для товару концепт-стору NEWBORN K:

Назва: {p.get('title')}
Бренд: {p.get('vendor')}
Категорія: {p.get('product_type')}
Ціна: {price} грн

Вимоги:
- Мова: українська
- Стиль: мінімалістичний, міський, streetwear
- Довжина: 80-120 слів
- Без кліше типу "неймовірний" або "унікальний\""""
                )
            )
        ],
        system_prompt="Ти копірайтер концепт-стору NEWBORN K у Києві. Пишеш короткі, стильні описи товарів українською мовою.",
        max_tokens=300,
    )
    return result.content.text


@mcp.prompt()
def seo_prompt(product_title: str, vendor: str, category: str, price: str) -> str:
    """Шаблон промпту для генерації SEO title і description"""
    return f"""Згенеруй SEO title та SEO description для товару концепт-стору NEWBORN K:

Товар: {product_title}
Бренд: {vendor}
Категорія: {category}
Ціна: {price} грн

Вимоги:
- Мова: українська
- Стиль: мінімалістичний, міський, streetwear
- SEO title: до 70 символів, містить назву бренду
- SEO description: до 160 символів, містить ціну і ключові слова
- Формат відповіді:
  TITLE: <seo title>
  DESC: <seo description>"""


@mcp.prompt()
def analytics_prompt(period: str = "останні 50 замовлень") -> str:
    """Шаблон промпту для аналізу продажів NEWBORN K"""
    return f"""Проаналізуй продажі NEWBORN K за {period}.

Зроби звіт у форматі:
1. Загальна виручка та кількість замовлень
2. Топ-5 товарів за кількістю продажів
3. Середній чек
4. Рекомендації для збільшення продажів (3 пункти)
5. Товари які варто просувати активніше

Стиль: лаконічно, по ділу, з конкретними цифрами."""


@mcp.prompt()
def shopify_dev_prompt(task: str) -> str:
    """Шаблон промпту для Shopify розробки (front-end, performance, CRO)"""
    return f"""Ти Shopify розробник для концепт-стору NEWBORN K (newbornk.com).

Завдання: {task}

Контекст магазину:
- Ніша: streetwear, кросівки, міська мода
- Аудиторія: молодь 18-35, Київ
- Пріоритети: швидкість завантаження, конверсія, мобільна версія

Надай конкретне технічне рішення з кодом якщо потрібно."""


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
