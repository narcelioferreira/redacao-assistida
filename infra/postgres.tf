# PostgreSQL Flexible Server (decisão D19): endpoint público, login só por Entra ID.

resource "azurerm_postgresql_flexible_server" "main" {
  name                = "psql-redacao-${local.sufixo}"
  location            = local.location
  resource_group_name = data.azurerm_resource_group.main.name
  # Postgres 17: a migration usa uuid_extract_version (D18).
  version = "17"
  # B1ms e 32 GB: dentro da franquia de 12 meses da conta gratuita.
  sku_name                      = "B_Standard_B1ms"
  storage_mb                    = 32768
  auto_grow_enabled             = false
  backup_retention_days         = 7
  geo_redundant_backup_enabled  = false
  public_network_access_enabled = true
  tags                          = local.tags

  # Sem senha: nenhum login por usuário e senha existe (ASI03).
  authentication {
    active_directory_auth_enabled = true
    password_auth_enabled         = false
    tenant_id                     = data.azurerm_client_config.atual.tenant_id
  }

  lifecycle {
    # O Azure escolhe a zona na criação; sem isto, todo plano tentaria trocá-la.
    ignore_changes = [zone]
  }
}

resource "azurerm_postgresql_flexible_server_database" "redacao" {
  name      = "redacao"
  server_id = azurerm_postgresql_flexible_server.main.id
  charset   = "UTF8"
  collation = "en_US.utf8"
}

# Administradora Entra: só a identidade das migrations (DDL). A aplicação ganha um papel sem DDL
# criado pela própria migração (T11b).
resource "azurerm_postgresql_flexible_server_active_directory_administrator" "migracao" {
  server_name         = azurerm_postgresql_flexible_server.main.name
  resource_group_name = data.azurerm_resource_group.main.name
  tenant_id           = data.azurerm_client_config.atual.tenant_id
  object_id           = azurerm_user_assigned_identity.migracao.principal_id
  principal_name      = azurerm_user_assigned_identity.migracao.name
  principal_type      = "ServicePrincipal"
}

# Só serviços da Azure alcançam o banco (0.0.0.0 é a regra especial "serviços do Azure"). Sem senha,
# alcançar não basta: é preciso o token Entra de uma identidade com papel. Risco residual em D19.
resource "azurerm_postgresql_flexible_server_firewall_rule" "servicos_azure" {
  name             = "servicos-do-azure"
  server_id        = azurerm_postgresql_flexible_server.main.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}

# Conexão só com TLS.
resource "azurerm_postgresql_flexible_server_configuration" "tls" {
  name      = "require_secure_transport"
  server_id = azurerm_postgresql_flexible_server.main.id
  value     = "ON"
}

# pgvector liberado para a busca semântica da F5. A migration que o usa ainda não existe.
resource "azurerm_postgresql_flexible_server_configuration" "extensoes" {
  name      = "azure.extensions"
  server_id = azurerm_postgresql_flexible_server.main.id
  value     = "VECTOR"
}
