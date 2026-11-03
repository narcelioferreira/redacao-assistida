variable "resource_group_name" {
  description = "Grupo de recursos do projeto. É criado pelo bootstrap: o Terraform não cria nem apaga o grupo."
  type        = string
  default     = "rg-redacao-demo"
}

variable "image" {
  description = "Imagem da API com a tag do SHA do commit, ex.: ghcr.io/narcelioferreira/redacao-assistida:<sha>."
  type        = string

  validation {
    condition     = can(regex("^ghcr\\.io/[a-z0-9._/-]+:[0-9a-f]{7,40}$", var.image))
    error_message = "Use a imagem do GHCR com a tag do SHA do commit. Com tag móvel (latest, main) não dá para saber o que está no ar (decisão D3)."
  }
}

variable "alert_email" {
  description = "E-mail que recebe os alertas de orçamento."
  type        = string
}

variable "monthly_budget" {
  description = "Orçamento mensal do grupo de recursos, na moeda da conta de cobrança (BRL numa conta brasileira)."
  type        = number
  default     = 50
}

variable "openai_modelo" {
  description = "Modelo do deployment padrão do Azure OpenAI (D19). O E3 compara com outros."
  type        = string
  default     = "gpt-5-mini"
}

variable "openai_modelo_versao" {
  description = "Versão fixa do modelo. Nula usa a versão padrão do Azure no momento da criação."
  type        = string
  default     = null
}

variable "openai_capacidade" {
  description = "Teto do deployment, em milhares de tokens por minuto (ASI08)."
  type        = number
  default     = 30

  validation {
    condition     = var.openai_capacidade >= 1 && var.openai_capacidade <= 100
    error_message = "Capacidade de 1 a 100 mil tokens/min: acima disso, meça antes (custo e abuso, ASI08)."
  }
}
