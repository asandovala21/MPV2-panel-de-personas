// Módulo: Container App Frontend (nginx)
// Expuesto públicamente con HTTPS — proxea /api al backend interno

param appName string
param location string
param containerAppEnvId string
param acrLoginServer string
param imageTag string
param managedIdentityId string
param backendInternalFqdn string
param minReplicas int = 1
param maxReplicas int = 3

resource frontendApp 'Microsoft.App/containerApps@2023-05-01' = {
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
        external: true            // Expuesto a internet con HTTPS gestionado por Azure
        targetPort: 80
        transport: 'http'
        traffic: [
          {
            weight: 100
            latestRevision: true
          }
        ]
      }
      registries: [
        {
          server: acrLoginServer
          identity: managedIdentityId
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'frontend'
          image: '${acrLoginServer}/panel-personas-frontend:${imageTag}'
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
          env: [
            {
              name: 'BACKEND_URL'
              value: 'http://${backendInternalFqdn}:8081'
            }
          ]
          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: '/health'
                port: 80
              }
              initialDelaySeconds: 5
              periodSeconds: 30
            }
          ]
        }
      ]
      scale: {
        minReplicas: minReplicas
        maxReplicas: maxReplicas
        rules: [
          {
            name: 'http-scale'
            http: {
              metadata: {
                concurrentRequests: '50'
              }
            }
          }
        ]
      }
    }
  }
}

output id string = frontendApp.id
output fqdn string = frontendApp.properties.configuration.ingress.fqdn
