# LEAD MACHINE — Diario de Progresso

> Sua empresa de agentes IA para captacao de leads sob demanda.
> Voce da o comando. Agentes executam.

---

## O que e este projeto

Um sistema onde voce digita um comando em linguagem natural e seus agentes IA saem buscando leads em todas as plataformas que voce mandar.

**Exemplo de comando:**
> "Preciso de leads para clinica odontologica que faz harmonizacao facial em Maringa-PR. Buscar no Instagram, X, Google e Reddit."

**O que acontece:**
1. CEO Agent interpreta: nicho, servico, cidade, plataformas
2. Cria tasks e distribui para agentes especializados
3. Cada agente busca na sua plataforma em paralelo
4. Qualificador classifica leads (quente/morno/frio)
5. Enriquecedor busca email, telefone, WhatsApp
6. Voce recebe a lista pronta

**Funciona para qualquer nicho:** dentistas, nutricionistas, franquias, academias, clinicas de estetica, advogados, imobiliarias, etc.

---

## Estrutura de Arquivos

```
C:/projetos/paperclip/
│
├── paperclip/                    # Repo Paperclip (backend, upstream)
│   ├── server/                   # API REST + orquestracao
│   ├── ui/                       # Frontend React original
│   ├── packages/                 # DB, shared, adapters, plugins
│   ├── cli/                      # CLI onboarding
│   └── doc/                      # Docs do projeto
│
├── dashboard/
│   └── index.html                # NOSSO FRONTEND — Lead Machine
│
├── SCRAPER-ORCHESTRATION-GUIDE.md  # Guia de orquestracao para leads
├── FERRAMENTAS.md                  # Comparativo completo de ferramentas e APIs
├── .env.example                    # Todas as API keys necessarias
└── PROGRESSO.md                    # << ESTE ARQUIVO
```

---

## Seus Agentes (Funcionarios)

| Agente | Funcao | Adapter | Status |
|--------|--------|---------|--------|
| **CEO** | Interpreta seus comandos, distribui tarefas | claude_local | Implementado no frontend |
| **CTO** | Monitora scrapers, detecta falhas | claude_local | Implementado no frontend |
| **Agent Instagram** | Busca hashtags, posts, perfis | process | Implementado no frontend |
| **Agent X/Twitter** | Busca tweets, replies, conversas | process | Implementado no frontend |
| **Agent Google** | Google Search + Maps, negocios locais | process | Implementado no frontend |
| **Agent Reddit** | Subreddits, posts, indicacoes | process | Implementado no frontend |
| **Agent LinkedIn** | Profissionais, empresas, decisores | process | Implementado no frontend |
| **Agent Facebook** | Grupos, paginas, comentarios | process | Implementado no frontend |
| **Agent TikTok** | Videos, comentarios, perfis | process | Implementado no frontend |
| **Qualificador** | Classifica leads quente/morno/frio | claude_local | Implementado no frontend |
| **Enriquecedor** | Busca email, telefone, WhatsApp | process | Implementado no frontend |

---

## Cronologia

### DIA 1 — 14/04/2026

#### Fase 1: Estudo da Arquitetura Paperclip — CONCLUIDO

- [x] Clonar repo `paperclipai/paperclip`
- [x] Estudar 65+ services do backend
- [x] Mapear 30+ rotas da API
- [x] Entender heartbeat loop (15 etapas)
- [x] Entender adapters (process, http, claude_local)
- [x] Entender budgets, routines, plugins, approvals
- [x] Entender modelo de dados (65+ tabelas)

**Descobertas chave:**
- Paperclip orquestra, nao executa
- Heartbeat e o ciclo central: trigger → checkout → adapter → custo → resultado
- Adapters sao plugaveis (qualquer script vira um agente)
- Budget enforcement pausa agente automaticamente
- Routines com cron + timezone

#### Fase 2: Documentacao — CONCLUIDO (REFEITO)

- [x] Criar guia de orquestracao
- [x] ~~Guia com exemplos de e-commerce~~ ERRO — removido
- [x] Guia refeito focado em LEAD GENERATION
  - Fluxo: comando → CEO → agentes por plataforma → qualificacao → enriquecimento
  - Ferramentas por plataforma (gratuitas e pagas)
  - Estrutura de dados do lead
  - Classificacao (quente/morno/frio)
  - Exemplos de comandos reais
  - Conexao com Paperclip API

#### Fase 3: Dashboard Frontend — CONCLUIDO (REFEITO)

- [x] ~~Dashboard de scraping e-commerce~~ ERRO — removido
- [x] Dashboard refeito: **Lead Machine**

**Paginas implementadas:**

| Pagina | O que faz |
|--------|-----------|
| **Central de Comando** | Campo de texto para dar comandos. KPIs (total leads, quentes, mornos, rodando, com contato). Status dos agentes. Atividade recente. Historico de comandos. |
| **Leads Coletados** | Tabela com todos os leads. Filtros por temperatura e plataforma. Exportar CSV. Nome, fonte, evidencia, cidade, score, contato. |
| **Agentes** | Cards de cada agente com descricao, adapter, status, plataforma. |
| **Tarefas** | Kanban com 3 colunas (Pendente, Executando, Concluido). Tasks criadas automaticamente pelo CEO. |
| **Atividades** | Timeline completa de tudo que aconteceu. |
| **Config** | API keys, proxies, tokens (Hunter.io, Apify). |

**Funcionalidades:**
- [x] Campo de comando com Enter para enviar
- [x] Parser de linguagem natural (extrai nicho, cidade, plataformas)
- [x] CEO processa e cria tasks automaticamente
- [x] Agentes mudam status para "running" durante execucao
- [x] Leads gerados por plataforma com evidencias realistas
- [x] Qualificador classifica em quente/morno/frio com score
- [x] Enriquecedor adiciona email e telefone
- [x] Filtros por temperatura e plataforma
- [x] Exportar leads em CSV
- [x] Notificacoes toast
- [x] Timeline de atividades em tempo real

**Correcao importante (Dia 1):**
O primeiro dashboard e guia foram feitos com exemplos de Mercado Livre / e-commerce. Isso foi um ERRO — o usuario quer captacao de leads para negocios locais (dentistas, nutricionistas, franquias). Tudo foi refeito do zero com foco correto.

---

#### Fase 4: Pesquisa de Ferramentas e APIs — CONCLUIDO

- [x] Pesquisar Apify actors para cada plataforma (55+ actors catalogados)
- [x] Pesquisar ferramentas pagas (Firecrawl, SerpAPI, BrightData, ScrapingBee, Hunter, Apollo, Snov, PhantomBuster)
- [x] Pesquisar ferramentas gratuitas (Instaloader, Tweepy, PRAW, Playwright, googlesearch, twscrape)
- [x] Criar `.env.example` com TODAS as variaveis necessarias
- [x] Criar `FERRAMENTAS.md` com comparativo completo
- [x] Definir 3 opcoes de stack (gratis / ideal / profissional)
- [x] Definir prioridade de contas para criar

**Descobertas chave:**
- **Apollo.io** tem o melhor free tier: 10.000 emails/mes GRATIS (Hunter da 25, Snov da 50)
- **Google Places API** da $200/mes de credito gratis (~11.000 buscas)
- **PRAW (Reddit)** e totalmente gratis, 60 req/min, sem limite mensal
- **Apify** tem actors prontos pra tudo — $5/mes de creditos gratis
- **Twitter/X free tier e inutil** pra lead gen (nao permite buscar tweets)
- **LinkedIn e o mais arriscado** — risco de ban + processo judicial
- Stack ideal custa ~$23/mes e cobre TODAS as plataformas

**Arquivos criados:**
- `.env.example` — todas as API keys com instrucoes de onde pegar
- `FERRAMENTAS.md` — comparativo completo de 20+ ferramentas

---

## Proximos Passos

### Fase 5: Criar Contas e Configurar APIs

- [ ] Criar conta Apollo.io (10.000 emails/mes gratis)
- [ ] Criar conta Apify (scrapers prontos)
- [ ] Ativar Google Places API ($200/mes gratis)
- [ ] Criar Reddit App (PRAW — 2 minutos)
- [ ] Criar conta SerpAPI (100 buscas gratis)
- [ ] Criar conta Hunter.io (25 buscas gratis)
- [ ] Criar conta Firecrawl (500 paginas gratis)
- [ ] Copiar .env.example para .env e preencher
- [ ] Instalar dependencias Python

### Fase 6: Criar Scripts dos Agentes (Python)

- [ ] Script Google Maps (Apify crawler-google-places + Google Places API)
- [ ] Script Instagram (Apify instagram-scraper + Instaloader fallback)
- [ ] Script Reddit (PRAW)
- [ ] Script Facebook (Apify facebook-pages-scraper)
- [ ] Script TikTok (Apify clockworks/tiktok-scraper)
- [ ] Script X/Twitter (Apify twitter-scraper)
- [ ] Script Enriquecedor (Apollo.io + Hunter.io + contact-info-scraper)
- [ ] Qualificador via Claude (claude_local)
- [ ] Script LinkedIn (Apify — ultimo, mais arriscado)

### Fase 7: Conectar ao Backend Paperclip

- [ ] Subir Paperclip server (`pnpm dev`)
- [ ] Criar company "Lead Machine" via API real
- [ ] Criar os 11 agentes via API com adapter configs reais
- [ ] Dashboard consome API real (fetch → localhost:3100)
- [ ] Comando cria issue real no Paperclip
- [ ] Heartbeat executa scripts de verdade
- [ ] WebSocket para status em tempo real

### Fase 8: Primeiro Comando Real End-to-End

- [ ] Escolher nicho real para testar
- [ ] Executar comando no sistema
- [ ] Verificar leads coletados de verdade
- [ ] Validar qualidade dos leads
- [ ] Ajustar scrapers conforme resultado

### Fase 9: Escalar

- [ ] Multiplos nichos simultaneos
- [ ] Rotinas automaticas (cron)
- [ ] Alertas por email/Telegram
- [ ] Deploy (Docker)
- [ ] Plugin de CRM (salvar leads em planilha/banco)

---

## Ferramentas — Stack Definida (Opcao Ideal ~$23/mes)

| Ferramenta | Para que | Free Tier | Status |
|------------|----------|-----------|--------|
| **Apify** | Scrapers prontos (IG, FB, TikTok, Maps) | $5/mes creditos | Criar conta |
| **Apollo.io** | Enriquecimento (email, telefone) | 10.000 emails/mes | Criar conta |
| **Google Places API** | Negocios locais | $200/mes gratis | Ativar no GCloud |
| **PRAW** | Reddit | 60 req/min, ilimitado | Criar Reddit App |
| **SerpAPI** | Google Search | 100 buscas/mes | Criar conta |
| **Hunter.io** | Email por dominio | 25 buscas/mes | Criar conta |
| **Firecrawl** | Scraping de websites | 500 paginas/mes | Criar conta |
| **Instaloader** | Instagram (fallback) | Gratis | `pip install` |
| **Playwright** | Browser automation | Gratis | `pip install` |
| **duckduckgo-search** | Busca web sem bloqueio | Gratis | `pip install` |

Ver detalhes completos em `FERRAMENTAS.md`

---

## Decisoes Tecnicas

| Data | Decisao | Motivo |
|------|---------|--------|
| 14/04 | Paperclip como control plane | Orquestracao atomica, budget, audit trail |
| 14/04 | Dashboard HTML puro | Independente, abre direto no browser |
| 14/04 | Adapter process para scrapers | Roda qualquer script Python/Node |
| 14/04 | Adapter claude_local para CEO/Qualificador | Precisam de raciocinio, nao so execucao |
| 14/04 | CORRECAO: foco em leads, nao e-commerce | O projeto e captacao de clientes para negocios locais |
| 14/04 | Apollo.io como enriquecedor principal | 10.000 emails/mes gratis, melhor free tier do mercado |
| 14/04 | Apify como scraper principal | Actors prontos pra todas as plataformas, pay-per-use |
| 14/04 | Google Places API pra negocios locais | $200/mes gratis do Google, dados completos |
| 14/04 | PRAW pra Reddit | Totalmente gratis, API mais generosa |
| 14/04 | Stack ideal ~$23/mes | Cobre TODAS plataformas com melhor custo-beneficio |

---

## Como Usar Este Documento

1. **Antes de cada sessao** → leia "Proximos Passos"
2. **Durante** → marque [x] no que concluir
3. **Ao final** → adicione nova entrada na Cronologia
4. **Decisao importante** → registre na tabela

---

### DIA 2 — 15/04/2026

#### Fase 5: Primeiro Comando Real — Leads de Harmonizacao Facial em Maringa — CONCLUIDO

- [x] Busca real no Google por clinicas e profissionais
- [x] WebFetch nos sites das clinicas para extrair contato completo
- [x] Busca no Doctoralia por profissionais verificados
- [x] Busca no GuiaSaudeCidades por especialistas
- [x] Busca no Instagram por perfis de profissionais
- [x] Extração de depoimentos REAIS de pacientes
- [x] Compilacao em `LEADS-HARMONIZACAO-MARINGA.md`

**Resultados:**
- 21 leads B2B (clinicas/profissionais) com telefone, WhatsApp, email, Instagram, endereco
- 12 leads B2C (pacientes que demonstraram interesse) com nome, evidencia, temperatura
- 5 clinicas com dados COMPLETOS (telefone + WhatsApp + email + Instagram + endereco)
- 8 perfis de Instagram mapeados (incluindo 1 com 27k seguidores)
- Depoimentos reais de pacientes satisfeitos extraidos

**Fontes utilizadas:** Google Search, Doctoralia, GuiaSaudeCidades, sites das clinicas (WebFetch), Instagram

---

#### Fase 5b: Criar Contas e Configurar APIs — CONCLUIDO

- [x] Apify (ja tinha token configurado)
- [x] Apollo.io — 10.000 emails/mes gratis (key via header, NAO URL)
- [x] Google Places API (New) — $200/mes gratis ativado no Google Cloud
- [x] SerpAPI — 100 buscas/mes gratis
- [x] Hunter.io — 25 buscas + 50 verificacoes/mes gratis
- [x] Firecrawl — 500 paginas/mes gratis
- [ ] Reddit — ADIADO (exige formulario de aprovacao, demora dias)
- [x] Instagram (ja tinha login configurado)
- [x] `.env` preenchido com todas as keys

**Decisoes:**
- Reddit API adiada — usaremos Apify como fallback
- Apollo.io exige key no HEADER (descontinuando via URL)
- Google Places API (New) ativada (versao antiga sendo descontinuada)

---

#### Fase 6: Scripts dos Agentes Python — CONCLUIDO

- [x] `agents/base.py` — modulo compartilhado (env, logging, DB com file locking, scoring, formato unificado, dedup, migracao)
- [x] `agents/agent_instagram.py` — Apify instagram-scraper (profiles + hashtags)
- [x] `agents/agent_google_maps.py` — Google Places API (New) + SerpAPI + Apify fallback
- [x] `agents/agent_facebook.py` — Apify facebook-pages-scraper (paginas + comentarios)
- [x] `agents/agent_tiktok.py` — Apify clockworks/free-tiktok-scraper
- [x] `agents/agent_twitter.py` — Apify twitter-scraper (fragil, error handling reforçado)
- [x] `agents/agent_enricher.py` — Apollo.io (header) + Hunter.io + Firecrawl + Apify contact-scraper
- [x] `agents/agent_qualifier.py` — Re-scoring multi-fator + cross-platform
- [x] `agents/requirements.txt` — apify-client, requests, python-dotenv, portalocker
- [x] Todos os imports testados e funcionando
- [x] Qualifier testado com leads reais — scores coerentes

**Arquitetura:**
- Formato unificado de lead (superset dashboard + leads-db.json)
- Migracao automatica de leads antigos
- IDs globais unicos (corrigido bug de IDs duplicados)
- Dedup por plataforma:user:url
- Parametros via CLI (--query, --city) OU env vars (SEARCH_QUERY, CITY) para Paperclip
- Saida JSON no stdout (Paperclip captura), logs no stderr + arquivo
- File locking com portalocker (execucao paralela segura)
- Cascata de fallback (Google Places → SerpAPI → Apify)

**Decisoes:**
- lead_machine.py mantido como esta (backward compat, DMs)
- Cada agente foca em descoberta, DMs separado
- Qualifier com peso dominante no texto (85pts intencao direta) — contato e bonus
- Twitter marcado como fragil — nao falha fatal se sem resultado

---

#### Fase 7: Conectar ao Backend Paperclip — CONCLUIDO

- [x] Paperclip server rodando em `http://localhost:3100` (embedded PostgreSQL)
- [x] Company "Lead Machine" criada via API (ID: `cdca3499-facb-45f8-84de-ae3814ba19cb`)
- [x] 9 agentes registrados via API:
  - CEO (claude_local) + CTO (claude_local)
  - Agent-Instagram, Agent-Google, Agent-Facebook, Agent-TikTok, Agent-Twitter (process)
  - Qualificador + Enriquecedor (process)
- [x] Teste end-to-end: wakeup do Agent-Google → 19 negocios encontrados via Google Places API → leads-db.json atualizado
- [x] `serve.py` — server local que serve dashboard + leads-db.json com CORS
- [x] Dashboard conectado ao Paperclip API:
  - Sync automatico de status dos agentes a cada 10s
  - Sync automatico de leads do leads-db.json
  - Comandos executam wakeups REAIS via API
  - Fallback para modo simulado quando Paperclip offline
  - Indicador visual "Paperclip Online" / "Modo Offline"

**Como rodar:**
```bash
# Terminal 1: Paperclip server
cd paperclip && pnpm dev

# Terminal 2: Dashboard + Leads API
python serve.py

# Abrir: http://localhost:8080
```

**Decisoes:**
- Dashboard roda em porta separada (8080) com CORS para buscar leads do filesystem
- Modo dual: online (Paperclip real) e offline (simulado) — sem breaking change
- Agent-Google testado end-to-end com sucesso (19 leads B2B em 1.6s)

---

#### Fase 8: Teste Completo End-to-End — CONCLUIDO

- [x] Todos os 5 scrapers disparados via Paperclip API com parametros reais
- [x] Resultados:
  - Google Maps: 34 leads B2B com telefone, rating, website
  - TikTok: 15 leads (perfis de profissionais)
  - Instagram: 13 leads (comentarios com intencao)
  - Facebook: actor rodou mas query retornou pouco
  - Twitter: actor corrigido (apidojo/tweet-scraper), tweets sem intencao de compra
- [x] Qualificador rodou nos 76 leads — scoring B2B corrigido (negocios Google = minimo morno)
- [x] Enriquecedor rodou nos top leads quentes (Apollo + Hunter + Firecrawl)
- [x] Correcao: "valor/preco" = lead quente (score 85+)
- [x] CORS resolvido: serve.py agora faz proxy para Paperclip API (mesma origem)
- [x] Comando real pelo dashboard: digita → agentes executam → leads aparecem
- [x] Bug fix: scroll do kanban nao reseta mais (preserva posicao no auto-sync)

**Dashboard — Melhorias Visuais:**
- [x] Kanban: foto real via unavatar.io, texto de evidencia em branco, cores por plataforma
- [x] Google Maps: estrelas visuais, nome truncado, telefone em verde
- [x] Separacao Pessoas vs Empresas:
  - Seletor [Pessoas] [Empresas] [Ambos] na Central de Comando
  - Abas dedicadas no menu lateral com badges
  - Tabelas filtradas por tipo, exportacao CSV independente
  - KPIs separados: Pessoas | Empresas | Quentes | Agentes | Com Contato
- [x] Links clicaveis nos perfis das pessoas
- [x] Campo `tipo` (pessoa/empresa) adicionado ao formato de lead

**Resultado final Dia 2:**
- 76 leads reais (28 pessoas + 48 empresas) de 3 plataformas
- 7 agentes testados end-to-end via Paperclip
- Dashboard profissional conectado ao backend real
- Sistema funcional para qualquer nicho/cidade

**Decisoes:**
- serve.py na porta 8081 (proxy resolve CORS sem mexer no Paperclip)
- Pessoas = redes sociais (Instagram, Facebook, TikTok) / Empresas = Google Maps
- Score de preco igualado ao de intencao direta (ambos quentes)
- Twitter usa actor `apidojo/tweet-scraper` (o oficial nao existe)

---

## Proximos Passos — Fase 9: Escalar

- [x] Criar `start.bat` para subir tudo com um clique
- [x] Alertas Telegram — notificar lead quente novo
- [x] Rotinas automaticas (cron) — scraping a cada X horas
- [x] Multi-nicho — salvar buscas e rodar em paralelo
- [ ] Envio de DM automatico — ADIADO (risco de ban, manual e mais seguro por ora)
- [ ] Deploy Docker — ADIADO (so faz sentido quando for hospedar em servidor)

---

### DIA 3 — 18/04/2026

#### Fase 9a: start.bat + stop.bat — CONCLUIDO E TESTADO

- [x] `start.bat` — sobe Paperclip em janela separada, aguarda API ficar UP (curl/poll
      a cada 1s, ate 120s), sobe `serve.py` em outra janela, abre dashboard no browser.
- [x] `stop.bat` — fecha as 2 janelas por titulo e libera portas 3100/8081.
- [x] Checagem de deps no start (pnpm/node/python/curl) com mensagem clara se faltar.
- [x] Log completo em `start.log` (ignorado no git) + `pause` no final para nao fechar
      janela antes do usuario ler o output.
- [x] Testado end-to-end: Paperclip 3100 UP + dashboard 8081 UP + proxy funcionando.

**Como usar:**

No PowerShell:
```
cd C:\projetos\paperclip
.\start.bat
```
(PowerShell exige o prefixo `.\` — se digitar so `start.bat` nao acha.)

No cmd normal ou duplo-clique no explorer: apenas `start.bat`.

**Bugs corrigidos durante o teste:**
- `timeout /t` do Windows conflita com `timeout` do Git Bash no PATH — trocado por
  `ping -n 2 127.0.0.1 >nul` (trick classico sleep em batch).
- Janela fechava antes do `pause` em alguns caminhos — adicionado `pause` no fim do
  sucesso tambem e delayed expansion (`!VAR!`) para loops de espera.

#### Fase 9b: Alertas Telegram — CONCLUIDO

- [x] `agents/telegram_notifier.py` — modulo standalone (so urllib, sem dependencia nova).
  - `send_message(text)` - POST pro Bot API
  - `notify_hot_lead(lead)` - formata lead quente em HTML
  - `notify_batch_summary(stats)` - resumo pos-qualificacao
  - `is_configured()` - checa se TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID estao no .env
  - `--test` - CLI pra enviar mensagem de teste
- [x] Integracao no `agent_qualifier.py`:
  - Ao qualificar, detecta leads que ficaram quentes (score >=80) e ainda nao foram
    notificados (flag `notified_at`).
  - Dispara notificacao individual por lead + resumo do batch.
  - Marca `notified_at` no lead pra nao duplicar em runs futuras.
- [x] `.env.example` + `.env` atualizados com `TELEGRAM_BOT_TOKEN` e `TELEGRAM_CHAT_ID`.
- [x] Testado: qualifier roda sem erro mesmo sem bot configurado (skip gracioso).

**Como configurar (2 minutos):**
1. No Telegram, procure `@BotFather` e rode `/newbot`. Escolha nome e username. Ele
   retorna um token tipo `123456789:ABCdef...`.
2. Procure seu bot no Telegram e mande `/start`.
3. Abra `https://api.telegram.org/bot<TOKEN>/getUpdates` no browser e copie o numero
   em `"chat":{"id": ...}`.
4. Cole no `.env`:
   ```
   TELEGRAM_BOT_TOKEN=123456789:ABCdef...
   TELEGRAM_CHAT_ID=123456789
   ```
5. Teste: `python agents/telegram_notifier.py --test`

**Decisoes:**
- Zero dependencia nova (urllib nativo) pra nao poluir requirements.
- Notificacao so no qualifier (1 ponto central) em vez de cada scraper — evita
  duplicatas e so alerta DEPOIS do scoring real.
- Flag `notified_at` idempotente: rodar qualifier 10x nao manda 10 notificacoes.

---

#### Fase 9c: Buscas salvas + Runner automatico + UI — CONCLUIDO

Sistema agora roda sozinho 24/7 sem intervencao manual. Voce cadastra buscas, define
intervalo, ativa, e o runner dispara automaticamente quando vence o proximo run.

**Arquivos novos:**

- `agents/searches.py` — modulo de gestao do `leads-export/searches.json`
  (CRUD + validacao + compute de `next_run` + `trigger_now` pra "rodar agora").
- `agents/runner.py` — daemon que loopa a cada 60s:
  - Pega buscas ATIVAS com `next_run` vencido
  - Dispara todos os agentes em paralelo via `ThreadPoolExecutor` + `subprocess`
    (passa `SEARCH_QUERY`, `CITY`, `NICHO` via env vars)
  - Quando todos terminam: roda qualifier (que ja dispara Telegram pros quentes)
  - Atualiza `last_run`, `next_run`, `last_status`, `last_stats` na busca
  - Flags: `--once` (1 iteracao), `--tick 30` (segundos entre checks), `--dry-run`
- `serve.py` refatorado:
  - Novos endpoints REST para buscas salvas (nao colidem com proxy Paperclip):
    - `GET /api/local/searches` - lista
    - `GET /api/local/searches/:id` - detalhe
    - `POST /api/local/searches` - cria (valida nome, query, plataformas, intervalo 1-168h)
    - `PATCH /api/local/searches/:id` - atualiza
    - `DELETE /api/local/searches/:id` - remove
    - `POST /api/local/searches/:id/run` - forca "rodar agora"
  - `DELETE` method adicionado (antes so GET/POST/PATCH)
- `dashboard/index.html`:
  - Nova aba **Buscas Salvas** no menu lateral com badge de buscas ativas
  - Lista de cards com nome, status, plataformas, query, cidade, nicho, intervalo,
    last_run, next_run, last_stats
  - Botoes por busca: Rodar agora / Pausar / Ativar / Editar / Remover
  - Modal de "Nova Busca" / "Editar Busca" (nome, query, cidade, nicho,
    checkboxes de plataformas, intervalo em horas, ativa/pausada)
  - Auto-sync a cada 10s (mesmo ciclo dos agentes e leads)
- `start.bat` — 4a janela "Lead Machine Runner" sobe junto (`python agents/runner.py`).
- `stop.bat` — mata tambem a janela do Runner.

**Testado end-to-end:**

- CRUD completo via curl (POST, GET, PATCH, DELETE) - todos 200
- Runner executou busca `dentista` em `Maringa-PR` via Google Maps:
  - Google agent: OK em 2.2s (rc=0)
  - Qualifier: OK (rodou Telegram internamente pros quentes novos)
  - `last_run`, `next_run` (+24h), `last_status=success` atualizados corretamente
- UI: abas navegam, badge de ativas atualiza, modal cria/edita, rodar agora funciona.

**Decisoes:**

- Buscas vivem em `searches.json` (nao no Paperclip) — evita acoplamento e fica
  portavel. File locking com `portalocker` pra runner + UI coexistirem.
- Endpoints em `/api/local/*` para nao colidir com o proxy `/api/*` do Paperclip.
- Runner e um processo separado (1 janela de terminal). Se voce fechar, o resto do
  sistema continua funcionando pra operacao manual via dashboard.
- `next_run = now` em criacao — roda na proxima iteracao (feedback imediato).
- `trigger_now` so muda `next_run` pra agora e forca `ativa=true` — runner pega.

**Como usar a partir de agora (setup diario):**

```
C:\projetos\paperclip\start.bat     # sobe tudo
# abre dashboard → aba "Buscas Salvas" → cria tuas buscas
# sai fazer outras coisas — runner trabalha sozinho
# leads quentes caem direto no teu Telegram
C:\projetos\paperclip\stop.bat      # quando quiser parar
```

---

### Status Final do Projeto

Sistema **completo e funcional**. Tudo que estava na Fase 9 esta entregue, exceto:

- **DM automatica**: adiada deliberadamente. Risco de ban da conta do Instagram
  e o `disparar-instagram.html` manual ja resolve com mais controle.
- **Docker**: adiado. Faz sentido so quando for hospedar em servidor 24/7 remoto.
  Hoje roda local.

Proximas direcoes possiveis (quando fizer sentido):

- [ ] Relatorios semanais por email/Telegram (resumo de leads coletados)
- [ ] Metricas: tempo medio de scraping por plataforma, taxa de conversao
- [ ] Export CRM (planilha automatica por busca)
- [ ] Webhook pra enviar leads quentes direto pro CRM externo (HubSpot, Pipedrive)
- [ ] Rotacao de proxy quando detectar rate limit
- [ ] UI de "testar busca" (roda 1 vez e mostra preview antes de salvar)

---

*Ultima atualizacao: 18/04/2026 — Dia 3 (Fase 9 COMPLETA: start.bat + Telegram + Runner + UI Buscas)*
