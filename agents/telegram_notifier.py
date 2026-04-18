"""
LEAD MACHINE - Notificador Telegram

Envia mensagem no Telegram quando aparece lead quente.
Requer TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID no .env.

Como configurar (3 passos, 2 minutos):
  1. No Telegram, procure por @BotFather e rode /newbot. Escolha nome+username.
     BotFather retorna um token tipo 123456789:ABCdefGhIJKlmNoPQR.
     Cole em TELEGRAM_BOT_TOKEN.
  2. Procure seu bot no Telegram e mande /start.
  3. Abra https://api.telegram.org/bot<SEU_TOKEN>/getUpdates e copie o numero
     em "chat":{"id": ...}. Cole em TELEGRAM_CHAT_ID.

Teste manual:
  python agents/telegram_notifier.py --test
"""

import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path


TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"


def _load_env() -> dict:
    """Carrega .env de forma leve. os.environ tem prioridade."""
    env = {}
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    for k, v in os.environ.items():
        env[k] = v
    return env


def _get_credentials():
    env = _load_env()
    token = env.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = env.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id or "XXXX" in token:
        return None, None
    return token, chat_id


def send_message(text: str, parse_mode: str = "HTML", disable_web_preview: bool = True) -> bool:
    """
    Envia mensagem para o chat configurado.
    Retorna True em sucesso, False em falha (sem levantar excecao).
    """
    token, chat_id = _get_credentials()
    if not token:
        return False

    url = TELEGRAM_API.format(token=token, method="sendMessage")
    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": "true" if disable_web_preview else "false",
    }).encode("utf-8")

    try:
        req = urllib.request.Request(url, data=data, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return bool(body.get("ok"))
    except Exception as e:
        print(f"[telegram] erro: {e}", file=sys.stderr)
        return False


def _escape_html(text: str) -> str:
    if not text:
        return ""
    return (text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;"))


def format_hot_lead(lead: dict) -> str:
    """Monta mensagem HTML bonitinha para um lead quente."""
    nome = _escape_html(lead.get("nome") or lead.get("user") or "Lead sem nome")
    plat = _escape_html((lead.get("plataforma") or "").title())
    score = lead.get("score", 0)
    temp = (lead.get("temp") or "quente").upper()
    cidade = _escape_html(lead.get("cidade") or "")
    nicho = _escape_html(lead.get("nicho") or "")
    evidencia = _escape_html(lead.get("evidencia") or lead.get("texto_original") or "")
    if len(evidencia) > 220:
        evidencia = evidencia[:217] + "..."
    url = lead.get("url") or ""
    perfil = _escape_html(lead.get("perfil") or "")
    tel = _escape_html(lead.get("telefone") or "")
    email = _escape_html(lead.get("email") or "")
    tipo = (lead.get("tipo") or "").upper()

    lines = [
        f"<b>LEAD {_temp_badge(temp)} ({score})</b>",
        f"<b>{nome}</b>" + (f" - <i>{tipo}</i>" if tipo else ""),
        f"Plataforma: {plat}" + (f" | {cidade}" if cidade else ""),
    ]
    if nicho:
        lines.append(f"Nicho: {nicho}")
    if perfil:
        lines.append(f"Perfil: {perfil}")
    if tel:
        lines.append(f"Tel: {tel}")
    if email:
        lines.append(f"Email: {email}")
    if evidencia:
        lines.append("")
        lines.append(f"<i>{evidencia}</i>")
    if url:
        lines.append("")
        lines.append(f'<a href="{_escape_html(url)}">Abrir origem</a>')

    return "\n".join(lines)


def _temp_badge(temp: str) -> str:
    return {"QUENTE": "QUENTE", "MORNO": "MORNO", "FRIO": "FRIO"}.get(temp.upper(), temp)


def notify_hot_lead(lead: dict) -> bool:
    """Envia notificacao de lead quente. Retorna True em sucesso."""
    return send_message(format_hot_lead(lead))


def notify_batch_summary(stats: dict) -> bool:
    """Notifica resumo apos rodada do qualifier."""
    novos_quentes = stats.get("novos_quentes", 0)
    total_quentes = stats.get("quentes", 0)
    mornos = stats.get("mornos", 0)
    frios = stats.get("frios", 0)
    duracao = stats.get("duration_sec", 0)

    if novos_quentes == 0:
        return False

    text = (
        f"<b>Qualificacao concluida</b>\n"
        f"Novos quentes: <b>{novos_quentes}</b>\n"
        f"Total - Quentes: {total_quentes} | Mornos: {mornos} | Frios: {frios}\n"
        f"Tempo: {duracao}s"
    )
    return send_message(text)


def is_configured() -> bool:
    token, chat_id = _get_credentials()
    return bool(token and chat_id)


def _cli():
    """Teste manual: python agents/telegram_notifier.py --test"""
    token, chat_id = _get_credentials()
    if not token:
        print("ERRO: TELEGRAM_BOT_TOKEN ou TELEGRAM_CHAT_ID ausentes no .env")
        print("Veja instrucoes no topo de agents/telegram_notifier.py")
        sys.exit(1)

    print(f"Token: {token[:12]}... | Chat: {chat_id}")
    print("Enviando mensagem de teste...")
    ok = send_message(
        "<b>Lead Machine conectado</b>\n"
        "Se voce ve essa mensagem, o bot esta funcionando.\n"
        "Voce vai receber aqui todo lead quente novo."
    )
    if ok:
        print("OK - verifique seu Telegram")
        sys.exit(0)
    else:
        print("FALHA - cheque token, chat_id e se voce mandou /start pro bot")
        sys.exit(1)


if __name__ == "__main__":
    if "--test" in sys.argv:
        _cli()
    else:
        print("Use --test para enviar mensagem de teste.")
