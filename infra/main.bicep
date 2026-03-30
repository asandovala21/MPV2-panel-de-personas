// =============================================================================
// Panel de Personas CGR — Infraestructura como Código (Bicep)
// Orquesta: Storage, ACR, Container Apps Environment, Frontend, Backend
// Uso: az deployment group create --resource-group panel-de-personas \
//        --template-file infra/main.bicep \
//        --parameters @infra/parameters.prod.json
// =============================================================================

targetScope = 'resourceGroup'

@description('Entorno de despliegue')
@allowed(['dev', 'staging', 'prod'])
param environment string = 'prod'

@description('Región Azure')
param location string = resourceGroup().location

@description('Sufijo único para nombres de recursos (6 chars alfanuméricos)')
param uniqueSuffix string

@description('Imagen del backend en ACR (ej: panel-personas:v20250101)')
param backendImageTag string = 'latest'

@description('Imagen del frontend en ACR')
param frontendImageTag string = 'latest'

@description('Réplicas mínimas del backend')
param backendMinReplicas int = 2

@description('Réplicas máximas del backend (escala automática)')
param backendMaxReplicas int = 10

@description('Réplicas mínimas del frontend')
param frontendMinReplicas int = 1

@description('Réplicas máximas del frontend')
param frontendMaxReplicas int = 3

// ─── Nombres de recursos ─────────────────────────────────────────────────────
var resourcePrefix = 'panel'
var storageAccountName = 'st${resourcePrefix}${uniqueSuffix}'
var acrName = 'acr${resourcePrefix}${uniqueSuffix}'
var containerAppEnvName = '${resourcePrefix}-env-${environment}'
var frontendAppName = '${resourcePrefix}-frontend-${environment}'
var backendAppName = '${resourcePrefix}-backend-${environment}'
var keyVaultName = 'kv${resourcePrefix}${uniqueSuffix}'
var logAnalyticsName = '${resourcePrefix}-logs-${environment}'
var managedIdentityName = '${resourcePrefix}-identity-${environment}'

// ─── Módulos ─────────────────────────────────────────────────────────────────

module logAnalytics 'modules/loganalytics.bicep' = {
  name: 'logAnalytics'
  params: {
    name: logAnalyticsName
    location: location
  }
}

module managedIdentity 'modules/identity.bicep' = {
  name: 'managedIdentity'
  params: {
    name: managedIdentityName
    location: location
  }
}

module storage 'modules/storage.bicep' = {
  name: 'storage'
  params: {
    storageAccountName: storageAccountName
    location: location
    managedIdentityPrincipalId: managedIdentity.outputs.principalId
  }
}

module acr 'modules/acr.bicep' = {
  name: 'acr'
  params: {
    acrName: acrName
    location: location
    managedIdentityPrincipalId: managedIdentity.outputs.principalId
  }
}

module keyVault 'modules/keyvault.bicep' = {
  name: 'keyVault'
  params: {
    keyVaultName: keyVaultName
    location: location
    managedIdentityPrincipalId: managedIdentity.outputs.principalId
    storageConnectionString: storage.outputs.connectionString
  }
}

module containerAppEnv 'modules/containerapp-env.bicep' = {
  name: 'containerAppEnv'
  params: {
    name: containerAppEnvName
    location: location
    logAnalyticsWorkspaceId: logAnalytics.outputs.workspaceId
    logAnalyticsKey: logAnalytics.outputs.primaryKey
  }
}

module backendApp 'modules/containerapp-backend.bicep' = {
  name: 'backendApp'
  params: {
    appName: backendAppName
    location: location
    containerAppEnvId: containerAppEnv.outputs.id
    acrLoginServer: acr.outputs.loginServer
    imageTag: backendImageTag
    managedIdentityId: managedIdentity.outputs.id
    managedIdentityClientId: managedIdentity.outputs.clientId
    keyVaultName: keyVaultName
    minReplicas: backendMinReplicas
    maxReplicas: backendMaxReplicas
  }
}

module frontendApp 'modules/containerapp-frontend.bicep' = {
  name: 'frontendApp'
  params: {
    appName: frontendAppName
    location: location
    containerAppEnvId: containerAppEnv.outputs.id
    acrLoginServer: acr.outputs.loginServer
    imageTag: frontendImageTag
    managedIdentityId: managedIdentity.outputs.id
    backendInternalFqdn: backendApp.outputs.internalFqdn
    minReplicas: frontendMinReplicas
    maxReplicas: frontendMaxReplicas
  }
}

// ─── Outputs ─────────────────────────────────────────────────────────────────
output frontendUrl string = 'https://${frontendApp.outputs.fqdn}'
output backendUrl string = 'https://${backendApp.outputs.fqdn}'
output acrLoginServer string = acr.outputs.loginServer
output storageAccountName string = storageAccountName
