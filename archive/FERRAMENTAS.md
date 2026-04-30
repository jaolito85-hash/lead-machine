# Lead Machine — Ferramentas e Stack Tecnico

## As 3 melhores combinacoes de ferramentas para scraping de leads

---

## RECOMENDACAO FINAL: Stack por Camada

```
CAMADA 1 — DESCOBERTA (encontrar leads)
├── Apify Actors      → Instagram, Facebook, TikTok, Google Maps
├── SerpAPI           → Google Search + Google Maps
├── PRAW (Python)     → Reddit (gratuito, generoso)
├── Google Places API → Negocios locais ($200/mes gratis)
└── Instaloader       → Instagram hashtags/perfis (gratuito)

CAMADA 2 — ENRIQUECIMENTO (encontrar contato)
├── Apollo.io         → Email + telefone (10.000/mes GRATIS)
├── Hunter.io         → Email por dominio (25 buscas gratis)
└── Firecrawl         → Extrair dados de websites (500 pag gratis)

CAMADA 3 — QUALIFICACAO (classificar leads)
└── Claude/LLM        → Classificar quente/morno/frio por evidencia
```

---

## Comparativo: 3 Opcoes de Stack

### Opcao 1: GRATIS (custo zero)

| Plataforma | Ferramenta | Limite |
|------------|-----------|--------|
| Instagram | Instaloader (Python) | ~1.000 posts/sessao |
| Google Maps | Google Places API | 11.000 buscas/mes (gratis) |
| Google Search | duckduckgo-search (Python) | Sem limite oficial |
| Reddit | PRAW (Python) | 60 req/min, sem limite mensal |
| Email | Apollo.io free | 10.000 emails/mes |
| Email backup | Hunter.io free | 25 buscas/mes |
| Websites | Firecrawl free | 500 paginas/mes |

**Total: $0/mes**
**Capacidade: ~5.000-10.000 leads/mes**
**Limitacao:** Sem Twitter/X, sem LinkedIn, Instagram pode bloquear

---

### Opcao 2: IDEAL (melhor custo-beneficio) — RECOMENDADA

| Plataforma | Ferramenta | Custo | Limite |
|------------|-----------|-------|--------|
| Instagram | Apify instagram-scraper | ~$5 | ~5.000 perfis |
| Google Maps | Apify crawler-google-places | ~$5 | ~5.000 negocios |
| Google Maps | Google Places API | $0 | 11.000 buscas (gratis) |
| Google Search | SerpAPI | $0 | 100 buscas/mes (gratis) |
| Facebook | Apify facebook-pages-scraper | ~$5 | ~5.000 paginas |
| TikTok | Apify tiktok-scraper (clockworks) | ~$3 | ~3.000 perfis |
| Reddit | PRAW | $0 | Ilimitado |
| Twitter/X | Apify twitter-scraper | ~$5 | ~2.000 tweets |
| Email | Apollo.io free | $0 | 10.000/mes |
| Email backup | Hunter.io free | $0 | 25/mes |
| Websites | Firecrawl free | $0 | 500 pag/mes |

**Total: ~$23/mes (Apify pay-per-use)**
**Capacidade: ~20.000-30.000 leads/mes**
**Cobertura: TODAS as plataformas**

---

### Opcao 3: PROFISSIONAL (sem limites)

| Plataforma | Ferramenta | Custo |
|------------|-----------|-------|
| Instagram | Apify (oficial) | $10-20 |
| Google Maps | Apify + Google Places | $0-10 |
| Google Search | SerpAPI Developer | $50 |
| Facebook | Apify (oficial) | $10-20 |
| TikTok | Apify (clockworks) | $5-10 |
| Reddit | PRAW | $0 |
| Twitter/X | API Basic oficial | $100 |
| LinkedIn | Proxycurl ou PhantomBuster | $50-100 |
| Email | Apollo.io Basic | $49 |
| Hunter | Hunter Starter | $34 |
| Websites | Firecrawl Hobby | $16 |
| Proxies | Residencial rotativo | $50-100 |

**Total: ~$350-500/mes**
**Capacidade: ~100.000+ leads/mes**
**Cobertura: TUDO, sem restricao**

---

## Detalhe por Ferramenta

### APIFY — Scrapers prontos (PRINCIPAL)

**O que e:** Plataforma com scrapers prontos para cada rede social. Voce passa parametros, ele executa na nuvem e retorna os dados estruturados.

**Env:** `APIFY_TOKEN`
**Free tier:** $5/mes de creditos
**Conta:** https://console.apify.com/sign-up

**Actors recomendados para lead gen:**

| Actor | Plataforma | O que coleta |
|-------|-----------|-------------|
| `apify/instagram-scraper` | Instagram | Posts, comentarios, hashtags, perfis, localizacao |
| `apify/instagram-profile-scraper` | Instagram | Bio, contato, seguidores, posts recentes |
| `compass/crawler-google-places` | Google Maps | Nome, endereco, telefone, site, avaliacao, horario |
| `poidata/google-maps-email-extractor` | Google Maps | Emails extraidos dos sites dos negocios |
| `apify/facebook-pages-scraper` | Facebook | Paginas de negocios, contato, metricas |
| `apify/facebook-page-contact-information` | Facebook | Email, telefone, endereco das paginas |
| `apify/facebook-groups-scraper` | Facebook | Posts em grupos, membros, discussoes |
| `clockworks/tiktok-scraper` | TikTok | Videos, perfis, hashtags, comentarios |
| `clockworks/tiktok-user-search-scraper` | TikTok | Busca de usuarios por keyword |
| `vdrmota/contact-info-scraper` | Qualquer site | Emails, telefones, redes sociais do site |
| `apify/google-search-scraper` | Google | Resultados de busca organica |

**Workflow tipico com Apify:**
```
1. compass/crawler-google-places
   Input: "clinica odontologica Maringa PR"
   Output: 200 clinicas com nome, telefone, site, avaliacao

2. vdrmota/contact-info-scraper
   Input: URLs dos sites das clinicas
   Output: Emails, telefones, redes sociais

3. apify/instagram-profile-scraper
   Input: @handles encontrados
   Output: Bio, seguidores, contato, posts recentes
```

---

### SERPAPI — Google Search + Maps

**O que e:** API que retorna resultados do Google em JSON. Proxy, CAPTCHA e parsing inclusos.

**Env:** `SERPAPI_API_KEY`
**Free tier:** 100 buscas/mes
**Conta:** https://serpapi.com/users/sign_up

**Para lead gen:**
```python
# Buscar negocios no Google Maps
GET https://serpapi.com/search?engine=google_maps&q=dentista+harmonizacao+Maringa+PR&api_key=XXX

# Retorna: nome, endereco, telefone, site, avaliacao, review_count
```

---

### GOOGLE PLACES API — Negocios locais

**O que e:** API oficial do Google para buscar negocios. $200/mes de credito GRATIS.

**Env:** `GOOGLE_PLACES_API_KEY`
**Free tier:** $200/mes = ~11.000 buscas
**Console:** https://console.cloud.google.com

**Capacidade no free tier:**
- ~11.764 Place Details (detalhes de um negocio)
- ~40.000 Place Search (busca por tipo + cidade)
- ~28.571 Geocoding (enderecos)

---

### APOLLO.IO — Enriquecimento de leads (MELHOR FREE TIER)

**O que e:** Banco de dados com 275M+ contatos. Busca email, telefone, empresa, cargo.

**Env:** `APOLLO_API_KEY`
**Free tier:** 10.000 emails/mes + API access
**Conta:** https://app.apollo.io

**Para lead gen:**
```python
# Buscar por titulo + cidade
POST https://api.apollo.io/api/v1/mixed_people/search
Headers: x-api-key: XXX
Body: { "person_titles": ["dentista"], "person_locations": ["Maringa, PR"] }

# Retorna: nome, email, telefone, empresa, cargo, LinkedIn
```

**Por que e o melhor:** 10.000 emails/mes gratis e absurdo. Hunter.io da 25. Snov.io da 50. Apollo da 10.000.

---

### HUNTER.IO — Email por dominio

**O que e:** Encontra emails de uma empresa pelo dominio do site.

**Env:** `HUNTER_API_KEY`
**Free tier:** 25 buscas de dominio + 50 verificacoes/mes
**Conta:** https://hunter.io/users/sign_up

**Workflow:**
```
1. Google Maps retorna: "Clinica Sorriso" → site: clinicasorriso.com.br
2. Hunter.io: GET /domain-search?domain=clinicasorriso.com.br
3. Retorna: contato@clinicasorriso.com.br, dr.joao@clinicasorriso.com.br
```

---

### PRAW — Reddit (TOTALMENTE GRATIS)

**O que e:** API oficial do Reddit. Gratuita e generosa.

**Env:** `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USER_AGENT`
**Free tier:** 60 req/min, SEM limite mensal
**Setup:** https://www.reddit.com/prefs/apps (2 minutos)

**Para lead gen:**
```python
import praw
reddit = praw.Reddit(client_id="XXX", client_secret="XXX", user_agent="lead_machine/1.0")

# Buscar pessoas perguntando sobre harmonizacao
for post in reddit.subreddit("all").search("harmonizacao facial indicacao", sort="new", limit=100):
    print(f"u/{post.author} — {post.title}")
    # → Lead potencial: pessoa buscando o servico
```

---

### INSTALOADER — Instagram (GRATIS)

**O que e:** Scraper open-source para Instagram. Sem API key.

**Install:** `pip install instaloader`
**Auth:** Opcional (conta burner recomendada para mais requests)

**Para lead gen:**
```python
import instaloader
L = instaloader.Instaloader()

# Buscar posts na hashtag #harmonizacaofacial
hashtag = instaloader.Hashtag.from_name(L.context, "harmonizacaofacial")
for post in hashtag.get_posts():
    if "maringa" in (post.caption or "").lower():
        print(f"@{post.owner_username} — {post.caption[:100]}")
        # → Lead: pessoa postando sobre harmonizacao em Maringa
```

---

### FIRECRAWL — Scraping de websites

**O que e:** API que transforma qualquer site em dados estruturados (markdown/JSON).

**Env:** `FIRECRAWL_API_KEY`
**Free tier:** 500 paginas/mes
**Conta:** https://firecrawl.dev

**Para lead gen:**
```python
# Extrair dados de um site de clinica
POST https://api.firecrawl.dev/v1/scrape
Headers: Authorization: Bearer fc-XXX
Body: { "url": "https://clinicasorriso.com.br", "formats": ["markdown"] }

# Retorna: todo o conteudo do site em markdown limpo
# Depois o Claude extrai: servicos, precos, equipe, contato
```

---

## Ferramentas GRATIS que dispensam API

| Ferramenta | Install | Plataforma | Nota |
|------------|---------|-----------|------|
| `instaloader` | `pip install instaloader` | Instagram | Melhor free |
| `praw` | `pip install praw` | Reddit | Melhor API gratuita |
| `duckduckgo-search` | `pip install duckduckgo-search` | DuckDuckGo | Alternativa ao Google sem bloqueio |
| `twscrape` | `pip install twscrape` | X/Twitter | Fragil, precisa pool de contas |
| `playwright` | `pip install playwright` | Qualquer site | Browser automation com stealth |
| `playwright-stealth` | `pip install playwright-stealth` | Anti-deteccao | Bypassa deteccao de bot |
| `facebook-scraper` | `pip install facebook-scraper` | Facebook | Semi-funcional, precisa login |
| `TikTokApi` | `pip install TikTokApi` | TikTok | Precisa cookie, fragil |
| `googlesearch-python` | `pip install googlesearch-python` | Google | Bloqueia rapido, usar com proxy |
| `beautifulsoup4` | `pip install beautifulsoup4` | HTML parsing | Parser de HTML |
| `linkedin-api` | `pip install linkedin-api` | LinkedIn | Risco de ban, usar com cuidado |

---

## Ranking de Confiabilidade por Plataforma

| # | Plataforma | Scraping | Nota |
|---|-----------|---------|------|
| 1 | **Reddit** | PRAW | Excelente — API generosa, estavel, sem bloqueio |
| 2 | **Google Maps** | Places API / Apify | Excelente — $200 gratis, dados completos |
| 3 | **Facebook** | Apify oficial | Bom — actors mantidos pela Apify |
| 4 | **TikTok** | Apify (clockworks) | Bom — mantido ativamente |
| 5 | **Instagram** | Instaloader / Apify | Medio — funciona mas bloqueia frequente |
| 6 | **LinkedIn** | Proxycurl / PhantomBuster | Fragil — risco legal e ban |
| 7 | **X/Twitter** | Apify / twscrape | Fragil — nenhum actor oficial, quebra sempre |

---

## Setup Rapido (instalar tudo de uma vez)

```bash
# Python dependencies
pip install instaloader praw tweepy playwright duckduckgo-search
pip install beautifulsoup4 requests httpx
pip install playwright-stealth
playwright install chromium

# Node.js (para Paperclip + Apify CLI)
npm install -g @apify/cli

# Criar .env
cp .env.example .env
# Preencher as chaves
```

---

## Prioridade de Contas para Criar (ordem)

| # | Servico | URL | Por que primeiro |
|---|---------|-----|-----------------|
| 1 | **Apollo.io** | https://app.apollo.io | 10.000 emails/mes gratis — melhor deal |
| 2 | **Apify** | https://console.apify.com | Scrapers prontos para tudo |
| 3 | **Google Cloud** | https://console.cloud.google.com | Places API com $200 gratis |
| 4 | **Reddit** | https://www.reddit.com/prefs/apps | API gratis, 2 min setup |
| 5 | **SerpAPI** | https://serpapi.com | 100 buscas Google gratis |
| 6 | **Hunter.io** | https://hunter.io | Email finder backup |
| 7 | **Firecrawl** | https://firecrawl.dev | Scraping de sites |
