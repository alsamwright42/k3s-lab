output "key_vault_id" {
  description = "The Azure Resource ID of the Key Vault"
  value       = azurerm_key_vault.vault.id
}

output "key_vault_uri" {
  description = "The URI of the Key Vault used for ESO authentication"
  value       = azurerm_key_vault.vault.vault_uri
}