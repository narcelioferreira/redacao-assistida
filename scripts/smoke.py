"""Smoke test pós-deploy: espera a API responder com a versão esperada.

Uso: python3 scripts/smoke.py <url-base> [--versao <sha>] [--timeout 300]

Só usa a biblioteca padrão, para rodar no runner do CI sem instalar o projeto. Com escala a zero, a
primeira requisição acorda uma réplica e pode demorar, por isso o script tenta de novo até o prazo.
Conferir a versão evita um falso positivo: a revisão antiga também responderia 200 (decisão D3).
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from urllib.parse import urlparse


def wait_for_version(
    base_url: str, expected: str | None, timeout_s: float, interval_s: float = 5.0
) -> bool:
    if urlparse(base_url).scheme not in {"http", "https"}:
        raise ValueError(f"URL precisa ser http(s): {base_url!r}")
    url = base_url.rstrip("/") + "/health/live"
    deadline = time.monotonic() + timeout_s
    last = "sem resposta"
    while True:
        try:
            # S310: o esquema foi conferido acima (nada de file://).
            with urllib.request.urlopen(url, timeout=10) as response:  # noqa: S310
                body = json.load(response)
            if expected is None or body.get("versao") == expected:
                print(f"OK: {url} respondeu {body}")
                return True
            last = f"versão no ar {body.get('versao')!r}, esperada {expected!r}"
        except (urllib.error.URLError, TimeoutError, ConnectionError, json.JSONDecodeError) as exc:
            last = type(exc).__name__
        if time.monotonic() + interval_s > deadline:
            print(f"FALHOU: {url} ({last})", file=sys.stderr)
            return False
        time.sleep(interval_s)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("base_url")
    parser.add_argument("--versao", help="SHA que /health/live precisa informar")
    parser.add_argument("--timeout", type=float, default=300.0, help="segundos (padrão: 300)")
    args = parser.parse_args(argv)
    return 0 if wait_for_version(args.base_url, args.versao, args.timeout) else 1


if __name__ == "__main__":
    sys.exit(main())
