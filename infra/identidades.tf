# Identidades gerenciadas (D5, ASI03). Nenhuma senha nem chave: cada identidade recebe só o que usa.

data "azurerm_client_config" "atual" {}

# Identidade da aplicação (API e, na F2, o worker): chama o Azure OpenAI e lê e grava no banco.
# O papel dela no Postgres (sem DDL) é criado pela migração (T11b).
resource "azurerm_user_assigned_identity" "app" {
  name                = "id-redacao-app"
  location            = local.location
  resource_group_name = data.azurerm_resource_group.main.name
  tags                = local.tags
}

# Identidade das migrations: administradora Entra do Postgres (DDL). Separada da aplicação para
# que um comprometimento da API não consiga alterar o schema.
resource "azurerm_user_assigned_identity" "migracao" {
  name                = "id-redacao-migracao"
  location            = local.location
  resource_group_name = data.azurerm_resource_group.main.name
  tags                = local.tags
}
