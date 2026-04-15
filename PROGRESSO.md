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

*Ultima atualizacao: 15/04/2026 — Dia 2 (Fase 5 concluida — primeiro comando real executado)*
