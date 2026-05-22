"""
Classificador de intencao de comentarios.

Dois modos:
  - heuristic: regex + keywords (gratis, rapido, menos preciso)
  - claude:    chama a API da Anthropic (paga, mais preciso, com cidade detectada)

DICA: por padrao fica em heuristic pra ter volume e velocidade. Quando quiser
uma revisao mais cara/precisa, ligue LEADS_USE_LLM=1.
"""

import functools
import json
import logging
import os
import re
from pathlib import Path
from typing import Optional

# paperclip/agents/comment_collector/classifier.py -> paperclip/
_BASE_DIR = Path(__file__).resolve().parent.parent.parent
PROMPTS_DIR = _BASE_DIR / "prompts"

# ── Mapeamento estado <> regiao do Brasil ──
ESTADOS = {
    "AC": ("Acre", "norte"), "AL": ("Alagoas", "nordeste"),
    "AM": ("Amazonas", "norte"), "AP": ("Amapa", "norte"),
    "BA": ("Bahia", "nordeste"), "CE": ("Ceara", "nordeste"),
    "DF": ("Distrito Federal", "centro-oeste"), "ES": ("Espirito Santo", "sudeste"),
    "GO": ("Goias", "centro-oeste"), "MA": ("Maranhao", "nordeste"),
    "MG": ("Minas Gerais", "sudeste"), "MS": ("Mato Grosso do Sul", "centro-oeste"),
    "MT": ("Mato Grosso", "centro-oeste"), "PA": ("Para", "norte"),
    "PB": ("Paraiba", "nordeste"), "PE": ("Pernambuco", "nordeste"),
    "PI": ("Piaui", "nordeste"), "PR": ("Parana", "sul"),
    "RJ": ("Rio de Janeiro", "sudeste"), "RN": ("Rio Grande do Norte", "nordeste"),
    "RO": ("Rondonia", "norte"), "RR": ("Roraima", "norte"),
    "RS": ("Rio Grande do Sul", "sul"), "SC": ("Santa Catarina", "sul"),
    "SE": ("Sergipe", "nordeste"), "SP": ("Sao Paulo", "sudeste"),
    "TO": ("Tocantins", "norte"),
}

# Cidades grandes -> UF (lista nao exaustiva, expanda conforme aparecer nos comentarios)
CIDADES_PRINCIPAIS = {
    "sao paulo": "SP", "sp": "SP",
    "rio de janeiro": "RJ", "rj": "RJ",
    "belo horizonte": "MG", "bh": "MG",
    "brasilia": "DF",
    "salvador": "BA", "fortaleza": "CE",
    "curitiba": "PR", "porto alegre": "RS",
    "manaus": "AM", "recife": "PE", "goiania": "GO",
    "belem": "PA", "guarulhos": "SP", "campinas": "SP",
    "sao luis": "MA", "maceio": "AL", "natal": "RN",
    "teresina": "PI", "joao pessoa": "PB", "aracaju": "SE",
    "florianopolis": "SC", "vitoria": "ES", "cuiaba": "MT",
    "campo grande": "MS", "macapa": "AP", "rio branco": "AC",
    "boa vista": "RR", "porto velho": "RO", "palmas": "TO",
    "maringa": "PR", "londrina": "PR",
    "ribeirao preto": "SP", "santos": "SP", "sorocaba": "SP",
    "uberlandia": "MG", "juiz de fora": "MG", "contagem": "MG",
    "feira de santana": "BA", "vitoria da conquista": "BA",
    "joinville": "SC", "blumenau": "SC", "sao jose": "SC",
    "caxias do sul": "RS", "pelotas": "RS",
    "niteroi": "RJ", "duque de caxias": "RJ", "nova iguacu": "RJ",
    "olinda": "PE", "jaboatao": "PE", "caruaru": "PE",
}


def _normalize(text: str) -> str:
    """Remove acentos e baixa caso pra matching."""
    import unicodedata
    nfkd = unicodedata.normalize("NFKD", text or "")
    no_accent = "".join(c for c in nfkd if not unicodedata.combining(c))
    return no_accent.lower()


# ════════════════════════════════════════
# CLASSIFIER HEURISTICO (sem IA)
# ════════════════════════════════════════

INTENT_PATTERNS = {
    "buscando_atendimento": [
        r"\bpreciso\b", r"\bquero\b", r"\bquer[ou]\b", r"\beu q\b",
        r"\bgostaria\b", r"\bqueria\b", r"\binteressad[ao]\b",
        r"\bagendar?\b", r"\bagenda(mento)?\b", r"\bmarcar\b", r"\bcomo marca",
        r"\bme ajud", r"\bcomo (faco|faz|consigo)\b", r"\baceita\b.*consult",
        r"\bmeu filho\b.*precisa", r"\bminha filha\b.*precisa",
        r"\baten[dc]e\b.*minh", r"\baten[dc]e\b.*meu",
        r"\b(me|mi|mim)\s+chama\b",
        r"\b(me|mi|mim)\s+cham[ae]\s+(no|na|por|pelo|pela)?\s*(privado|pv|pvd|priv|inbox|direct|dm|particular)\b",
        r"\bcham[ae]?\s+(no|na|por|pelo|pela)?\s*(privado|pv|pvd|priv|inbox|direct|dm|particular)\b",
        r"\bmanda\b.*(contato|privado|pv|pvd|inbox|direct|dm|whats)",
        r"\bchama.*(whats|privado|pv|pvd|inbox|direct|dm)",
        # Apostas: intencao de registrar/apostar
        r"\bcomo (me )?cadastr", r"\bquero (me )?cadastr", r"\bcomo (que )?aposta",
        r"\bquero jogar\b", r"\bquero apostar\b", r"\bcomo entrar\b",
        r"\btem (como|pra) come[cç]ar\b", r"\bme indica uma casa\b",
        r"\bqual casa\b.*(confiavel|confiável|boa|melhor|paga)",
        r"\bme passa o link\b", r"\btem o link\b",
    ],
    "perguntando_preco": [
        r"\bquanto\b.*custa", r"\bvalor\b", r"\bvcalor\b", r"\bpre[cç]o\b",
        r"\borcamento\b", r"\bparcela", r"\bconvenio\b",
        r"\bplano\b.*saude", r"\bquanto\b.*sai", r"\bquanto\b.*fica",
        r"\bvlr\b", r"\bvl\b", r"\bfalar.*pre[cç]o", r"\btem.*pre[cç]o",
        r"\bvcalo", r"\bvalo(r+|res)\b", r"\bqnt.*custa",
        # Apostas: perguntas sobre bonus, deposito, saque
        r"\bb[oô]nus\b", r"\bbonus de (quanto|primeiro)", r"\bprimeiro dep[oó]sito\b",
        r"\bdep[oó]sito m[ií]nimo\b", r"\bquanto precisa depositar\b",
        r"\bvale a pena\b.*casa", r"\baceita pix\b", r"\btem pix\b",
        r"\bsaque\b.*(rapido|rápido|demora|direto|liberado)",
        r"\bpaga mesmo\b", r"\bpaga direito\b", r"\bessa casa paga\b",
        r"\bdemora pra (pagar|sacar|liberar)", r"\brollover\b",
    ],
    "apostador_ativo": [
        # Jargao direto de resultado positivo — apostador engajado
        r"\bdeu green\b", r"\bfoi green\b", r"\bmuito green\b", r"\bgreens\b",
        r"\bfechou green\b", r"\bgreen na\b", r"\bgreen em\b",
        r"\bestou no verde\b", r"\bt[oô] no verde\b",
        # Mercados e jargao tecnico
        r"\bodds?\b", r"\bhandicap\b", r"\bcashout\b", r"\bcash out\b",
        r"\bunder\b.*(\d|gol|\.5|\.25)", r"\bover\b.*(\d|gol|\.5|\.25)",
        r"\bml(s)?\b.*(gols?|cartoes|escanteios)", r"\bambos marcam\b",
        r"\bescanteio\b", r"\bsimples\b.*aposta",
        r"\bmultipla\b", r"\bmult\b", r"\baposta multipla\b",
        r"\btiro\b.*odds?", r"\btiro\b.*(simples|multipla)",
        r"\bbanca\b.*(apost|bet|vai|cresc|turbin)",
        r"\bstake\b", r"\bstacando\b",
        # Casas especificas (se citou = apostador reconhece o mercado)
        r"\bbetano\b", r"\bbet365\b", r"\bpixbet\b", r"\bblaze\b",
        r"\bsportingbet\b", r"\bsuperbet\b", r"\bestrelabet\b", r"\bestrela bet\b",
        r"\bbrazino\b", r"\bkto\b", r"\brivalo\b", r"\bsportsbet\b",
        r"\baposta ganha\b", r"\bgalera bet\b", r"\bnovibet\b",
        r"\bbetfair\b", r"\bbetway\b", r"\b1xbet\b",
        # Saques/depositos com verbo ativo (ja e cliente)
        r"\bsaquei\b", r"\bdepositei\b", r"\bdeposita\w* ai\b",
        r"\bbanco ja caiu\b", r"\bcaiu rapido\b", r"\bpagou na hora\b",
        r"\bpagou rapido\b", r"\bpagou em\b.*minuto",
        # Pergunta tecnica de quem ja aposta
        r"\bmelhor casa\b", r"\bqual casa (paga|saca|credita)\b",
        r"\bcasa que paga\b", r"\bmelhores odds\b", r"\bmais odds\b",
        r"\bqual a melhor\b.*(bet|casa|aposta)",
    ],
    "perguntando_local": [
        r"\bonde\b.*fica", r"\bonde\b.*atende", r"\bem qual\b",
        r"\bcidade\b", r"\batende\b.*em\b", r"\btem\b.*em\b",
        r"\baqui em\b", r"\baqui no\b", r"\bna minha cidade\b",
    ],
    "elogio": [
        r"\blind", r"\bmaravilhos", r"\bperfeit", r"\bincriv",
        r"\bamei\b", r"\bamo\b", r"\babencoad", r"\banj",
        r"\bdeus\b.*abencoe", r"\bque trabalho\b", r"\bemocionante\b",
    ],
}


def classify_heuristic(text: str) -> dict:
    """Classifica intencao por regex. Retorna dict completo."""
    norm = _normalize(text)

    # Detectar intencao (prioridade: atendimento explicito > preco > apostador ativo
    # > pergunta de local > elogio > outros).
    intent = "outros"
    for candidate in ["buscando_atendimento", "perguntando_preco",
                      "apostador_ativo", "perguntando_local", "elogio"]:
        if any(re.search(p, norm) for p in INTENT_PATTERNS[candidate]):
            intent = candidate
            break

    # Score baseado em intencao
    score_map = {
        "buscando_atendimento": 90,
        "perguntando_preco": 80,
        "apostador_ativo": 82,   # apostador engajado: ja e cliente do nicho, otimo pra conversao
        "perguntando_local": 70,
        "elogio": 20,
        "outros": 30,
    }
    lead_score = score_map[intent]

    # Urgencia: palavras como "urgente", "ja", "hoje", "preciso" boostam
    urgency = "baixa"
    if any(w in norm for w in ["urgente", "urgencia", "ja", "hoje", "agora"]):
        urgency = "alta"
        lead_score = min(100, lead_score + 5)
    elif intent in ("buscando_atendimento", "perguntando_preco", "apostador_ativo"):
        urgency = "media"

    # Detectar cidade/estado
    city, state, region = _extract_location(norm)

    # Boost se mencionou cidade (intencao + local = lead muito mais quente)
    if city and intent in ("buscando_atendimento", "perguntando_preco", "perguntando_local"):
        lead_score = min(100, lead_score + 5)

    return {
        "intent": intent,
        "urgency": urgency,
        "lead_score": lead_score,
        "city": city,
        "state": state,
        "region": region,
        "classifier": "heuristic",
        "raw_reasoning": None,
    }


def _extract_location(norm_text: str) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """Tenta extrair cidade/UF/regiao do texto normalizado."""
    # Busca cidade
    for cidade, uf in CIDADES_PRINCIPAIS.items():
        # \b nao funciona bem com espacos no meio, entao usa lookahead/behind
        if re.search(rf"(^|[^a-z]){re.escape(cidade)}([^a-z]|$)", norm_text):
            estado_nome, regiao = ESTADOS[uf]
            return (cidade.title(), uf, regiao)

    # Busca UF isolada (ex: "moro em SP", "aqui no RJ")
    uf_match = re.search(r"\b(em|no|na|aqui)\s+([a-z]{2})\b", norm_text)
    if uf_match:
        uf = uf_match.group(2).upper()
        if uf in ESTADOS:
            estado_nome, regiao = ESTADOS[uf]
            return (None, uf, regiao)

    return (None, None, None)


# ════════════════════════════════════════
# CLASSIFIER CLAUDE (com IA)
# ════════════════════════════════════════

# Mapa NICHO -> prompt file. Match por substring (case-insensitive).
# Adicione mais nichos aqui criando prompts/classifier_<nome>.md
NICHO_PROMPT_MAP = {
    "divida_rural": [
        "divida rural", "dividas rurais", "dívida rural", "dívidas rurais",
        "divida agro", "rural endividado", "pronaf", "advogado agrario",
        "advogado agrário", "credito rural", "crédito rural",
        "divida agricola", "dívida agrícola", "renegociacao rural",
        "renegociação rural",
    ],
    "pne": [
        "pne", "necessidades especiais", "carol pantaleao",
        "carol pantaleão", "dentista pne", "odonto pne",
    ],
}


@functools.lru_cache(maxsize=8)
def _load_prompt_file(name: str) -> str:
    """Le e cacheia o conteudo de prompts/classifier_<name>.md."""
    path = PROMPTS_DIR / f"classifier_{name}.md"
    if not path.exists():
        path = PROMPTS_DIR / "classifier_default.md"
    return path.read_text(encoding="utf-8").strip()


def _resolve_system_prompt(nicho: str = "") -> str:
    """Resolve o system prompt do classifier a partir do nicho da busca.

    Override manual: env LEADS_CLASSIFIER_PROMPT=<id> forca um prompt especifico
    (ex: LEADS_CLASSIFIER_PROMPT=divida_rural).
    """
    override = os.environ.get("LEADS_CLASSIFIER_PROMPT", "").strip().lower()
    if override:
        return _load_prompt_file(override)

    if not nicho:
        return _load_prompt_file("default")

    norm = nicho.lower().strip()
    for nicho_id, keywords in NICHO_PROMPT_MAP.items():
        if any(kw in norm for kw in keywords):
            return _load_prompt_file(nicho_id)
    return _load_prompt_file("default")


def classify_openai(text: str, api_key: str, model: str = "gpt-4o-mini",
                    system_prompt: str = "") -> dict:
    """Classifica via API OpenAI. Retorna dict no mesmo formato do heuristico."""
    try:
        from openai import OpenAI
    except ImportError:
        raise RuntimeError(
            "Pacote 'openai' nao instalado. Rode: pip install openai"
        )

    if not system_prompt:
        system_prompt = _resolve_system_prompt(os.environ.get("NICHO", ""))

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        max_tokens=300,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ],
    )

    raw = response.choices[0].message.content.strip()
    # Defesa: alguns modelos ainda embrulham em markdown
    if raw.startswith("```"):
        raw = re.sub(r"^```(json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

    parsed = json.loads(raw)

    # Resolver state -> region
    state = parsed.get("state")
    region = ESTADOS.get(state, (None, None))[1] if state in ESTADOS else None

    return {
        "intent": parsed.get("intent", "outros"),
        "urgency": parsed.get("urgency", "baixa"),
        "lead_score": int(parsed.get("lead_score", 0)),
        "city": parsed.get("city"),
        "state": state,
        "region": region,
        "classifier": "openai",
        "raw_reasoning": parsed.get("reasoning"),
    }


# ════════════════════════════════════════
# INTERFACE UNIFICADA
# ════════════════════════════════════════

# Flag em memoria: uma vez que o LLM falhar com erro fatal (sem credito, key
# invalida, rate limit persistente), paramos de tentar pelo resto desta execucao.
# Isso evita enviar 1000+ requests identicas quando a API esta claramente fora.
_LLM_DISABLED_REASON: str | None = None

_FATAL_LLM_MARKERS = (
    "credit balance", "insufficient_quota", "invalid_api_key",
    "authentication_error", "invalid x-api-key", "permission_error",
    "invalid_request_error", "billing_hard_limit_reached",
    "incorrect api key",
)


def _is_fatal_llm_error(err: Exception) -> bool:
    msg = str(err).lower()
    return any(m in msg for m in _FATAL_LLM_MARKERS)


def classify(text: str, logger: logging.Logger | None = None) -> dict:
    """
    Classifica um comentario. Por padrao usa heuristic (rapido/gratis).
    Se LEADS_USE_LLM=1, tenta OpenAI primeiro e cai pra heuristic se falhar.

    Variaveis de ambiente:
      OPENAI_API_KEY  — se setada, usa GPT
      OPENAI_MODEL    — modelo (default: gpt-4o-mini)
      LEADS_USE_LLM=1 — liga IA por comentario (alias antigo: LEADS_USE_CLAUDE=1)
      LEADS_CLASSIFIER_MODE=heuristic|openai — override explicito
    """
    global _LLM_DISABLED_REASON
    log = logger or logging.getLogger(__name__)
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()

    mode = os.environ.get("LEADS_CLASSIFIER_MODE", "").strip().lower()
    if mode in ("heuristic", "heuristica", "regex", "fast"):
        return classify_heuristic(text)
    if mode in ("openai", "llm", "ai", "ia"):
        use_llm_flag = "1"
    else:
        # Default rapido: nao chama IA por comentario sem opt-in explicito.
        use_llm_flag = (
            os.environ.get("LEADS_USE_LLM")
            or os.environ.get("LEADS_USE_CLAUDE")
            or "0"
        ).strip().lower()

    if use_llm_flag not in ("1", "true", "yes", "on"):
        return classify_heuristic(text)

    # Se LLM ja foi marcado como indisponivel nesta execucao, nao tenta de novo
    if api_key and _LLM_DISABLED_REASON is None:
        try:
            model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
            return classify_openai(text, api_key, model)
        except Exception as e:
            if _is_fatal_llm_error(e):
                _LLM_DISABLED_REASON = str(e)[:160]
                log.error(
                    f"OpenAI desabilitado pelo resto da execucao: {_LLM_DISABLED_REASON}"
                )
                log.error("Todos os proximos comentarios serao classificados por heuristica (gratuito).")
            else:
                # Erro transitorio (rate limit, timeout) — so avisa, segue heuristica deste item
                log.warning(f"OpenAI falhou neste item ({e}), usando heuristic so pra este")

    return classify_heuristic(text)
