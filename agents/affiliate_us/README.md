# Pipeline de Afiliados (EUA + Brasil)

Sistema pra **achar pessoas com intenção de comprar um produto** nas redes sociais,
filtrar os compradores reais e **gerar a mensagem de outreach** com o link de afiliado.
Acessível pelas abas **Afiliados EUA** e **Afiliados Brasil** no dashboard.

## Como subir o ambiente

Dois serviços (rodam em paralelo, em background):

```bash
# 1) Backend Paperclip (porta 3100)
corepack pnpm dev

# 2) Frontend / dashboard (porta 8081)
#    USE `py` (Python 3.14), nao `python` — o python padrao nao tem portalocker
py serve.py
```

- Dashboard: <http://localhost:8081> → menu lateral → **Afiliados EUA / Brasil**
- Pra parar: `stop.bat` ou encerrar os processos nas portas 3100/8081.

## Fluxo de uso (na aba)

1. **Cadastrar produto**: caixa no topo → produto (ex: "copo Stanley") + seu link de afiliado + rede.
   - ⚠️ Amazon **não** permite link em DM (avisa na hora). Pra mandar mensagem, use AliExpress/Mercado Livre/Shopee/marca direta.
2. **Buscar compradores**: cada produto tem 3 botões — **Reddit · TikTok · Instagram**. A busca roda em background (1–3 min) e **gasta crédito Apify** (confirma antes).
3. **Ver compradores**: seção **Compradores** (lojas/concorrentes ficam separados em "Concorrentes / lojas"). Filtro por produto no topo.
4. **Agir**: botão **✍️ Gerar DM** (mensagem personalizada + link + disclosure, editável/copiável) ou **⬇ Exportar @s (CSV)**.

## Filtros automáticos na coleta (em camadas)

`safety` (transtorno alimentar, menor, gravidez, medicação) → `idioma` (BR=pt, US=en) →
`vendedor` (separa quem vende de quem compra) → ranqueia compradores.

## Arquivos

| Arquivo | O que é |
|---|---|
| `discovery.json` | subreddits, queries, rubric de intent, exclusões de safety, idioma-alvo |
| `offers.json` | catálogo de produtos/ofertas (PREENCHER `affiliate_link` após aprovação na rede) |
| `spike_collect.py` | motor de coleta+classificação (`--platform reddit\|tiktok\|instagram\|all`, `--market us\|br`, `--product "..."`) |
| `outreach.py` | gera a mensagem de DM (LLM + link + disclosure) |
| `intent_signals.json` | resultado das buscas (**gitignored** — dado local; merge por produto) |
| `last_search.log` | log da última busca disparada pela aba (gitignored) |

(O mesmo `spike_collect.py`/`outreach.py` servem aos dois mercados — `affiliate_br/` só tem os JSONs.)

## Config necessária (`.env`, gitignored)

- `APIFY_TOKEN` — coleta (plano FREE: US$ 5/mês, reseta dia ~29)
- `OPENAI_API_KEY` + `OPENAI_MODEL=gpt-4o-mini` — classificação de intent e geração de DM
- `INSTAGRAM_SESSIONID` + `IG_COMMENTS_MODE=auth` — Instagram autenticado (sem isso o IG público rende quase nada). Conta usada: @ofarobusca.

## Custo por busca (referência)

| Plataforma | Comentários | Custo aprox |
|---|---|---|
| TikTok | ~100 (25/vídeo × 5) | US$ 0,15 |
| Instagram (auth) | ~30 | US$ 0,08 |
| Reddit | ~15 | US$ 0,40–0,65 |

## Aprendizados (validados)

- **TikTok é o melhor canal** pra produto físico/Brasil (compradores reais diretos: "como faço pra comprar?").
- **Instagram** só rende com login (`IG_COMMENTS_MODE=auth`); hashtag atrai muita loja → filtro de vendedor é essencial.
- **Reddit** é ok pros EUA, fraco pro Brasil.

## Próximos passos (não feitos)

- Cadastrar os **links reais** nas redes (hoje os `offers.json` têm placeholder).
- Persistir **status** de "já abordei" por comprador.
- A/B testar variações de mensagem.
