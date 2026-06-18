#!/usr/bin/env python3
"""
Coleta de INTENT por PRODUTO (ou nicho) — Reddit via Apify + classificacao gpt-4o.

Acha pessoas com intencao de comprar um produto especifico, aplica os
guard-rails de seguranca e salva em agents/affiliate_{market}/intent_signals.json.
NAO faz outreach. So encontra os compradores.

Uso:
  # busca por PRODUTO especifico (o que a aba do dashboard dispara)
  py agents/affiliate_us/spike_collect.py --market us --product "stanley cup"
  py agents/affiliate_us/spike_collect.py --market br --product "copo stanley"

  # ou roda as queries de nicho do discovery.json daquele mercado
  py agents/affiliate_us/spike_collect.py --market us --max-queries 2
"""
import argparse
import json
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).parent.parent.parent


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


BUY = ["recommend", "what should i", "looking for", "where to buy", "worth it",
       "willing to pay", "suggestions", "best", "what helped", "what worked",
       "anything that", "link?", "where did you", "want one", "thinking of buying"]
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


def classify_llm(items, model, api_key, exclusions, product):
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    target = f'the product "{product}"' if product else "a weight-loss product"
    blob = "\n".join(f"[{i}] ({it['kind']} r/{it['subreddit']}) {it['text'][:400]}"
                     for i, it in enumerate(items))
    prompt = f"""You are a buyer-intent classifier for an affiliate marketer.
For each numbered item, judge the person's intent to BUY {target}.

intent_type: "buying" (wants to buy / asking where to buy / asking for rec),
"researching" (comparing, asking if it's worth it), "frustrated" (unhappy with
current option), or "noise" (no purchase intent / selling / off-topic).
score: 0.0-1.0 likelihood of buying soon.
desired_category: short tag for what they want, or "".
safety_drop: true if the item shows any of these (NEVER target): {exclusions}.

Return ONLY JSON: {{"results":[{{"i":0,"intent_type":"...","score":0.0,"desired_category":"...","safety_drop":false,"safety_reason":""}}]}}

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
    return {r["i"]: r for r in data.get("results", [])}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--market", choices=["us", "br"], default="us")
    ap.add_argument("--product", default="", help="palavra-chave do produto afiliado")
    ap.add_argument("--max-queries", type=int, default=2)
    ap.add_argument("--max-items", type=int, default=15)
    ap.add_argument("--no-llm", action="store_true")
    args = ap.parse_args()

    aff_dir = ROOT / "agents" / f"affiliate_{args.market}"
    env = load_env()
    token = env.get("APIFY_TOKEN")
    if not token:
        print("ERRO: APIFY_TOKEN ausente no .env")
        sys.exit(1)

    disc = json.loads((aff_dir / "discovery.json").read_text(encoding="utf-8"))
    exclusions = disc.get("safety_exclusions", {}).get("drop_if", [])
    product = args.product.strip()
    queries = [product] if product else disc["intent_queries"][: args.max_queries]
    print(f"[busca] mercado={args.market} | alvo={product or '(nicho)'} | queries={queries}")

    # 1) COLETA
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
    print("[busca] rodando trudax/reddit-scraper-lite ... (1-3 min)")
    run = client.actor("trudax/reddit-scraper-lite").call(run_input=run_input, timeout_secs=240)
    raw = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    items = [n for n in (normalize(it) for it in raw) if len(n["text"]) > 20]
    print(f"[busca] {len(raw)} itens crus -> {len(items)} com texto util")
    if not items:
        (aff_dir / "intent_signals.json").write_text("[]", encoding="utf-8")
        print("[busca] nada encontrado pra esse termo.")
        sys.exit(0)

    # 2) CLASSIFICACAO
    use_llm = (not args.no_llm) and bool(env.get("OPENAI_API_KEY"))
    model = env.get("OPENAI_MODEL", "gpt-4o")
    llm_map = {}
    if use_llm:
        print(f"[busca] classificando intent com {model} ...")
        try:
            llm_map = classify_llm(items, model, env["OPENAI_API_KEY"], exclusions, product)
        except Exception as e:
            print(f"[busca] OpenAI falhou ({e}); usando heuristica.")
            use_llm = False
    for i, it in enumerate(items):
        it.update(llm_map.get(i) if use_llm else classify_heuristic(it["text"]))
        it["query"] = product or "(nicho)"
        it["market"] = args.market

    # 3) GUARD-RAILS + ranking
    safe = [it for it in items if not it.get("safety_drop")]
    dropped = len(items) - len(safe)
    safe.sort(key=lambda x: x.get("score", 0), reverse=True)
    buying = sum(1 for it in safe if it.get("intent_type") == "buying")

    # 4) SALVA + RESUMO
    out = aff_dir / "intent_signals.json"
    out.write_text(json.dumps(safe, ensure_ascii=False, indent=2), encoding="utf-8")
    print("=" * 56)
    print(f"  alvo            : {product or '(nicho)'}")
    print(f"  itens uteis     : {len(items)}")
    print(f"  safety dropped  : {dropped}")
    print(f"  COMPRANDO       : {buying}")
    print(f"  salvo em        : {out.relative_to(ROOT)}")
    for it in safe[:5]:
        print(f"  [{it.get('intent_type')} {it.get('score')}] r/{it['subreddit']}: "
              f"{it['text'][:90].replace(chr(10),' ')}")
    print("[busca] fim.")


if __name__ == "__main__":
    main()
