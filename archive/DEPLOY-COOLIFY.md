# DEPLOY COOLIFY — Lead Machine (dashboard + runner)

> Documento de planejamento. Nada foi criado/alterado no repo ainda.
> Confirme/edite os campos **A DECIDIR** antes de executar.

---

## 1. Escopo confirmado

| Item | Decisão |
|---|---|
| O que sobe | **Agentes Python + Dashboard + Runner** |
| Paperclip Node (container 3100) | **Não sobe** |
| Objetivo | Dashboard acessível online **+** runner rodando 24/7 na VPS |
| Dados | Começar do zero (sem migrar `leads-db.json` atual) |
| Domínio | **A DECIDIR** (ex: `leads-machine.visualizemais.com.br`) |

**Por que não precisa do Paperclip Node:** o dashboard (`dashboard/index.html`) só chama `/api/local/searches*` — todas essas rotas são atendidas pelo próprio `serve.py`. O proxy `/api/*` → `localhost:3100` nunca é acionado em uso normal.

---

## 2. Arquitetura na VPS

```
                    ┌─────────────────────────────┐
Coolify Proxy ─────►│  Container: lead-machine    │
(Traefik, HTTPS)    │                             │
                    │  ┌──────────┐  ┌─────────┐ │
                    │  │ serve.py │  │runner.py│ │
                    │  │  :8081   │  │  loop   │ │
                    │  └────┬─────┘  └────┬────┘ │
                    │       └──────┬──────┘       │
                    │              ▼              │
                    │      /data (volume)         │
                    │   ├─ leads-export/          │
                    │   │   ├─ leads-db.json      │
                    │   │   └─ comments.db        │
                    │   └─ agents/searches.json   │
                    └─────────────────────────────┘
```

- **1 container**, 2 processos gerenciados via `supervisord` (ou `honcho`/`s6`). Compartilham volume e variáveis de ambiente.
- **Volume persistente** `/data` montado em `/app/leads-export` + `/app/agents/searches.json`.
- **Porta exposta:** 8081 (Coolify liga HTTPS automaticamente via Let's Encrypt).

### Alternativa (se preferir separar)
- 2 services no mesmo `docker-compose.yml`: `dashboard` e `runner`, ambos com o mesmo volume.
- Vantagem: logs separados, restart independente.
- Desvantagem: mais 1 container pra gerenciar no Coolify.

**Recomendação:** 1 container + supervisord. Menos overhead, deploy mais simples.

---

## 3. PROBLEMA CRÍTICO: Autenticação

`serve.py` **hoje não tem autenticação nenhuma**. Subir como está = qualquer um na internet:
- Vê leads coletados (dados pessoais de prospects — LGPD)
- Cria/edita/roda buscas (queima custo de API Apify/SerpAPI)
- Lê `leads-db.json` completo via `/leads.json`

**Opções de gate (escolher 1):**

| Opção | Esforço | Como funciona |
|---|---|---|
| **A. Basic Auth no Traefik (Coolify)** | Baixo | Coolify tem label pra basic auth. Usuário/senha fixo. Nenhuma mudança no código. |
| **B. Token header no serve.py** | Médio | Adicionar header `Authorization: Bearer <token>` em todas rotas. Editar código + UI. |
| **C. Cloudflare Access** | Médio | Coloca Cloudflare na frente, Access gate por email/Google. Sem mudar código. |
| **D. Deixar público (SÓ SE)** | Zero | Inaceitável com dados de lead — descartar. |

**Sugerido:** Opção **A** (basic auth Traefik) pra MVP. Migrar pra C depois se tiver mais gente acessando.

**A DECIDIR:** qual opção + credenciais iniciais.

---

## 4. Arquivos a criar no repo

```
paperclip/
├── Dockerfile.leadmachine          ← NOVO (Python slim + supervisord)
├── docker-compose.coolify.yml      ← NOVO (referência; Coolify aceita)
├── deploy/
│   ├── supervisord.conf            ← NOVO (gerencia serve.py + runner.py)
│   └── entrypoint.sh               ← NOVO (copia .env, ajusta permissões)
└── .dockerignore                   ← NOVO (exclui node_modules, leads atuais)
```

### 4.1 `Dockerfile.leadmachine` (rascunho)

```dockerfile
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
      supervisor ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

COPY agents/requirements.txt /app/agents/requirements.txt
RUN pip install --no-cache-dir -r /app/agents/requirements.txt

# Copia só o que o Lead Machine precisa (sem paperclip/ Node)
COPY agents/ /app/agents/
COPY dashboard/ /app/dashboard/
COPY serve.py /app/serve.py
COPY deploy/supervisord.conf /etc/supervisor/conf.d/leadmachine.conf

# Volume pros dados persistentes
RUN mkdir -p /app/leads-export && chmod -R 755 /app

ENV DASHBOARD_PORT=8081 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8081

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/leadmachine.conf"]
```

### 4.2 `deploy/supervisord.conf` (rascunho)

```ini
[supervisord]
nodaemon=true
user=root
logfile=/dev/null
logfile_maxbytes=0

[program:dashboard]
command=python serve.py
directory=/app
autostart=true
autorestart=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0

[program:runner]
command=python agents/runner.py --tick 60
directory=/app
autostart=true
autorestart=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0
```

### 4.3 `docker-compose.coolify.yml` (referência pra colar no Coolify)

```yaml
services:
  leadmachine:
    build:
      context: .
      dockerfile: Dockerfile.leadmachine
    restart: unless-stopped
    ports:
      - "8081"
    volumes:
      - leadmachine_data:/app/leads-export
      - leadmachine_searches:/app/agents/searches.json
    environment:
      DASHBOARD_PORT: 8081
      # API keys: setar no painel Coolify (não commitar)
      APIFY_TOKEN: ${APIFY_TOKEN}
      SERPAPI_API_KEY: ${SERPAPI_API_KEY}
      FIRECRAWL_API_KEY: ${FIRECRAWL_API_KEY}
      GOOGLE_PLACES_API_KEY: ${GOOGLE_PLACES_API_KEY}
      APOLLO_API_KEY: ${APOLLO_API_KEY}
      HUNTER_API_KEY: ${HUNTER_API_KEY}
      TELEGRAM_BOT_TOKEN: ${TELEGRAM_BOT_TOKEN}
      TELEGRAM_CHAT_ID: ${TELEGRAM_CHAT_ID}
      # ...demais keys conforme .env.example

volumes:
  leadmachine_data:
  leadmachine_searches:
```

### 4.4 `.dockerignore` (rascunho)

```
paperclip/
node_modules/
__pycache__/
*.pyc
.env
leads-export/leads-db.json
leads-export/comments.db*
start.log
start_boot.out
video-lancamento/
*.tmp
.git/
```

---

## 5. Passos no Coolify (ordem)

### 5.1 Pré-requisitos na VPS
- [ ] Coolify já instalado e rodando (**confirmado** — visualizemais já usa)
- [ ] Domínio/subdomínio apontando pra IP da VPS (A record) — **A DECIDIR**
- [ ] Conta GitHub conectada no Coolify (ou usar Deploy Key SSH pro repo privado)

### 5.2 Criação do resource
1. Coolify → **New Resource** → **Public Repository** (ou Private, via GitHub App)
2. Repositório: `git@github.com:jaolito85-hash/lead-machine.git`
3. Branch: `main`
4. Build Pack: **Dockerfile** → apontar pra `Dockerfile.leadmachine`
5. Port Exposes: `8081`
6. Domínio: `<A DECIDIR>` → Coolify emite Let's Encrypt automático

### 5.3 Variáveis de ambiente (no painel Coolify)
Copiar do `.env.example` local e preencher com valores reais:
- `APIFY_TOKEN` (real, não dummy)
- `SERPAPI_API_KEY`
- `FIRECRAWL_API_KEY`
- `GOOGLE_PLACES_API_KEY`
- `APOLLO_API_KEY`
- `HUNTER_API_KEY`
- `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` (opcional — se quer notificações do runner produção separadas das locais, criar bot novo)
- `APOSTAS_*` (se for usar runner SeuBet também) — **A DECIDIR** se esse runner sobe aqui ou fica só local
- `DASHBOARD_PORT=8081`

**Todas as secrets marcar como "Is Build Time?" = Não** (devem ser só runtime).

### 5.4 Volumes persistentes
- [ ] `/app/leads-export` → volume nomeado `leadmachine_data`
- [ ] `/app/agents/searches.json` → volume nomeado `leadmachine_searches` (ou file mount)

Sem volume = toda redeploy apaga leads e buscas.

### 5.5 Auth (escolher e aplicar)
- Se **Opção A (basic auth)**: Coolify → Service → Advanced → Labels:
  ```
  traefik.http.middlewares.leadmachine-auth.basicauth.users=admin:$$apr1$$HASH
  traefik.http.routers.leadmachine.middlewares=leadmachine-auth
  ```
  (gerar hash com `htpasswd -nb admin SENHA`)

### 5.6 Deploy + smoke test
- [ ] Primeiro deploy → esperar build (~3-5min)
- [ ] Logs: `supervisord started` → `serve.py listening on 0.0.0.0:8081` → `runner iniciado`
- [ ] Acessar `https://<dominio>/` → dashboard carrega
- [ ] Basic auth prompt aparece (se opção A)
- [ ] Criar busca de teste → apertar "Rodar agora" → ver no log do runner
- [ ] Telegram recebe alerta (se configurado)

---

## 6. Pontos em aberto / A DECIDIR

Marcar aqui conforme definir:

- [ ] **Domínio final:** `________________`
- [ ] **Método de auth:** A (basic auth) / B (token) / C (Cloudflare Access)
- [ ] **Credenciais iniciais:** user=`_____` pass=`_____` (guardar em 1Password/similar)
- [ ] **Runner SeuBet:** sobe junto (via `START_APOSTAS_RUNNER=1`) ou fica só local?
- [ ] **Telegram:** reusar bot atual ou criar `lead-machine-prod-bot` separado?
- [ ] **Apify token:** reusar o da máquina local ou criar token dedicado pra VPS (rastrear custo separado)?
- [ ] **Branch de deploy:** `main` ou criar `production` como gate?
- [ ] **Backups:** Coolify tem backup automático de volume? Ou script cron `pg_dump`-style pra `leads-db.json`?
- [ ] **Limite de recursos:** CPU/RAM pro container (runner pode picar durante buscas paralelas)

---

## 7. Riscos & mitigações

| Risco | Mitigação |
|---|---|
| Leads vazados publicamente | Auth obrigatório (§3) antes do 1º deploy |
| Custos Apify/SerpAPI disparando | Token dedicado + limite no painel do provider + `APOSTAS_MVP_MAX_LEADS` |
| Volume corrompido em redeploy | Volume nomeado Coolify (não bind mount do build context) |
| `searches.json` em volume = lock em paralelo | `portalocker` já cuida (dep do requirements.txt) |
| Runner fica pra trás se crashar | `supervisord autorestart=true` |
| Container OOM em scrape pesado | Limit inicial 1GB RAM, monitorar e ajustar |
| Timezone do runner diferente | Setar `TZ=America/Sao_Paulo` no env |

---

## 8. Próximos passos (quando você liberar)

1. Você revisa este doc, anota ajustes (pontos §6 + qualquer outro)
2. Me devolve: "confirmado, subir como está" OU "muda X/Y/Z"
3. Eu crio os 4 arquivos do §4 no repo (commit separado, sem tocar em nada mais)
4. Você faz push + configura o resource no Coolify
5. Primeiro deploy + smoke test juntos

---

**Data do documento:** 2026-04-22
**Autor:** Claude (Lead Machine deploy planning)
**Versão:** 1 (pendente revisão do João)
