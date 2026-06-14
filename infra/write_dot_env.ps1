function Get-AzdValue {
	param([string]$Name)
	try {
		$value = azd env get-value $Name 2>&1
		if ($null -eq $value) { return "" }
		$trimmed = ($value -join "`n").Trim()
		if ($trimmed.StartsWith("ERROR:")) { return "" }
		if ($trimmed.Contains("key not found in environment values")) { return "" }
		return $trimmed
	}
	catch {
		return ""
	}
}

function Get-FirstArrayValue {
	param([string]$Raw)
	if ([string]::IsNullOrWhiteSpace($Raw)) { return "" }
	$trimmed = $Raw.Trim()
	if ($trimmed.StartsWith("[") -and $trimmed.EndsWith("]")) {
		try {
			$values = $trimmed | ConvertFrom-Json
			if ($values -and $values.Count -gt 0) { return [string]$values[0] }
		}
		catch {
			return ""
		}
		return ""
	}
	return $trimmed
}

$azureTenantId = Get-AzdValue "AZURE_TENANT_ID"
$foundryModelsEndpoint = Get-AzdValue "FOUNDRY_MODELS_ENDPOINT"
$foundryOpenAiDeployment = Get-AzdValue "FOUNDRY_OPENAI_DEPLOYMENT"
if ([string]::IsNullOrWhiteSpace($foundryOpenAiDeployment)) {
	$foundryOpenAiDeployment = Get-AzdValue "AZURE_OPENAI_CHAT_DEPLOYMENT"
}
if ([string]::IsNullOrWhiteSpace($foundryOpenAiDeployment)) {
	$foundryOpenAiDeployment = Get-FirstArrayValue (Get-AzdValue "FOUNDRY_OPENAI_DEPLOYMENT_NAMES")
}

$foundryClaudeDeployment = Get-AzdValue "FOUNDRY_CLAUDE_DEPLOYMENT"
if ([string]::IsNullOrWhiteSpace($foundryClaudeDeployment)) {
	$foundryClaudeDeployment = Get-FirstArrayValue (Get-AzdValue "CLAUDE_DEPLOYMENT_NAMES")
}


$envLines = @(
	"AZURE_TENANT_ID=$azureTenantId",
	"",
	"FOUNDRY_MODELS_ENDPOINT=$foundryModelsEndpoint",
	"FOUNDRY_OPENAI_DEPLOYMENT=$foundryOpenAiDeployment",
	"FOUNDRY_CLAUDE_DEPLOYMENT=$foundryClaudeDeployment"
)

Set-Content -Path .env -Value $envLines
