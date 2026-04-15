# Paperclip Lead Machine — Guia de Orquestracao

## Sua empresa de agentes IA para captacao de leads sob demanda

> Voce da o comando. Seus agentes executam.

---

## Como Funciona

```
VOCE (Board):
  "Preciso de leads para clinica odontologica que faz
   harmonizacao facial em Maringa-PR. Buscar no Instagram,
   X, Google e Reddit."

        |
        v

CEO Agent (interpreta seu comando):
  - Entende: nicho, servico, localizacao, plataformas
  - Quebra em sub-tarefas
  - Distribui para os agentes certos

        |
        v

AGENTES EXECUTAM EM PARALELO:
  [Instagram] → hashtags, comentarios, perfis interessados
  [X/Twitter] → conversas, perguntas sobre o tema
  [Google]    → buscas locais, Maps, quem pesquisa isso
  [Reddit]    → discussoes, pedidos de indicacao
  [LinkedIn]  → profissionais, clinicas, decisores

        |
        v

RESULTADO:
  Lista de leads qualificados com nome, contato, fonte,
  nivel de interesse, pronto para abordagem comercial
```

---

## 1. Arquitetura dos Agentes

### Organograma da Empresa

```
VOCE (Board — da os comandos)
  |
  CEO — Interpreta comandos e distribui tarefas
  |
  |--- CTO — Garante que os scrapers funcionam
  |     |
  |     |--- Agent Instagram    (busca no Instagram)
  |     |--- Agent X/Twitter    (busca no X)
  |     |--- Agent Google       (busca no Google + Maps)
  |     |--- Agent Reddit       (busca no Reddit)
  |     |--- Agent LinkedIn     (busca no LinkedIn)
  |     |--- Agent Facebook     (busca no Facebook)
  |     |--- Agent TikTok       (busca no TikTok)
  |
  |--- Qualificador — Filtra e pontua os leads
  |
  |--- Enriquecedor — Encontra email, telefone, redes sociais
```

### O que cada agente faz

| Agente | Adapter | Funcao |
|--------|---------|--------|
| **CEO** | `claude_local` | Recebe seu comando em linguagem natural. Entende nicho, servico, cidade, plataformas. Cria as tasks e distribui. |
| **CTO** | `claude_local` | Monitora se os scrapers estao rodando. Detecta falhas. Ajusta estrategia de busca. |
| **Instagram** | `process` | Busca por hashtags, localizacao, comentarios em posts. Coleta perfis que demonstram interesse. |
| **X/Twitter** | `process` | Busca conversas, perguntas, reclamacoes sobre o tema. Coleta perfis engajados. |
| **Google** | `process` | Busca no Google Search, Google Maps, Places API. Coleta negocios locais e quem pesquisa o servico. |
| **Reddit** | `process` | Busca em subreddits relevantes, posts pedindo indicacao, discussoes sobre o tema. |
| **LinkedIn** | `process` | Busca profissionais, empresas, decisores do nicho na regiao. |
| **Facebook** | `process` | Busca em grupos, paginas, comentarios. Coleta perfis interessados. |
| **TikTok** | `process` | Busca videos sobre o tema, comentarios de pessoas interessadas. |
| **Qualificador** | `claude_local` | Recebe leads brutos. Classifica por nivel de interesse (quente/morno/frio). Remove duplicatas. |
| **Enriquecedor** | `process` | Pega um lead e busca: email, telefone, WhatsApp, outras redes sociais, site. |

---

## 2. Ferramentas Necessarias

### Para cada plataforma

| Plataforma | Ferramenta Gratuita | Ferramenta Paga (melhor) | O que coleta |
|------------|--------------------|-----------------------------|--------------|
| **Instagram** | Instaloader (Python), Playwright | Apify Instagram Scraper, PhantomBuster | Perfis, posts, comentarios, seguidores de hashtag/local |
| **X/Twitter** | Tweepy (API v2 free tier), snscrape | Twitter API Pro, Apify Twitter Scraper | Tweets, replies, perfis, buscas por keyword |
| **Google Search** | googlesearch-python, Playwright | SerpAPI, DataForSEO, Apify Google Scraper | Resultados de busca, People Also Ask, snippets |
| **Google Maps** | Playwright, Overpass API | Google Places API, Apify Google Maps Scraper | Negocios locais, avaliacoes, telefone, site, horario |
| **Reddit** | PRAW (Python Reddit API), Pushshift | Apify Reddit Scraper | Posts, comentarios, subreddits, autores |
| **LinkedIn** | Playwright (limitado) | PhantomBuster, Apollo.io, Apify LinkedIn | Perfis profissionais, empresas, cargos |
| **Facebook** | Playwright (limitado) | Apify Facebook Scraper, PhantomBuster | Grupos, paginas, posts, comentarios |
| **TikTok** | TikTok Research API, Playwright | Apify TikTok Scraper | Videos, comentarios, perfis |
| **Enriquecimento** | Clearbit free tier, Hunter.io free | Apollo.io, Hunter.io, Snov.io | Email, telefone, empresa, cargo, redes sociais |

### Infraestrutura base

| Item | O que e | Por que precisa |
|------|---------|-----------------|
| **Python 3.10+** | Linguagem dos scrapers | Maioria das libs de scraping sao Python |
| **Node.js 20+** | Runtime do Paperclip | Server, CLI, adapters |
| **Playwright** | Browser automation | Scraping de sites que precisam renderizar JS |
| **Proxy rotativo** | IPs diferentes a cada request | Evitar bloqueio dos sites |
| **PostgreSQL** | Banco de dados | Armazenar leads, tasks, historico |
| **Paperclip** | Control plane | Orquestrar tudo |

### Instalacao das ferramentas Python

```bash
pip install instaloader tweepy praw playwright googlesearch-python
pip install apollo-sdk hunter beautifulsoup4 requests
playwright install chromium
```

---

## 3. Fluxo de Execucao — Exemplo Real

### Voce digita:

> "Preciso de leads para clinica odontologica que faz harmonizacao facial em Maringa-PR. Buscar no Instagram, X, Google e Reddit."

### CEO Agent processa:

```json
{
  "nicho": "clinica odontologica",
  "servico": "harmonizacao facial",
  "cidade": "Maringa",
  "estado": "PR",
  "plataformas": ["instagram", "x", "google", "reddit"],
  "tipo_lead": "pessoas interessadas no servico",
  "idioma": "pt-BR"
}
```

### CEO cria as tasks:

| Task | Agente | Comando |
|------|--------|---------|
| T-001 | Instagram | Buscar hashtags: #harmonizacaofacial #harmonizacaomaringa #odontoestetica. Buscar posts geolocalizados em Maringa. Coletar perfis que comentaram/curtiram. |
| T-002 | X/Twitter | Buscar tweets com: "harmonizacao facial" "maringa", "quero fazer harmonizacao", "indicacao dentista maringa". Coletar perfis. |
| T-003 | Google | Buscar: "harmonizacao facial maringa", "dentista harmonizacao maringa". Coletar clinicas do Maps. Buscar quem avaliou clinicas similares. |
| T-004 | Reddit | Buscar em r/brasil, r/desabafos, r/cuidadospessoais: posts sobre harmonizacao facial, pedidos de indicacao. |
| T-005 | Qualificador | Receber leads brutos de T-001 a T-004. Classificar, deduplicar, pontuar. |
| T-006 | Enriquecedor | Pegar leads qualificados. Buscar email, telefone, WhatsApp. |

### Resultado final entregue a voce:

```
LEADS — Harmonizacao Facial Maringa-PR
Total: 847 leads brutos → 312 qualificados → 89 quentes

LEAD #001 [QUENTE]
  Nome: Maria Silva
  Instagram: @mariasilva_
  Fonte: Comentou "quero muito fazer" em post de #harmonizacaofacial
  Cidade: Maringa-PR (bio)
  Email: maria.silva@gmail.com (Hunter.io)
  Score: 92/100

LEAD #002 [QUENTE]
  Nome: Carlos Oliveira
  X/Twitter: @carlosoliv
  Fonte: Tweet "alguem indica dentista pra harmonizacao em maringa?"
  Email: carlos.o@hotmail.com
  Score: 88/100

LEAD #003 [MORNO]
  Nome: Ana Santos
  Reddit: u/anasantos_pr
  Fonte: Post "estou pensando em fazer harmonizacao, vale a pena?"
  Cidade: Maringa (post history)
  Score: 65/100

... (mais 86 leads)
```

---

## 4. Exemplos de Comandos que Voce Pode Dar

```
"Buscar leads de nutricionistas em Curitiba que atendem
 emagrecimento. Instagram e Google."

"Encontrar donos de franquias de acai no Parana.
 LinkedIn e Google Maps."

"Pessoas interessadas em implante dentario em Londrina.
 Todas as plataformas."

"Academias de crossfit em Maringa que nao tem site.
 Google Maps e Instagram."

"Dentistas que fazem lentes de contato dental em SP capital.
 Google Maps, Instagram, Facebook."

"Pessoas reclamando de dor nas costas em Maringa.
 Reddit, X, Facebook groups."

"Clinicas de estetica em Maringa sem Instagram profissional.
 Google Maps."

"Franquias da Cacau Show em cidades do interior do PR
 com menos de 100k habitantes. Google Maps."
```

Nao importa o nicho. Nao importa a cidade. Nao importa a plataforma.
Voce da o comando, os agentes executam.

---

## 5. Estrutura de Dados do Lead

Cada lead coletado segue esta estrutura:

```json
{
  "id": "L-00001",
  "nome": "Maria Silva",
  "plataforma_origem": "instagram",
  "url_perfil": "https://instagram.com/mariasilva_",
  "evidencia": "Comentou 'quero muito fazer' em post de harmonizacao",
  "cidade": "Maringa",
  "estado": "PR",
  "email": "maria@gmail.com",
  "telefone": "(44) 99999-0000",
  "whatsapp": true,
  "instagram": "@mariasilva_",
  "facebook": null,
  "linkedin": null,
  "nicho_interesse": "harmonizacao facial",
  "score": 92,
  "temperatura": "quente",
  "coletado_em": "2026-04-14T18:30:00Z",
  "enriquecido": true,
  "notas": "Bio menciona Maringa, engajou com 3 posts sobre o tema"
}
```

---

## 6. Classificacao de Leads

| Temperatura | Score | Criterio |
|-------------|-------|----------|
| **Quente** | 80-100 | Demonstrou interesse direto (perguntou, comentou querendo, pediu indicacao) |
| **Morno** | 50-79 | Interesse indireto (curtiu posts, segue perfis do tema, esta na regiao) |
| **Frio** | 20-49 | Interesse possivel (esta na regiao, perfil compativel, mas sem evidencia direta) |
| **Descartado** | 0-19 | Sem relevancia (bot, fora da regiao, sem conexao com o tema) |

---

## 7. Como Conectar ao Paperclip

### Criar a company

```bash
POST /api/companies
{ "name": "Lead Machine" }
```

### Criar o CEO

```bash
POST /api/companies/{cid}/agents
{
  "name": "CEO",
  "role": "ceo",
  "adapterType": "claude_local",
  "adapterConfig": {
    "systemPrompt": "Voce e o CEO de uma empresa de captacao de leads. Quando o board der um comando, interprete: nicho, servico, cidade, plataformas. Crie tasks para cada plataforma e distribua para os agentes."
  }
}
```

### Criar agente de plataforma (exemplo Instagram)

```bash
POST /api/companies/{cid}/agents
{
  "name": "Agent-Instagram",
  "role": "engineer",
  "adapterType": "process",
  "adapterConfig": {
    "command": "python3 /agents/instagram_scraper.py",
    "env": {
      "PLATFORM": "instagram",
      "OUTPUT_DIR": "/data/leads/raw"
    }
  },
  "reportsTo": "{ctoId}"
}
```

### Dar um comando (criar issue)

```bash
POST /api/companies/{cid}/issues
{
  "title": "Leads: harmonizacao facial em Maringa-PR",
  "description": "Buscar pessoas interessadas em harmonizacao facial em Maringa-PR. Plataformas: Instagram, X, Google, Reddit.",
  "assigneeAgentId": "{ceoId}",
  "priority": "high"
}
```

O CEO recebe via heartbeat, interpreta, e cria sub-tasks para cada agente.

---

## 8. Roadmap

| Fase | O que | Status |
|------|-------|--------|
| 1 | Estudar arquitetura Paperclip | Concluido |
| 2 | Documentacao de orquestracao | Concluido |
| 3 | Dashboard frontend | Concluido |
| 4 | Refazer dashboard para lead generation | Proximo |
| 5 | Conectar ao backend Paperclip | Pendente |
| 6 | Criar scripts dos agentes (Python) | Pendente |
| 7 | Primeiro comando real end-to-end | Pendente |
| 8 | Escalar para multi-nicho | Pendente |
