# BETS / APOSTAS — Export de Contexto

> Consolidação de **tudo** que existe sobre apostas esportivas / cassino no Paperclip (Lead Machine) — pronto pra portar pra outro projeto de bets.
> Gerado em 2026-04-22.

---

## 1. Cliente ativo: SeuBet (pilot comercial)

| Campo | Valor |
|---|---|
| Brand | **SeuBet** |
| Slug cliente | `seubet` |
| Operador legal | H2 LICENSED LTDA |
| Autorização | **SPA/MF 253/2025** |
| Domínio oficial | https://www.seu.bet.br/ |
| btag afiliado | **`2709913`** |
| Base do affiliate link | `https://www.seu.bet.br/affiliates/?btag=2709913` |
| UTM campaign | `seubet_br_pilot` |
| Budget do pilot | **USD 5.000** |
| Meta de leads (MVP) | **300** qualificados |
| Nicho | `apostas_esportivas` |

### Formato do link afiliado gerado por lead

```
https://www.seu.bet.br/affiliates/?btag=2709913
  &utm_source=<plataforma>          # instagram | tiktok | twitter | google
  &utm_medium=outreach
  &utm_campaign=seubet_br_pilot
  &utm_content=B-<id:05d>            # B-00001, B-00042, etc
```

**Regra de negócio:** só leads **hot** e **warm** recebem `affiliate_url`. Leads frios = sem link (função `is_eligible()` no `lead_system/utils/affiliate.py`).

---

## 2. Arquitetura atual (2 projetos interligados)

### 2.1 `lead_system` (produção — **onde acontece o pilot**)

- **URL:** https://leads.visualizemais.com.br/
- **Repo:** `github.com/jaolito85-hash/lead-system` (branch `master`)
- **Deploy:** Coolify auto-deploy no push pra master
- **Stack:** Flask + SQLAlchemy + SQLite (`data/leads.db`) + OpenAI **GPT-4.1-mini** + Apify
- **Local dev:** `C:/Users/Joao Marcos/lead_system/` (venv em `.venv/Scripts/python.exe`)
- **Bot Telegram:** `bot/seubet_bot.py` envia DMs automáticas a partir dos leads qualificados
- **Templates:** `index.html` (dashboard), `login.html`, `telegram.html`

#### API do lead_system
```
GET  /api/leads?temperature=hot&days_back=365&limit=50   # lista leads
GET  /api/leads/<id>                                      # detalhe
PATCH /api/leads/<id>/status                              # update status
GET  /api/dashboard/stats                                 # contadores
GET  /api/audiences                                       # 1036 audience profiles pra Meta Ads
POST /api/pipeline/run                                    # dispara pipeline manual
POST /api/telegram/send-dms                               # bot envia DMs automáticas
```

#### Schema Lead (`database/models.py`)
```
id, source_platform, source_url, author_username, author_display_name,
raw_text, temperature (hot|warm|cold|discard), score 0-100,
classification_reason, detected_intent, competitor_mentioned, sentiment,
urgency_level, best_contact_channel, contact_priority 1-10,
suggested_message, status, dm_sent, exported_to_meta,
affiliate_url (calculado on-the-fly), affiliate_id (B-NNNNN)
```

### 2.2 Paperclip / Lead Machine (local — `C:/projetos/paperclip/`)

- Camada de agentes IA + governance (ceo/cto/engineer roles)
- Hoje tem o sistema **Campanhas (Workspaces)** com 1 campanha ativa pra bets: **C-0003 Apostas Esportivas - Brasil**
- Dashboard Kanban glassmorphism com filtro por campanha/plataforma/tipo/busca textual
- Scraping via Apify (TikTok Data Extractor + TikTok Comments Scraper + Instagram Hashtag Scraper)
- Classificador heurístico + Claude Haiku opcional (fallback gratuito)

---

## 3. Variáveis de ambiente (`.env.example` — seção APOSTAS)

```bash
# ══════════════════════════════════════════════════════════════
# NICHO: APOSTAS ESPORTIVAS
# ══════════════════════════════════════════════════════════════

# ─── Identificação do cliente ───
APOSTAS_CLIENTE=seubet
APOSTAS_BRAND=SeuBet
APOSTAS_OPERATOR=H2 LICENSED LTDA
APOSTAS_OFFICIAL_DOMAIN=https://www.seu.bet.br/
APOSTAS_AFFILIATE_URL=https://www.seu.bet.br/affiliates/?btag=2709913
APOSTAS_UTM_CAMPAIGN=seubet_br_pilot
APOSTAS_OPERATOR_AUTH=SPA/MF 253/2025
APOSTAS_PILOT_BUDGET_USD=5000
APOSTAS_MVP_MAX_LEADS=300

# ─── Nicho específico ───
APOSTAS_NICHO=apostas_esportivas
# Outros: futebol_apostas, cassino_online, esports_betting

# ─── Perfis Instagram extras ───
APOSTAS_INSTAGRAM_PROFILES=
# Padrão (definido em base_apostas.py): bet365brasil_, betanobrasil, vaidebet_, etc.

# ─── Score mínimo para notificar no Telegram ───
APOSTAS_SCORE_MIN_NOTIF=80

# ─── Número máximo de leads por ciclo ───
APOSTAS_LIMIT_POR_AGENTE=50

# ─── Telegram separado (opcional) ───
APOSTAS_TELEGRAM_BOT_TOKEN=
APOSTAS_TELEGRAM_CHAT_ID=

# ─── Runner ───
START_APOSTAS_RUNNER=1
```

### Env vars legado no Coolify do `lead_system` (6 vars, NÃO mexer sem entender)

| Var | Usado por | Consequência se remover |
|---|---|---|
| `COMPANY_NAME` | Bot Telegram + GPT enricher | Quebra outreach |
| `AFFILIATE_LINK` | Bot Telegram + GPT enricher | Quebra outreach |
| `BONUS_OFFER` | Bot Telegram + GPT enricher | Quebra outreach |
| `APOSTAS_AFFILIATE_URL` | Dashboard (render affiliate_url por lead) | Degradação graciosa |
| `APOSTAS_UTM_CAMPAIGN` | Dashboard | Degradação graciosa |
| `APOSTAS_CLIENTE` | Dashboard | Degradação graciosa |

**Source of truth pra UTM/tracking:** `lead_system/utils/affiliate.py`

---

## 4. Classificador de intenção (heurística regex) — pronto pra copiar

### 4.1 Intent `apostador_ativo` — score 82 (lead quente)

Este intent é **específico pra bets**. Reconhece apostador engajado (já cliente do nicho, ótimo pra conversão/migração de casa).

```python
INTENT_PATTERNS = {
    "apostador_ativo": [
        # Resultado positivo (green) — apostador engajado
        r"\bdeu green\b", r"\bfoi green\b", r"\bmuito green\b",
        r"\bgreens\b", r"\bfechou green\b", r"\bgreen na\b", r"\bgreen em\b",
        r"\bestou no verde\b", r"\bt[oô] no verde\b",

        # Mercados e jargão técnico
        r"\bodds?\b", r"\bhandicap\b", r"\bcashout\b", r"\bcash out\b",
        r"\bunder\b.*(\d|gol|\.5|\.25)", r"\bover\b.*(\d|gol|\.5|\.25)",
        r"\bml(s)?\b.*(gols?|cartoes|escanteios)", r"\bambos marcam\b",
        r"\bescanteio\b", r"\bsimples\b.*aposta",
        r"\bmultipla\b", r"\bmult\b", r"\baposta multipla\b",
        r"\btiro\b.*odds?", r"\btiro\b.*(simples|multipla)",
        r"\bbanca\b.*(apost|bet|vai|cresc|turbin)",
        r"\bstake\b", r"\bstacando\b",

        # Casas específicas (apostador brasileiro conhece o mercado)
        r"\bbetano\b", r"\bbet365\b", r"\bpixbet\b", r"\bblaze\b",
        r"\bsportingbet\b", r"\bsuperbet\b", r"\bestrelabet\b", r"\bestrela bet\b",
        r"\bbrazino\b", r"\bkto\b", r"\brivalo\b", r"\bsportsbet\b",
        r"\baposta ganha\b", r"\bgalera bet\b", r"\bnovibet\b",
        r"\bbetfair\b", r"\bbetway\b", r"\b1xbet\b",

        # Saques/depósitos com verbo ativo (já é cliente)
        r"\bsaquei\b", r"\bdepositei\b", r"\bdeposita\w* ai\b",
        r"\bbanco ja caiu\b", r"\bcaiu rapido\b", r"\bpagou na hora\b",
        r"\bpagou rapido\b", r"\bpagou em\b.*minuto",

        # Pergunta técnica de quem já aposta (busca troca de casa)
        r"\bmelhor casa\b", r"\bqual casa (paga|saca|credita)\b",
        r"\bcasa que paga\b", r"\bmelhores odds\b", r"\bmais odds\b",
        r"\bqual a melhor\b.*(bet|casa|aposta)",
    ],
}
```

### 4.2 Intent `buscando_atendimento` — bets (score 90)

Pessoa que quer **começar** a apostar:
```python
r"\bcomo (me )?cadastr",       # "como me cadastro?"
r"\bquero (me )?cadastr",      # "quero me cadastrar"
r"\bcomo (que )?aposta",       # "como aposta?"
r"\bquero jogar\b",
r"\bquero apostar\b",
r"\bcomo entrar\b",
r"\btem (como|pra) come[cç]ar\b",
r"\bme indica uma casa\b",
r"\bqual casa\b.*(confiavel|confiável|boa|melhor|paga)",
r"\bme passa o link\b", r"\btem o link\b",
```

### 4.3 Intent `perguntando_preco` — bets (score 80)

Pessoa perguntando bônus/depósito/saque:
```python
r"\bb[oô]nus\b", r"\bbonus de (quanto|primeiro)",
r"\bprimeiro dep[oó]sito\b", r"\bdep[oó]sito m[ií]nimo\b",
r"\bquanto precisa depositar\b",
r"\bvale a pena\b.*casa",
r"\baceita pix\b", r"\btem pix\b",
r"\bsaque\b.*(rapido|rápido|demora|direto|liberado)",
r"\bpaga mesmo\b", r"\bpaga direito\b", r"\bessa casa paga\b",
r"\bdemora pra (pagar|sacar|liberar)", r"\brollover\b",
```

### 4.4 Score map e prioridade

```python
# Prioridade (primeiro match vence):
priority = ["buscando_atendimento", "perguntando_preco",
            "apostador_ativo", "perguntando_local", "elogio"]

score_map = {
    "buscando_atendimento": 90,  # quer começar — lead HOT
    "perguntando_preco":    80,  # pergunta bônus/saque
    "apostador_ativo":      82,  # engajado, cliente do nicho
    "perguntando_local":    70,
    "elogio":               20,
    "outros":               30,
}
```

### 4.5 Frustração é descartada (fica em `outros`, score 30)

Estes NÃO são leads quentes — são apostadores frustrados:
- `"nem deu"`, `"nem deu dessa vez"`
- `"perdi a aposta"`, `"fui red"`, `"tomei red"`
- `"nunca mais aposto"` (churn, sinal ruim)

---

## 5. Anti-spam: tipsters e afiliados disfarçados

BOT_KEYWORDS que rejeitam comentários de concorrentes/afiliados (não são leads reais):

```python
# Tipsters e afiliados de apostas (concorrência disfarçada)
"canal telegram", "canal no telegram", "sala vip", "sala de vip",
"tipster certificado", "tipster profissional", "mentoria apostas",
"mentoria de apostas", "grupo de apostas", "grupo vip", "sala paga",
"entra no meu grupo", "entra no meu canal", "metodo", "metodologia propria",
"opera comigo", "opere conosco", "pix liberado pra vc", "deposita que eu",
"clique no link da bio", "aff link", "link afiliado",
"operacional de apostas", "scalper", "surebet", "arbitragem",
"robô de aposta", "robo de aposta", "ia de aposta",
```

---

## 6. Campanha C-0003 atual (bets rodando no Paperclip)

Do `leads-export/campaigns.json`:

```json
{
  "id": "C-0003",
  "nome": "Apostas Esportivas - Brasil",
  "nicho": "apostas esportivas",
  "cidade": "",
  "cliente_destino": "",
  "query": "aposta esportiva dicas",
  "plataformas": ["tiktok", "x"],
  "nacional": true,
  "status": "ativa",
  "notes": "Pilot SeuBet"
}
```

**Nacional = true** significa: ignora filtro geográfico, aceita leads de qualquer lugar do Brasil.

---

## 7. Preset JS (Dashboard do Paperclip)

Preset do modal "Nova Campanha" pra apostas:

```javascript
const CAMPAIGN_PRESETS = {
  apostas: {
    nome: 'Apostas Esportivas — Brasil',
    nicho: 'apostas esportivas',
    query: 'aposta esportiva dicas',     // ← user quer reescrever
    plataformas: ['tiktok', 'x'],
    nacional: true,
    notes: 'Tipsters e apostadores reais. Filtrar afiliados/concorrentes. Atua Brasil todo.',
  },
  // ... outros presets: estetica, solar, juridico
};
```

---

## 8. Scrapers Apify usados pra bets

### TikTok (caminho principal — 1170 comentários em 1 run)
```python
# 1) Busca vídeos por query
client.actor("clockworks/free-tiktok-scraper").call(run_input={
    "searchQueries": [query],
    "resultsPerPage": 15,
    "shouldDownloadVideos": False,
    "shouldDownloadCovers": False,
})

# 2) Coleta comentários dos vídeos
client.actor("clockworks/tiktok-comments-scraper").call(run_input={
    "postURLs": [video_urls],
    "commentsPerPost": 300,
    "maxRepliesPerComment": 5,
})
```

### Instagram (baixa tração pra bets — mais útil em nichos visuais)
```python
# Busca por hashtag
client.actor("apify/instagram-hashtag-scraper").call(run_input={
    "hashtags": ["apostasesportivas"],  # ou betano, pixbet, etc
    "resultsLimit": 15,
})

# Comentários
client.actor("apify/instagram-comment-scraper").call(run_input={
    "directUrls": [post_urls],
    "resultsLimit": 300,
    "isNewestComments": False,
})
```

**Custo típico:** ~$1.50 por run completa (15 TikToks + 1170 comentários).

---

## 9. Filtros do pipeline (reutilizáveis)

### 9.1 Filtro de idioma (pt-BR strict)

Rejeita cirílico/CJK/árabe/hebraico + textos majoritariamente ingleses. Aceita textos com sinais de PT-BR (quero, valor, onde, pra, pq, amei, etc). Tem 60+ palavras PT-signal.

Função em `agents/base.py::is_brazilian_portuguese(text)`.

### 9.2 Filtro de relevância do vídeo

Antes de baixar comentários, rejeita vídeos:
- Com marcadores cross-lusofonia (`#angolaAOportugalPTbrasilBR`, `mocambiqueMZ`)
- Com 2+ hashtags de países não-BR
- Off-topic (caption/owner sem keyword do nicho)

Função em `agents/comment_collector/pipeline.py::_is_topic_relevant()`.

### 9.3 Hot intents (o que vira lead)

```python
hot_intents = ("buscando_atendimento", "perguntando_preco",
               "apostador_ativo", "perguntando_local")
```

Só comentários classificados nesses 4 intents E com `lead_score >= min_score (60)` viram lead.

---

## 10. Perfis Instagram padrão pra bets (de `base_apostas.py` legado)

Lista que estava sendo usada antes da migração pra `lead_system`:

```
bet365brasil_
betanobrasil
vaidebet_
atletabet
pixbet_oficial
blaze_com
brazino777oficial
estrelabet.br
```

Pra usar no `APOSTAS_INSTAGRAM_PROFILES` (separados por vírgula).

---

## 11. Histórico e decisões

- **2026-04-21:** deploy do `lead_system` no Coolify; tracking de affiliate migrado pro `lead_system` (fora do Paperclip). Paperclip ficou redundante pra reunião SeuBet.
- **2026-04-22:** `agents-apostas/` removido do Paperclip no commit `776cabe` ("chore: remove unused apostas agents"). Toda lógica de apostas consolidada dentro do classifier genérico (`apostador_ativo` intent) + campanha C-0003 criada no sistema novo de Campanhas/Workspaces.
- **Reunião:** acontece em `leads.visualizemais.com.br` (lead_system). Paperclip continua rodando local pra prospecção adicional.

### ⚠️ Segurança — PAT exposto

Local em `C:/Users/Joao Marcos/lead_system/.git/config` tinha PAT `ghp_j9Hy47g83...` embedado na URL do remote. Precisa rotacionar em https://github.com/settings/tokens. Avisado em 2026-04-21.

---

## 12. Portando pra outro projeto — checklist

Se você vai usar essa camada de apostas em outro projeto, copie:

- [ ] **Env vars** da seção 3 (`APOSTAS_*` — 11 vars) + vars legado se usar bot Telegram (`COMPANY_NAME`, `AFFILIATE_LINK`, `BONUS_OFFER`)
- [ ] **Função `build_affiliate_url(lead)`** do `lead_system/utils/affiliate.py` (source of truth pra UTMs)
- [ ] **INTENT_PATTERNS** seção 4 (apostador_ativo, buscando_atendimento-bets, perguntando_preco-bets)
- [ ] **BOT_KEYWORDS** seção 5 (anti-tipster)
- [ ] **Scripts Apify** seção 8 (TikTok + Instagram hashtag)
- [ ] **Filtro de idioma pt-BR** e **filtro de relevância de vídeo** seção 9
- [ ] **Schema Lead** seção 2.1 (com campo `affiliate_url` calculado)
- [ ] **Regra `is_eligible(lead)`**: só hot/warm recebem affiliate_url
- [ ] **Perfis IG padrão** seção 10 (se usar scraping de perfil específico)

---

**Arquivo gerado:** 2026-04-22
**Repo origem:** `C:/projetos/paperclip/` (Lead Machine)
**Campanha ativa aqui:** C-0003 — Apostas Esportivas - Brasil
**Sistema de produção bets:** https://leads.visualizemais.com.br/
