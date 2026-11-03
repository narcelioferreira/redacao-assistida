# Azure OpenAI (decisão D19): Global Standard no Brazil South, com gpt-5-mini como padrão.

resource "azurerm_cognitive_account" "openai" {
  name                = "oai-redacao-${local.sufixo}"
  location            = local.location
  resource_group_name = data.azurerm_resource_group.main.name
  kind                = "OpenAI"
  sku_name            = "S0"
  # O subdomínio próprio é obrigatório para autenticar por Entra ID.
  custom_subdomain_name = "oai-redacao-${local.sufixo}"
  # Sem chave de API: só identidades com papel acessam (ASI03).
  local_auth_enabled            = false
  public_network_access_enabled = true
  tags                          = local.tags
}

resource "azurerm_cognitive_deployment" "chat" {
  name                 = var.openai_modelo
  cognitive_account_id = azurerm_cognitive_account.openai.id

  model {
    format  = "OpenAI"
    name    = var.openai_modelo
    version = var.openai_modelo_versao
  }

  # Global Standard: é o único tipo desses modelos no Brazil South. O texto pode ser processado em
  # outra região (D19); chega sem nome de aluno e com dados pessoais mascarados (T33).
  sku {
    name = "GlobalStandard"
    # Milhares de tokens por minuto. Teto de custo e de abuso (ASI08), bem abaixo da cota.
    capacity = var.openai_capacidade
  }
}

# A aplicação só chama o modelo: "OpenAI User" não cria deployments nem lê chaves.
resource "azurerm_role_assignment" "app_openai" {
  scope                = azurerm_cognitive_account.openai.id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = azurerm_user_assigned_identity.app.principal_id
  principal_type       = "ServicePrincipal"
}
