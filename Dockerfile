FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
      supervisor ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

COPY agents/requirements.txt /app/agents/requirements.txt
RUN pip install --no-cache-dir -r /app/agents/requirements.txt

COPY agents/ /app/agents/
COPY dashboard/ /app/dashboard/
COPY serve.py /app/serve.py
COPY prompts/ /app/prompts/

COPY deploy/supervisord.conf /etc/supervisor/conf.d/leadmachine.conf

RUN mkdir -p /app/leads-export && chmod -R 755 /app

ENV DASHBOARD_PORT=8081 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=America/Sao_Paulo

EXPOSE 8081

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/leadmachine.conf"]
