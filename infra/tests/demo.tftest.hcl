# Testes do Terraform sem credencial do Azure: o provider é simulado (mock_provider) e só o plano é
# avaliado. Rodam no CI com `terraform test` (docs/03-seguranca.md).

mock_provider "azurerm" {
  mock_data "azurerm_resource_group" {
    defaults = {
      id       = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-redacao-demo"
      location = "brazilsouth"
    }
  }
}

variables {
  image       = "ghcr.io/narcelioferreira/redacao-assistida:0123abc"
  alert_email = "alertas@example.com"
}

# D3 · ASI04: tag móvel não entra. Sem a validação, `latest` iria para o ar.
run "tag_movel_e_recusada" {
  command = plan

  variables {
    image = "ghcr.io/narcelioferreira/redacao-assistida:latest"
  }

  expect_failures = [var.image]
}

# D3 · ASI04: imagem de fora do GHCR do projeto também não entra.
run "registro_desconhecido_e_recusado" {
  command = plan

  variables {
    image = "docker.io/qualquer/imagem:0123abc"
  }

  expect_failures = [var.image]
}

run "versao_no_ar_e_o_sha_da_imagem" {
  command = plan

  assert {
    condition = one([
      for e in azurerm_container_app.api.template[0].container[0].env : e.value if e.name == "GIT_SHA"
    ]) == "0123abc"
    error_message = "GIT_SHA precisa ser a tag da imagem: é o que o smoke test confere."
  }
}

# D2 · ASI08: escala a zero e teto de réplicas limitam custo e o raio de uma falha.
run "escala_limitada" {
  command = plan

  assert {
    condition     = azurerm_container_app.api.template[0].min_replicas == 0
    error_message = "A API precisa escalar a zero (D2)."
  }

  assert {
    condition     = azurerm_container_app.api.template[0].max_replicas <= 2
    error_message = "Teto de réplicas acima do previsto: revise o custo antes de subir."
  }
}

# D10 · ASI08: os logs chegam ao Log Analytics, com teto de ingestão diária.
run "logs_com_destino_e_teto" {
  command = plan

  assert {
    condition     = azurerm_container_app_environment.main.logs_destination == "log-analytics"
    error_message = "Sem logs_destination, nenhum log chega ao Log Analytics."
  }

  assert {
    condition     = azurerm_log_analytics_workspace.main.daily_quota_gb > 0 && azurerm_log_analytics_workspace.main.daily_quota_gb <= 0.5
    error_message = "O Log Analytics precisa de teto diário de ingestão (até 0,5 GB)."
  }
}

# ASI03: a connection string do App Insights chega ao container como secret, nunca como valor
# literal de variável de ambiente.
run "connection_string_como_secret" {
  command = plan

  assert {
    condition = alltrue([
      for e in azurerm_container_app.api.template[0].container[0].env :
      e.secret_name == "appinsights-connection-string" && e.value == null # pragma: allowlist secret
      if e.name == "APPLICATIONINSIGHTS_CONNECTION_STRING"
    ])
    error_message = "A connection string precisa vir de um secret do Container App."
  }
}
