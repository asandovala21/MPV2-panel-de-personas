// ─── identity.bicep ──────────────────────────────────────────────────────────
// Guarda como: infra/modules/identity.bicep
// Managed Identity usada por Container Apps para acceder a ACR, Key Vault y Storage
// sin necesidad de credenciales hardcodeadas

param name string
param location string

resource managedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: name
  location: location
}

output id string = managedIdentity.id
output principalId string = managedIdentity.properties.principalId
output clientId string = managedIdentity.properties.clientId
