$ErrorActionPreference = 'Stop'
$workspaceRoot = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $workspaceRoot '.env'
if (Test-Path -LiteralPath $envPath) {
    Write-Output 'Existing .env preserved.'
    exit 0
}
$secretBytes = New-Object byte[] 32
$generator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
try { $generator.GetBytes($secretBytes) } finally { $generator.Dispose() }
$localPassword = ([BitConverter]::ToString($secretBytes)).Replace('-', '').ToLowerInvariant()
$template = Get-Content -LiteralPath (Join-Path $workspaceRoot '.env.example') -Raw
$template.Replace('replace-with-a-long-random-local-password', $localPassword) | Set-Content -LiteralPath $envPath -Encoding ascii
Write-Output 'Created local .env with a random database password. Keep this file private.'

