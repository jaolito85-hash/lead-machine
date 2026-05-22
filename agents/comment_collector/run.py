"""
CLI principal — voce roda este arquivo.

Exemplos:
  # Coleta padrao: Carol no Instagram + TikTok, 20 videos cada, 500 comentarios cada
  python -m agents.comment_collector.run

  # So Instagram, 50 videos
  python -m agents.comment_collector.run --platform instagram --max-videos 50

  # So TikTok do perfil X
  python -m agents.comment_collector.run --platform tiktok --profile outroperfil

  # Reclassificar comentarios pendentes (sem chamar Apify de novo)
  python -m agents.comment_collector.run --reclassify

  # Ver estatisticas atuais
  python -m agents.comment_collector.run --stats
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

# Permite rodar como modulo (-m) OU direto (python run.py)
if __name__ == "__main__" and __package__ is None:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    __package__ = "agents.comment_collector"

from .. import base  # noqa: E402  reaproveita load_env, setup_logger
from . import db, pipeline  # noqa: E402


def main():
    parser = argparse.ArgumentParser(
        prog="comment_collector",
        description="Coletor de comentarios das redes da Dra. Carol"
    )
    parser.add_argument(
        "--platform", choices=["instagram", "tiktok", "both"], default="both",
        help="Plataforma a coletar (default: both)"
    )
    parser.add_argument(
        "--profile", default=None,
        help="Username (sem @). Default: dracarolpantaleao"
    )
    parser.add_argument(
        "--max-videos", type=int, default=20,
        help="Quantos videos recentes coletar por plataforma (default: 20)"
    )
    parser.add_argument(
        "--max-comments-per-video", type=int, default=None,
        help="Maximo de comentarios por video (default: 500 ou MAX_COMMENTS_PER_VIDEO do .env)"
    )
    parser.add_argument(
        "--reclassify", action="store_true",
        help="So reclassifica comentarios sem classificacao (nao chama Apify)"
    )
    parser.add_argument(
        "--stats", action="store_true",
        help="Mostra estatisticas atuais e sai"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Logging detalhado"
    )
    args = parser.parse_args()

    env = base.load_env()
    logger = base.setup_logger("comment_collector", verbose=args.verbose)

    # Garantir que o banco existe
    db.init_db()

    # ── Modo --stats ──
    if args.stats:
        stats = db.get_stats()
        print(json.dumps(stats, ensure_ascii=False, indent=2))
        return 0

    # ── Modo --reclassify ──
    if args.reclassify:
        done = pipeline.reclassify_pending(batch_size=500, logger=logger)
        logger.info(f"Reclassificacao concluida: {done} comentarios")
        return 0

    # ── Modo coleta ──
    apify_token = env.get("APIFY_TOKEN", "").strip()
    if not apify_token:
        logger.error("APIFY_TOKEN nao configurado no .env")
        return 1

    profile_ig = args.profile or env.get("DEFAULT_PROFILE_INSTAGRAM", "dracarolpantaleao")
    profile_tt = args.profile or env.get("DEFAULT_PROFILE_TIKTOK", "dracarolpantaleao")

    max_comments = args.max_comments_per_video or int(
        env.get("MAX_COMMENTS_PER_VIDEO", "500")
    )

    # Propagar ANTHROPIC_API_KEY do .env pro classifier (que le os.environ)
    if env.get("ANTHROPIC_API_KEY"):
        os.environ["ANTHROPIC_API_KEY"] = env["ANTHROPIC_API_KEY"]
    if env.get("ANTHROPIC_MODEL"):
        os.environ["ANTHROPIC_MODEL"] = env["ANTHROPIC_MODEL"]

    classifier_mode = "claude" if env.get("ANTHROPIC_API_KEY") else "heuristic"
    logger.info(f"Classifier: {classifier_mode}")
    logger.info(f"Max comentarios por video: {max_comments}")

    results = []
    start = time.time()

    if args.platform in ("instagram", "both"):
        logger.info(f"=== INSTAGRAM (@{profile_ig}) ===")
        try:
            r = pipeline.collect_instagram_profile(
                apify_token, profile_ig,
                max_videos=args.max_videos,
                max_comments_per_video=max_comments,
                logger=logger,
            )
            results.append(r)
        except Exception as e:
            logger.error(f"Erro no Instagram: {e}")
            results.append({"platform": "instagram", "error": str(e)})

    if args.platform in ("tiktok", "both"):
        logger.info(f"=== TIKTOK (@{profile_tt}) ===")
        try:
            r = pipeline.collect_tiktok_profile(
                apify_token, profile_tt,
                max_videos=args.max_videos,
                max_comments_per_video=max_comments,
                logger=logger,
            )
            results.append(r)
        except Exception as e:
            logger.error(f"Erro no TikTok: {e}")
            results.append({"platform": "tiktok", "error": str(e)})

    duration = round(time.time() - start, 1)

    # Resumo final
    summary = {
        "duration_sec": duration,
        "results": results,
        "stats_after": db.get_stats(),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    logger.info(f"Concluido em {duration}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
