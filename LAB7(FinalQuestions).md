"Vin's Questions" — дослідження та оцінка власного сетапу AI-інфраструктури.

1. How could we handle 'agent got stuck' scenarios?
    - Для початку - це таймаути
    - Кубернетес liveness probe - рестартує под якщо він завис
    - Ретрай полісі в agnetgateway
    - На рівні kagent - кількість ітерацій і їх ліміт встановлений 
    - Circuit breker - якщо бекенд падає частно то Gaway перестае cлати
    - Ще трейсінг якраз ьреба що це все відстежувати як у нас через Фенікс - це і буде обсервабіліті

2. Any automatic timeout/circuit breaker patterns coming out form this framework ?
Я не знаю як назвати саме паттерни але є автоматичний ретрай в залежності від кодів які тригерять, наприклад 429 - rate limit. 

3.  How does kgateway handle model failover?
Реалізовано три режими роботи з weight:

weight	поведінка
1 / 0	active/passive failover — gemini тільки якщо anthropic впав
1 / 1	round-robin 50/50 між двома
3 / 1	75% anthropic, 25% gemini (canary)

Наприклад:
запит з x-provider: anthropic
        │
        ▼
   Anthropic API  ← weight: 1 (primary)
        │
   якщо 500/502/503 → retry 3x
        │
   якщо всі спроби невдалі
        │
        ▼
   Gemini API  ← weight: 0 (failover)


4. Can we automatically switch from OpenAI to Claude to local model ?Так, можливо, наприклад через логіку weight/failover(500/503) - retry
Але головне мати  налаштовані альтернативні LLM та створенні secrets для них. Як би банально це не звучало.

5. Could we seamlessly handle the response formats form these providers?
Більшість проблем agentgateway вирішує самостійно автоматично без конфігу переводячи все в OpenAI формат (нормалізація)
    Те що не вирішується автоматично - треба проганяти через transaformations, наприклад:
        
        policies:
            transformations:
                response:
                remove:
                    - "usage.cache_read_input_tokens"   # Anthropic-specific
                add:
                    x-provider-used: "anthropic"        # додати header для дебагу

Тобто, так - seamlessly - клієнт не буде знати

6. Can we version the agents built form kagent?
Kagent не має вбудованої версіонування але у нас це реалізовано через
- Git + Flux 
Кожен гіт пуш - це версія, а кожен чекаут - це як роллбек. Це - GitOps версіонування.
- Куб labels - версія як метадані але я це не додавав.

7. Any blue/green or canary deployment patterns for agents?
Запущено 2 версії із різним weight 9 | 1 
![alt text](<Screenshot 2026-04-05 at 22.54.47.png>)

Проведенно тестування одним і тим самим промтом

![alt text](<Screenshot 2026-04-05 at 22.59.03.png>)

![alt text](<Screenshot 2026-04-05 at 22.59.26.png>)

різні відповіді та різна швидкість - обираємо агента який краще підходить і активуємо командами

kubectl label agent newbornk-agent-v2 active=true -n kagent --overwrite
kubectl label agent newbornk-agent active=false -n kagent --overwrite

8. What's the fastmcp-python framework mentioned?
FastMCP - частина офіційного mcp пакету від антропік 
Це аналог FastAPI для REST. 
    - Пришвидшує написання Пайтон функцій 
    - Вбудований MCP Sampling MCP Prompts та Resources 
    - JSON Schema 

В проекті реалізовано 7 інструментів через анотації mcp.tools() та 3 промти через @mcp.prompt() і ctx.session.create_message() -> MCP Sampling в generate_product_description

9.  Is it the easiest path to mcp?
Так, в порівнянні MCP SDK або TypeScript SDK
Менше коду та все генерується з type hints та docstrings

10. About finops: how much control I can have?
    - Вибір моделі - дорога або більше дешевша, ще на етапі A/B тестування або Canary.
    - Налаштувати в Agentgateway - localRateLimits - max N запитів на хвилину
    - Налаштувати в kagent ai.defaults.maxTokents - кількість токенів на запит
    - Phoenix traces - скільки токенів кожен виклик


11. Token level / per agent level
 Токен левел можно реалізувати для всього маршруту 
    # config.yaml — глобально для всього маршруту
    policies:
        ai:
            defaults:
            maxTokens: 500    
            overrides:
            maxTokens: 2000

Токен левел на кожен агент 
    # agent.yaml — кожен агент має свій ліміт
    metadata:
        name: newbornk-agent        # бізнес агент — більше токенів
    spec:
        declarative:
            maxIterations: 10       # max 10 LLM викликів на сесію
            maxTokens: 2000

    ---
    metadata:
        name: devops-agent        # технічний агент — менше
    spec:
        declarative:
            maxIterations: 5
            maxTokens: 500


      
12. Can I implement custom cost controls?
Це можливо спостерігати в Phoenix або налаштувати алертс в Графана 
В проекті реалізовано за допомогою скрипта cost-alerts.py
Трекінг використання токенів в Фенікс
![alt text](<Screenshot 2026-04-06 at 19.06.35.png>)

13. Per-agent budgets or depth of Token limits
Нативного per-agent token budget в kagent немає — це gap в фреймворку, який закривається або на рівні gateway (routing), або зовнішнім моніторингом (Phoenix + cost-alert.py).

14. vLLM suitable for agents with many back and forth tool calls, or is it better for single shot inference?

15. llm-d's scheduler - helps when agents makes 15 llms calls?
