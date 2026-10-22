param([string]$BaseUrl = "http://localhost:8000")

$payload = Get-Content (Join-Path $PSScriptRoot "sample-data.json") -Raw | ConvertFrom-Json
try {
    Invoke-WebRequest -UseBasicParsing -Method Post -Uri "$BaseUrl/api/auth/register" `
        -ContentType "application/json" -Body ($payload | ConvertTo-Json) | Out-Null
} catch {
    if ($_.Exception.Response.StatusCode.value__ -ne 409) { throw }
}
$loginBody = @{ email = $payload.email; password = $payload.password } | ConvertTo-Json
$response = Invoke-WebRequest -UseBasicParsing -Method Post -Uri "$BaseUrl/api/auth/login" `
    -ContentType "application/json" -Body $loginBody
if ($response.StatusCode -ne 200) {
    throw "Expected POST /api/auth/login to return 200, got $($response.StatusCode)."
}
$response.Content