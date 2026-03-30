// ─── acr.bicep ───────────────────────────────────────────────────────────────
// Azure Container Registry — almacena las imágenes Docker
// Guarda como: infra/modules/acr.bicep

param acrName string
param location string
param managedIdentityPrincipalId string

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: acrName
  location: location
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: false       // Usamos Managed Identity, no usuario/password
    publicNetworkAccess: 'Enabled'
  }
}

// Rol AcrPull para que Container Apps pueda pull de imágenes
resource acrPullRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(acr.id, managedIdentityPrincipalId, 'acrPull')
  scope: acr
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d') // AcrPull
    principalId: managedIdentityPrincipalId
    principalType: 'ServicePrincipal'
  }
}

output loginServer string = acr.properties.loginServer
output acrId string = acr.id
