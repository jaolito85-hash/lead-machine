# Comment Collector

Captura comentarios dos videos da Carol no Instagram e TikTok, classifica
intencao com IA e mostra a demanda agregada num dashboard bonito.

## O que esta pasta faz

```
comment_collector/
├── __init__.py              # marca como pacote Python
├── README.md                # este arquivo
├── .env.example             # modelo das variaveis de ambiente
├── db.py                    # SQLite — schema + inserts/updates/stats
├── instagram_collector.py   # wrapper Apify pra Instagram
├── tiktok_collector.py      # wrapper Apify pra TikTok
├── classifier.py            # classifica intencao (heuristico + IA)
├── pipeline.py              # orquestra: coleta -> classifica -> grava
├── run.py                   # CLI principal — voce roda este arquivo
└── dashboard/
    ├── serve.py             # servidor HTTP do dashboard (porta 8090)
    └── index.html           # pagina do dashboard
```

**Onde ficam os dados:**
O banco SQLite vai pra `paperclip/leads-export/comments.db` — um arquivo unico.
Pra fazer backup, voce so precisa copiar esse arquivo. Pra inspecionar manualmente,
abre no [DB Browser for SQLite](https://sqlitebrowser.org).

---

## Setup (uma vez so)

### 1. Pegar token do Apify

1. Cria conta gratuita em https://console.apify.com
2. Vai em **Settings -> Integrations -> Tokens**
3. Copia o token

> **Custo:** o Apify da $5/mes de credito gratis. Cada 1000 comentarios
> custa ~$0.30. Os videos da Carol tem ~5k-15k comentarios cada,
> entao com $5 voce processa uns 15-30 videos.

### 2. Configurar o .env

Na raiz do projeto (`paperclip/.env`), adicione:

```bash
APIFY_TOKEN=apify_api_AAAAAAAAAA_seu_token_aqui

# Opcional — sem isto usa heuristica (gratis, menos preciso)
ANTHROPIC_API_KEY=sk-ant-AAAAAA_sua_chave_aqui
ANTHROPIC_MODEL=claude-haiku-4-5-20251001
```

> **Dica:** se voce ja tem APIFY_TOKEN no .env existente (o `agent_instagram.py`
> usa o mesmo), nao precisa duplicar. Compartilham a mesma chave.

### 3. Instalar dependencia da Anthropic (opcional)

So se voce for usar Claude pra classificar:

```bash
pip install anthropic
```

Os outros pacotes (`apify-client`, `python-dotenv`) ja estao no
`agents/requirements.txt`.

---

## Como usar

Todos os comandos abaixo voce roda da pasta `paperclip/` (a raiz do projeto).

### Coleta padrao — Carol no Instagram + TikTok

```bash
python -m agents.comment_collector.run
```

Isso pega os 20 videos mais recentes em cada plataforma e ate 500 comentarios
por video. No fim imprime um JSON com o resumo.

### Variantes uteis

```bash
# So Instagram, 50 videos
python -m agents.comment_collector.run --platform instagram --max-videos 50

# So TikTok, com perfil diferente
python -m agents.comment_collector.run --platform tiktok --profile outroperfil

# Mais comentarios por video (cuidado com custo no Apify)
python -m agents.comment_collector.run --max-comments-per-video 1000

# Logging detalhado pra debugar
python -m agents.comment_collector.run --verbose
```

### Reclassificar (sem chamar Apify de novo)

Se voce coletou comentarios sem ter ainda a chave da Anthropic e depois
configurou ela, pode reclassificar tudo:

```bash
python -m agents.comment_collector.run --reclassify
```

Roda ate 500 comentarios por vez. Se voce tem milhares, roda o comando varias vezes.

### Ver stats sem fazer nada

```bash
python -m agents.comment_collector.run --stats
```

---

## Dashboard

Pra ver os numeros num dashboard bonito (mesma identidade visual da
apresentacao da Carol):

```bash
python -m agents.comment_collector.dashboard.serve
```

Depois abre no navegador: **http://localhost:8090**

O dashboard atualiza sozinho a cada 30 segundos. Voce pode deixar ele aberto
enquanto roda novas coletas — vai ver os numeros crescendo em tempo real.

> **Dica:** se a porta 8090 estiver ocupada, edita `dashboard/serve.py` na
> linha `PORT = 8090` e troca pra outra (ex: 8091).

---

## Como o sistema funciona (vibe-coder style)

```
Voce roda o run.py
       |
       v
  pipeline.py  ── 1. lista videos do perfil (Apify, barato)
       |        2. salva videos no banco SQLite
       |        3. baixa todos comentarios (Apify, custa mais)
       |        4. pra cada comentario: classifica e grava
       v
  banco SQLite  ────  dashboard HTML mostra tudo
```

**Cada arquivo tem uma responsabilidade unica:**
- `db.py` — so mexe no banco. Se voce quiser trocar pra Postgres no futuro,
  so mexe aqui.
- `instagram_collector.py` / `tiktok_collector.py` — so falam com Apify.
  Se aparecer um actor melhor, voce troca a string do actor.
- `classifier.py` — so classifica texto. E o lugar mais provavel de voce
  querer mexer pra ajustar prompt/heuristica.
- `pipeline.py` — so orquestra. Praticamente nao precisa mexer.
- `run.py` — so faz parsing de argumento e chama o pipeline.

---

## Onde mexer pra customizar

| Quero mudar... | Mexa em... |
|----------------|------------|
| Quais palavras viram "buscando_atendimento" | `classifier.py` -> `INTENT_PATTERNS` |
| Adicionar mais cidades brasileiras | `classifier.py` -> `CIDADES_PRINCIPAIS` |
| Usar outro modelo da Anthropic | `.env` -> `ANTHROPIC_MODEL` |
| Mudar o que o dashboard mostra | `dashboard/index.html` |
| Mudar as cores/fontes do dashboard | `dashboard/index.html` -> `tailwind.config` no `<head>` |
| Adicionar nova tabela no banco | `db.py` -> `SCHEMA` (e cria funcao helper) |
| Trocar perfil da Carol | `.env` -> `DEFAULT_PROFILE_INSTAGRAM` / `DEFAULT_PROFILE_TIKTOK` |

---

## Proximos passos sugeridos

1. **Validar com 1 video so:** roda `--platform instagram --max-videos 1` pra
   confirmar que ta tudo funcionando antes de gastar Apify.
2. **Ligar o Claude:** configura `ANTHROPIC_API_KEY` e roda `--reclassify`.
   Vai ver os scores ficarem mais inteligentes (e cidades menores aparecem).
3. **Mostrar pra Carol:** abre o dashboard num browser, deixa rodar a coleta
   uns 15 min, mostra pra ela. O numero "X% buscando atendimento" e o que
   prova a tese.
4. **Plugar no agent_lead_machine:** os hot leads (score 80+) podem virar
   leads no `leads-db.json` existente, pra entrar no fluxo de DM/WhatsApp.
   (Quando voce quiser, eu te ajudo a fazer essa ponte.)
