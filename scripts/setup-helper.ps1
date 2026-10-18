param(
    [ValidateSet('Bundled', 'Existing')][string]$Database = 'Bundled',
    [string]$WebsiteOrigin = ''
)
$ErrorActionPreference = 'Stop'
$workspaceRoot = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $workspaceRoot '.env.helper'
if ($WebsiteOrigin) {
    $parsedOrigin = $null
    if (-not [Uri]::TryCreate($WebsiteOrigin, [UriKind]::Absolute, [ref]$parsedOrigin) -or
        ($parsedOrigin.Scheme -ne 'https' -and -not ($parsedOrigin.Scheme -eq 'http' -and $parsedOrigin.IsLoopback)) -or
        $parsedOrigin.AbsolutePath -ne '/' -or $parsedOrigin.Query -or $parsedOrigin.Fragment -or $parsedOrigin.UserInfo) {
        throw 'Enter just the HTTPS website address (scheme, hostname and optional port), or HTTP on localhost.'
    }
    $WebsiteOrigin = $parsedOrigin.GetLeftPart([UriPartial]::Authority).TrimEnd('/')
}
if (Test-Path -LiteralPath $envPath) {
    if ($WebsiteOrigin) {
        $lines = @(Get-Content -LiteralPath $envPath -Encoding utf8)
        $found = $false
        for ($index = 0; $index -lt $lines.Length; $index++) {
            if ($lines[$index] -match '^QUERYLAB_HELPER_ALLOWED_ORIGINS=(.*)$') {
                $origins = @()
                foreach ($candidate in $matches[1].Split(',')) {
                    if ($candidate -and $origins -cnotcontains $candidate) { $origins += $candidate }
                }
                if ($origins -cnotcontains $WebsiteOrigin) { $origins += $WebsiteOrigin }
                $lines[$index] = 'QUERYLAB_HELPER_ALLOWED_ORIGINS=' + ($origins -join ',')
                $found = $true
            }
        }
        if (-not $found) { $lines += 'QUERYLAB_HELPER_ALLOWED_ORIGINS=' + $WebsiteOrigin }
        [System.IO.File]::WriteAllLines($envPath, [string[]]$lines, (New-Object System.Text.UTF8Encoding($false)))
    }
    Write-Output 'Existing local configuration preserved; the selected website is trusted.'
    return
}
function New-LocalSecret([int]$Length) {
    $bytes = New-Object byte[] $Length
    $generator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $generator.GetBytes($bytes) } finally { $generator.Dispose() }
    return ([BitConverter]::ToString($bytes)).Replace('-', '').ToLowerInvariant()
}
$template = Get-Content -LiteralPath (Join-Path $workspaceRoot 'helper.env.example') -Raw
$template = $template.Replace('generate-a-local-pairing-code', (New-LocalSecret 32))
$template = $template.Replace('generate-a-local-namespace', (New-LocalSecret 6))
if ($Database -eq 'Bundled') {
    $template = $template.Replace('replace-with-your-local-mysql-password', (New-LocalSecret 32))
} else {
    $template = $template.Replace('MYSQL_HOST=mysql', 'MYSQL_HOST=host.docker.internal')
}
if ($WebsiteOrigin) {
    $template = [regex]::Replace($template, '(?m)^QUERYLAB_HELPER_ALLOWED_ORIGINS=([^\r\n]*)', {
        param($entry)
        $origins = @()
        foreach ($candidate in $entry.Groups[1].Value.Split(',')) {
            if ($candidate -and $origins -cnotcontains $candidate) { $origins += $candidate }
        }
        if ($origins -cnotcontains $WebsiteOrigin) { $origins += $WebsiteOrigin }
        return 'QUERYLAB_HELPER_ALLOWED_ORIGINS=' + ($origins -join ',')
    })
}
[System.IO.File]::WriteAllText($envPath, $template, (New-Object System.Text.UTF8Encoding($false)))
Write-Output 'Created private local .env.helper with a pairing code and installation namespace.'
if ($Database -eq 'Existing') { Write-Output 'Set MYSQL_HOST, MYSQL_PORT, MYSQL_ROOT_USER and MYSQL_ROOT_PASSWORD in .env.helper before starting.' }

