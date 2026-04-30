# Estratégia Lead Machine — Visão Geral dos 5 Verticais

Este diretório contém o plano de execução completo para as 5 frentes estratégicas do Lead Machine, organizadas por ordem de prioridade.

## Sequência recomendada de ataque

A ordem importa. Cada vertical foi posicionada por três critérios: (1) velocidade até o primeiro dinheiro entrando, (2) solidez da validação inicial, e (3) potencial de escala no longo prazo.

### Fase 1 — Agora (maio a julho/2026)

**01 — Tia da Carol (Clínica Estética Maringá)**
Cliente pagante imediato. Substitui a funcionária manual por IA. Vira o case study #1. Meta: primeiro R$ 2-3k/mês entrando em 30 dias.

**02 — Rede Nacional PNE (Dra. Carol)**
O ativo mais valioso de todos. Audiência viral + nicho único + missão real. Construir MVP em paralelo enquanto a tia roda. Meta: primeiros dentistas parceiros pagantes em 90 dias.

### Fase 2 — Meio do ano (agosto a outubro/2026)

**03 — Cota Fácil (Franqueados de Consórcio)**
Teste B2B2C com 3 franqueados piloto. Só consórcio no início (menor fricção regulatória). Meta: validar modelo, faturar R$ 10-20k/mês até dezembro.

### Fase 3 — Longo prazo (2027 em diante)

**04 — Painel Solar**
Mercado em explosão, ticket alto. Precisa de foco total, então só quando os 3 primeiros estiverem andando sozinhos. Meta: começar em uma região e escalar.

**05 — Móveis Gazin (Colchões)**
Sonho enterprise. Ciclo de venda longo. Precisa de cases reais pra chegar lá. Trunfo pra 12+ meses.

## Como usar estes documentos

Cada arquivo segue a mesma estrutura:

1. **Visão geral** do vertical
2. **Por que funciona** (análise estratégica)
3. **Perfil do cliente ideal** (persona)
4. **Modelo de negócio** (como ganha dinheiro)
5. **Arquitetura técnica** (encaixe no Paperclip + agentes Python)
6. **Jornada do lead** (ponta a ponta)
7. **Copy e scripts** (mensagens reais)
8. **KPIs e métricas**
9. **Plano de execução** (cronograma)
10. **Riscos e precauções**
11. **Checklist de próximos passos**

Imprima os que você for atacar primeiro, deixe do lado do computador, e vá riscando os checklists. Estratégia que não vira execução é só vontade.

## Princípios que valem para todos os verticais

Independente do nicho, cinco princípios se aplicam:

1. **Lead quente > lead frio**. Sempre. Gaste mais tempo qualificando que captando.
2. **O cliente não compra sistema, compra resultado**. Sempre venda "agendamentos" ou "oportunidades", nunca "software".
3. **Prova social vale mais que pitch**. Um case real convence mais que 10 reuniões.
4. **LGPD é pra valer**. Consentimento, base legal, direito ao esquecimento. Não brinque.
5. **Comece pequeno e prove antes de escalar**. 3 clientes felizes valem mais que 30 infelizes.

## Stack técnico compartilhado entre todos

Todos os verticais usam a mesma infraestrutura que você já tem:

- **Paperclip** (porta 3100) — orquestrador, armazena companies e leads
- **Agentes Python** (pasta `agents/`) — scrapers e processadores
- **Dashboard customizado** (um por vertical) — interface do cliente
- **WhatsApp Business API** ou **Evolution API** — canal de conversa
- **IA conversacional** (Claude API) — qualificação automática

Cada vertical vai ter sua própria "company" no Paperclip e seu próprio dashboard rodando numa porta diferente. Essa é a arquitetura que a gente já desenhou antes.
