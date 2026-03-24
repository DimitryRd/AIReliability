# MCP Sampling: AI у реальному e-commerce бізнесі
## Кейс: NEWBORN K — concept store (newbornk.com)

---

## 1. Що таке MCP Sampling

**MCP Sampling** — механізм протоколу MCP, який дозволяє **серверу** ініціювати запит до LLM через клієнта (а не навпаки).

```
Звичайний MCP flow:
  Клієнт → запит → MCP Server → відповідь → Клієнт

MCP Sampling flow:
  MCP Server → "мені потрібна LLM" → Клієнт → LLM → відповідь → MCP Server
                                         ↑
                                   людина може переглянути
                                   і схвалити/відхилити
```

**Ключові особливості:**
- Сервер не платить за LLM — платить клієнт (користувач)
- Людина бачить і контролює кожен запит (human-in-the-loop)
- Сервер може вбудувати "розум" без власного LLM API ключа

---

## 2. Архітектура для NEWBORN K

```
Shopify (newbornk.com)
    │
    ├── Продукти, замовлення, клієнти, аналітика
    │
    ▼
MCP Server (NEWBORN K)          ←── наш власний KMCP сервер
    │  tools:
    │  - get_products()
    │  - get_orders()
    │  - get_customer_history()
    │  - check_inventory()
    │  - get_analytics()
    │
    │  sampling: ←── сервер просить LLM проаналізувати дані
    │
    ▼
agentgateway (наш кластер)
    │
    ├── Anthropic Claude
    └── Gemini
```

---

## 3. Реальні бізнес-кейси для NEWBORN K

### Кейс 1: Персональний стиліст-агент 🛍️

**Проблема:** Клієнт заходить на сайт і не знає що вибрати.

**Рішення з MCP Sampling:**
```
1. MCP Server отримує: розмір клієнта, попередні покупки, бюджет
2. Sampling запит до LLM:
   "На основі цих даних [дані клієнта] і поточного асортименту [список товарів]
    запропонуй 3 аутфіти для весни до 5000 грн"
3. LLM генерує персональну добірку
4. Клієнт отримує рекомендації + пряме посилання на товари
```

**Бізнес-цінність:**
- Конверсія +30-40% (дані Shopify e-comm звітів)
- Середній чек зростає через cross-sell
- Клієнт отримує досвід особистого шопінгу онлайн

---

### Кейс 2: Автоматичний опис товарів 📝

**Проблема:** Нові надходження потрібно описувати вручну — довго і дорого.

**Рішення з MCP Sampling:**
```
1. MCP Server отримує: фото товару, назву, бренд, ціну
2. Sampling запит до LLM:
   "Напиши продаючий опис для цього товару [дані] в стилі NEWBORN K —
    молодіжно, по-міськи, українською. Максимум 150 слів."
3. Менеджер бачить згенерований текст, схвалює або редагує
4. Товар публікується в Shopify
```

**Бізнес-цінність:**
- Час публікації товару: 2 год → 10 хв
- Консистентний tone of voice бренду
- SEO-оптимізовані описи

---

### Кейс 3: Аналітик продажів 📊

**Проблема:** Власник не має часу аналізувати дані щодня.

**Рішення з MCP Sampling:**
```
1. MCP Server щодня збирає дані з Shopify:
   - продажі по категоріях
   - найпопулярніші товари
   - клієнти що не повертаються
2. Sampling запит до LLM:
   "Проаналізуй ці дані [weekly_data] і дай 3 конкретні дії
    для збільшення продажів цього тижня"
3. Власник отримує звіт у Telegram/Email щопонеділка
```

**Бізнес-цінність:**
- Швидкі data-driven рішення без аналітика
- Виявлення трендів і мертвого стоку
- Автоматичні сповіщення про аномалії

---

### Кейс 4: Агент підтримки клієнтів 💬

**Проблема:** Багато однотипних питань (статус замовлення, повернення, розміри).

**Рішення з MCP Sampling:**
```
1. Клієнт пише питання в чат
2. MCP Server дістає: статус замовлення, таблицю розмірів, FAQ
3. Sampling запит до LLM:
   "Відповідь клієнту: [питання]. Дані: [замовлення, FAQ].
    Стиль: дружній, короткий, українською."
4. Відповідь показується оператору → підтверджує → надсилається
```

**Бізнес-цінність:**
- Час відповіді: 24 год → миттєво
- Оператор перевіряє тільки нестандартні кейси
- Клієнтський досвід значно покращується

---

### Кейс 5: Генерація контенту для соцмереж 📱

**Проблема:** Instagram/Facebook потребує щоденного контенту.

**Рішення з MCP Sampling:**
```
1. MCP Server бере: нові надходження, акції, тренди
2. Sampling запит до LLM:
   "Напиши пост для Instagram про [товар] в стилі streetwear,
    з хештегами, емодзі, українською. Тон — молодіжний, трендовий."
3. SMM-менеджер редагує і публікує
```

**Бізнес-цінність:**
- Контент-план на тиждень за 30 хв
- A/B тести різних стилів текстів
- Консистентність бренду

---

## 4. Технічна реалізація

### Стек для NEWBORN K MCP Server

```
Language:     Python (FastMCP)
Deploy:       Kubernetes (наш kind кластер)
Data source:  Shopify Admin API
LLM:          agentgateway → Anthropic Claude / Gemini
GitOps:       Flux (автодеплой з GitHub)
```

### Структура KMCP сервера

```
newbornk-mcp/
├── server.py              # FastMCP сервер
├── tools/
│   ├── products.py        # get_products, update_product
│   ├── orders.py          # get_orders, get_order_status
│   ├── customers.py       # get_customer_history
│   └── analytics.py      # get_weekly_stats
├── sampling/
│   └── prompts.py         # шаблони для sampling запитів
├── Dockerfile
└── k8s/
    ├── deployment.yaml
    └── mcpserver.yaml     # KMCP ресурс
```

### Приклад sampling запиту (Python)

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("newbornk-assistant")

@mcp.tool()
async def generate_product_description(product_id: str) -> str:
    """Генерує опис товару через LLM"""
    product = await shopify_api.get_product(product_id)

    # MCP Sampling — сервер просить клієнта використати LLM
    result = await mcp.sampling.create_message(
        messages=[{
            "role": "user",
            "content": f"""
                Напиши продаючий опис для товару NEWBORN K:
                Назва: {product['title']}
                Бренд: {product['vendor']}
                Ціна: {product['price']} грн
                Категорія: {product['type']}

                Стиль: молодіжний, міський, українська мова.
                Довжина: 100-150 слів.
            """
        }],
        system_prompt="Ти копірайтер для концепт-стору NEWBORN K у Києві.",
        max_tokens=300
    )
    return result.content[0].text
```

---

## 5. ROI оцінка для NEWBORN K

| Кейс | Час до AI | Час з AI | Економія/міс |
|------|-----------|----------|--------------|
| Описи товарів | 2 год/товар | 10 хв/товар | ~40 год |
| Аналітика | 4 год/тиждень | 0 | ~16 год |
| Підтримка | 24 год відповідь | < 1 год | +NPS |
| Контент | 2 год/день | 30 хв/тиждень | ~50 год |

**Загальна економія: ~100 год/місяць** — еквівалент 0.5 ставки менеджера.

---

## 6. Roadmap впровадження

```
Тиждень 1:  KMCP сервер + Shopify API інтеграція
Тиждень 2:  Кейс "Описи товарів" → production
Тиждень 3:  Кейс "Аналітика" → Telegram bot
Тиждень 4:  Кейс "Підтримка клієнтів" → тест на реальних запитах
Місяць 2:   Кейс "Персональний стиліст" → на сайті
```

---

## Джерела

- [MCP Sampling — офіційна специфікація](https://modelcontextprotocol.io/docs/concepts/sampling)
- [MCP Sampling Explained](https://www.mcpevals.io/blog/mcp-sampling-explained)
- [Flipping the flow: How MCP sampling works](https://workos.com/blog/mcp-sampling)
- [MCP Use Cases: Real-World Examples](https://apigene.ai/blog/mcp-use-cases)
- [MCP in Enterprise AI](https://appwrk.com/insights/top-enterprise-mcp-use-cases)
