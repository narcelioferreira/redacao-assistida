# Testes do Terraform sem credencial do Azure: o provider é simulado (mock_provider) e só o plano é
# avaliado. Rodam no CI com `terraform test` (docs/03-seguranca.md).

mock_provider "azurerm" {
  mock_data "azurerm_resource_group" {
    defaults = {
      id       = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-redacao-demo"
      location = "brazilsouth"
    }
  }

  mock_data "azurerm_client_config" {
    defaults = {
      tenant_id = "11111111-1111-1111-1111-111111111111"
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

# --- T11 · Azure OpenAI e Postgres (D19) ----------------------------------------------------

# ASI03: o Azure OpenAI não aceita chave de API, só identidade com papel.
run "openai_sem_chave" {
  command = plan

  assert {
    condition     = azurerm_cognitive_account.openai.local_auth_enabled == false
    error_message = "O Azure OpenAI precisa ter a autenticação por chave desligada."
  }
}

# D19 · ASI08: Global Standard com teto de capacidade baixo.
run "deployment_global_com_teto" {
  command = plan

  assert {
    condition     = azurerm_cognitive_deployment.chat.sku[0].name == "GlobalStandard"
    error_message = "O deployment precisa ser Global Standard (D19)."
  }

  assert {
    condition     = azurerm_cognitive_deployment.chat.sku[0].capacity <= 100
    error_message = "Capacidade acima de 100 mil tokens/min exige medição antes (ASI08)."
  }
}

run "capacidade_acima_do_teto_e_recusada" {
  command = plan

  variables {
    openai_capacidade = 500
  }

  expect_failures = [var.openai_capacidade]
}

# ASI03: a aplicação só usa o modelo, no recurso do projeto.
run "papel_da_aplicacao_no_openai" {
  command = plan

  assert {
    condition     = azurerm_role_assignment.app_openai.role_definition_name == "Cognitive Services OpenAI User"
    error_message = "A aplicação deve ter só o papel de usuária do OpenAI."
  }
}

# ASI03: Postgres sem senha, só Entra ID, com TLS obrigatório.
run "postgres_sem_senha_e_com_tls" {
  command = plan

  assert {
    condition = (
      azurerm_postgresql_flexible_server.main.authentication[0].password_auth_enabled == false &&
      azurerm_postgresql_flexible_server.main.authentication[0].active_directory_auth_enabled == true
    )
    error_message = "O Postgres precisa aceitar só login por Entra ID."
  }

  assert {
    condition     = azurerm_postgresql_flexible_server_configuration.tls.value == "ON"
    error_message = "O Postgres precisa exigir TLS."
  }

  assert {
    condition     = azurerm_postgresql_flexible_server.main.version == "17"
    error_message = "A migration usa uuid_extract_version, do Postgres 17 (D18)."
  }
}

# ASI03: a administradora do banco é a identidade das migrations, nunca a da aplicação.
run "admin_do_banco_e_a_identidade_das_migrations" {
  command = plan

  assert {
    condition     = azurerm_postgresql_flexible_server_active_directory_administrator.migracao.principal_name == "id-redacao-migracao"
    error_message = "Só a identidade das migrations pode ser administradora do Postgres."
  }
}

# Firewall: só a regra especial dos serviços do Azure, nunca a internet inteira.
run "firewall_so_servicos_do_azure" {
  command = plan

  assert {
    condition = (
      azurerm_postgresql_flexible_server_firewall_rule.servicos_azure.start_ip_address == "0.0.0.0" &&
      azurerm_postgresql_flexible_server_firewall_rule.servicos_azure.end_ip_address == "0.0.0.0"
    )
    error_message = "A regra de firewall não pode abrir faixas da internet."
  }
}
