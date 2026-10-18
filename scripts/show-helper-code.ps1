$ErrorActionPreference = 'Stop'
$envPath = Join-Path (Split-Path -Parent $PSScriptRoot) '.env.helper'
if (-not (Test-Path -LiteralPath $envPath)) { throw 'Run scripts/setup-helper.ps1 first.' }
$entry = Get-Content -LiteralPath $envPath -Encoding utf8 | Where-Object { $_ -match '^QUERYLAB_PAIRING_TOKEN=' } | Select-Object -First 1
if (-not $entry) { throw 'The local helper pairing code is missing.' }
Write-Output 'Pairing code for your local helper (treat it as private):'
Write-Output $entry.Substring('QUERYLAB_PAIRING_TOKEN='.Length)

