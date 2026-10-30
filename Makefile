.PHONY: install fmt lint typecheck test security check run docker-run smoke tf-check mutacao

install:
	uv sync --locked

fmt:
	uv run ruff format .
	uv run ruff check --fix .

lint:
	uv run ruff format --check .
	uv run ruff check .

typecheck:
	uv run mypy

test:
	uv run pytest --cov --cov-report=term-missing

# Gate de segurança (docs/03-seguranca.md). Os lockfiles têm hashes que parecem segredos.
security:
	uv run bandit -q -c pyproject.toml -r src scripts
	uv run detect-secrets-hook --baseline .secrets.baseline --exclude-files '^uv\.lock$$' --exclude-files '^infra/\.terraform\.lock\.hcl$$' $$(git ls-files --cached --others --exclude-standard)
	uv run pip-audit --skip-editable --progress-spinner off
	uv run zizmor --offline --persona pedantic .github/workflows

# O que o CI roda no job de Python. Rode antes de abrir um PR.
check: lint typecheck test security

run:
	uv run uvicorn --factory redacao.api.app:create_app --reload --port 8000

docker-run:
	docker compose up --build

smoke:
	python3 scripts/smoke.py http://127.0.0.1:8000 --timeout 30

tf-check:
	terraform -chdir=infra fmt -check -recursive
	terraform -chdir=infra init -backend=false -input=false
	terraform -chdir=infra validate
	terraform -chdir=infra test

# Desliga cada controle de security/mutacoes.toml e exige que os testes falhem. Precisa do terraform.
mutacao:
	python3 scripts/mutacao.py --relatorio reports/seguranca/mutacao.md
