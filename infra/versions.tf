terraform {
  required_version = ">= 1.16, < 2.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 5.10"
    }
  }

  # Estado remoto no Storage Account criado pelo bootstrap, acessado só por Entra ID (a conta não
  # aceita chave de acesso). Nomes passados por -backend-config no CD (docs/deploy-azure.md).
  backend "azurerm" {
    use_azuread_auth = true
  }
}

provider "azurerm" {
  features {}

  # O bootstrap registra os provedores de recurso. A identidade do CD só tem acesso ao grupo de
  # recursos do projeto e não conseguiria registrar nada na assinatura (decisão D4).
  resource_provider_registrations = "none"
  storage_use_azuread             = true
}
