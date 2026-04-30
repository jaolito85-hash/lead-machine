# Vertical 04 — Painel Solar Residencial

**Status:** Alto potencial, mas só começar depois que os 3 primeiros verticais estiverem andando.
**Horizonte de execução:** Início em 6-9 meses. Escala em 12-18 meses.
**Meta de receita:** R$ 50.000 a R$ 150.000/mês em 18 meses.

---

## 1. Visão Geral

O mercado de energia solar residencial no Brasil está em **explosão**. Conta de luz virou dor coletiva, equipamento ficou mais barato, e a regulação favoreceu a geração distribuída. Em 2024-2025 o Brasil passou de 30 GW instalados em energia solar, e o crescimento continua a dois dígitos ao ano.

Você tem contatos no setor, o que diminui drasticamente o custo de começar. E sua infraestrutura técnica (captação + qualificação com IA + WhatsApp) se encaixa como luva pro perfil do lead solar: pessoa frustrada com conta alta, pesquisando online, aberta a conversar.

Mas atenção: **este vertical exige foco**. Volume é alto, qualificação é complexa (fatores técnicos), concorrência por leads em Google/Meta é feroz, e os integradores solares já são bombardeados por "vendedores de lead". Entrar aqui sem diferenciação = virar commodity.

Por isso a recomendação é: **começar só depois que os outros três estiverem rodando sozinhos**. Solar precisa da sua atenção inteira.

## 2. Por Que Este Vertical Funciona

### Dor crescente e universal

Conta de luz subiu ~50% em 5 anos. Todo mundo sente. O impulso de "preciso fazer alguma coisa" é real e crescente.

### Ticket altíssimo

- Sistema residencial pequeno (2-5 kWp): R$ 12k-25k
- Sistema médio (5-10 kWp): R$ 25k-50k
- Sistema grande residencial (10-20 kWp): R$ 50k-100k
- Comercial/industrial: R$ 100k+

Isso justifica **caro** custo por lead qualificado. Integrador paga R$ 100-500 por lead tranquilamente se converte.

### Decisão relativamente rápida

Do primeiro contato à venda: 30-90 dias em média. Não é imediato como estética, mas muito mais rápido que imóvel ou franquia.

### Payback claro pro cliente final

Cliente faz a conta e vê: "em 4-6 anos o sistema se paga, e depois tenho 20 anos de energia praticamente grátis". É argumento lógico forte.

### Mercado fragmentado

Existem milhares de integradores solares pequenos no Brasil. A maioria **péssima em marketing**. Isso cria oportunidade clara pra parceria.

## 3. Análise do Mercado

### Grandes players (observar, não competir de frente)

- **Portal Solar / Solfácil / 123 Solar** — agregadores que já capturam muito lead
- **Empresas integradoras de grande porte** — Blue Sol, Canadian Solar, etc.
- **Marketplaces nacionais** — têm SEO forte

**Tradução:** você não vai ranquear "energia solar" no Google contra eles. Não tenta.

### Onde está a oportunidade real

1. **Cidades médias do interior** (100k-500k habitantes) onde os grandes players não investem localmente
2. **Segmentação ultra-específica** — "energia solar para fazendas em Mato Grosso", "energia solar condomínios SP"
3. **Facebook/Instagram local** — onde os grandes não estão
4. **Parceria profunda com 2-3 integradores** ao invés de vender lead pra muitos

## 4. O Modelo de Negócio

### Opção A — Lead Seller (commodity)

Você capta leads e vende pra integradores por R$ 100-300 cada.

**Pros:** começo rápido, sem dependência de um só cliente
**Contras:** commodity, preço cai com o tempo, margem apertada

### Opção B — Parceria Profunda (recomendada)

Você se torna o "time de marketing" de 2-3 integradores em regiões específicas. Não vende lead: vende o funil inteiro (captação + qualificação + agendamento).

**Pros:** receita recorrente, relacionamento mais forte, pode cobrar bem mais
**Contras:** mais trabalho de gestão, dependência maior

**Modelo de precificação:**
- Setup: R$ 5.000
- Mensalidade: R$ 2.500 a R$ 5.000 (inclui gestão de ads + captura + qualificação)
- Per agendamento qualificado (visita técnica confirmada): R$ 150-300
- Bônus por venda fechada (opcional): R$ 500-1.500

### Opção C — Whitelabel / SaaS (longo prazo)

Você vira o fornecedor de tecnologia pra integradores. Eles usam sua plataforma com a marca deles.

**Pros:** margem gigante, escala sem esforço operacional
**Contras:** desenvolvimento caro, venda consultiva, só após ter 10+ clientes

### Recomendação

Começa **Opção B**. Dois integradores em regiões diferentes (ex: um no norte do Paraná, um no interior de SP). Valida em 6 meses. Aí escolhe se vai pra A, B, ou C.

## 5. Perfil do Lead Ideal

### Lead QUENTE (entrega direta pro integrador)

- Proprietário do imóvel (ou autorização do proprietário)
- Conta de luz acima de R$ 400/mês (abaixo disso o ROI fica longo)
- Residência de alvenaria com telhado estruturado
- Intenção declarada de instalar em até 6 meses
- Tem capacidade de financiar (renda compatível) ou já tem o valor

### Lead MORNO (entra em nurturing)

- Interesse genérico, sem urgência
- Conta de luz entre R$ 200-400 (precisa educar sobre economia)
- Dúvidas sobre telhado / financiamento
- Pesquisando sem decisão clara

### Lead FRIO (não interessa)

- Inquilino sem autorização
- Conta de luz baixa (<R$ 200)
- Imóvel irregular (terreno invadido, construção sem alvará)
- Sem intenção real (só curiosidade)

## 6. Perguntas de Qualificação

A IA precisa capturar (em ordem de importância):

1. **Qual sua conta de luz mensal média?** (filtro crítico)
2. **Você é proprietário do imóvel?** (obstáculo legal)
3. **Tipo de telhado** (cerâmica, fibrocimento, laje) — afeta custo e viabilidade
4. **Cidade/estado** — determina irradiação solar e integrador parceiro
5. **Pretende à vista ou financiado?** — determina perfil de cliente
6. **Prazo de decisão** — urgência
7. **Já pesquisou com outras empresas?** — nível de awareness

**Dica:** não faz tudo de uma vez. Fragmenta em 2-3 mensagens. Pergunta mata a paciência do lead.

## 7. Arquitetura Técnica

### Fluxo do lead

```
Facebook/Instagram Ads (segmentação regional)
     ↓
Lead preenche formulário na landing regional
     ↓
Paperclip cria lead na company do integrador parceiro
     ↓
agent_conversador_solar.py dispara mensagem
     ↓
IA qualifica: conta de luz, telhado, proprietário, prazo
     ↓
Se QUENTE:
  - agent_simulador_solar.py calcula economia estimada
  - Envia simulação personalizada pro lead
  - Agenda visita técnica pro integrador
  - Notifica integrador (dashboard + WhatsApp)
     ↓
Se MORNO:
  - Entra em nurturing educacional (sequência 30 dias)
     ↓
Se FRIO:
  - Arquiva
```

### Componentes novos

- `agent_conversador_solar.py` — conversa específica pra solar (tom mais técnico que estética, mais pragmático)
- `agent_simulador_solar.py` — calcula simulação de economia baseado em: conta de luz + cidade (irradiação) + tarifa da distribuidora local
- `agent_matcher_solar.py` — matching lead → integrador parceiro da região

### Integração com tarifas e irradiação

Dados externos importantes:
- Tarifa de energia por distribuidora (ANEEL publica)
- Índice de irradiação solar por município (INPE/CRESESB)
- Bandeira tarifária atual

Isso permite simulação realista e customizada. Diferencial competitivo enorme.

### Companies no Paperclip

- `solar-parceiro-curitiba`
- `solar-parceiro-ribeirao`
- `solar-master` (dados agregados)

## 8. Copy e Scripts

### Anúncio no Facebook

**Formato:** vídeo curto (15s) ou carrossel

**Headline:** *"Conta de luz do mês: R$ 823. Com energia solar, seria R$ 0. Simula a sua."*

**Copy:** 
> *"Sua conta de luz subiu de novo? Em [cidade], quem instalou energia solar tá pagando entre R$ 40 e R$ 100/mês pela conta. Simula em 2 minutos quanto você economizaria. Grátis, sem compromisso."*

**CTA:** "Simular economia"

**Dica:** segmentação por CEP + renda aparente + interesse em "conta de luz, economia, energia". Público grande, mas filtrado.

### Formulário da landing

Só 4 campos (fricção baixa):
1. Nome
2. WhatsApp
3. Cidade
4. Valor médio da conta de luz (faixas: até 200, 200-400, 400-800, 800+)

### Primeira mensagem no WhatsApp

> *"Oi [nome], aqui é o Rafael da [nome da empresa parceira]! Vi que você simulou nossa economia com energia solar em [cidade].
> 
> Vou fazer uma simulação personalizada pra você. Me confirma: sua conta média tá na faixa de R$ [faixa]?
> 
> E outra: você é o dono do imóvel mesmo?"*

### Após qualificação, envia simulação

> *"Ó [nome], fiz a conta aqui:
> 
> ✓ Sua conta média hoje: R$ 650/mês
> ✓ Com sistema solar: R$ 50/mês (só a taxa mínima)
> ✓ Economia mensal: R$ 600
> ✓ Economia anual: R$ 7.200
> ✓ Custo do sistema estimado: R$ 28.000
> ✓ Payback (tempo pra se pagar): 4 anos
> ✓ Depois disso, 20+ anos de energia praticamente grátis
> 
> Posso agendar uma visita técnica gratuita do nosso engenheiro essa semana pra medir seu telhado e fazer proposta final?"*

**Princípios:**
- Números específicos (não "mais ou menos")
- Sem rebuscar técnica (kWp, inversor, etc.) na primeira hora
- Foco em **economia**, não em tecnologia
- Fechamento direto (agendamento, não "te ligo"

### Tratamento de objeções

**"É muito caro"**
> *"Entendo. Mas pense assim: você tá pagando R$ 650/mês de luz, que viram R$ 0 (só taxa mínima) em 4 anos. O que hoje vai pra CPFL/Enel/etc., vira investimento no seu patrimônio. Quer ver opções de financiamento pra não desembolsar nada? Tem linhas específicas pra solar com parcela menor que a sua conta de luz atual."*

**"Meu telhado aguenta?"**
> *"Ótima pergunta! Sistema solar é leve (~15kg/m²), e nosso engenheiro faz avaliação estrutural na visita técnica sem custo. Se não aguentar, a gente fala antes de você investir qualquer coisa."*

**"E se eu mudar de casa?"**
> *"Duas opções: você pode tirar o sistema e levar (custa, mas é possível), ou o imóvel valoriza com o sistema e você inclui no preço de venda. Casas com energia solar vendem 3-6% mais caro em média."*

**"E se quebrar?"**
> *"Painéis têm garantia de 25 anos na geração. Inversor de 10 anos. Nós damos 2 anos de garantia de instalação. Em 99% dos casos, o sistema roda tranquilo por décadas."*

## 9. KPIs e Métricas

| Métrica | Meta mês 3 | Meta mês 12 |
|---|---|---|
| Leads capturados/mês (por integrador) | 100 | 500 |
| Taxa de qualificação | 25% | 40% |
| Taxa de visita técnica confirmada | 15% | 30% |
| Taxa de proposta → venda | 25% | 35% |
| Custo por lead qualificado | R$ 80 | R$ 45 |
| LTV do integrador parceiro | R$ 30k | R$ 80k+ |

## 10. Plano de Execução

### Pré-requisito: outros verticais andando

Antes de começar, confirmar:
- [ ] Tia já paga há 3+ meses, sistema estável
- [ ] Rede PNE com 15+ parceiros rodando
- [ ] Cota Fácil com 10+ franqueados pagantes
- [ ] Você tem 2+ horas por dia pra dedicar ao solar

### Mês 1 (fase solar) — Prospecção de parceiros

- [ ] Lista 20 integradores solares em 2 regiões-alvo (ex: PR e SP interior)
- [ ] Contato com os 20 (seus amigos podem ajudar com intros)
- [ ] Pitch pra 5-10
- [ ] Fecha 2 pilotos

### Mês 2 — Setup técnico

- [ ] Landing pages regionais
- [ ] Companies no Paperclip (uma por parceiro)
- [ ] `agent_conversador_solar.py` e `agent_simulador_solar.py`
- [ ] Integração com dados de tarifa/irradiação
- [ ] Primeiro R$ 3-5k em tráfego pago pra testar

### Mês 3 — Execução e ajuste

- [ ] Volume de lead fluindo
- [ ] Medir cada métrica obsessivamente
- [ ] Ajustar copy, perguntas, timing
- [ ] Primeiras visitas técnicas acontecendo
- [ ] Primeiras vendas fechadas pelos integradores

### Mês 4-6 — Validação e escala

- [ ] Dados suficientes pra comprovar ROI pros integradores
- [ ] Aumento de budget de tráfego
- [ ] Mais 2-3 integradores adicionados

### Mês 7-12 — Consolidação

- [ ] 6-10 integradores parceiros
- [ ] Receita estável R$ 50k-100k/mês
- [ ] Pode começar a pensar em whitelabel/SaaS

## 11. Riscos e Precauções

### Risco 1 — Concorrência com grandes agregadores

**Problema:** Solfácil, 123 Solar, Portal Solar capturam leads em massa com SEO e investimento pesado.

**Mitigação:**
- Não competir no Google por palavra genérica "energia solar"
- Foco em Facebook/Instagram regional (onde eles não investem tão forte)
- Pitch local: "somos da sua cidade, não somos agregador nacional frio"

### Risco 2 — Integrador parceiro ruim

**Problema:** Vende sonho no WhatsApp mas a execução é péssima. Cliente reclama. Sua reputação cai.

**Mitigação:**
- Escolhe parceiros com base técnica forte (CREA, certificações, 50+ instalações prévias)
- Pede referências reais
- Monitora NPS pós-instalação
- Descredenciamento rápido se cair qualidade

### Risco 3 — Promessa de economia sem fundamento

**Problema:** Prometer "R$ 0 de conta de luz" e cliente descobre que paga R$ 80 de taxa mínima sempre. Reclamação.

**Mitigação:**
- Sempre explicar: "conta vai pra taxa mínima da distribuidora"
- Copy honesta: "economia de 90-95%", não "economia total"
- Simulação com números reais, não promessas vagas

### Risco 4 — Lead desatualizado

**Problema:** Lead esperou 2 dias pro integrador visitar. Já tinha falado com concorrente.

**Mitigação:**
- SLA rígido: visita técnica agendada em até 3 dias
- Se parceiro não cumpre, multa na mensalidade
- Lead só vai pra parceiro que tem disponibilidade real na semana

### Risco 5 — Mudança regulatória

**Problema:** Mudança na Lei 14.300 de 2022 já aconteceu (fim da gratuidade total). Futuras mudanças podem apertar mais.

**Mitigação:**
- Acompanhar ANEEL mensalmente
- Copy que se adapta rápido a mudanças
- Não prometer o que é "direito adquirido" que pode mudar

## 12. Checklist de Próximos Passos (quando chegar a hora)

Antes de começar (6-9 meses à frente):

- [ ] Confirmar que os 3 primeiros verticais estão saudáveis
- [ ] Listar seus contatos do setor solar (lembra que você mencionou amigos?)
- [ ] Fazer benchmark de 5 empresas já atuando no lead gen solar
- [ ] Estudar a Lei 14.300 e suas implicações atuais
- [ ] Escolher 2 regiões-piloto com base em: (a) cidade média, (b) irradiação boa, (c) tarifa alta, (d) seu acesso pessoal

Quando começar:

- [ ] Contatar seus amigos do setor — eles podem virar os primeiros parceiros
- [ ] Criar deck específico pra integradores (diferente do de estética/clínica)
- [ ] Adaptar pipeline do Paperclip
- [ ] Preparar orçamento inicial de tráfego (mínimo R$ 3-5k/mês por parceiro)

---

**Observação final:** solar é um vertical **grande demais pra ser prioridade 1**. Tem espaço pra criar um negócio de R$ 500k+/mês, mas exige dedicação total. Entra só quando os outros estiverem no piloto automático.
