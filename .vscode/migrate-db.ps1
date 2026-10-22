$workspaceRoot = Split-Path $PSScriptRoot -Parent
$environmentFile = Join-Path $workspaceRoot ".env"

Get-Content $environmentFile | ForEach-Object {
    $line = $_.Trim()
    if (-not $line -or $line.StartsWith("#")) { return }

    $name, $value = $line -split "=", 2
    Set-Item -Path "Env:$name" -Value $value
}

Set-Location (Join-Path $workspaceRoot "services/incident-api")
python -m alembic upgrade head
exit $LASTEXITCODE