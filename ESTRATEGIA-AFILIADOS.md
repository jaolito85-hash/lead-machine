# ESTRATÉGIA DE AFILIADOS — Lead Machine

> Documento completo da estratégia de vendas via afiliados no Brasil e EUA.
> Atualizado em 26/06/2026.

---

## VISÃO GERAL

O Lead Machine coleta automaticamente pessoas com intenção de compra em redes sociais (TikTok, Instagram) e plataformas (Google Maps, Reddit), classifica por temperatura (quente/morno/frio) e gera mensagens de outreach prontas com link de afiliado + disclosure.

Você só precisa: aprovar nas redes de afiliados, preencher os links nas ofertas, e fazer o outreach manual pelos leads quentes que chegam no Telegram.

---

## O QUE JÁ ESTÁ PRONTO

### Infraestrutura (24/7 no Coolify)
- Dashboard: http://y26e7qe79gptx9u4u3omn80h.143.95.213.89.sslip.io
- Container rodando com supervisord (dashboard + runner)
- Volume persistente: leads-db.json, searches.json, campaigns.json sobrevivem a restarts
- Bot Telegram configurado: alertas de leads quentes em tempo real
- 11 buscas salvas ativas (6 BR + 5 US)
- 335 leads já coletados (231 quentes)

### Agentes ativos
| Agente | Plataforma | Função |
|--------|-----------|--------|
| agent_instagram.py | Instagram | Coleta posts + comentários com intenção de compra |
| agent_tiktok.py | TikTok | Coleta vídeos + comentários com intenção de compra |
| agent_google_maps.py | Google Maps | Coleta negócios locais (B2B) |
| agent_youtube.py | YouTube | Coleta vídeos + comentários |
| agent_qualifier.py | — | Classifica leads em quente/morno/frio + dispara Telegram |
| agent_enricher.py | — | Busca email, telefone, WhatsApp via Apollo/Hunter/Firecrawl |
| telegram_notifier.py | — | Alerta de lead quente no Telegram |

### Módulos de afiliados
| Arquivo | Função |
|---------|--------|
| agents/affiliate_br/offers.json | Catálogo de ofertas BR (9 ofertas, 6 nichos) |
| agents/affiliate_us/offers.json | Catálogo de ofertas US (9 ofertas, 5 nichos) |
| agents/affiliate_br/discovery.json | Config de descoberta BR (15 intent queries) |
| agents/affiliate_us/discovery.json | Config de descoberta US (15 intent queries) |
| agents/affiliate_us/spike_collect.py | Coleta de intent por produto (Reddit + TikTok) |
| agents/affiliate_us/outreach.py | Geração de DM de outreach com disclosure |

---

## OS 5 NICHOS

### BRASIL

#### 1. Emagrecimento (nutra/suplementos)
- **Plataformas:** TikTok + Instagram
- **Redes:** Hotmart, Monetizze, Eduzz
- **Comissão:** 30-50%
- **Produtos:** Termogênico, Shake substituto, Plano de dieta
- **Busca salva:** S-0001 — a cada 6h
- **Ofertas:** OFF-BR-001, OFF-BR-002, OFF-BR-008

#### 2. Beleza/Skincare (harmonização facial, skincare)
- **Plataformas:** TikTok + Instagram
- **Redes:** Shopee, Amazon BR, Hotmart
- **Comissão:** 10-60% (digital > físico)
- **Produtos:** Kit skincare, Serum vitamina C, Curso harmonização
- **Buscas salvas:** S-002 (harmonização, 6h), S-003 (skincare, 8h)
- **Ofertas:** OFF-BR-003, OFF-BR-004, OFF-BR-005

#### 3. Apostas esportivas (SeuBet)
- **Plataforma:** Lead system separado (leads.visualizemais.com.br)
- **Rede:** Direto com operadora
- **Comissão:** CPA R$50-150
- **Status:** Já em produção — 174 leads quentes com link rastreável
- **Oferta:** OFF-BR-009 (link real já configurado)

#### 4. Pets (rações, suplementos)
- **Plataformas:** Google Maps (pet shops) + TikTok
- **Redes:** Shopee, Magalu Parceiro
- **Comissão:** 8-15%
- **Produtos:** Ração premium, Suplemento articular
- **Busca salva:** S-0006 — a cada 24h
- **Ofertas:** OFF-BR-006, OFF-BR-007

#### 5. Nutrição (nutricionistas)
- **Plataformas:** Google Maps
- **Redes:** Eduzz
- **Comissão:** 30-50%
- **Produtos:** Plano de dieta personalizado
- **Busca salva:** S-0005 — a cada 24h
- **Oferta:** OFF-BR-008

### EUA

#### 1. Weight Loss (emagrecimento)
- **Plataformas:** TikTok
- **Redes:** ClickBank, ShareASale, Digistore24
- **Comissão:** 40-75%
- **Produtos:** GLP-1 Alternative, Appetite Control, Meal Replacement
- **Buscas salvas:** S-0007 (6h), S-0009 (8h)
- **Ofertas:** OFF-US-001, OFF-US-002, OFF-US-009

#### 2. Fitness/Supplements
- **Plataformas:** TikTok
- **Redes:** iHerb, brand_direct (Refersion/GoAffPro)
- **Comissão:** 10-25%
- **Produtos:** Whey Protein, Creatine
- **Busca salva:** S-0008 — a cada 8h
- **Ofertas:** OFF-US-003, OFF-US-004

#### 3. Skincare
- **Plataformas:** TikTok
- **Redes:** ShareASale, iHerb
- **Comissão:** 10-30%
- **Produtos:** Vitamin C Serum, Anti-Aging Cream
- **Busca salva:** S-0010 — a cada 8h
- **Ofertas:** OFF-US-005, OFF-US-006

#### 4. Home/Kitchen Gadgets
- **Plataformas:** TikTok
- **Redes:** Amazon Associates (conteúdo only, sem DM)
- **Comissão:** 4-8%
- **Produtos:** Stanley Tumbler, Air Fryer
- **Busca salva:** S-0011 — a cada 12h
- **Ofertas:** OFF-US-007, OFF-US-008

---

## REDES DE AFILIADOS — ONDE SE CADASTRAR

### Brasil
| Rede | Link | Aprovação | Permite DM | Nichos |
|------|------|-----------|-----------|--------|
| Hotmart | hotmart.com | 24-48h | Sim | Infoprodutos, emagrecimento, cursos |
| Monetizze | monetizze.com.br | 24-48h | Sim | Nutra, físico, digital |
| Eduzz | eduzz.com | 24-48h | Sim | Nutrição, educação, software |
| Braip | braip.com | 24-48h | Sim | Infoprodutos |
| Shopee Afiliados | affiliate.shopee.com.br | Na hora | Sim | Físico (skincare, pets) |
| Amazon BR | associados.amazon.com.br | 1-3 dias | Não (só conteúdo) | Físico (skincare) |
| Magalu Parceiro | parceiro.magazineluiza.com.br | 1-3 dias | Sim | Físico (pets) |

### EUA
| Rede | Link | Aprovação | Permite DM | Nichos |
|------|------|-----------|-----------|--------|
| ClickBank | clickbank.com | 1-7 dias | Sim | Digital+físico, weight loss |
| ShareASale | shareasale.com | 1-7 dias | Sim | Skincare, supplements |
| iHerb | iherb.com/rewards | Na hora | Sim | Supplements, skincare |
| Digistore24 | digistore24.com | 1-3 dias | Sim | Digital, weight loss |
| Amazon Associates | affiliate-program.amazon.com | 1-3 dias | Não (só conteúdo) | Home, kitchen |

---

## COMO PREENCHER OS LINKS DE AFILIADO

Quando for aprovado em uma rede e pegar o link de afiliado:

### Opção 1: Pelo dashboard
1. Abre o dashboard > aba Afiliados
2. Clica na oferta que quer editar
3. Cola o link de afiliado no campo
4. Salva

### Opção 2: Editando o arquivo direto
1. Edita `agents/affiliate_br/offers.json` ou `agents/affiliate_us/offers.json`
2. Troca `PLACEHOLDER_TROCAR_APOS_APROVACAO` pelo link real
3. Commit + push (deploy automático no Coolify)

O sistema usa o link automaticamente quando gera a DM de outreach.

---

## FLUXO COMPLETO (como funciona)

```
1. Runner coleta leads (a cada 6-24h, automático)
   ↓
2. Agentes buscam no TikTok/Instagram/Google Maps
   ↓
3. Qualifier classifica (quente/morno/frio)
   ↓
4. Telegram alerta leads quentes (tempo real)
   ↓
5. Você abre o dashboard, vê o lead no kanban
   ↓
6. Clica no perfil da pessoa (link direto)
   ↓
7. Gera a DM (botão no dashboard)
   ↓
8. DM tem: greeting + recomendação + link de afiliado + disclosure
   ↓
9. Manda 20-30 DMs por dia por conta (limite seguro anti-ban)
   ↓
10. Pessoa compra → você ganha comissão
```

---

## DASHBOARD — COMO USAR

### Central de Comando
- Digita o comando em linguagem natural
- Ex: "Preciso de leads para harmonização facial em São Paulo. TikTok e Instagram."
- O sistema dispara os agentes automaticamente

### Kanban (Leads)
- Cards com nome, @, plataforma, score, temperatura
- Botões: Ver perfil, Enviar DM, Abrir post original
- Filtro por temperatura (quente/morno/frio) e plataforma

### Buscas Salvas
- 11 buscas ativas (6 BR + 5 US)
- Roda automaticamente no intervalo configurado
- Botão "Rodar agora" pra forçar execução

### Afiliados
- Ver ofertas cadastradas (BR e US)
- Cadastrar nova oferta
- Disparar coleta de intent por produto (spike_collect)
- Gerar DM de outreach

---

## COMPLIANCE (IMPORTANTE)

### Brasil
- Disclosure OBRIGATÓRIO: `#publi — link de afiliado, posso receber comissão`
- Sem promessa de resultado (Anvisa/Procon/CDC)
- Frases proibidas: "cura", "garantido", "emagreça X kg", "milagroso", "aprovado pela Anvisa"

### EUA
- Disclosure OBRIGATÓRIO: `#ad — affiliate link, I may earn a commission`
- Sem promessa de resultado (FTC/FDA)
- Frases proibidas: "cure", "guaranteed results", "lose X pounds in", "miracle", "FDA approved"

### Safety exclusions (NUNCA fazer outreach)
- Sinais de transtorno alimentar
- Menor de 18 anos
- Gravidez ou amamentação
- Condição médica ou medicamento citado
- Pediu pra não receber DM

---

## METAS

| Período | Leads/dia | DMs/dia | Vendas/dia | Receita/dia |
|---------|-----------|---------|------------|-------------|
| Semana 2 | 200 | 30 | 0-1 | R$0-100 |
| Mês 1 | 500 | 50 | 1-3 | R$100-300 |
| Mês 2 | 1000 | 100 | 3-7 | R$300-700 |
| Mês 3 | 2000 | 150 | 5-15 | R$500-1500 |

### Ticket médio por nicho
| Nicho | Mercado | Ticket médio | Comissão |
|-------|---------|-------------|----------|
| Emagrecimento (nutra) | BR | R$50-200 | 30-50% |
| Skincare (físico) | BR | R$30-80 | 10-15% |
| Curso (digital) | BR | R$97-497 | 40-60% |
| Apostas (CPA) | BR | R$50-150 | Fixo |
| Pets | BR | R$30-100 | 8-15% |
| Weight loss (ClickBank) | US | $20-80 | 50-75% |
| Supplements (iHerb) | US | $10-50 | 10-25% |
| Skincare (ShareASale) | US | $15-60 | 15-30% |
| Home/Kitchen (Amazon) | US | $20-150 | 4-8% |

---

## CHECKLIST — O QUE FAZER AGORA

### Hoje
- [ ] Criar conta na Hotmart (https://hotmart.com)
- [ ] Criar conta na Monetizze (https://monetizze.com.br)
- [ ] Criar conta na Shopee Afiliados (https://affiliate.shopee.com.br)
- [ ] Criar conta no ClickBank (https://clickbank.com)
- [ ] Criar conta no iHerb (https://iherb.com/rewards)

### Esta semana
- [ ] Escolher 1-2 produtos por nicho nas redes aprovadas
- [ ] Pegar links de afiliado
- [ ] Preencher offers.json (trocar PLACEHOLDER pelo link real)
- [ ] Começar outreach pelos 231 leads quentes já coletados
- [ ] Mandar 20-30 DMs por dia

### Mês 1
- [ ] Aprovar em todas as redes restantes (Eduzz, Braip, ShareASale, Digistore24)
- [ ] Ajustar buscas salvas conforme performance por nicho
- [ ] Medir conversão (DMs enviadas vs vendas)
- [ ] Otimizar: nichos com mais conversão recebem mais buscas

---

## COMANDOS ÚTEIS

### Disparar busca manual (API)
```bash
docker exec <CONTAINER> curl -s -X POST http://localhost:8081/api/run \
  -H "Content-Type: application/json" \
  -d '{"query":"harmonizacao facial","cidade":"Sao Paulo","nicho":"harmonizacao facial","plataformas":["tiktok","instagram"],"campaign_id":"C-LEGACY"}'
```

### Ver status de um run
```bash
docker exec <CONTAINER> curl -s http://localhost:8081/api/run/<RUN_ID>
```

### Listar buscas ativas
```bash
docker exec <CONTAINER> curl -s http://localhost:8081/api/local/searches
```

### Ver leads
```bash
docker exec <CONTAINER> curl -s http://localhost:8081/leads.json | python3 -m json.tool | head -50
```

### Ver logs do runner
```bash
docker exec <CONTAINER> cat /app/leads-export/runner.log | tail -20
```

### Ver logs de um agente
```bash
docker exec <CONTAINER> cat /app/leads-export/tiktok.log | tail -20
docker exec <CONTAINER> cat /app/leads-export/instagram.log | tail -20
docker exec <CONTAINER> cat /app/leads-export/google_maps.log | tail -20
```

### Forçar execução de uma busca salva
```bash
docker exec <CONTAINER> curl -s -X POST http://localhost:8081/api/local/searches/S-0001/run
```

---

## ESTRUTURA DE ARQUIVOS

```
lead-machine/
├── serve.py                          # Backend (dashboard + API + agentes on-demand)
├── dashboard/index.html              # Frontend (kanban, comandos, afiliados)
├── Dockerfile                        # Container com VOLUME persistente
├── deploy/supervisord.conf           # Supervisor (dashboard + runner)
├── agents/
│   ├── base.py                       # Helper compartilhado + apify_dataset_id()
│   ├── agent_instagram.py            # Scraper Instagram
│   ├── agent_tiktok.py               # Scraper TikTok
│   ├── agent_google_maps.py          # Scraper Google Maps
│   ├── agent_youtube.py              # Scraper YouTube
│   ├── agent_qualifier.py            # Classificador + Telegram notifier
│   ├── agent_enricher.py             # Enriquecedor (email/telefone)
│   ├── runner.py                     # Daemon 24/7 (buscas salvas)
│   ├── searches.py                   # CRUD buscas salvas
│   ├── campaigns.py                  # CRUD campanhas
│   ├── exports.py                    # Export CSV/XLSX
│   ├── telegram_notifier.py          # Bot Telegram
│   ├── affiliate_br/
│   │   ├── offers.json               # 9 ofertas BR (6 nichos)
│   │   └── discovery.json            # 15 intent queries BR
│   ├── affiliate_us/
│   │   ├── offers.json               # 9 ofertas US (5 nichos)
│   │   ├── discovery.json            # 15 intent queries US
│   │   ├── spike_collect.py          # Coleta de intent por produto
│   │   └── outreach.py               # Geração de DM
│   └── comment_collector/            # Pipeline de comentários
├── leads-export/                     # VOLUME PERSISTENTE
│   ├── leads-db.json                 # Banco de leads
│   ├── searches.json                 # Buscas salvas
│   ├── campaigns.json                # Campanhas
│   ├── exports/                      # CSV/XLSX
│   ├── runner.log                    # Log do runner
│   ├── tiktok.log                    # Log TikTok
│   ├── instagram.log                 # Log Instagram
│   ├── google_maps.log               # Log Google Maps
│   ├── qualifier.log                 # Log qualifier
│   └── enricher.log                  # Log enricher
└── ESTRATEGIA-AFILIADOS.md            # Este documento
```

---

*Última atualização: 26/06/2026*
