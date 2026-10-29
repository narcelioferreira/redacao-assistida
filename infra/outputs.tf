output "api_url" {
  description = "URL pública da API. O smoke test do CD usa esta saída."
  value       = "https://${azurerm_container_app.api.ingress[0].fqdn}"
}
