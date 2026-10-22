param([string]$BaseUrl = "http://localhost:8000")

$payload = Get-Content (Join-Path $PSScriptRoot "sample-data.json") -Raw | ConvertFrom-Json
$payload.email = "debug-$([DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds())@example.com"
$response = Invoke-WebRequest -UseBasicParsing -Method Post -Uri "$BaseUrl/api/auth/register" `
    -ContentType "application/json" -Body ($payload | ConvertTo-Json)
if ($response.StatusCode -ne 201) {
    throw "Expected POST /api/auth/register to return 201, got $($response.StatusCode)."
}
$response.Content