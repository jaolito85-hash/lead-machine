#!/usr/bin/env python3
"""
SPIKE — valida que existe INTENT PESCAVEL de emagrecimento (US) no Reddit.

Coleta posts/comentarios via Apify (trudax/reddit-scraper-lite), classifica a
intencao com gpt-4o e aplica os guard-rails de seguranca do discovery.json.
NAO faz outreach. So prova que da pra encontrar gente com intencao de compra.

Uso:
  py agents/affiliate_us/spike_collect.py                 # 2 queries, 15 itens
  py agents/affiliate_us/spike_collect.py --max-queries 3 --max-items 20
  py agents/affiliate_us/spike_collect.py --no-llm        # sem OpenAI (heuristica)
"""
import argparse
import json
import sys
from pathlib import Path

# Evita UnicodeEncodeError no console do Windows (cp1252)
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = Path(__file__).parent
ROOT = HERE.parent.parent


def load_env() -> dict:
    env = {}
    f = ROOT / ".env"
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def normalize(it: dict) -> dict:
    """Achata um item do actor (post ou comentario) num formato unico."""
    title = it.get("title") or ""
    body = it.get("body") or it.get("text") or it.get("content") or it.get("comment") or ""
    text = (title + "\n" + body).strip()
    kind = it.get("dataType") or it.get("type") or ("post" if title else "comment")
    return {
        "kind": kind,
        "text": text,
        "author": it.get("username") or it.get("author") or it.get("userName") or "?",
        "subreddit": (it.get("communityName") or it.get("subreddit")
                      or it.get("parsedCommunityName") or "?").removeprefix("r/"),
        "url": it.get("url") or it.get("link") or "",
        "upvotes": it.get("upVotes") or it.get("score") or it.get("upvotes") or 0,
    }


# ---- Classificacao heuristica (fallback se OpenAI falhar) ----
BUY = ["recommend", "what should i", "looking for", "anyone tried", "worth it",
       "where to buy", "willing to pay", "suggestions", "best supplement",
       "what helped", "what worked", "anything that"]
SAFETY = ["eating disorder", "anorexi", "bulimi", "purg", "16 year", "15 year",
          "17 year", "underage", "pregnan", "breastfeed", "my doctor", "prescribed"]


def classify_heuristic(text: str) -> dict:
    t = text.lower()
    drop = any(s in t for s in SAFETY)
    hits = sum(1 for s in BUY if s in t)
    score = min(1.0, 0.4 + hits * 0.2) if hits else 0.1
    itype = "buying" if score >= 0.8 else "researching" if score >= 0.5 else "noise"
    return {"intent_type": itype, "score": round(score, 2),
            "desired_category": "", "safety_drop": drop,
            "safety_reason": "heuristic safety match" if drop else ""}


def classify_llm(items, model, api_key, exclusions):
    """Classifica todos os itens numa unica chamada gpt-4o (barato)."""
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    blob = "\n".join(f"[{i}] ({it['kind']} r/{it['subreddit']}) {it['text'][:400]}"
                     for i, it in enumerate(items))
    prompt = f"""You are a lead-intent classifier for a WEIGHT-LOSS affiliate (US market).
For each numbered item, judge the person's intent to BUY a weight-loss product.

intent_type: "buying" (asking for product rec / wants to buy), "researching"
(comparing, asking if X works), "frustrated" (tried everything, nothing works),
or "noise" (no purchase intent / selling / off-topic).
score: 0.0-1.0 likelihood of buying soon.
desired_category: short tag (e.g. appetite_control, protein_shake, fat_burner, sleep_aid) or "".
safety_drop: true if the item shows any of these (NEVER target these): {exclusions}.

Return ONLY a JSON object: {{"results":[{{"i":0,"intent_type":"...","score":0.0,"desired_category":"...","safety_drop":false,"safety_reason":""}}]}}

ITEMS:
{blob}
"""
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0,
    )
    data = json.loads(resp.choices[0].message.content)
    by_i = {r["i"]: r for r in data.get("results", [])}
    return by_i


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-queries", type=int, default=2)
    ap.add_argument("--max-items", type=int, default=15)
    ap.add_argument("--no-llm", action="store_true")
    args = ap.parse_args()

    env = load_env()
    token = env.get("APIFY_TOKEN")
    if not token:
        print("ERRO: APIFY_TOKEN ausente no .env")
        sys.exit(1)

    disc = json.loads((HERE / "discovery.json").read_text(encoding="utf-8"))
    queries = disc["intent_queries"][: args.max_queries]
    exclusions = disc.get("safety_exclusions", {}).get("drop_if", [])
    print(f"[spike] nicho={disc['niche']} | mercado={disc['market']}")
    print(f"[spike] {len(queries)} queries: {queries}")

    # 1) COLETA via Apify
    from apify_client import ApifyClient
    client = ApifyClient(token)
    run_input = {
        "searches": queries,
        "searchPosts": True,
        "searchComments": True,
        "sort": "relevance",
        "time": "year",
        "maxItems": args.max_items,
        "maxPostCount": args.max_items,
        "maxComments": 6,
        "includeNSFW": False,
        "proxy": {"useApifyProxy": True},
    }
    print("[spike] rodando actor trudax/reddit-scraper-lite ... (1-3 min)")
    run = client.actor("trudax/reddit-scraper-lite").call(run_input=run_input, timeout_secs=240)
    raw = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    items = [n for n in (normalize(it) for it in raw) if len(n["text"]) > 20]
    print(f"[spike] coletados {len(raw)} itens crus -> {len(items)} com texto util")
    if not items:
        print("[spike] nada coletado. Tente outras queries ou aumente --max-items.")
        sys.exit(0)

    # 2) CLASSIFICACAO
    use_llm = (not args.no_llm) and bool(env.get("OPENAI_API_KEY"))
    model = env.get("OPENAI_MODEL", "gpt-4o")
    llm_map = {}
    if use_llm:
        print(f"[spike] classificando intent com {model} ...")
        try:
            llm_map = classify_llm(items, model, env["OPENAI_API_KEY"], exclusions)
        except Exception as e:
            print(f"[spike] OpenAI falhou ({e}); usando heuristica.")
            use_llm = False

    for i, it in enumerate(items):
        c = llm_map.get(i) if use_llm else None
        if not c:
            c = classify_heuristic(it["text"])
        it.update(c)

    # 3) GUARD-RAILS + ranking
    safe = [it for it in items if not it.get("safety_drop")]
    dropped = len(items) - len(safe)
    safe.sort(key=lambda x: x.get("score", 0), reverse=True)
    buying = [it for it in safe if it.get("intent_type") == "buying"]
    researching = [it for it in safe if it.get("intent_type") == "researching"]

    # 4) SALVA + RESUMO
    out = HERE / "intent_signals.json"
    out.write_text(json.dumps(safe, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n" + "=" * 60)
    print("RESULTADO DO SPIKE")
    print("=" * 60)
    print(f"  itens uteis coletados : {len(items)}")
    print(f"  descartados (safety)  : {dropped}")
    print(f"  COMPRANDO (buying)    : {len(buying)}")
    print(f"  pesquisando           : {len(researching)}")
    print(f"  salvo em              : {out.relative_to(ROOT)}")
    print("\n--- TOP sinais com maior intencao ---")
    for it in safe[:6]:
        snippet = it["text"].replace("\n", " ")[:140]
        print(f"\n  [{it.get('intent_type')} {it.get('score')}] r/{it['subreddit']} "
              f"cat={it.get('desired_category') or '-'}")
        print(f"  u/{it['author']} | {it['url']}")
        print(f"  \"{snippet}\"")
    print("\n[spike] fim.")


if __name__ == "__main__":
    main()
