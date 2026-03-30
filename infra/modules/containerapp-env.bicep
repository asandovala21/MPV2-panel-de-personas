// Módulo: Container Apps Environment
// El entorno compartido que aloja frontend y backend

param name string
param location string
param logAnalyticsWorkspaceId string
param logAnalyticsKey string

resource containerAppEnv 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: name
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalyticsWorkspaceId
        sharedKey: logAnalyticsKey
      }
    }
    workloadProfiles: [
      {
        name: 'Consumption'
        workloadProfileType: 'Consumption'
      }
    ]
  }
}

output id string = containerAppEnv.id
output defaultDomain string = containerAppEnv.properties.defaultDomain
