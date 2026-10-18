param(
    [ValidateSet('Bundled', 'Existing')][string]$Database = 'Bundled',
    [switch]$Preview,
    [switch]$Quiet,
    [ValidatePattern('^[a-z0-9][a-z0-9_-]*$')][string]$ProjectName = ''
)
$ErrorActionPreference = 'Stop'
$workspaceRoot = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $workspaceRoot '.env.helper'
if (-not (Test-Path -LiteralPath $envPath)) {
    & (Join-Path $PSScriptRoot 'setup-helper.ps1') -Database $Database
}
$config = @{}
foreach ($line in Get-Content -LiteralPath $envPath -Encoding utf8) {
    if ($line -match '^([A-Z_]+)=(.*)$') { $config[$matches[1]] = $matches[2] }
}
if ($config['MYSQL_ROOT_PASSWORD'] -eq 'replace-with-your-local-mysql-password') {
    throw 'Configure your MySQL connection in the local .env.helper file before starting.'
}
if ($Database -eq 'Bundled' -and $config['MYSQL_HOST'] -ne 'mysql') {
    throw 'This configuration targets an existing server. Use -Database Existing, or edit .env.helper deliberately.'
}
$composeArgs = @('compose', '--env-file', $envPath, '-f', (Join-Path $workspaceRoot 'compose.helper.yaml'))
if ($ProjectName) { $composeArgs += @('--project-name', $ProjectName) }
if ($Database -eq 'Bundled') { $composeArgs += @('--profile', 'bundled') }
if ($Preview) { $composeArgs += @('--profile', 'preview') }
$composeArgs += @('up', '--build', '--wait', '--wait-timeout', '180')
& docker @composeArgs
if ($LASTEXITCODE -ne 0) { throw 'The helper stack did not start successfully. See the Docker output above.' }
Write-Output "Helper: http://127.0.0.1:$($config['QUERYLAB_HELPER_PORT'])"
if ($Preview) { Write-Output "Website preview: http://127.0.0.1:$($config['QUERYLAB_HELPER_PREVIEW_PORT'])" }
if (-not $Quiet) { & (Join-Path $PSScriptRoot 'show-helper-code.ps1') }

