# Vertical 01 — Tia da Carol (Clínica Estética Maringá)

**Status:** Prioridade máxima. Primeiro cliente pagante. Case study #1.
**Horizonte de execução:** 30 a 60 dias.
**Meta de receita:** R$ 2.500 a R$ 3.500 por mês recorrente.

---

## 1. Visão Geral

A tia da Carol é o cliente perfeito para validar o Lead Machine em produção real. Ela já tem dor comprovada, budget alocado, e uma operação manual que pode ser substituída por automação. O objetivo aqui não é inovar — é provar que a máquina funciona com um cliente de verdade, gerando receita, métricas e confiança.

Este vertical não é o maior em potencial de escala. É o mais importante em **velocidade de prova**. Dele nasce tudo.

## 2. Diagnóstico da Situação Atual

O que a tia está fazendo hoje:

- **R$ 5.000/mês** em tráfego pago (Meta Ads — Facebook e Instagram)
- Leads que chegam caem numa caixa de entrada do WhatsApp
- Uma funcionária (provavelmente custa R$ 2.500 a R$ 4.000/mês com encargos) responde cada lead manualmente
- Depois que a funcionária "pré-qualifica", passa os bons para a tia fechar
- Os procedimentos vendidos são harmonização facial, preenchimento, botox, bioestimuladores, etc.

### Dores reais que essa estrutura gera

- **Tempo de resposta lento**: lead que chega às 22h só é atendido no dia seguinte. 40% desses leads somem.
- **Custo humano alto**: a funcionária custa caro, tira férias, fica doente, pede aumento.
- **Inconsistência na qualificação**: em dias ruins, a funcionária passa lead ruim. Em dias bons, deixa escapar bons.
- **Sem métricas reais**: ninguém sabe direito a taxa de conversão de lead pra consulta, de consulta pra venda.
- **Escala travada**: dobrar o tráfego = dobrar a funcionária = dobrar o problema.

## 3. A Proposta Comercial

O pitch para ela deve ser direto:

> *"Tia, vou trocar sua funcionária do WhatsApp por um sistema meu que responde em 30 segundos, 24 horas por dia, e te entrega só os leads quentes prontos pra agendar. Cobro R$ 2.500 por mês. Você economiza em folha e ainda converte mais."*

### Modelo de precificação

**Opção A — Mensalidade simples (recomendado para começar)**
- R$ 2.500/mês fixos
- Sem fidelidade no primeiro mês (ganha confiança)
- Contrato simples, tipo "pacote de serviços"

**Opção B — Mensalidade + performance (a partir do 3º mês)**
- R$ 1.800/mês fixos
- + R$ 100 por agendamento confirmado que comparece na clínica
- Esse modelo alinha incentivos e você ganha mais se o sistema funcionar

**Opção C — Revenue share (para quando tiver muito case)**
- 15% do faturamento gerado por leads entregues pelo sistema
- Exige integração com sistema de agendamento e confiança alta

**Dica de ouro:** começa na opção A. Não tente fazer o modelo perfeito no primeiro cliente. Faça o modelo simples funcionar e evolua.

## 4. Perfil do Lead Ideal (o que o sistema vai qualificar)

A IA precisa identificar um lead "quente" para harmonização/estética. Critérios:

**Lead quente (passa pra tia):**
- Mulher, 25-55 anos (ajusta conforme público dela)
- Já fez procedimento antes ou pesquisou ativamente
- Mora em Maringá ou região num raio de 50km
- Orçamento compatível (pergunta qual procedimento quer saber)
- Disponibilidade nas próximas 2 semanas
- Respondeu ao menos 3 mensagens no WhatsApp (engajamento mínimo)

**Lead morno (entra em nurturing):**
- Demonstrou interesse mas não tem urgência
- Tá pesquisando preço (vai ficar procurando concorrência)
- Agenda mensagem automática pra voltar em 15 e 30 dias

**Lead frio (descarta):**
- Só curioso, sem intenção real
- Fora da região
- Perfil completamente diferente (homem muito jovem perguntando por botox pra testa sem contexto, etc.)

## 5. Arquitetura Técnica

### Como o sistema vai funcionar

```
Meta Ads (Facebook/Instagram)
     ↓
Lead preenche formulário (Lead Ad ou Landing)
     ↓
Webhook dispara pro Paperclip
     ↓
Paperclip cria registro na company "tia-maringa"
     ↓
Agente "conversador" dispara mensagem no WhatsApp
     ↓
IA (Claude API) conversa, qualifica, agenda
     ↓
Lead classificado: quente / morno / frio
     ↓
Se quente: notifica tia + envia pro dashboard dela
Se morno: entra em sequência de nurturing (7, 15, 30 dias)
Se frio: arquiva com motivo
```

### Componentes do Lead Machine que você vai usar

- **Paperclip**: armazena a company "clinica-tia-maringa", guarda leads, histórico de conversas, agenda
- **agent_conversador.py** (novo — você vai criar): recebe webhook, dispara mensagem, mantém contexto
- **agent_qualifier.py** (você já tem): analisa histórico de conversa e classifica o lead
- **agent_enricher.py** (você já tem): enriquece dados do lead (busca Instagram, confirma cidade, etc.)
- **Dashboard da tia**: porta 8082 (replicar o `dashboard/index.html` atual)

### Integração do WhatsApp

Duas opções:

**Opção 1 — WhatsApp Business API oficial (Meta)**
- Mais confiável, não corre risco de ban
- Precisa aprovação da Meta (leva 1-2 semanas)
- Custo: ~R$ 0,05 por conversa iniciada + taxa de setup
- Ideal para volume alto ou quando for escalar

**Opção 2 — Evolution API (não oficial, usando WhatsApp Web)**
- Funciona em minutos
- Grátis (só custa um servidor pequeno pra rodar)
- Risco de ban se exagerar ou parecer spam
- Ideal para começar e testar

**Dica:** comece com Evolution API pra validar o fluxo em 1 semana. Migra pra API oficial no mês 2 ou 3.

## 6. Jornada do Lead (exemplo real)

Imagine que a Maria, 34 anos, ver um anúncio no Instagram às 21h:

**21:00** — Maria clica no anúncio "Harmonização Facial em Maringá - Agenda sua avaliação"
**21:01** — Preenche o formulário: nome, WhatsApp, idade, procedimento de interesse
**21:01:30** — Webhook chega no Paperclip, cria lead na company "tia-maringa"
**21:02** — Primeira mensagem automática no WhatsApp:
> *"Oi Maria! Vi que você tem interesse em harmonização facial. Eu sou a Sofia, assistente virtual da Dra. [nome da tia]. Posso te ajudar com algumas perguntinhas rápidas pra preparar melhor sua avaliação?"*

**21:03** — Maria responde: "Oi, pode"
**21:03:30** — IA: *"Perfeito! Você já fez algum procedimento estético antes?"*
**21:04** — Maria: "Fiz botox uma vez"
... (IA faz 5-8 perguntas de qualificação)
**21:12** — IA já tem: orçamento, urgência, localização, expectativas
**21:12** — IA classifica como QUENTE
**21:13** — IA propõe horário: *"Dra. [nome] tem um horário na quinta às 14h pra avaliação gratuita presencial. Funciona pra você?"*
**21:15** — Maria confirma
**21:16** — Notificação dispara pra tia: "LEAD QUENTE: Maria, 34, harmonização, agendou quinta 14h"
**21:17** — Lead aparece no dashboard com cor verde, histórico completo, botão "confirmar presença"

A funcionária humana faria isso em 2 dias. O sistema faz em 15 minutos.

## 7. Copy e Scripts de Conversação

### Mensagem inicial (quando lead chega)

> *"Oi [nome]! Aqui é a Sofia, assistente da Dra. [nome da tia]. Vi que você pediu informações sobre [procedimento]. Posso fazer 3 perguntinhas rápidas pra já deixar tudo pronto pra sua avaliação?"*

**Princípios da copy:**
- Humanizar (nome próprio: Sofia)
- Ser transparente que é assistente
- Lembrar o que o lead pediu (contextualização)
- Combinar "3 perguntinhas" (baixa fricção, quebra objeção)
- Tom carinhoso mas profissional (público feminino, estética)

### Perguntas de qualificação (em ordem)

1. *"Você já fez algum procedimento estético antes? Se sim, qual e quando foi?"*
2. *"Qual incômodo te fez procurar [o procedimento]? O que você quer melhorar?"*
3. *"Você tá com pressa ou pode agendar pra semana que vem/daqui 15 dias?"*
4. *"Você mora em Maringá mesmo ou em qual cidade?"*
5. *"Qual a melhor faixa de horário pra você? Manhã, tarde ou depois do trabalho?"*

**Dica importante:** não pergunte preço direto. Se o lead perguntar, responda: *"O valor depende muito da avaliação. Na consulta a Dra. avalia tudo e te passa o orçamento personalizado. A avaliação é gratuita."*

### Objeções comuns e respostas

**"Quanto custa?"**
> *"Depende do seu caso, [nome]. Por isso a Dra. faz avaliação presencial gratuita — ela vê sua estrutura, entende o que você quer, e te passa um orçamento sob medida. Te interessa agendar?"*

**"Vou pensar e te aviso"**
> *"Claro, [nome]. Quer que eu reserve um horário provisório? Você pode cancelar depois sem compromisso."*

**"Quanto tempo dura?"**
> *"O efeito varia de 6 meses a 2 anos, depende do produto e do seu metabolismo. Na avaliação a Dra. te explica direitinho. Posso agendar?"*

### Nurturing (lead morno)

**Dia 3 após primeiro contato (se não agendou):**
> *"Oi [nome], tudo bem? Aqui é a Sofia. Quero só te lembrar que seu orçamento personalizado ainda tá disponível. Quer que eu reserve um horário pra essa semana?"*

**Dia 10:**
> *"Oi [nome], passando pra avisar: a Dra. abriu 3 horários pra próxima semana com desconto de avaliação. Quer conhecer? (a avaliação continua gratuita, mas nesse lote tem cupom pro procedimento)."*

**Dia 30:**
> *"Oi [nome], a Dra. tá com agenda do mês cheia mas conseguiu abrir 2 horários. Se ainda tiver interesse, me avisa que eu reservo."*

## 8. KPIs e Métricas

O que você vai medir e mostrar pra tia (no dashboard):

| Métrica | Meta no mês 1 | Meta no mês 3 |
|---|---|---|
| Tempo médio de primeira resposta | < 2 minutos | < 30 segundos |
| Taxa de resposta do lead (responde 1ª msg) | > 60% | > 75% |
| Taxa de qualificação (completa o fluxo) | > 30% | > 45% |
| Taxa de agendamento sobre leads quentes | > 50% | > 65% |
| Taxa de comparecimento na consulta | > 40% | > 55% |
| Custo por agendamento (CPA) | Ela já sabe o dela | -20% vs manual |

**Dica de ouro:** no dashboard da tia, coloca esses números GRANDES em destaque. Cliente que vê número crescendo paga mensalidade feliz.

## 9. Plano de Execução (cronograma)

### Semana 1 — Setup

- [ ] Conversa formal com a tia: pitch, fechamento, contrato simples
- [ ] Cria company "clinica-tia-maringa" no Paperclip
- [ ] Configura Evolution API com o número dela (ou cria um número novo)
- [ ] Mapeia os procedimentos dela e preços (pelo menos faixa)
- [ ] Cria o `agent_conversador.py` com o prompt inicial

### Semana 2 — Piloto em paralelo

- [ ] Sistema roda em paralelo com a funcionária (não substitui ainda)
- [ ] Compara: mesmo lead, como a IA qualifica vs. como a humana qualifica
- [ ] Ajusta prompts baseado nas divergências
- [ ] Cria dashboard em porta 8082

### Semana 3 — Go-live gradual

- [ ] 30% dos leads vão pra IA, 70% pra funcionária
- [ ] Tia e funcionária validam qualidade dos leads da IA
- [ ] Ajusta problemas identificados

### Semana 4 — 100% IA

- [ ] Todos os leads passam pela IA primeiro
- [ ] Funcionária agora só faz tarefas mais estratégicas (ou a tia reavalia o papel dela)
- [ ] Primeiro relatório mensal pra tia com todos os números

### Mês 2 — Otimização

- [ ] Migra pra WhatsApp Business API oficial se volume justificar
- [ ] A/B teste de copy (2 versões da mensagem inicial)
- [ ] Ajustes finos de qualificação
- [ ] Primeiro vídeo/depoimento da tia elogiando o sistema (PRA USAR DEPOIS)

### Mês 3 — Case study pronto

- [ ] Documentar resultados com números concretos
- [ ] Gravar depoimento da tia em vídeo
- [ ] Criar case de estudo em PDF bonito
- [ ] **Esse material vira sua arma para vender pros próximos clientes**

## 10. Riscos e Precauções

### Riscos técnicos

**WhatsApp ban (se usar Evolution API):**
- Mitigação: começa com volume baixo, aumenta gradualmente
- Mitigação: jamais manda mensagem em massa "spam"; só responde quem veio do anúncio
- Mitigação: migra pra API oficial no mês 2

**IA alucinando (inventando coisas):**
- Mitigação: prompt bem específico, com instruções claras do que NÃO pode dizer
- Mitigação: nunca deixar IA dar preço, prometer resultado, ou falar sobre procedimento que a tia não oferece
- Mitigação: testa com 20-30 conversas reais antes de liberar

### Riscos comerciais

**Tia querer pagar menos ou atrasar:**
- Mitigação: contrato simples por escrito (nem precisa ser registrado)
- Mitigação: mensalidade via PIX automático
- Mitigação: deixa claro desde o início que é relação profissional, não familiar

**Funcionária atual ficar "contra" o sistema:**
- Muito comum. Ela se sente ameaçada.
- Mitigação: envolver ela no processo. Pedir a opinião dela. Ela vira aliada, não inimiga.
- Mitigação: talvez ela continue no time com outro papel (fechamento de venda, por exemplo)

### Riscos regulatórios

**LGPD (Lei Geral de Proteção de Dados):**
- O formulário no anúncio **precisa** ter consentimento explícito
- Guardar base legal (interesse legítimo + consentimento)
- Direito ao esquecimento: se o lead pedir, apagar
- Política de privacidade no site/landing

**CFO (Conselho Federal de Odontologia) — se a tia for dentista:**
- Publicidade em estética odontológica tem regras
- Mas estética facial (harmonização não odonto) é com CRM se for médica, ou livre se for biomédica
- Confere qual é o registro dela e adequa o tom

## 11. Checklist de Próximos Passos (Agora)

Passos concretos pra essa semana:

- [ ] **Marcar conversa com a tia** (café, jantar, lá na clínica). Levar o pitch pronto.
- [ ] **Pedir acesso aos números dela atuais**: quantos leads/mês, custo por lead, taxa de agendamento. Sem isso, você não tem baseline.
- [ ] **Pedir acesso ao Meta Ads dela** (pode adicionar você como parceiro). Assim você vê os anúncios e o formulário.
- [ ] **Definir o preço final** (R$ 2.500 mensal é um bom ponto de partida)
- [ ] **Assinar um contrato simples** (pode ser só um email trocado com os termos básicos)
- [ ] **Configurar ambiente Evolution API** no seu servidor
- [ ] **Criar company "clinica-tia-maringa"** no Paperclip
- [ ] **Definir a prompt base** do `agent_conversador.py` pra harmonização

**Dica de ouro final:** não espera tudo estar perfeito pra fechar com ela. Fecha primeiro, depois construa. Cliente pagando é o maior motivador que existe pra finalizar código.
