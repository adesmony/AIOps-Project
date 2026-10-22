param([string]$BaseUrl = "http://localhost:8000")

$payload = Get-Content (Join-Path $PSScriptRoot "sample-data.json") -Raw | ConvertFrom-Json
try {
    Invoke-WebRequest -UseBasicParsing -Method Post -Uri "$BaseUrl/api/auth/register" `
        -ContentType "application/json" -Body ($payload.credentials | ConvertTo-Json) | Out-Null
} catch {
    if ($_.Exception.Response.StatusCode.value__ -ne 409) { throw }
}
$session = [Microsoft.PowerShell.Commands.WebRequestSession]::new()
$loginBody = @{
    email = $payload.credentials.email
    password = $payload.credentials.password
} | ConvertTo-Json
Invoke-WebRequest -UseBasicParsing -Method Post -Uri "$BaseUrl/api/auth/login" `
    -ContentType "application/json" -Body $loginBody -WebSession $session | Out-Null
$response = Invoke-WebRequest -UseBasicParsing -Method Post -Uri "$BaseUrl/api/incidents/analyze" `
    -ContentType "application/json" -Body ($payload.request | ConvertTo-Json) -WebSession $session
if ($response.StatusCode -ne 200) {
    throw "Expected POST /api/incidents/analyze to return 200, got $($response.StatusCode)."
}
$response.Content