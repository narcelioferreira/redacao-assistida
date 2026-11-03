output "api_url" {
  description = "URL pública da API. O smoke test do CD usa esta saída."
  value       = "https://${azurerm_container_app.api.ingress[0].fqdn}"
}

output "openai_endpoint" {
  description = "Endpoint do Azure OpenAI (sem chave: acesso por identidade)."
  value       = azurerm_cognitive_account.openai.endpoint
}

output "postgres_fqdn" {
  description = "Endereço do Postgres (login só por Entra ID)."
  value       = azurerm_postgresql_flexible_server.main.fqdn
}

output "identidade_migracao_client_id" {
  description = "Client ID da identidade das migrations (administradora Entra do Postgres)."
  value       = azurerm_user_assigned_identity.migracao.client_id
}
