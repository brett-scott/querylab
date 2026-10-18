$ErrorActionPreference = 'Stop'
$repository = Split-Path -Parent $PSScriptRoot
$launcher = Join-Path $repository 'distribution/windows/launch-helper.ps1'
. $launcher -LibraryOnly
$temporaryRoot = Join-Path ([System.IO.Path]::GetTempPath()) ('querylab-launcher-test-' + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path (Join-Path $temporaryRoot 'scripts') -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'setup-helper.ps1') -Destination (Join-Path $temporaryRoot 'scripts/setup-helper.ps1')
Copy-Item -LiteralPath (Join-Path $repository 'helper.env.example') -Destination (Join-Path $temporaryRoot 'helper.env.example')
$script:InstallRoot = $temporaryRoot
$script:WorkerStatusPath = Join-Path $temporaryRoot 'status.json'
$script:Count = 0
function Assert([bool]$Condition, [string]$Message) { if (-not $Condition) { throw $Message }; $script:Count++ }
function Assert-Throws([scriptblock]$Action, [string]$Match) {
    $failure = ''
    try { & $Action | Out-Null } catch { $failure = $_.Exception.Message }
    Assert ($failure -like "*$Match*") ('Expected actionable failure containing: ' + $Match)
}
$originalDocker = (Get-Item function:Invoke-LauncherDocker).ScriptBlock
$originalPrerequisites = (Get-Item function:Test-LauncherPrerequisites).ScriptBlock
$originalPortAvailable = (Get-Item function:Test-PortAvailable).ScriptBlock
try {
    Assert ((Get-WebsiteOrigin 'https://querylab.example/') -eq 'https://querylab.example') 'HTTPS origin should normalise.'
    Assert ((Get-WebsiteOrigin 'http://127.0.0.1:8081') -eq 'http://127.0.0.1:8081') 'Local preview should be accepted.'
    foreach ($invalid in @('http://querylab.example', 'https://querylab.example/path', 'https://user:password@querylab.example', 'https://querylab.example?x=1', 'file:///C:/test', '')) {
        Assert-Throws { Get-WebsiteOrigin $invalid } 'website address'
    }
    & (Join-Path $temporaryRoot 'scripts/setup-helper.ps1') -WebsiteOrigin 'http://127.0.0.1:8081' | Out-Null
    $first = Get-HelperConfiguration
    Assert (@($first['QUERYLAB_HELPER_ALLOWED_ORIGINS'].Split(',') | Where-Object { $_ -ceq 'http://127.0.0.1:8081' }).Count -eq 1) 'Fresh setup with a default origin must not duplicate it.'
    Assert ($first['QUERYLAB_PAIRING_TOKEN'] -match '^[a-f0-9]{64}$') 'Generated code must be random and long.'
    Assert ($first['QUERYLAB_WORKSPACE_NAMESPACE'] -match '^[a-f0-9]{12}$') 'Generated installation namespace is invalid.'
    $duplicatePath = Join-Path $temporaryRoot '.env.helper'
    $duplicateLines = @(Get-Content -LiteralPath $duplicatePath -Encoding utf8 | ForEach-Object {
        if ($_ -match '^QUERYLAB_HELPER_ALLOWED_ORIGINS=') { $_ + ',http://127.0.0.1:8081,http://127.0.0.1:8081' } else { $_ }
    })
    [System.IO.File]::WriteAllLines($duplicatePath, [string[]]$duplicateLines, (New-Object System.Text.UTF8Encoding($false)))
    & (Join-Path $temporaryRoot 'scripts/setup-helper.ps1') -WebsiteOrigin 'http://127.0.0.1:8081' | Out-Null
    $cleaned = Get-HelperConfiguration
    Assert (@($cleaned['QUERYLAB_HELPER_ALLOWED_ORIGINS'].Split(',') | Where-Object { $_ -ceq 'http://127.0.0.1:8081' }).Count -eq 1) 'Reopen must clean previously duplicated origins.'
    foreach ($key in @('MYSQL_ROOT_PASSWORD', 'QUERYLAB_PAIRING_TOKEN', 'QUERYLAB_WORKSPACE_NAMESPACE')) {
        Assert ($first[$key] -ceq $cleaned[$key]) ('Duplicate cleanup must preserve ' + $key)
    }
    $cleanedText = Get-Content -LiteralPath $duplicatePath -Raw -Encoding utf8
    & (Join-Path $temporaryRoot 'scripts/setup-helper.ps1') -WebsiteOrigin 'http://127.0.0.1:8081' | Out-Null
    Assert ($cleanedText -ceq (Get-Content -LiteralPath $duplicatePath -Raw -Encoding utf8)) 'Reopening with the same website must be idempotent.'
    & (Join-Path $temporaryRoot 'scripts/setup-helper.ps1') -WebsiteOrigin 'https://another.example' | Out-Null
    & (Join-Path $temporaryRoot 'scripts/setup-helper.ps1') -WebsiteOrigin 'https://another.example' | Out-Null
    $second = Get-HelperConfiguration
    foreach ($key in @('MYSQL_ROOT_PASSWORD', 'QUERYLAB_PAIRING_TOKEN', 'QUERYLAB_WORKSPACE_NAMESPACE')) {
        Assert ($first[$key] -ceq $second[$key]) ('Retry must preserve ' + $key)
    }
    Assert (@($second['QUERYLAB_HELPER_ALLOWED_ORIGINS'].Split(',') | Where-Object { $_ -eq 'https://another.example' }).Count -eq 1) 'Trusted origin should be added once.'
    $before = Get-Content -LiteralPath (Join-Path $temporaryRoot '.env.helper') -Raw
    Assert-Throws { & (Join-Path $temporaryRoot 'scripts/setup-helper.ps1') -WebsiteOrigin 'http://untrusted.example' } 'HTTPS'
    Assert ($before -ceq (Get-Content -LiteralPath (Join-Path $temporaryRoot '.env.helper') -Raw)) 'Invalid origins must not rewrite config.'

    function Get-Command { param($Name, $ErrorAction) if ($Name -eq 'docker') { return $null }; Microsoft.PowerShell.Core\Get-Command $Name }
    Assert-Throws { Test-LauncherPrerequisites } 'Docker Desktop is required'
    Remove-Item function:Get-Command
    function Invoke-LauncherDocker { param($DockerArguments) return @{ ExitCode = 1; Output = 'private failure detail' } }
    Assert-Throws { Test-LauncherPrerequisites } 'not ready'
    function Invoke-LauncherDocker { param($DockerArguments) return @{ ExitCode = 0; Output = 'windows' } }
    Assert-Throws { Test-LauncherPrerequisites } 'Linux containers'
    function Invoke-LauncherDocker { param($DockerArguments) if ($DockerArguments[0] -eq 'info') { return @{ ExitCode = 0; Output = 'linux' } }; return @{ ExitCode = 1; Output = '' } }
    Assert-Throws { Test-LauncherPrerequisites } 'Compose is missing'
    function Test-PortAvailable { param($Port) return $false }
    function Invoke-LauncherDocker { param($DockerArguments) return @{ ExitCode = 0; Output = '' } }
    Assert-Throws { Assert-HelperPortOwner 8765 'querylab-installed-123456abcdef' } 'already used'
    function Invoke-LauncherDocker {
        param($DockerArguments)
        if ($DockerArguments[0] -eq 'ps') { return @{ ExitCode = 0; Output = 'owned-container' } }
        return @{ ExitCode = 0; Output = '[{"NetworkSettings":{"Ports":{"8000/tcp":[{"HostIp":"127.0.0.1","HostPort":"8765"}]}}}]' }
    }
    Assert-HelperPortOwner 8765 'querylab-installed-123456abcdef'
    Assert $true 'The current installation may reuse its own published port.'
    Assert-Throws { Assert-HelperPortOwner 8766 'querylab-installed-123456abcdef' } 'already used'

    function Test-LauncherPrerequisites {}
    function Test-PortAvailable { param($Port) return $true }
    function Invoke-LauncherDocker { param($DockerArguments) return @{ ExitCode = 1; Output = 'private failure detail' } }
    Assert-Throws { Start-LocalHelper 'https://querylab.example' 8767 } 'could not start'
    $failed = Get-HelperConfiguration
    Assert ($first['MYSQL_ROOT_PASSWORD'] -ceq $failed['MYSQL_ROOT_PASSWORD']) 'Startup failure must preserve database credentials.'
    function Invoke-LauncherDocker { param($DockerArguments) $script:StartedArguments = $DockerArguments; return @{ ExitCode = 0; Output = '' } }
    function Invoke-RestMethod { param($Uri, $TimeoutSec) return @{ mode = 'helper'; protocol_version = 1; database = @{ connected = $true } } }
    $ready = Start-LocalHelper 'https://querylab.example' 8767
    Assert ($ready.HelperUrl -eq 'http://127.0.0.1:8767') 'Explicit helper port should be used.'
    Assert ($ready.ProjectName -eq ('querylab-installed-' + $first['QUERYLAB_WORKSPACE_NAMESPACE'])) 'Installation must use its own compose project.'
    Assert ($script:StartedArguments -contains $ready.ProjectName) 'Compose must receive the isolated project name.'
    $statusText = Get-Content -LiteralPath $script:WorkerStatusPath -Raw
    Assert ($statusText -notlike ('*' + $first['QUERYLAB_PAIRING_TOKEN'] + '*')) 'Status must never contain pairing code.'
    Assert ($statusText -notlike ('*' + $first['MYSQL_ROOT_PASSWORD'] + '*')) 'Status must never contain database password.'
    Assert (($statusText | ConvertFrom-Json).state -eq 'ready') 'Only a compatible helper with connected database should become ready.'
    $envPath = Join-Path $temporaryRoot '.env.helper'
    $existingLines = @(Get-Content -LiteralPath $envPath | ForEach-Object { if ($_ -eq 'MYSQL_HOST=mysql') { 'MYSQL_HOST=host.docker.internal' } else { $_ } })
    Set-Content -LiteralPath $envPath -Value $existingLines -Encoding ascii
    $existingReady = Start-LocalHelper 'https://querylab.example' 8767
    Assert ($script:StartedArguments -notcontains 'bundled') 'Existing server configuration must not start bundled MySQL.'
    Assert ((Get-HelperConfiguration)['MYSQL_ROOT_PASSWORD'] -ceq $first['MYSQL_ROOT_PASSWORD']) 'Existing server password must be preserved.'
    Write-Output ("Launcher checks passed: $script:Count. No local secrets printed.")
} finally {
    Set-Item function:Invoke-LauncherDocker $originalDocker
    Set-Item function:Test-LauncherPrerequisites $originalPrerequisites
    Set-Item function:Test-PortAvailable $originalPortAvailable
    Remove-Item function:Invoke-RestMethod -ErrorAction SilentlyContinue
    Remove-Item function:Get-Command -ErrorAction SilentlyContinue
    # Only this exact freshly generated test directory can be removed.
    $resolved = [System.IO.Path]::GetFullPath($temporaryRoot)
    $tempParent = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath())
    if ($resolved.StartsWith($tempParent, [StringComparison]::OrdinalIgnoreCase) -and (Split-Path -Leaf $resolved) -match '^querylab-launcher-test-[a-f0-9]{32}$') {
        Remove-Item -LiteralPath $resolved -Recurse -Force
    }
}
