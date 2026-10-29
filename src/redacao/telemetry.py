"""Telemetria com OpenTelemetry (decisão D10).

Sempre existe um TracerProvider, mesmo localmente: toda requisição ganha um trace_id, que vai na
resposta de erro e é o mesmo `operation_Id` que se procura no App Insights. A exportação para o
Azure Monitor só liga quando a connection string está configurada.
"""

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.trace import TracerProvider

from redacao.config import Settings

# As probes do Container Apps chamam /health a cada poucos segundos: rastrear isso só gera custo.
_UNTRACED_URLS = "health/.*"

# O OpenTelemetry aceita um único TracerProvider global por processo. A fábrica da API pode rodar
# várias vezes (testes), então o provider é configurado só na primeira.
_provider_ready = False


def configure_telemetry(app: FastAPI, settings: Settings) -> None:
    global _provider_ready
    if not _provider_ready:
        if settings.applicationinsights_connection_string is not None:
            from azure.monitor.opentelemetry import configure_azure_monitor

            configure_azure_monitor(
                connection_string=settings.applicationinsights_connection_string.get_secret_value(),
                # O FastAPI é instrumentado abaixo, app por app; a instrumentação automática da
                # distro só pega apps criados depois dela e duplicaria os spans.
                instrumentation_options={"fastapi": {"enabled": False}},
                # Só os logs do projeto vão para o App Insights, não os de bibliotecas.
                logger_name="redacao",
            )
        else:
            trace.set_tracer_provider(TracerProvider())
        _provider_ready = True
    FastAPIInstrumentor.instrument_app(app, excluded_urls=_UNTRACED_URLS)


def current_trace_id() -> str | None:
    """Trace da requisição em andamento, no formato do W3C Trace Context (32 hex)."""
    context = trace.get_current_span().get_span_context()
    return format(context.trace_id, "032x") if context.is_valid else None
