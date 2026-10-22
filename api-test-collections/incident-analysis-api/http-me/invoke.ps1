param([string]$BaseUrl = "http://localhost:8000")

$payload = Get-Content (Join-Path $PSScriptRoot "sample-data.json") -Raw | ConvertFrom-Json
try {
    Invoke-WebRequest -UseBasicParsing -Method Post -Uri "$BaseUrl/api/auth/register" `
        -ContentType "application/json" -Body ($payload | ConvertTo-Json) | Out-Null
} catch {
    if ($_.Exception.Response.StatusCode.value__ -ne 409) { throw }
}
$session = [Microsoft.PowerShell.Commands.WebRequestSession]::new()
$loginBody = @{ email = $payload.email; password = $payload.password } | ConvertTo-Json
Invoke-WebRequest -UseBasicParsing -Method Post -Uri "$BaseUrl/api/auth/login" `
    -ContentType "application/json" -Body $loginBody -WebSession $session | Out-Null
$response = Invoke-WebRequest -UseBasicParsing -Uri "$BaseUrl/api/auth/me" -WebSession $session
if ($response.StatusCode -ne 200) {
    throw "Expected GET /api/auth/me to return 200, got $($response.StatusCode)."
}
$response.Content