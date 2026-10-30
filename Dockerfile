# Imagem única da aplicação: a API agora; o worker da F2 usa a mesma imagem com outro comando.
# Imagens fixadas por digest: a tag sozinha pode mudar por baixo (OWASP AST07). O Dependabot atualiza.

FROM ghcr.io/astral-sh/uv:0.13.6@sha256:af22a52f5eafef3d78e551599d405c02df61919d18028f0cea8eda93bc9986d0 AS uv

FROM python:3.12.16-slim-trixie@sha256:aa943ce411423c7582288f18707ff66eddcbaeb510502d747a72aeb34f30d159 AS build
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_CACHE=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv
WORKDIR /app
# Dependências primeiro, para aproveitar o cache de camadas. --locked: só versões e hashes do uv.lock.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --locked --no-dev --no-install-project
COPY src ./src
# --no-editable: o pacote vai para dentro do .venv, e a imagem final não precisa do código-fonte.
RUN uv sync --locked --no-dev --no-editable

FROM python:3.12.16-slim-trixie@sha256:aa943ce411423c7582288f18707ff66eddcbaeb510502d747a72aeb34f30d159
# Usuário sem privilégio e nenhum binário setuid/setgid: dentro do container não sobra caminho de
# escalada, mesmo onde o runtime não aplica `no-new-privileges`.
RUN useradd --system --uid 10001 --no-create-home app \
    && find / -xdev -perm /6000 -type f -exec chmod a-s {} +
WORKDIR /app
COPY --from=build --chown=root:root /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
USER 10001
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --start-period=10s \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/live', timeout=2)"]
# Sem access log: as requisições já viram telemetria no App Insights, e as probes (a cada poucos
# segundos) só encheriam o Log Analytics.
CMD ["uvicorn", "--factory", "redacao.api.app:create_app", "--host", "0.0.0.0", "--port", "8000", "--no-server-header", "--no-access-log"]
