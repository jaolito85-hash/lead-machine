"""
SQLite database para armazenar videos, comentarios e classificacoes.

DICA: o banco e um arquivo unico (.db) na pasta do projeto.
Voce pode abrir ele no DB Browser for SQLite (https://sqlitebrowser.org)
e clicar em "Browse Data" pra ver tudo numa tabela tipo Excel.
"""

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

# Caminho do arquivo do banco — fica dentro de leads-export/ junto com o resto
BASE_DIR = Path(__file__).parent.parent.parent  # paperclip/
DB_PATH = BASE_DIR / "leads-export" / "comments.db"


SCHEMA = """
-- Tabela de videos: cada video que a gente coletou comentarios
CREATE TABLE IF NOT EXISTS videos (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    platform        TEXT NOT NULL,          -- 'instagram' ou 'tiktok'
    video_url       TEXT NOT NULL UNIQUE,
    video_id        TEXT,                   -- shortcode do IG ou ID do TikTok
    owner_username  TEXT,                   -- @dracarolpantaleao
    caption         TEXT,
    view_count      INTEGER,
    like_count      INTEGER,
    comment_count   INTEGER,
    posted_at       TEXT,                   -- data que o video foi postado
    collected_at    TEXT NOT NULL,          -- quando a gente coletou
    last_collected  TEXT NOT NULL           -- ultima vez que recoletou
);

CREATE INDEX IF NOT EXISTS idx_videos_platform ON videos(platform);

-- Tabela de comentarios crus
CREATE TABLE IF NOT EXISTS comments (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id        INTEGER NOT NULL,
    platform        TEXT NOT NULL,
    external_id     TEXT,                   -- id do comentario na plataforma (pra dedup)
    author_username TEXT,
    author_fullname TEXT,
    author_url      TEXT,
    text            TEXT NOT NULL,
    like_count      INTEGER DEFAULT 0,
    reply_count     INTEGER DEFAULT 0,
    posted_at       TEXT,                   -- quando o comentario foi feito
    collected_at    TEXT NOT NULL,
    is_reply        INTEGER DEFAULT 0,      -- 0 = comentario raiz, 1 = resposta
    FOREIGN KEY (video_id) REFERENCES videos(id)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_comments_external
    ON comments(platform, external_id) WHERE external_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_comments_video ON comments(video_id);
CREATE INDEX IF NOT EXISTS idx_comments_author ON comments(author_username);

-- Tabela de classificacoes (uma por comentario)
-- Separada pra voce poder reclassificar sem perder os comentarios crus
CREATE TABLE IF NOT EXISTS classifications (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    comment_id      INTEGER NOT NULL UNIQUE,
    intent          TEXT NOT NULL,          -- buscando_atendimento|perguntando_preco|perguntando_local|elogio|duvida_geral|outros
    urgency         TEXT,                   -- alta|media|baixa
    lead_score      INTEGER DEFAULT 0,      -- 0-100
    city            TEXT,                   -- cidade detectada (se mencionada)
    state           TEXT,                   -- UF detectada
    region          TEXT,                   -- norte|nordeste|centro-oeste|sudeste|sul
    classifier      TEXT NOT NULL,          -- 'heuristic' ou 'claude'
    classified_at   TEXT NOT NULL,
    raw_reasoning   TEXT,                   -- justificativa da IA (pra voce auditar)
    FOREIGN KEY (comment_id) REFERENCES comments(id)
);

CREATE INDEX IF NOT EXISTS idx_class_intent ON classifications(intent);
CREATE INDEX IF NOT EXISTS idx_class_score ON classifications(lead_score);
CREATE INDEX IF NOT EXISTS idx_class_state ON classifications(state);
"""


@contextmanager
def get_conn():
    """Context manager que abre conexao, commita no fim, fecha sempre."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Permite acessar colunas por nome
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Cria as tabelas se nao existirem. Idempotente — pode rodar varias vezes."""
    with get_conn() as conn:
        conn.executescript(SCHEMA)


def upsert_video(platform: str, video_url: str, **fields) -> int:
    """
    Insere ou atualiza um video. Retorna o ID interno.
    Se ja existe (mesma URL), atualiza last_collected e contadores.
    """
    now = datetime.now().isoformat()
    with get_conn() as conn:
        # Tenta inserir
        cur = conn.execute(
            """INSERT OR IGNORE INTO videos
               (platform, video_url, video_id, owner_username, caption,
                view_count, like_count, comment_count, posted_at,
                collected_at, last_collected)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                platform, video_url,
                fields.get("video_id"),
                fields.get("owner_username"),
                fields.get("caption"),
                fields.get("view_count"),
                fields.get("like_count"),
                fields.get("comment_count"),
                fields.get("posted_at"),
                now, now,
            ),
        )
        if cur.rowcount > 0:
            return cur.lastrowid

        # Ja existia: atualiza contadores e last_collected
        conn.execute(
            """UPDATE videos
               SET view_count = COALESCE(?, view_count),
                   like_count = COALESCE(?, like_count),
                   comment_count = COALESCE(?, comment_count),
                   last_collected = ?
               WHERE video_url = ?""",
            (
                fields.get("view_count"),
                fields.get("like_count"),
                fields.get("comment_count"),
                now, video_url,
            ),
        )
        row = conn.execute(
            "SELECT id FROM videos WHERE video_url = ?", (video_url,)
        ).fetchone()
        return row["id"]


def insert_comment(video_id: int, platform: str, **fields) -> int | None:
    """
    Insere um comentario. Se ja existe (mesmo external_id), retorna None.
    Retorna o ID interno do comentario inserido.
    """
    now = datetime.now().isoformat()
    with get_conn() as conn:
        try:
            cur = conn.execute(
                """INSERT INTO comments
                   (video_id, platform, external_id, author_username,
                    author_fullname, author_url, text, like_count,
                    reply_count, posted_at, collected_at, is_reply)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    video_id, platform,
                    fields.get("external_id"),
                    fields.get("author_username"),
                    fields.get("author_fullname"),
                    fields.get("author_url"),
                    fields.get("text", ""),
                    fields.get("like_count", 0),
                    fields.get("reply_count", 0),
                    fields.get("posted_at"),
                    now,
                    1 if fields.get("is_reply") else 0,
                ),
            )
            return cur.lastrowid
        except sqlite3.IntegrityError:
            # Comentario ja existia (UNIQUE constraint no external_id)
            return None


def upsert_classification(comment_id: int, **fields):
    """Salva ou atualiza a classificacao de um comentario."""
    now = datetime.now().isoformat()
    with get_conn() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO classifications
               (comment_id, intent, urgency, lead_score, city, state, region,
                classifier, classified_at, raw_reasoning)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                comment_id,
                fields.get("intent", "outros"),
                fields.get("urgency"),
                fields.get("lead_score", 0),
                fields.get("city"),
                fields.get("state"),
                fields.get("region"),
                fields.get("classifier", "heuristic"),
                now,
                fields.get("raw_reasoning"),
            ),
        )


def get_unclassified_comments(limit: int = 100) -> list[dict]:
    """Retorna comentarios que ainda nao foram classificados."""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT c.id, c.text, c.author_username, c.platform, v.video_url
               FROM comments c
               JOIN videos v ON v.id = c.video_id
               LEFT JOIN classifications cl ON cl.comment_id = c.id
               WHERE cl.id IS NULL
               LIMIT ?""",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_stats() -> dict:
    """Estatisticas agregadas pro dashboard."""
    with get_conn() as conn:
        total_videos = conn.execute("SELECT COUNT(*) c FROM videos").fetchone()["c"]
        total_comments = conn.execute("SELECT COUNT(*) c FROM comments").fetchone()["c"]
        total_classified = conn.execute(
            "SELECT COUNT(*) c FROM classifications"
        ).fetchone()["c"]

        # Distribuicao por intencao
        intents = conn.execute(
            """SELECT intent, COUNT(*) c
               FROM classifications
               GROUP BY intent
               ORDER BY c DESC"""
        ).fetchall()

        # Top cidades
        cities = conn.execute(
            """SELECT city, state, COUNT(*) c
               FROM classifications
               WHERE city IS NOT NULL AND city != ''
               GROUP BY city, state
               ORDER BY c DESC
               LIMIT 20"""
        ).fetchall()

        # Distribuicao por estado
        states = conn.execute(
            """SELECT state, COUNT(*) c
               FROM classifications
               WHERE state IS NOT NULL AND state != ''
               GROUP BY state
               ORDER BY c DESC"""
        ).fetchall()

        # Distribuicao por regiao
        regions = conn.execute(
            """SELECT region, COUNT(*) c
               FROM classifications
               WHERE region IS NOT NULL AND region != ''
               GROUP BY region
               ORDER BY c DESC"""
        ).fetchall()

        # Hot leads (score >= 80, intent buscando_atendimento)
        hot_leads = conn.execute(
            """SELECT c.author_username, c.text, c.platform, v.video_url,
                      cl.lead_score, cl.intent, cl.city, cl.state
               FROM classifications cl
               JOIN comments c ON c.id = cl.comment_id
               JOIN videos v ON v.id = c.video_id
               WHERE cl.lead_score >= 80
               ORDER BY cl.lead_score DESC, c.like_count DESC
               LIMIT 50"""
        ).fetchall()

        return {
            "total_videos": total_videos,
            "total_comments": total_comments,
            "total_classified": total_classified,
            "intents": [dict(r) for r in intents],
            "cities": [dict(r) for r in cities],
            "states": [dict(r) for r in states],
            "regions": [dict(r) for r in regions],
            "hot_leads": [dict(r) for r in hot_leads],
        }


if __name__ == "__main__":
    # Rodar este arquivo direto inicializa o banco
    init_db()
    print(f"Banco inicializado em: {DB_PATH}")
