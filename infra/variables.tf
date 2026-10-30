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
