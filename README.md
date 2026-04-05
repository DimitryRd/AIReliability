# AIReliability — AI Infrastructure Project

**Автор:** Dimitry  
**Репозиторій:** [github.com/DimitryRd/AIReliability](https://github.com/DimitryRd/AIReliability)  
**Курс:** AI Reliability & Infrastructure

---

## Огляд проекту

Цей проект демонструє побудову production-ready AI інфраструктури з нуля — від локального LLM gateway до повноцінної GitOps-системи з AI агентами, що вирішують реальні бізнес-задачі.

Реальний бізнес-кейс: **NEWBORN K** ([newbornk.com](https://newbornk.com)) — концепт-стор у Києві. Автоматизація SEO опису товарів та аналітики продажів через AI агентів.

---

## Архітектура

```
GitHub Repository (AIReliability)
          │
          │  Flux GitOps — автодеплой при кожному push
          ▼
Kubernetes (kind — локальний кластер)
  │
  ├── default namespace
  │     └── agentgateway          ← LLM Gateway (Anthropic + Gemini)
  │           ├── port 3000       ← OpenAI-compatible API endpoint
  │           └── port 15000      ← Admin UI
  │
  ├── kagent namespace
  │     ├── kagent-controller     ← A2A protocol endpoint (port 8083)
  │     ├── kagent-ui             ← Web UI (port 8080)
  │     ├── kagent-tools          ← 80+ Kubernetes MCP tools
  │     ├── kagent-grafana-mcp    ← Grafana MCP server
  │     ├── newbornk-mcp          ← Custom MCP Server (Shopify API)
  │     ├── devops-agent          ← DevOps AI агент
  │     ├── newbornk-agent        ← NEWBORN K бізнес агент
  │     └── ModelConfigs          ← Anthropic, Gemini, OpenAI
  │
  └── flux-system namespace
        ├── flux-operator         ← Web UI
        ├── source-controller     ← Git sync
        └── kustomize-controller  ← Apply resources
```

---

## Лабораторна №1 — LLM Gateway

**Мета:** Розгорнути agentgateway як LLM proxy в Kubernetes.

### Що зроблено

- Налаштовано `config.yaml` з маршрутизацією по `x-provider` header
- Розроблено Helm chart (`helm/agentgateway/`) з:
  - `Deployment` — запуск контейнера
  - `Service` — мережевий доступ
  - `ConfigMap` — конфігурація gateway
- Виправлено liveness/readiness probe (TCP socket замість HTTP)
- Підключено провайдери: **Anthropic Claude** та **Google Gemini**
- Kubernetes Secrets для API ключів

### Ключові файли

```
config.yaml                              ← agentgateway конфіг
helm/agentgateway/
  ├── Chart.yaml
  ├── values.yaml
  └── templates/
      ├── deployment.yaml
      ├── service.yaml
      └── configmap.yaml
```

### Доступ

```bash
kubectl port-forward svc/agentgateway 3000:3000 15000:15000
```

- Admin UI: http://localhost:15000/ui/
- API: http://localhost:3000

### Тест

```bash
# Anthropic
curl http://localhost:3000 \
  -H "Content-Type: application/json" \
  -H "x-provider: anthropic" \
  -d '{"model":"claude-sonnet-4-20250514","messages":[{"role":"user","content":"Hello!"}]}'

# Gemini
curl http://localhost:3000 \
  -H "Content-Type: application/json" \
  -H "x-provider: gemini" \
  -d '{"messages":[{"role":"user","content":"Hello!"}]}'
```

---

## Лабораторна №2 — kagent + GitOps

**Мета:** Розгорнути AI агентів через GitOps (Flux).

### Що зроблено

- Встановлено **kagent** з CRDs (Helm)
- Налаштовано **ModelConfig** для Anthropic та Gemini
- Встановлено **Flux** + підключено GitHub репо
- Створено `devops-agent` — декларативний AI агент для DevOps задач
- Реалізовано **GitOps pipeline**: зміни в git → Flux → Kubernetes

### GitOps Flow

```
git push → GitHub → Flux pull (кожну хвилину) → kubectl apply → кластер
```

### Ключові файли

```
flux/
  ├── kustomization.yaml          ← що деплоїть Flux
  ├── flux-ui/
  └── kagent/
      └── agent.yaml              ← devops-agent декларація
kagent/
  └── model-config.yaml           ← Anthropic + Gemini ModelConfig
```

### Перевірка

```bash
flux get kustomizations
kubectl get agents -n kagent
```

### Agent Card (A2A)

```bash
kubectl port-forward svc/kagent-controller 8083:8083 -n kagent
curl http://localhost:8083/api/a2a/kagent/devops-agent/.well-known/agent.json
```

---

## Лабораторна №3 — MCP Sampling

**Мета:** Реалізувати власний MCP сервер з MCP Sampling для реального e-commerce бізнесу.

### Research

Документ: [research/mcp-sampling-ecomm.md](research/mcp-sampling-ecomm.md)

**5 бізнес-кейсів MCP Sampling для NEWBORN K:**
1. Персональний стиліст-агент (+30-40% конверсія)
2. Автоматична генерація описів товарів (2 год → 10 хв)
3. Аналітик продажів (щотижневий звіт автоматично)
4. Агент підтримки клієнтів (24 год → миттєво)
5. Генерація контенту для соцмереж

### Реалізація — newbornk-mcp

Власний KMCP сервер на Python (FastMCP) з інтеграцією Shopify API:

```
newbornk-mcp/
  ├── server.py              ← FastMCP сервер (6 tools + MCP Sampling)
  ├── sampling_client.py     ← MCP Sampling demo клієнт
  ├── requirements.txt
  ├── Dockerfile
  └── k8s/
      ├── deployment.yaml    ← Deployment + Service + RemoteMCPServer
      └── agent.yaml         ← newbornk-agent з a2aConfig
```

### MCP Tools

| Tool | Опис |
|------|------|
| `get_products` | Список товарів з Shopify |
| `get_product_details` | Деталі товару по ID |
| `find_product_by_name` | Пошук товару по назві |
| `update_product_seo` | Оновити SEO title + description в Shopify |
| `get_products_without_seo` | Товари без SEO (для масового оновлення) |
| `get_orders_analytics` | Аналітика останніх 50 замовлень |
| `generate_product_description` | **MCP Sampling** — LLM генерує опис |

### MCP Sampling Flow

```
sampling_client.py
  └── session.call_tool("generate_product_description")
        └── server.py: ctx.session.create_message()   ← MCP Sampling
              └── sampling_callback()                  ← клієнт обробляє
                    └── Anthropic Claude API           ← реальний LLM
                          └── відповідь → сервер → клієнт
```

### Запуск MCP Sampling Demo

```bash
# Термінал 1
kubectl port-forward svc/newbornk-mcp 3000:3000 -n kagent

# Термінал 2
cd newbornk-mcp
export ANTHROPIC_API_KEY=sk-ant-...
export SHOPIFY_ADMIN_TOKEN=shpat_...
export SHOPIFY_DOMAIN=newbornk-com.myshopify.com
.venv/bin/python sampling_client.py
```

### Доступ до агента

```bash
kubectl port-forward svc/kagent-ui 8080:8080 -n kagent
# → http://localhost:8080 → newbornk-agent
```

**Команди для агента:**
- `Update SEO for UVEX Blaze` — знайде товар і оновить SEO в Shopify
- `Show me products without SEO` — список товарів без SEO
- `Show me sales analytics` — аналітика + рекомендації

---

## Лабораторна №4 — A2A Protocol

**Мета:** Ознайомитись з A2A специфікацією, реалізувати Agent Card.

### Research

Документ: [research/a2a-protocol.md](research/a2a-protocol.md)

**Ключові концепти:**
- **Agent Card** — JSON паспорт агента (name, skills, capabilities, url)
- **Well-Known URI** — `/.well-known/agent.json` для discovery
- **Task** — одиниця роботи між агентами (submitted → working → completed)
- **JSON-RPC 2.0** — транспортний протокол

### Agent Card newbornk-agent

```bash
kubectl port-forward svc/kagent-controller 8083:8083 -n kagent
curl http://localhost:8083/api/a2a/kagent/newbornk-agent/.well-known/agent.json
```

Відповідь містить 3 skills: `seo-automation`, `sales-analytics`, `product-management`

### Inventory — AI ресурси кластера

```bash
kubectl get agents,remotemcpservers,modelconfigs -n kagent
```

| Тип | Кількість | Приклади |
|-----|-----------|---------|
| Agents | 13 | k8s-agent, helm-agent, devops-agent, newbornk-agent |
| RemoteMCPServers | 3 | kagent-tool-server, kagent-grafana-mcp, newbornk-mcp |
| ModelConfigs | 3 | Anthropic, Gemini, OpenAI |

---

## Встановлення та запуск

### Передумови

```bash
# Інструменти
brew install kind kubectl helm flux
npm install -g @modelcontextprotocol/inspector
```

### Кластер

```bash
kind create cluster
```

### agentgateway

```bash
# Secrets
kubectl create secret generic agentgateway-secret \
  --from-literal=ANTHROPIC_API_KEY=sk-ant-... \
  --from-literal=GEMINI_API_KEY=AIza...

# Deploy
helm install agentgateway ./helm/agentgateway
```

### kagent

```bash
helm install kagent-crds oci://ghcr.io/kagent-dev/kagent/helm/kagent-crds -n kagent --create-namespace
helm install kagent oci://ghcr.io/kagent-dev/kagent/helm/kagent -n kagent
kubectl apply -f kagent/model-config.yaml
```

### Flux GitOps

```bash
flux install
flux create source git airel \
  --url=https://github.com/DimitryRd/AIReliability \
  --branch=master
flux create kustomization airel \
  --source=airel \
  --path=./flux
```

### newbornk-mcp

```bash
# Secret
kubectl create secret generic newbornk-shopify \
  --from-literal=SHOPIFY_ADMIN_TOKEN=shpat_... \
  --from-literal=SHOPIFY_DOMAIN=newbornk-com.myshopify.com \
  -n kagent

# Build і deploy
cd newbornk-mcp
docker build -t newbornk-mcp:latest .
kind load docker-image newbornk-mcp:latest
kubectl apply -f k8s/
```

---

## Доступ до UI

| Сервіс | Команда | URL |
|--------|---------|-----|
| agentgateway Admin | `kubectl port-forward svc/agentgateway 15000:15000` | http://localhost:15000/ui/ |
| kagent UI | `kubectl port-forward svc/kagent-ui 8080:8080 -n kagent` | http://localhost:8080 |
| Flux UI | `kubectl port-forward svc/flux-operator 9080:9080 -n flux-system` | http://localhost:9080 |
| A2A Controller | `kubectl port-forward svc/kagent-controller 8083:8083 -n kagent` | http://localhost:8083 |

---

## Технічний стек

| Категорія | Технологія |
|-----------|-----------|
| Orchestration | Kubernetes (kind) |
| Package Manager | Helm |
| GitOps | Flux |
| LLM Gateway | agentgateway v1.0.0-rc.2 |
| Agent Framework | kagent v0.7.23 |
| LLM Providers | Anthropic Claude, Google Gemini |
| MCP Protocol | Python FastMCP |
| Data Source | Shopify Admin API |
| Language | Python 3.12 |
| Container | Docker |

---

## Скрінкасти

| Файл | Опис |
|------|------|
| `screencasts/` | Демонстрація роботи інфраструктури |
| `newbornk-mcp/demoSampling#2.cast` | MCP Sampling demo |
