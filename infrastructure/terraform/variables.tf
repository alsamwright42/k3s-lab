variable "location" {
  description = "The Azure region to deploy resources into"
  type        = string
  default     = "East US"
}

variable "resource_group_name" {
  description = "The name of the homelab resource group"
  type        = string
  default     = "rg-homelab-core"
}

variable "key_vault_name" {
  description = "The globally unique name of the Azure Key Vault"
  type        = string
  default     = "kv-homelab-samjam" # Must be globally unique
}