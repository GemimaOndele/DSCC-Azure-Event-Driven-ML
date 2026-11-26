targetScope = 'resourceGroup'

param location string
param storageName string
param prefix string = 'dscc'
@description('Globally unique Function App name.')
param functionName string
@description('Approved immutable ghcr.io image digest, not a mutable latest tag.')
param apiImage string
param cosmosEndpoint string = ''
@description('Exact dashboard origin, no trailing slash; empty until static site is configured.')
param dashboardOrigin string = ''
@description('Only temporary public synthetic-data demo is currently supported. This parameter is a deliberate opt-in.')
@allowed(['approved-synthetic-demo'])
param exposureApproval string
@description('Set to private only when scoped pull credentials have been approved.')
@allowed(['public','private'])
param registryMode string
param registryUsername string = ''
@secure()
param registryPassword string = ''
@allowed([512,2048,4096])
param functionMemoryMB int = 512
param tags object = {
  project: 'DSCC'
  purpose: 'academic-demo'
}

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: storageName
}
resource runtimeIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' existing = {
  name: '${prefix}-runtime-mi'
}
resource insights 'Microsoft.Insights/components@2020-02-02' existing = {
  name: '${prefix}-insights'
}
resource logs 'Microsoft.OperationalInsights/workspaces@2023-09-01' existing = {
  name: '${prefix}-logs'
}

resource environment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: '${prefix}-env'
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logs.properties.customerId
        sharedKey: logs.listKeys().primarySharedKey
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
resource api 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${prefix}-api'
  location: location
  tags: union(tags, { exposure: exposureApproval })
  properties: {
    managedEnvironmentId: environment.id
    workloadProfileName: 'Consumption'
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 8000
        allowInsecure: false
        transport: 'auto'
      }
      secrets: registryMode == 'private' ? [
        {
          name: 'ghcr-pull'
          value: registryPassword
        }
      ] : []
      registries: registryMode == 'private' ? [
        {
          server: 'ghcr.io'
          username: registryUsername
          passwordSecretRef: 'ghcr-pull'
        }
      ] : []
    }
    template: {
      containers: [
        {
          name: 'api'
          image: apiImage
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
          env: [
            {
              name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
              value: insights.properties.ConnectionString
            }
          ]
        }
      ]
      scale: {
        minReplicas: 0
        maxReplicas: 2
      }
    }
  }
}

resource plan 'Microsoft.Web/serverfarms@2024-04-01' = {
  name: '${prefix}-flex'
  location: location
  tags: tags
  kind: 'functionapp'
  sku: {
    name: 'FC1'
    tier: 'FlexConsumption'
  }
  properties: {
    reserved: true
  }
}
resource functions 'Microsoft.Web/sites@2024-04-01' = {
  name: functionName
  location: location
  tags: tags
  kind: 'functionapp,linux'
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${runtimeIdentity.id}': {}
    }
  }
  properties: {
    serverFarmId: plan.id
    httpsOnly: true
    functionAppConfig: {
      deployment: {
        storage: {
          type: 'blobContainer'
          value: '${storage.properties.primaryEndpoints.blob}deployment'
          authentication: {
            type: 'UserAssignedIdentity'
            userAssignedIdentityResourceId: runtimeIdentity.id
          }
        }
      }
      runtime: {
        name: 'python'
        version: '3.12'
      }
      scaleAndConcurrency: {
        instanceMemoryMB: functionMemoryMB
        maximumInstanceCount: 40
      }
    }
    siteConfig: {
      appSettings: [
        {
          name: 'AzureWebJobsStorage__accountName'
          value: storage.name
        }
        {
          name: 'AzureWebJobsStorage__credential'
          value: 'managedidentity'
        }
        {
          name: 'AzureWebJobsStorage__clientId'
          value: runtimeIdentity.properties.clientId
        }
        {
          name: 'AZURE_CLIENT_ID'
          value: runtimeIdentity.properties.clientId
        }
        {
          name: 'STORAGE_ACCOUNT'
          value: storage.name
        }
        {
          name: 'MODEL_API_URL'
          value: 'https://${api.properties.configuration.ingress.fqdn}'
        }
        {
          name: 'COSMOS_ENDPOINT'
          value: cosmosEndpoint
        }
        {
          name: 'DASHBOARD_ORIGIN'
          value: dashboardOrigin
        }
        {
          name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
          value: insights.properties.ConnectionString
        }
        {
          name: 'APPLICATIONINSIGHTS_AUTHENTICATION_STRING'
          value: 'ClientId=${runtimeIdentity.properties.clientId};Authorization=AAD'
        }
      ]
    }
  }
}
output apiName string = api.name
output apiUrl string = 'https://${api.properties.configuration.ingress.fqdn}'
output functionAppName string = functions.name
output functionUrl string = 'https://${functions.properties.defaultHostName}'
