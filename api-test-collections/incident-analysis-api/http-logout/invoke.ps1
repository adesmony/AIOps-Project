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
$response = Invoke-WebRequest -UseBasicParsing -Method Post -Uri "$BaseUrl/api/auth/logout" `
    -WebSession $session
if ($response.StatusCode -ne 204) {
    throw "Expected POST /api/auth/logout to return 204, got $($response.StatusCode)."
}
"POST /api/auth/logout returned 204."