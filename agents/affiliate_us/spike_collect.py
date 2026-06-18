#!/usr/bin/env python3
"""
Coleta de INTENT por PRODUTO (ou nicho), multi-plataforma — Reddit + TikTok.

Acha pessoas com intencao de comprar um produto, classifica com gpt-4o,
aplica guard-rails e salva em agents/affiliate_{market}/intent_signals.json.

Uso:
  py agents/affiliate_us/spike_collect.py --market us --product "stanley cup" --platform tiktok
  py agents/affiliate_us/spike_collect.py --market br --product "copo stanley" --platform both
  py agents/affiliate_us/spike_collect.py --market us --platform reddit --max-queries 2
"""
import argparse
import json
import logging
import os
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


# ─────────────────────── COLETORES ───────────────────────

def normalize_reddit(it: dict) -> dict:
    title = it.get("title") or ""
    body = it.get("body") or it.get("text") or it.get("content") or it.get("comment") or ""
    text = (title + "\n" + body).strip()
    kind = it.get("dataType") or it.get("type") or ("post" if title else "comment")
    sub = (it.get("communityName") or it.get("subreddit")
           or it.get("parsedCommunityName") or "?").removeprefix("r/")
    return {
        "platform": "reddit", "kind": kind, "text": text,
        "author": it.get("username") or it.get("author") or it.get("userName") or "?",
        "source": f"r/{sub}" if sub and sub != "?" else "?",
        "subreddit": sub,
        "url": it.get("url") or it.get("link") or "",
        "upvotes": it.get("upVotes") or it.get("score") or it.get("upvotes") or 0,
    }


def collect_reddit(token, queries, max_items, log):
    from apify_client import ApifyClient
    client = ApifyClient(token)
    run_input = {
        "searches": queries, "searchPosts": True, "searchComments": True,
        "sort": "relevance", "time": "year", "maxItems": max_items,
        "maxPostCount": max_items, "maxComments": 6, "includeNSFW": False,
        "proxy": {"useApifyProxy": True},
    }
    log.info(f"[reddit] rodando trudax/reddit-scraper-lite {queries}")
    run = client.actor("trudax/reddit-scraper-lite").call(run_input=run_input, timeout_secs=240)
    raw = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    items = [n for n in (normalize_reddit(it) for it in raw) if len(n["text"]) > 20]
    log.info(f"[reddit] {len(raw)} crus -> {len(items)} uteis")
    return items


def collect_tiktok(token, query, max_videos, max_comments, log):
    """Busca videos pelo produto e coleta os comentarios (intent de compra)."""
    sys.path.insert(0, str(ROOT / "agents" / "comment_collector"))
    import tiktok_collector as tt
    videos = tt.search_videos_by_query(token, query, limit=max_videos, logger=log)
    urls = [v["video_url"] for v in videos if v.get("video_url")][:max_videos]
    if not urls:
        log.info("[tiktok] nenhum video encontrado")
        return []
    comments = tt.fetch_comments(token, urls, max_comments_per_video=max_comments, logger=log)
    items = []
    for c in comments:
        text = (c.get("text") or "").strip()
        if len(text) < 8:
            continue
        author = c.get("author_username") or "?"
        items.append({
            "platform": "tiktok", "kind": "comment", "text": text,
            "author": author, "source": f"@{author}",
            "url": c.get("video_url") or c.get("author_url") or "",
            "upvotes": c.get("like_count", 0),
        })
    log.info(f"[tiktok] {len(comments)} comentarios -> {len(items)} uteis")
    return items


def collect_instagram(token, query, max_posts, max_comments, log):
    """Busca posts por hashtag do produto e coleta os comentarios."""
    sys.path.insert(0, str(ROOT / "agents" / "comment_collector"))
    import instagram_collector as ig
    posts = ig.search_posts_by_query(token, query, limit=max_posts, logger=log)
    urls = [p["video_url"] for p in posts if p.get("video_url")][:max_posts]
    if not urls:
        log.info("[instagram] nenhum post encontrado")
        return []
    comments = ig.fetch_comments(token, urls, max_comments_per_post=max_comments, logger=log)
    items = []
    for c in comments:
        text = (c.get("text") or "").strip()
        if len(text) < 8:
            continue
        author = c.get("author_username") or "?"
        items.append({
            "platform": "instagram", "kind": "comment", "text": text,
            "author": author, "source": f"@{author}",
            "url": c.get("video_url") or c.get("author_url") or "",
            "upvotes": c.get("like_count", 0),
        })
    log.info(f"[instagram] {len(comments)} comentarios -> {len(items)} uteis")
    return items


# ─────────────────────── CLASSIFICACAO ───────────────────────

BUY = ["recommend", "what should i", "looking for", "where to buy", "worth it",
       "willing to pay", "suggestions", "best", "link?", "where did you", "want one",
       "onde compro", "onde comprar", "qual link", "quanto custa", "tem link", "quero um"]
SAFETY = ["eating disorder", "anorexi", "bulimi", "16 year", "underage", "pregnan",
          "my doctor", "prescribed", "transtorno alimentar", "menor de idade"]


def classify_heuristic(text: str) -> dict:
    t = text.lower()
    drop = any(s in t for s in SAFETY)
    hits = sum(1 for s in BUY if s in t)
    score = min(1.0, 0.4 + hits * 0.2) if hits else 0.1
    itype = "buying" if score >= 0.8 else "researching" if score >= 0.5 else "noise"
    return {"intent_type": itype, "score": round(score, 2), "desired_category": "",
            "safety_drop": drop, "safety_reason": "heuristic" if drop else ""}


def classify_llm(items, model, api_key, exclusions, product):
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    target = f'the product "{product}"' if product else "the niche product"
    blob = "\n".join(f"[{i}] ({it['platform']}:{it.get('source','')}) {it['text'][:400]}"
                     for i, it in enumerate(items))
    prompt = f"""You are a buyer-intent classifier for an affiliate marketer.
For each numbered item, judge the person's intent to BUY {target}.

intent_type: "buying" (wants to buy / asking where to buy / asking for a link or rec),
"researching" (comparing, asking if it's worth it), "frustrated" (unhappy with current
option), or "noise" (no purchase intent / selling / off-topic).
score: 0.0-1.0 likelihood of buying soon.
desired_category: short tag, or "".
safety_drop: true if the item shows any of these (NEVER target): {exclusions}.
Items may be in English or Portuguese.

Return ONLY JSON: {{"results":[{{"i":0,"intent_type":"...","score":0.0,"desired_category":"...","safety_drop":false,"safety_reason":""}}]}}

ITEMS:
{blob}
"""
    resp = client.chat.completions.create(
        model=model, messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}, temperature=0)
    data = json.loads(resp.choices[0].message.content)
    return {r["i"]: r for r in data.get("results", [])}


# ─────────────────────── MAIN ───────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--market", choices=["us", "br"], default="us")
    ap.add_argument("--product", default="", help="palavra-chave do produto afiliado")
    ap.add_argument("--platform", choices=["reddit", "tiktok", "instagram", "all"], default="reddit")
    ap.add_argument("--max-queries", type=int, default=2)
    ap.add_argument("--max-items", type=int, default=15)
    ap.add_argument("--tt-videos", type=int, default=5)
    ap.add_argument("--tt-comments", type=int, default=30)
    ap.add_argument("--ig-posts", type=int, default=8)
    ap.add_argument("--ig-comments", type=int, default=15)
    ap.add_argument("--no-llm", action="store_true")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    log = logging.getLogger("busca")

    aff_dir = ROOT / "agents" / f"affiliate_{args.market}"
    env = load_env()
    # propaga .env pro ambiente — coletores (ex: Instagram) leem INSTAGRAM_SESSIONID
    # e IG_COMMENTS_MODE direto de os.environ
    for k, v in env.items():
        if v:
            os.environ[k] = v
    token = env.get("APIFY_TOKEN")
    if not token:
        print("ERRO: APIFY_TOKEN ausente no .env")
        sys.exit(1)

    disc = json.loads((aff_dir / "discovery.json").read_text(encoding="utf-8"))
    exclusions = disc.get("safety_exclusions", {}).get("drop_if", [])
    product = args.product.strip()
    queries = [product] if product else disc["intent_queries"][: args.max_queries]
    tt_query = product or (queries[0] if queries else "")
    print(f"[busca] mercado={args.market} | plataforma={args.platform} | alvo={product or '(nicho)'}")

    # 1) COLETA
    items = []
    if args.platform in ("reddit", "all"):
        try:
            items += collect_reddit(token, queries, args.max_items, log)
        except Exception as e:
            log.info(f"[reddit] falhou: {e}")
    if args.platform in ("tiktok", "all") and tt_query:
        try:
            items += collect_tiktok(token, tt_query, args.tt_videos, args.tt_comments, log)
        except Exception as e:
            log.info(f"[tiktok] falhou: {e}")
    if args.platform in ("instagram", "all") and tt_query:
        try:
            items += collect_instagram(token, tt_query, args.ig_posts, args.ig_comments, log)
        except Exception as e:
            log.info(f"[instagram] falhou: {e}")

    if not items:
        (aff_dir / "intent_signals.json").write_text("[]", encoding="utf-8")
        print("[busca] nada encontrado pra esse termo.")
        sys.exit(0)

    # 2) CLASSIFICACAO
    use_llm = (not args.no_llm) and bool(env.get("OPENAI_API_KEY"))
    model = env.get("OPENAI_MODEL", "gpt-4o")
    llm_map = {}
    if use_llm:
        print(f"[busca] classificando {len(items)} itens com {model} ...")
        try:
            llm_map = classify_llm(items, model, env["OPENAI_API_KEY"], exclusions, product)
        except Exception as e:
            print(f"[busca] OpenAI falhou ({e}); heuristica.")
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
    by_plat = {}
    for it in safe:
        by_plat[it["platform"]] = by_plat.get(it["platform"], 0) + 1
    print("=" * 56)
    print(f"  alvo            : {product or '(nicho)'}")
    print(f"  por plataforma  : {by_plat}")
    print(f"  itens uteis     : {len(items)} | safety dropped: {dropped}")
    print(f"  COMPRANDO       : {buying}")
    print(f"  salvo em        : {out.relative_to(ROOT)}")
    for it in safe[:5]:
        print(f"  [{it.get('intent_type')} {it.get('score')}] {it['platform']}:{it.get('source')} "
              f"{it['text'][:80].replace(chr(10), ' ')}")
    print("[busca] fim.")


if __name__ == "__main__":
    main()
