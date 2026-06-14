// Foundry account + project + list-based Claude deployments + optional RBAC.

type OpenAiDeployment = {
  deploymentName: string
  modelName: string
  modelVersion: string
  capacity: int
  format: string?
  skuName: string?
}

type ClaudeModelDeployment = {
  name: string
  capacity: int
  version: string?
}

param location string
param tags object
param accountName string
param projectName string

param openAiModels OpenAiDeployment[]
param claudeModels ClaudeModelDeployment[]

param claudeOrganizationName string
@minLength(2)
@maxLength(2)
param claudeCountryCode string
@allowed([
  'technology'
  'finance'
  'healthcare'
  'education'
  'retail'
  'manufacturing'
  'government'
  'media'
  'other'
])
param claudeIndustry string
param principalId string
param assignRbac bool = true

var defaultClaudeModelVersion = '1'
var rbacEnabled = assignRbac && !empty(principalId)
var effectiveOpenAiModels = [for model in openAiModels: {
  deploymentName: model.deploymentName
  modelName: model.modelName
  modelVersion: model.modelVersion
  capacity: model.capacity
  format: model.?format ?? 'OpenAI'
  skuName: model.?skuName ?? 'GlobalStandard'
}]
var effectiveClaudeModels = [for model in claudeModels: {
  name: model.name
  capacity: model.capacity
  version: model.?version ?? defaultClaudeModelVersion
}]
var openAiDeploymentNames = [for model in effectiveOpenAiModels: model.deploymentName]
var deploymentNames = [for model in effectiveClaudeModels: model.name]

// Built-in role definition IDs.
// NOTE: Azure renamed these roles. The GUIDs are stable.
//   53ca6127-... : "Azure AI User" -> "Foundry User" (data-plane access)
//   eadc314b-... : "Azure AI Project Manager" -> "Foundry Project Manager"
var foundryUserRoleId = '53ca6127-db72-4b80-b1b0-d745d6d5456d'
var foundryProjectManagerRoleId = 'eadc314b-1a2d-4efa-be10-5d325db5065e'

resource account 'Microsoft.CognitiveServices/accounts@2025-10-01-preview' = {
  name: accountName
  location: location
  tags: tags
  kind: 'AIServices'
  sku: {
    name: 'S0'
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    customSubDomainName: accountName
    allowProjectManagement: true
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: false
  }
}

resource project 'Microsoft.CognitiveServices/accounts/projects@2025-10-01-preview' = {
  parent: account
  name: projectName
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {}
}

@batchSize(1)
resource openAiDeployments 'Microsoft.CognitiveServices/accounts/deployments@2025-10-01-preview' = [for model in effectiveOpenAiModels: {
  parent: account
  name: model.deploymentName
  sku: {
    name: model.skuName
    capacity: model.capacity
  }
  properties: {
    model: {
      format: model.format
      name: model.modelName
      version: model.modelVersion
    }
    versionUpgradeOption: 'OnceNewDefaultVersionAvailable'
    raiPolicyName: 'Microsoft.DefaultV2'
  }
  dependsOn: [
    project
  ]
}]

@batchSize(1)
resource claudeDeployments 'Microsoft.CognitiveServices/accounts/deployments@2025-10-01-preview' = [for model in effectiveClaudeModels: {
  parent: account
  name: model.name
  sku: {
    name: 'GlobalStandard'
    capacity: model.capacity
  }
  properties: {
    model: {
      format: 'Anthropic'
      name: model.name
      version: model.version
    }
    modelProviderData: {
      organizationName: claudeOrganizationName
      countryCode: claudeCountryCode
      industry: claudeIndustry
    }
    versionUpgradeOption: 'OnceNewDefaultVersionAvailable'
    raiPolicyName: 'Microsoft.DefaultV2'
  }
  dependsOn: [
    openAiDeployments
  ]
}]

resource foundryUserAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (rbacEnabled) {
  name: guid(account.id, principalId, foundryUserRoleId)
  scope: account
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', foundryUserRoleId)
    principalId: principalId
    principalType: 'User'
  }
}

resource foundryProjectManagerAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (rbacEnabled) {
  name: guid(account.id, principalId, foundryProjectManagerRoleId)
  scope: account
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', foundryProjectManagerRoleId)
    principalId: principalId
    principalType: 'User'
  }
}

output modelsEndpoint string = 'https://${account.name}.services.ai.azure.com'
output foundryProjectEndpoint string = 'https://${account.name}.services.ai.azure.com/api/projects/${project.name}'
output foundryAccountName string = account.name
output openAiDeploymentNames array = openAiDeploymentNames
output claudeDeploymentNames array = deploymentNames
