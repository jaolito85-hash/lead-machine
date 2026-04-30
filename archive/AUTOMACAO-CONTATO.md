# Automação de Contato com Leads — Plano

> Para retomar amanhã. Leituras antes: `BETS-EXPORT.md` (contexto bets) e `DEPLOY-COOLIFY.md` (deploy).
> Status: planejamento. Nada foi implementado.
> Data: 2026-04-22

---

## TL;DR

Você já tem metade disso construído no **`lead_system`** (produção em leads.visualizemais.com.br). O Paperclip virou motor de prospecção; o lead_system é motor de contato. Falta **conectar os dois**.

---

## O que você já tem funcionando

| Capacidade | Onde | Status |
|---|---|---|
| Coleta de leads (TikTok/IG/bets) com classifier | **Paperclip** | ✅ rodando |
| Bot Telegram que envia DMs | `lead_system/bot/seubet_bot.py` | ✅ em produção |
| GPT-4.1-mini gera `suggested_message` por lead | `lead_system` | ✅ |
| Affiliate URL com UTM por lead | `lead_system/utils/affiliate.py` | ✅ |
| 1036 audience profiles pra Meta Ads | `lead_system /api/audiences` | ✅ |
| Dashboard com botão "Enviar DM" | `lead_system/templates/telegram.html` | ✅ |

---

## Os 3 caminhos pra automatizar contato

### 🟢 Caminho 1 — Meta Custom Audiences + Ads (recomendado, escalável, sem risco de ban)

Em vez de mandar DM 1-a-1, **anuncia pra eles** via Instagram/Facebook/Messenger Ads.

- Exporta lista de leads (usernames, phones, emails) pro Facebook Ads Manager como **Custom Audience**
- Meta cria lookalikes (500 → 50k pessoas similares)
- Rodam ads segmentados só pra esses perfis
- **Permitido pela Meta** (é o jeito oficial)
- CPM ~R$10-30. Pra apostas, com SPA/MF 253/2025, tá liberado com creative correto

**Tradeoff:** paga ads, mas lead vê você 5-10× (vs 1 DM que vai pro spam).

### 🟡 Caminho 2 — Cold email pra leads tipo empresa (B2B only)

Pros leads de Google Maps (dentista/advogado/clínica) que têm email público:
- **Resend** (3k emails/mês grátis) ou SendGrid
- Sequence D0/D3/D7 automatizada
- Tracking open/click/reply

**Tradeoff:** só funciona com leads que têm email. Pra bets (b2c): **~0% dos leads têm**, não serve.

### 🔴 Caminho 3 — DM automática em massa IG/TikTok/WhatsApp (não faça)

- **IG DM automática:** conta some em 3-7 dias (>30 DMs/dia pra não-seguidores)
- **TikTok DM:** API não permite; Selenium = ban em horas
- **WhatsApp não-oficial** (Waha, whatsapp-web.js): ban iminente
- **WhatsApp Business oficial** (Twilio/Z-API): pago por msg, exige opt-in

Custo × benefício não compensa o risco.

---

## Plano Faseado (o que fazer)

### Fase 1 — Conectar Paperclip → lead_system (1 semana)

**Objetivo:** leads quentes coletados no Paperclip alimentam o bot Telegram que já funciona.

**Opções de integração (escolher 1):**

- **A. REST pull do lead_system:** lead_system tem job periódico que chama `GET http://paperclip/leads.json?since=<timestamp>&tipo=pessoa&min_score=70`. Import idempotente por `plataforma:user:url`.
- **B. REST push do Paperclip:** após cada scrape, Paperclip chama `POST leads.visualizemais.com.br/api/leads/import` com batch JSON.
- **C. Banco compartilhado:** ambos lêem/escrevem mesmo SQLite. Rejeitado — acopla muito.

**Recomendado:** **A** (pull). Menos acoplado, lead_system fica no comando do fluxo de contato.

**Tasks:**
1. No Paperclip: endpoint `GET /leads.json` já existe, adicionar query params `?since=<iso>&campaign_id=<id>&min_score=<n>&tipo=<t>`
2. No `lead_system`: job (Celery/APScheduler) que chama de X em X min e faz upsert na `leads.db` usando `source_url + author_username` como chave
3. Mapping dos campos:
   - Paperclip `user` → lead_system `author_username`
   - Paperclip `url` → lead_system `source_url`
   - Paperclip `evidencia`/`texto_original` → lead_system `raw_text`
   - Paperclip `intent` → lead_system `detected_intent`
   - Paperclip `score`/`temp` → lead_system `score`/`temperature`
   - Paperclip `campaign_id` → lead_system `campaign` (novo campo? ou tag?)
4. Conferir que leads importados geram `suggested_message` via GPT já existente
5. Smoke test: criar lead no Paperclip, ver aparecer no dashboard `/telegram.html` do lead_system em < 10 min

### Fase 2 — Meta Custom Audiences (2 semanas)

**Objetivo:** export automático de leads pro Facebook Ads Manager.

**Tasks:**
1. Paperclip exporta CSV formato Meta (email hashed SHA256 + phone hashed + FN + LN + city) — formato oficial
2. Upload via **Meta Marketing API** (v20.0) em Custom Audience por campanha
3. lead_system cria conta de ads + pixel + creative inicial
4. Campanha de teste com 100 leads SeuBet, budget R$50/dia por 7 dias
5. Medir CTR + CPA real

Formatos Meta: https://developers.facebook.com/docs/marketing-api/audiences/guides/custom-audiences

### Fase 3 — Cold email B2B (depois, só pros nichos b2b)

**Objetivo:** sequence automática pra leads empresa (Google Maps).

**Tasks:**
1. Integrar Resend SDK no lead_system
2. Templates por nicho: advocacia, clínica estética, dentista, solar B2B
3. Warm-up de domínio (2 semanas antes de volume)
4. UTM tracking nos CTAs
5. Reply detection → marca lead como "respondeu" no Kanban

---

## Perguntas pendentes (decidir antes de implementar Fase 1)

- [ ] **Canal prioritário:** bot Telegram existente (já pago, já funciona) ou Meta Ads direto?
- [ ] **Integração Paperclip ↔ lead_system:** pull (A) ou push (B)? → recomendo **A**
- [ ] **Mensagem:** GPT gera automática ou você revisa cada uma antes de enviar?
- [ ] **SeuBet é único cliente bets ativo** ou tem mais casas no pipeline?
- [ ] **Orçamento Meta Ads:** do budget $5k do pilot, quanto alocar? Sugestão: $500-1k pra teste Fase 2
- [ ] **LGPD/opt-in:** leads de comentário público são "dados públicos", mas DM direto pede opt-in. Meta Ads contorna isso

---

## Riscos & mitigações

| Risco | Mitigação |
|---|---|
| Lead Machine sobrecarrega bot Telegram | Rate limit no job de pull (max 50 leads/hora) |
| Duplicatas entre Paperclip e lead_system | Chave dedupe `source_url + author_username` |
| Mensagem do GPT genérica demais | Templates por intent: "apostador_ativo" ≠ "buscando_atendimento" ≠ "perguntando_preco" |
| Reclamação/denúncia no IG por DM | **Não fazemos DM automatizada** — usamos Meta Ads |
| Anúncio de apostas bloqueado | SPA/MF 253/2025 + creative conforme regulação + disclaimer |
| Base de audiência pequena (<100 leads) pra Ads | Usa lookalike 1% (Meta expande pra 50k-500k) |

---

## Stack sugerido pra Fase 1

- **Paperclip API:** já Python http.server — só adicionar query params no `/leads.json`
- **lead_system pull job:** Celery beat OU APScheduler (já rola Flask, APScheduler mais simples)
- **Dedupe:** `leads.db` com UNIQUE index em `(source_url, author_username)`
- **Monitoramento:** log simples em `data/import.log` + endpoint `/api/health/import` expondo `last_run_at`, `leads_imported_last_run`

---

## Estimativas

| Fase | Duração | Esforço | Custo externo |
|---|---|---|---|
| Fase 1 (integração) | 3-5 dias | eu codifico, você revisa | R$0 |
| Fase 2 (Meta Ads) | 1-2 semanas | eu: export+automation / você: configurar Ads Manager | R$500-1k teste + CPM |
| Fase 3 (email) | 1 semana | eu codifico | Resend grátis até 3k/mês |

---

## Ações amanhã (quando acordar)

1. Ler este documento + `BETS-EXPORT.md`
2. Responder as 5 perguntas pendentes (seção "Perguntas pendentes" acima)
3. Decidir: **Fase 1 primeiro** (conectar) ou **Fase 2 primeiro** (Meta Ads)?
4. Me devolver com decisões → eu toco a implementação

---

**Bom descanso. Abraço 👊**
