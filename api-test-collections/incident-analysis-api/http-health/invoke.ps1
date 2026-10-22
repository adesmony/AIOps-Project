param([string]$BaseUrl = "http://localhost:8000")

$response = Invoke-WebRequest -UseBasicParsing -Uri "$BaseUrl/api/health"
if ($response.StatusCode -ne 200) {
    throw "Expected GET /api/health to return 200, got $($response.StatusCode)."
}
$response.Content