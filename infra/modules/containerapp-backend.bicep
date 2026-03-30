// Módulo: Container App Backend (Flask/Gunicorn)
// Auto-scaling por CPU: 2 réplicas mínimo, hasta 10 bajo carga (100+ usuarios)

param appName string
param location string
param containerAppEnvId string
param acrLoginServer string
param imageTag string
param managedIdentityId string
param managedIdentityClientId string
param keyVaultName string
param minReplicas int = 2
param maxReplicas int = 10

resource backendApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: appName
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${managedIdentityId}': {}
    }
  }
  properties: {
    managedEnvironmentId: containerAppEnvId
    configuration: {
      ingress: {
        external: false          // Solo accesible internamente (frontend lo llama por red interna)
        targetPort: 8081
        transport: 'http'
        corsPolicy: {
          allowedOrigins: ['*']
          allowedMethods: ['GET', 'POST', 'OPTIONS']
          allowedHeaders: ['*']
        }
      }
      registries: [
        {
          server: acrLoginServer
          identity: managedIdentityId
        }
      ]
      secrets: [
        {
          name: 'storage-connection-string'
          keyVaultUrl: 'https://${keyVaultName}.vault.azure.net/secrets/storage-connection-string'
          identity: managedIdentityId
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'backend'
          image: '${acrLoginServer}/panel-personas-backend:${imageTag}'
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: [
            {
              name: 'AZURE_STORAGE_CONNECTION_STRING'
              secretRef: 'storage-connection-string'
            }
            {
              name: 'AZURE_STORAGE_CONTAINER_NAME'
              value: 'datos'
            }
            {
              name: 'AZURE_CLIENT_ID'
              value: managedIdentityClientId
            }
            {
              name: 'PORT'
              value: '8081'
            }
            {
              name: 'HOST'
              value: '0.0.0.0'
            }
          ]
          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: '/'
                port: 8081
              }
              initialDelaySeconds: 15
              periodSeconds: 30
            }
            {
              type: 'Readiness'
              httpGet: {
                path: '/api/health'
                port: 8081
              }
              initialDelaySeconds: 10
              periodSeconds: 10
            }
          ]
        }
      ]
      scale: {
        minReplicas: minReplicas
        maxReplicas: maxReplicas
        rules: [
          {
            name: 'cpu-scale'
            custom: {
              type: 'cpu'
              metadata: {
                type: 'Utilization'
                value: '70'          // Escala cuando CPU supera 70%
              }
            }
          }
          {
            name: 'http-scale'
            http: {
              metadata: {
                concurrentRequests: '20'  // Escala por requests concurrentes
              }
            }
          }
        ]
      }
    }
  }
}

output id string = backendApp.id
output fqdn string = backendApp.properties.configuration.ingress.fqdn
output internalFqdn string = '${appName}.internal'
