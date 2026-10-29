data "azurerm_resource_group" "main" {
  name = var.resource_group_name
}

locals {
  location = data.azurerm_resource_group.main.location
  # A tag da imagem é o SHA do commit; a API informa esse valor em /health/live.
  git_sha = element(split(":", var.image), 1)

  tags = {
    projeto        = "redacao-assistida"
    ambiente       = "demo"
    gerenciado-por = "terraform"
  }
}

# --- Observabilidade (decisão D10) -----------------------------------------------------------

resource "azurerm_log_analytics_workspace" "main" {
  name                = "log-redacao-demo"
  location            = local.location
  resource_group_name = data.azurerm_resource_group.main.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
  # Teto de ingestão diária: se algo sair do controle (um loop de logs, por exemplo), a ingestão
  # para no limite e a conta não dispara.
  daily_quota_gb = 0.5
  tags           = local.tags
}

resource "azurerm_application_insights" "main" {
  name                = "appi-redacao-demo"
  location            = local.location
  resource_group_name = data.azurerm_resource_group.main.name
  workspace_id        = azurerm_log_analytics_workspace.main.id
  application_type    = "web"
  tags                = local.tags
}

# --- Execução (decisão D2) -----------------------------------------------------------------------

resource "azurerm_container_app_environment" "main" {
  name                = "cae-redacao-demo"
  location            = local.location
  resource_group_name = data.azurerm_resource_group.main.name
  # Sem logs_destination, os logs dos containers só aparecem ao vivo e não chegam ao Log Analytics.
  logs_destination           = "log-analytics"
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id
  tags                       = local.tags
}

resource "azurerm_container_app" "api" {
  name                         = "ca-redacao-api"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = data.azurerm_resource_group.main.name
  revision_mode                = "Single"
  tags                         = local.tags

  secret {
    name  = "appinsights-connection-string"
    value = azurerm_application_insights.main.connection_string
  }

  ingress {
    external_enabled = true
    target_port      = 8000
    transport        = "auto"

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  template {
    # Escala a zero: sem tráfego, nenhuma réplica roda e o custo é zero. O preço é o cold start
    # da primeira requisição, medido no experimento P3.
    min_replicas = 0
    max_replicas = 2

    container {
      name   = "api"
      image  = var.image
      cpu    = 0.25
      memory = "0.5Gi"

      env {
        name  = "APP_ENV"
        value = "demo"
      }

      env {
        name  = "GIT_SHA"
        value = local.git_sha
      }

      env {
        name        = "APPLICATIONINSIGHTS_CONNECTION_STRING"
        secret_name = "appinsights-connection-string"
      }

      liveness_probe {
        transport = "HTTP"
        port      = 8000
        path      = "/health/live"
      }

      readiness_probe {
        transport = "HTTP"
        port      = 8000
        path      = "/health/ready"
      }
    }

    http_scale_rule {
      name                = "http"
      concurrent_requests = "20"
    }
  }
}

# --- Custo -----------------------------------------------------------------------------------

resource "azurerm_consumption_budget_resource_group" "main" {
  name              = "budget-redacao-demo"
  resource_group_id = data.azurerm_resource_group.main.id
  amount            = var.monthly_budget
  time_grain        = "Monthly"

  time_period {
    # O orçamento precisa começar no dia 1 de um mês. O ignore_changes abaixo impede que a data
    # seja recalculada a cada apply.
    start_date = formatdate("YYYY-MM-01'T'00:00:00Z", plantimestamp())
  }

  notification {
    enabled        = true
    threshold      = 50
    operator       = "GreaterThan"
    threshold_type = "Actual"
    contact_emails = [var.alert_email]
  }

  notification {
    enabled        = true
    threshold      = 80
    operator       = "GreaterThan"
    threshold_type = "Actual"
    contact_emails = [var.alert_email]
  }

  # Avisa antes de estourar: a previsão do mês passou do orçamento.
  notification {
    enabled        = true
    threshold      = 100
    operator       = "GreaterThan"
    threshold_type = "Forecasted"
    contact_emails = [var.alert_email]
  }

  lifecycle {
    ignore_changes = [time_period]
  }
}
