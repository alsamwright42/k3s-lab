# 1. Resource Group
resource "azurerm_resource_group" "homelab" {
  name     = "rg-homelab-core"
  location = "canadacentral" # Update if you used a different region
}

# 2. Azure Key Vault (Updated for AzureRM v5.0.0)
resource "azurerm_key_vault" "vault" {
  name                        = var.key_vault_name
  location                    = azurerm_resource_group.homelab.location
  resource_group_name         = azurerm_resource_group.homelab.name
  enabled_for_disk_encryption = false
  tenant_id                   = data.azurerm_client_config.current.tenant_id
  soft_delete_retention_days  = 7
  purge_protection_enabled    = false

  sku_name = "standard"

  # Enterprise Security Standard: Use Entra ID RBAC
  rbac_authorization_enabled = true
}

# 3. Entra ID Application for K3s External Secrets Operator
resource "azuread_application" "k3s_eso" {
  display_name = "app-homelab-k3s-eso"
}

# 4. Service Principal for the Application
resource "azuread_service_principal" "k3s_eso_sp" {
  client_id = azuread_application.k3s_eso.client_id
}

# 5. Password (client secret) for the Service Principal
resource "azuread_service_principal_password" "k3s_eso_sp_password" {
  service_principal_id = azuread_service_principal.k3s_eso_sp.id
}

# 6. Assign "Key Vault Secrets User" role to the Service Principal
resource "azurerm_role_assignment" "eso_kv_secrets_user" {
  scope                = azurerm_key_vault.vault.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azuread_service_principal.k3s_eso_sp.object_id
}
