targetScope = 'resourceGroup'

@description('Region validated for the selected student subscription.')
param location string
@description('Globally unique storage account name, 3-24 lower-case letters/digits.')
@minLength(3)
@maxLength(24)
param storageName string
@description('Unique, lowercase name for Cosmos account (if used).')
param cosmosName string
@description('Only select Table after explicit fallback approval.')
@allowed(['cosmosFreeTier', 'table'])
param resultBackend string = 'cosmosFreeTier'
param prefix string = 'dscc'
param tags object = {
  project: 'DSCC'
  purpose: 'academic-demo'
}

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageName
  location: location
  tags: tags
  kind: 'StorageV2'
  sku: {
    name: 'Standard_LRS'
  }
  properties: {
    accessTier: 'Hot'
    supportsHttpsTrafficOnly: true
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    allowSharedKeyAccess: false
    publicNetworkAccess: 'Enabled'
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  name: 'default'
  parent: storage
  properties: {}
}
resource containers 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = [for name in ['input', 'output', 'rejected', 'models', 'deployment']: {
  name: name
  parent: blobService
  properties: {
    publicAccess: 'None'
  }
}]
resource queueService 'Microsoft.Storage/storageAccounts/queueServices@2023-05-01' = {
  name: 'default'
  parent: storage
  properties: {}
}
resource queues 'Microsoft.Storage/storageAccounts/queueServices/queues@2023-05-01' = [for name in ['inference-requests', 'inference-requests-poison']: {
  name: name
  parent: queueService
  properties: {}
}]
resource tableService 'Microsoft.Storage/storageAccounts/tableServices@2023-05-01' = if (resultBackend == 'table') {
  name: 'default'
  parent: storage
  properties: {}
}
resource table 'Microsoft.Storage/storageAccounts/tableServices/tables@2023-05-01' = if (resultBackend == 'table') {
  name: 'inferences'
  parent: tableService
  properties: {}
}

resource runtimeIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${prefix}-runtime-mi'
  location: location
  tags: tags
}
resource deploymentIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${prefix}-github-mi'
  location: location
  tags: tags
}
resource federation 'Microsoft.ManagedIdentity/userAssignedIdentities/federatedIdentityCredentials@2023-01-31' = {
  name: 'github-production'
  parent: deploymentIdentity
  properties: {
    issuer: 'https://token.actions.githubusercontent.com'
    // Match the immutable GitHub subject observed in OIDC run 45966902708.
    subject: 'repo:GemimaOndele@128593071/DSCC-Azure-Event-Driven-ML@1462622773:environment:production'
    audiences: ['api://AzureADTokenExchange']
  }
}

// Scope all runtime data access to the project storage account.
var blobOwner = 'b7e6dc6d-f1e8-4753-8033-0f276bb0955b'
var queueContributor = '974c5e8b-45b9-4653-ba55-5f855dd0fb88'
var tableContributor = '0a9a7e1f-b9d0-4cc4-a60d-0319b160aaa3'
var requiredStorageRoles = resultBackend == 'table' ? [blobOwner, queueContributor, tableContributor] : [blobOwner, queueContributor]
resource storageRoles 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for role in requiredStorageRoles: {
  name: guid(storage.id, runtimeIdentity.id, role)
  scope: storage
  properties: {
    principalId: runtimeIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', role)
  }
}]
resource githubRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, deploymentIdentity.id, 'contributor')
  properties: {
    principalId: deploymentIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'b24988ac-6180-42a0-ab88-20f7382dd24c')
  }
}

resource cosmos 'Microsoft.DocumentDB/databaseAccounts@2024-05-15' = if (resultBackend == 'cosmosFreeTier') {
  name: cosmosName
  location: location
  tags: tags
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    enableFreeTier: true
    disableLocalAuth: true
    publicNetworkAccess: 'Enabled'
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'
    }
    locations: [
      {
        locationName: location
        failoverPriority: 0
        isZoneRedundant: false
      }
    ]
    capacity: {
      totalThroughputLimit: 1000
    }
  }
}
resource database 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2024-05-15' = if (resultBackend == 'cosmosFreeTier') {
  name: 'pipeline'
  parent: cosmos
  properties: {
    resource: {
      id: 'pipeline'
    }
    options: {
      throughput: 400
    }
  }
}
resource results 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-05-15' = if (resultBackend == 'cosmosFreeTier') {
  name: 'inferences'
  parent: database
  properties: {
    resource: {
      id: 'inferences'
      partitionKey: {
        paths: ['/fileName']
        kind: 'Hash'
        version: 2
      }
    }
    options: {}
  }
}
resource cosmosDataRole 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2024-05-15' = if (resultBackend == 'cosmosFreeTier') {
  name: guid(cosmos.id, runtimeIdentity.id, 'data-contributor')
  parent: cosmos
  properties: {
    principalId: runtimeIdentity.properties.principalId
    roleDefinitionId: '${cosmos.id}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002'
    scope: cosmos.id
  }
}

resource logs 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${prefix}-logs'
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
    workspaceCapping: {
      dailyQuotaGb: json('0.2')
    }
  }
}
resource insights 'Microsoft.Insights/components@2020-02-02' = {
  name: '${prefix}-insights'
  location: location
  tags: tags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logs.id
  }
}
resource monitorRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(insights.id, runtimeIdentity.id, 'metrics-publisher')
  scope: insights
  properties: {
    principalId: runtimeIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '3913510d-42f4-4e42-8a64-420c390055eb')
  }
}

output storageAccount string = storage.name
output cosmosEndpoint string = resultBackend == 'cosmosFreeTier' ? cosmos!.properties.documentEndpoint : ''
output runtimeIdentityName string = runtimeIdentity.name
output githubClientId string = deploymentIdentity.properties.clientId
output githubTenantId string = tenant().tenantId
output githubSubscriptionId string = subscription().subscriptionId
output insightsName string = insights.name
output logWorkspaceName string = logs.name
