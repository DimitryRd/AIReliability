# A2A Protocol — Agent2Agent Специфікація

## 1. Що таке A2A?

**Agent2Agent (A2A)** — відкритий стандартний протокол для комунікації між AI агентами різних фреймворків та вендорів. Розроблений Google, переданий Linux Foundation.

```
Без A2A:                          З A2A:
AgentA ──custom──► AgentB         AgentA ──A2A──► AgentB
AgentA ──custom──► AgentC         AgentA ──A2A──► AgentC
AgentA ──custom──► AgentD         AgentA ──A2A──► AgentD
(кожна інтеграція унікальна)      (єдиний стандарт)
```

### Місце в AI стеку

```
┌─────────────────────────────────────────┐
│           AI Application                │
├─────────────────────────────────────────┤
│  A2A Protocol  │  Agent ↔ Agent         │
├─────────────────────────────────────────┤
│  MCP Protocol  │  Agent ↔ Tools/Data    │
├─────────────────────────────────────────┤
│  LLM           │  Claude, Gemini, GPT   │
└─────────────────────────────────────────┘
```

- **MCP** — агент ↔ інструменти/дані
- **A2A** — агент ↔ агент

---

## 2. Agent Card

**Agent Card** — JSON документ-паспорт агента. Описує хто він, що вміє і як з ним спілкуватись.

### Well-Known URI

Клієнт знаходить агента за стандартним шляхом (RFC 8615):

```
GET https://{agent-domain}/.well-known/agent.json
```

### Структура Agent Card

```json
{
  "name": "newbornk-agent",
  "description": "AI асистент для концепт-стору NEWBORN K",
  "url": "https://agent.newbornk.com/a2a",
  "version": "1.0.0",
  "provider": {
    "organization": "NEWBORN K",
    "url": "https://newbornk.com"
  },
  "capabilities": {
    "streaming": true,
    "pushNotifications": false,
    "stateTransitionHistory": true
  },
  "defaultInputModes": ["text/plain"],
  "defaultOutputModes": ["text/plain"],
  "skills": [
    {
      "id": "seo-generator",
      "name": "SEO Generator",
      "description": "Генерує SEO title та description для товарів",
      "inputModes": ["text/plain"],
      "outputModes": ["text/plain"],
      "examples": ["Update SEO for UVEX Blaze", "Generate description for product 123"]
    },
    {
      "id": "analytics",
      "name": "Sales Analytics",
      "description": "Аналізує продажі та дає рекомендації",
      "inputModes": ["text/plain"],
      "outputModes": ["text/plain"]
    }
  ]
}
```

---

## 3. Task — одиниця роботи

**Task** — базова одиниця комунікації між агентами. Кожен task має унікальний ID і проходить lifecycle:

```
submitted → working → completed
                   ↘ failed
                   ↘ canceled
                   ↘ input-required → (чекає уточнення від клієнта)
```

### JSON-RPC методи

| Метод | Опис |
|-------|------|
| `message/send` | Надіслати повідомлення → отримати повну відповідь |
| `message/stream` | Надіслати повідомлення → отримати відповідь стрімом (SSE) |
| `tasks/get` | Отримати статус та результат task |

### Приклад запиту

```json
POST /a2a
{
  "jsonrpc": "2.0",
  "id": "req-1",
  "method": "message/send",
  "params": {
    "message": {
      "role": "user",
      "parts": [{"kind": "text", "text": "Update SEO for UVEX Blaze"}]
    }
  }
}
```

### Відповідь

```json
{
  "jsonrpc": "2.0",
  "id": "req-1",
  "result": {
    "id": "task-abc123",
    "status": {"state": "completed"},
    "artifacts": [
      {
        "parts": [{"kind": "text", "text": "✅ SEO оновлено..."}]
      }
    ]
  }
}
```

---

## 4. Технічний стек

- **Transport:** HTTP/HTTPS
- **Format:** JSON-RPC 2.0
- **Streaming:** Server-Sent Events (SSE)
- **Discovery:** Well-Known URI (RFC 8615)
- **Auth:** Bearer Token, OAuth2

---

## 5. A2A в kagent

Кожен агент kagent автоматично імплементує A2A протокол.

### Endpoint pattern

```
http://kagent-controller.kagent:8083/api/a2a/{namespace}/{agent-name}
```

### Agent Card

```bash
curl http://localhost:8083/api/a2a/kagent/newbornk-agent/.well-known/agent.json
```

### A2A конфігурація агента (YAML)

```yaml
spec:
  type: Declarative
  declarative:
    a2aConfig:
      skills:
        - id: seo-automation
          name: SEO Automation
          description: Автоматизація SEO для Shopify товарів NEWBORN K
          inputModes: ["text/plain"]
          outputModes: ["text/plain"]
          tags: ["seo", "shopify", "ecommerce"]
          examples:
            - "Update SEO for all products"
            - "Generate description for UVEX Blaze"
```

---

## 6. AI Ресурси в кластері (Inventory)

```bash
kubectl get agents,remotemcpservers,modelconfigs -n kagent
```

### Агенти (13)

| Агент | Призначення |
|-------|-------------|
| `k8s-agent` | Kubernetes операції |
| `helm-agent` | Helm chart management |
| `devops-agent` | DevOps автоматизація |
| `newbornk-agent` | SEO для NEWBORN K |
| `observability-agent` | Моніторинг |
| `promql-agent` | PromQL запити |
| `istio-agent` | Service mesh |
| `cilium-*` | Network policy |
| `argo-rollouts-*` | Deployment strategies |

### MCP Сервери (3)

| Сервер | URL |
|--------|-----|
| `kagent-tool-server` | k8s tools (80+ інструментів) |
| `kagent-grafana-mcp` | Grafana метрики |
| `newbornk-mcp` | Shopify API (власний) |

### Model Configs (3)

| Config | Provider | Model |
|--------|----------|-------|
| `anthropic-model-config` | Anthropic | claude-sonnet-4 |
| `gemini-model-config` | Gemini | gemini-2.5-flash |
| `default-model-config` | OpenAI | gpt-4.1-mini |

---

## 7. A2A vs MCP — порівняння

| | MCP | A2A |
|-|-----|-----|
| **Хто з ким** | Agent ↔ Tool | Agent ↔ Agent |
| **Стан** | Stateless | Stateful (Tasks) |
| **Виконавець** | Сервер-інструмент | Автономний агент |
| **Відповідь** | Синхронна | Async + Streaming |
| **Discovery** | Manual | Well-Known URI |

---

## Джерела

- [A2A Protocol Specification](https://a2a-protocol.org/latest/specification/)
- [Agent Discovery](https://a2a-protocol.org/latest/topics/agent-discovery/)
- [kagent A2A Docs](https://kagent.dev/docs/kagent/examples/a2a-agents)
- [Google A2A Announcement](https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/)
- [HuggingFace A2A Explained](https://huggingface.co/blog/1bo/a2a-protocol-explained)
