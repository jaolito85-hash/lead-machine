# Guia — Como criar campanhas que geram leads

> Template universal pra criar **Campanha** + rodar **Central de Comando** ou **Busca Salva**, com regras testadas em produção.

---

## 2 regras de ouro

1. **Crie a CAMPANHA antes de buscar.** Assim os leads já caem com `campaign_id` certo. Se buscar antes, eles caem em `C-LEGACY` e precisam ser movidos na mão depois.
2. **Query ≠ marca pura.** A query melhor é `<objeto/serviço> + <palavra de fricção de compra>` (ex: `panela le creuset`, `le creuset preço`). Marca pura (`le creuset`) pega fãs/seguidores, não compradores.

---

## 📋 Template — formulário "Nova Campanha"

| Campo | Como preencher | Exemplo produto físico | Exemplo serviço local |
|---|---|---|---|
| **NOME** | `<Cliente> — <Categoria> — <Cidade ou "BR">` | `haus — Le Creuset — BR` | `Dra. Camila — Botox — Maringa-PR` |
| **NACIONAL** ☐ | ✅ marque se: produto físico, e-commerce, SaaS, apostas, infoprodutos, marca nacional. ❌ deixe vazio se: serviço presencial com cidade fixa. | ✅ marcado | ❌ vazio |
| **NICHO** | A **comunidade do público comprador** (não o produto/marca). É o que dá contexto pro classifier IA. | `mesa posta` | `harmonizacao facial` |
| **CIDADE** | Vazio se `NACIONAL=true`. `Cidade-UF` se for local. | (vazio) | `Maringa-PR` |
| **CLIENTE DESTINO** | Quem recebe a lista. Aparece no export. | `haus` | `Dra. Camila / Clinica Royal Face` |
| **QUERY PADRÃO** | Termo **objeto/serviço + qualificador de intenção**. Veja regras abaixo. ⚠️ máx 3 palavras (o sistema corta variantes maiores). | `panela le creuset` | `botox` |
| **PLATAFORMAS** | Marque por tipo de oferta — veja tabela abaixo. | TikTok ☑ Instagram ☑ YouTube ☑ | Google ☑ Instagram ☑ TikTok ☑ |
| **NOTAS** | Liste as 3-5 queries-variante que você vai rodar manualmente depois. | `Variantes: panela le creuset, le creuset preco, le creuset vale a pena, le creuset onde comprar` | `Variantes: botox, harmonizacao facial, preencher labio` |

---

## 🎯 Plataformas por tipo de oferta

| Oferta | Google Maps | Instagram | TikTok | YouTube |
|---|:-:|:-:|:-:|:-:|
| **Produto físico B2C** (Le Creuset, IKEA, vestuário, gadgets) | ❌ | ✅ | ✅ ⭐ | ✅ |
| **Serviço local** (dentista, clínica, advogado, salão) | ✅ ⭐ | ✅ | ✅ | ❌ |
| **Apostas / finanças / consórcio** | ❌ | ❌ | ✅ ⭐ | ✅ |
| **SaaS / infoproduto / curso** | ❌ | ✅ | ✅ | ✅ ⭐ |
| **Imobiliário / veículo** | ✅ | ✅ ⭐ | ✅ | ❌ |

⭐ = plataforma mais forte pra esse nicho.

**Regra do Google Maps:** só use se o público procura **endereço físico** dessa categoria no Maps. Não use pra produto que se compra online.

---

## ✍️ Como montar uma boa QUERY PADRÃO

Fórmula: `<palavra do produto/serviço> <palavra de intenção>` — máx 3 palavras.

### Palavras de intenção de compra (use 1 por variante)

| Tipo | Palavras |
|---|---|
| Decisão de preço | `preco`, `quanto custa`, `vale a pena` |
| Aquisição | `onde comprar`, `comprar`, `como adquirir` |
| Comparação | `vs <concorrente>`, `melhor`, `qual escolher` |
| Reclamação/desejo | `quero`, `sonho`, `desejo` |
| Recomendação | `indica`, `recomenda` |

### Exemplos prontos por nicho

| Cliente | Query padrão (1ª da campanha) | Variantes pra rodar depois na Central |
|---|---|---|
| Le Creuset / mesa posta | `panela le creuset` | `le creuset preco`, `le creuset vale a pena`, `panela ferro fundido` |
| Implante dental local | `implante dental` | `implante dental preco`, `dentista implante`, `quero implante` |
| Apostas esportivas | `aposta esportiva` | `bet melhor`, `casa de aposta confiavel`, `quanto ganha aposta` |
| Curso de inglês | `curso de ingles` | `ingles online preco`, `qual curso ingles`, `quero aprender ingles` |
| Vestido de festa | `vestido festa` | `vestido madrinha preco`, `onde comprar vestido`, `aluguel vestido` |
| Painel solar | `painel solar` | `painel solar preco`, `instalar placa solar`, `vale a pena solar` |
| Consórcio | `consorcio` | `consorcio veiculo`, `consorcio imovel preco`, `quero consorcio` |

---

## 🚀 Fluxo de execução

### 1) Cria a campanha
Preenche o formulário com a QUERY PADRÃO mais forte (a #1 das suas variantes).

### 2) Roda as variantes — escolha 1 dos 2 caminhos:

**Caminho A — Central de Comando (ad-hoc)**
- Aba **Central de Comando** → digita 1 comando por variante em linguagem natural.
- Exemplos válidos:
  - *"Buscar le creuset preço no TikTok e YouTube"*
  - *"Procurar pessoas que querem panela le creuset no Instagram e TikTok"*
  - *"Encontrar implante dental em Maringa-PR no Google e Instagram"*
- Selecione **[Pessoas]** no toggle "BUSCAR" (queremos leads de consumidores, não empresas).
- Clique **EXECUTAR**.
- ⚠️ **NÃO dispare várias buscas em paralelo** — Apify free tier só aguenta 1-2 actors simultâneos. Aguarde uma terminar antes da próxima.

**Caminho B — Busca Salva (agendado)**
- Aba **Buscas Salvas** → criar busca com intervalo (ex: a cada 6h).
- O `runner.py` dispara sozinho no horário programado.
- Bom pra campanha que precisa coletar continuamente.

### 3) Qualifier
Após coletar, rode o qualifier no terminal:
```bash
py -3.12 agents/agent_qualifier.py --limit 500
```
Isso re-pontua os leads com lógica multi-fator e cross-platform. Leads quentes geram notificação Telegram (se configurado).

### 4) Exporta
No dashboard, filtre por campanha → "Exportar CSV/XLSX".

---

## ⚠️ Erros comuns

| Erro | Sintoma | Correção |
|---|---|---|
| Marca pura como query | 0 leads, hashtag genérica/internacional | Adicione palavra de intenção (`panela X`, `X preco`) |
| Cidade preenchida + `nacional=true` | Filtro de cidade aplicado em busca nacional → corta resultados | Ou cidade vazia + `nacional=true`, ou cidade preenchida + `nacional=false` |
| Google Maps em campanha de produto físico | 0 leads ou só lojas de revendedor | Tire Google Maps pra produto B2C |
| Query com 4+ palavras | Sistema corta variantes e perde o sentido | Máx 3 palavras na query padrão |
| Nicho = marca | Classifier não entende contexto | Nicho = **comunidade do comprador** (mesa posta, mães, cozinheiros, noivas) |
| Buscar primeiro, criar campanha depois | Leads caem em `C-LEGACY` | Crie a campanha antes |
| Disparar 12 actors em paralelo | `Monthly usage hard limit exceeded` / `memory limit 8192MB` | Rode 1-2 por vez. Use Buscas Salvas pra agendar. |
| Hashtag com nome curto (`le creuset`) | Pegava só `#creuset` antes do fix | Já corrigido em `instagram_collector.py` — aceita tokens de 2 letras |

---

## 🔁 Caso real validado — campanha "haus" (Le Creuset)

**Setup:**
- Nome: `haus`, Nicho: `mesa posta`, Cidade: vazio, Nacional: ✅
- Cliente: `haus`, Query: `le creuset`
- Plataformas: Instagram, TikTok, YouTube

**Variantes rodadas (12 jobs no total):**

| Plataforma | Query | Leads salvos |
|---|---|---|
| TikTok | `panela le creuset` | **47** 🥇 |
| TikTok | `le creuset preco` | **63** 🥇 |
| TikTok | `le creuset` | 4 |
| TikTok | `onde comprar le creuset` | 0 |
| Instagram | `panela le creuset` | 10 |
| Instagram | `le creuset` | 0 |
| Instagram | `le creuset preco` | 0 |
| Instagram | `onde comprar le creuset` | 0 |
| YouTube | (4 queries) | ⛔ Apify estourou cota mensal |

**Total: 124 leads** → após qualifier: **53 quentes + 17 mornos + 54 frios**.

**Lições:**
- `panela le creuset` e `le creuset preco` foram queries de ouro (gerei 110 dos 124 leads).
- TikTok superior ao Instagram em produto físico B2C (114 vs 10 leads).
- `onde comprar X` virou `comprar X mesa` pelo normalizador interno e morreu — prefira `X preco` ou `X vale a pena`.

---

## 📝 Checklist rápida antes de clicar "Criar"

- [ ] Nome segue padrão `Cliente — Categoria — Cidade/BR`?
- [ ] `Nacional` está coerente com `Cidade` (um vazio quando o outro está preenchido)?
- [ ] Nicho descreve a **comunidade do comprador**, não a marca?
- [ ] Query tem **objeto + intenção** e ≤3 palavras?
- [ ] Plataformas batem com o tipo de oferta (ver tabela)?
- [ ] Notas têm 3-5 variantes anotadas pra rodar depois?
