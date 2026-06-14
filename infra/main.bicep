targetScope = 'subscription'

@minLength(1)
@maxLength(64)
@description('Name of the the environment which is used to generate a short unique hash used in all resources.')
param environmentName string
@description('Azure region. All three families coexist in eastus2 or swedencentral.')
@allowed([
  'eastus2'
  'swedencentral'
  'westus2'
])
param location string

@description('Id of the user or app to assign application roles')
param principalId string = ''

@description('Whether to assign Foundry roles to principalId.')
param assignRbac bool = true

@description('Organization name surfaced via Claude modelProviderData.')
param claudeOrganizationName string

@description('Two-letter ISO country code for Claude modelProviderData.')
@minLength(2)
@maxLength(2)
param claudeCountryCode string = 'US'

@description('Industry for Claude modelProviderData. Must be lowercase.')
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
param claudeIndustry string = 'technology'

var resourceToken = toLower(uniqueString(subscription().id, environmentName, location))
var prefix = '${environmentName}${resourceToken}'
var tags = { 'azd-env-name': environmentName }
var foundryAccountName = '${prefix}-foundry'
var foundryProjectName = '${prefix}-proj'
var openAiDeploymentName = 'gpt-5.4-mini'
var claudeDeploymentName = 'claude-sonnet-4-5'

// Organize resources in a resource group
resource resourceGroup 'Microsoft.Resources/resourceGroups@2021-04-01' = {
    name: '${prefix}-rg'
    location: location
    tags: tags
}

module foundry 'foundry.bicep' = {
  name: 'foundry'
  scope: resourceGroup
  params: {
    location: location
    tags: tags
    accountName: foundryAccountName
    projectName: foundryProjectName
    openAiModels: [
      {
        deploymentName: openAiDeploymentName
        modelName: 'gpt-5.4-mini'
        modelVersion: '2026-03-17'
        capacity: 50
        format: 'OpenAI'
        skuName: 'GlobalStandard'
      }
    ]
    claudeModels: [
      {
        name: claudeDeploymentName
        capacity: 50
        version: '20250929'
      }
    ]
    claudeOrganizationName: claudeOrganizationName
    claudeCountryCode: claudeCountryCode
    claudeIndustry: claudeIndustry
    principalId: principalId
    assignRbac: assignRbac
  }
}

// Log Analytics workspace for Application Insights
var logAnalyticsName = '${prefix}-loganalytics'
module logAnalytics 'br/public:avm/res/operational-insights/workspace:0.9.1' = {
  name: 'loganalytics'
  scope: resourceGroup
  params: {
    name: logAnalyticsName
    location: location
    tags: tags
  }
}

// Application Insights for OpenTelemetry export
var appInsightsName = '${prefix}-appinsights'
module appInsights 'br/public:avm/res/insights/component:0.4.2' = {
  name: 'appinsights'
  scope: resourceGroup
  params: {
    name: appInsightsName
    location: location
    tags: tags
    workspaceResourceId: logAnalytics.outputs.resourceId
    kind: 'web'
    applicationType: 'web'
  }
}

output AZURE_LOCATION string = location
output AZURE_TENANT_ID string = tenant().tenantId
output AZURE_RESOURCE_GROUP string = resourceGroup.name

// Specific to Application Insights
output APPLICATIONINSIGHTS_CONNECTION_STRING string = appInsights.outputs.connectionString

// Specific to Microsoft Foundry
output FOUNDRY_PROJECT_ENDPOINT string = foundry.outputs.foundryProjectEndpoint
output FOUNDRY_ACCOUNT_NAME string = foundry.outputs.foundryAccountName

// Specific to model deployments
output FOUNDRY_MODELS_ENDPOINT string = foundry.outputs.modelsEndpoint
output FOUNDRY_OPENAI_DEPLOYMENT string = openAiDeploymentName
output FOUNDRY_OPENAI_DEPLOYMENT_NAMES array = foundry.outputs.openAiDeploymentNames
output FOUNDRY_CLAUDE_DEPLOYMENT string = claudeDeploymentName
output CLAUDE_DEPLOYMENT_NAMES array = foundry.outputs.claudeDeploymentNames
