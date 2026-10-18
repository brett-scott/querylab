param(
    [switch]$Headless,
    [switch]$ValidateUI,
    [switch]$LibraryOnly,
    [string]$WebsiteOrigin = '',
    [ValidateRange(1024, 65535)][int]$HelperPort = 0,
    [switch]$Quiet,
    [string]$StatusPath = '',
    [string]$PreviewPath = ''
)
$ErrorActionPreference = 'Stop'
if ($PreviewPath -and -not $ValidateUI) { throw 'PreviewPath is available only with ValidateUI.' }
$script:InstallRoot = Split-Path -Parent $PSScriptRoot
$script:DockerHelp = 'https://docs.docker.com/desktop/setup/install/windows-install/'

function Get-HelperConfiguration {
    $values = @{}
    $path = Join-Path $script:InstallRoot '.env.helper'
    if (Test-Path -LiteralPath $path) {
        foreach ($line in Get-Content -LiteralPath $path -Encoding utf8) {
            if ($line -match '^([A-Z_]+)=(.*)$') { $values[$matches[1]] = $matches[2] }
        }
    }
    return $values
}

function Get-WebsiteOrigin([string]$Address) {
    $parsed = $null
    if (-not [Uri]::TryCreate($Address.Trim(), [UriKind]::Absolute, [ref]$parsed) -or
        ($parsed.Scheme -ne 'https' -and -not ($parsed.Scheme -eq 'http' -and $parsed.IsLoopback)) -or
        $parsed.AbsolutePath -ne '/' -or $parsed.Query -or $parsed.Fragment -or $parsed.UserInfo) {
        throw 'Enter the website address copied from QueryLab: HTTPS and hostname only, or HTTP on localhost for a preview.'
    }
    return $parsed.GetLeftPart([UriPartial]::Authority).TrimEnd('/')
}

function Invoke-LauncherDocker([string[]]$DockerArguments) {
    # Native command stderr is data, including informational Docker progress.
    $previous = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $output = @(& docker @DockerArguments 2>&1 | ForEach-Object { $_.ToString() })
        $code = $LASTEXITCODE
    } finally { $ErrorActionPreference = $previous }
    return @{ ExitCode = $code; Output = ($output -join "`n") }
}

function Test-LauncherPrerequisites {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw "Docker Desktop is required. Install it from $script:DockerHelp, restart Windows if requested, then open Docker Desktop and try again."
    }
    $info = Invoke-LauncherDocker -DockerArguments @('info', '--format', '{{.OSType}}')
    if ($info.ExitCode -ne 0) { throw 'Docker is installed but is not ready. Open Docker Desktop, finish its setup and wait for Engine running, then choose Start helper again.' }
    if (@($info.Output -split '\r?\n' | ForEach-Object { $_.Trim() }) -notcontains 'linux') { throw 'Docker is using Windows containers. In Docker Desktop switch to Linux containers, wait for Engine running, then try again.' }
    $compose = Invoke-LauncherDocker -DockerArguments @('compose', 'version', '--short')
    if ($compose.ExitCode -ne 0) { throw 'Docker Compose is missing. Update Docker Desktop, reopen it and try again.' }
}

function Test-PortAvailable([int]$Port) {
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $pending = $client.BeginConnect('127.0.0.1', $Port, $null, $null)
        if (-not $pending.AsyncWaitHandle.WaitOne(500)) { return $true }
        try { $client.EndConnect($pending); return $false } catch { return $true }
    } finally { $client.Dispose() }
}

function Assert-HelperPortOwner([int]$Port, [string]$ProjectName) {
    if (Test-PortAvailable $Port) { return }
    $containers = Invoke-LauncherDocker -DockerArguments @('ps', '-q', '--filter', "label=com.docker.compose.project=$ProjectName", '--filter', 'label=com.docker.compose.service=helper')
    if ($containers.ExitCode -eq 0 -and $containers.Output.Trim()) {
        foreach ($id in ($containers.Output.Trim() -split '\s+')) {
            $inspection = Invoke-LauncherDocker -DockerArguments @('inspect', $id)
            if ($inspection.ExitCode -ne 0) { continue }
            $container = @($inspection.Output | ConvertFrom-Json)[0]
            foreach ($binding in @($container.NetworkSettings.Ports.'8000/tcp')) {
                if ($binding.HostIp -eq '127.0.0.1' -and [int]$binding.HostPort -eq $Port) { return }
            }
        }
    }
    throw "Port $Port is already used by another application or QueryLab installation. Close that application, or use this launcher's advanced HelperPort option. No containers were changed."
}

function Set-LauncherStatus([string]$State, [string]$Message, [string]$HelperUrl = '') {
    if ($script:WorkerStatusPath) {
        $temporary = $script:WorkerStatusPath + '.tmp'
        @{ state = $State; message = $Message; helperUrl = $HelperUrl } | ConvertTo-Json -Compress | Set-Content -LiteralPath $temporary -Encoding utf8
        Move-Item -LiteralPath $temporary -Destination $script:WorkerStatusPath -Force
    }
}

function Start-LocalHelper([string]$Address, [int]$Port = 0) {
    $origin = Get-WebsiteOrigin $Address
    Set-LauncherStatus 'working' 'Checking Docker Desktop...'
    Test-LauncherPrerequisites
    $configuration = Get-HelperConfiguration
    $database = 'Bundled'
    if ($configuration.ContainsKey('MYSQL_HOST') -and $configuration['MYSQL_HOST'] -ne 'mysql') { $database = 'Existing' }
    # Existing credentials and namespace are always preserved by setup-helper.
    & (Join-Path $script:InstallRoot 'scripts/setup-helper.ps1') -Database $database -WebsiteOrigin $origin | Out-Null
    $configuration = Get-HelperConfiguration
    $namespace = $configuration['QUERYLAB_WORKSPACE_NAMESPACE']
    if ($namespace -notmatch '^[0-9a-f]{12}$') { throw 'The local installation namespace is invalid. Restore your original .env.helper; do not delete it or change its database credentials.' }
    if ($configuration['QUERYLAB_PAIRING_TOKEN'].Length -lt 24) { throw 'The pairing code is missing or invalid in .env.helper. Restore your original local configuration.' }
    if (-not $Port) { $Port = [int]$configuration['QUERYLAB_HELPER_PORT'] }
    if ($Port -lt 1024 -or $Port -gt 65535) { throw 'The helper port in .env.helper must be between 1024 and 65535.' }
    $project = 'querylab-installed-' + $namespace
    Assert-HelperPortOwner $Port $project
    $lines = @(Get-Content -LiteralPath (Join-Path $script:InstallRoot '.env.helper') -Encoding utf8)
    $lines = @($lines | ForEach-Object { if ($_ -match '^QUERYLAB_HELPER_PORT=') { "QUERYLAB_HELPER_PORT=$Port" } else { $_ } })
    [System.IO.File]::WriteAllLines((Join-Path $script:InstallRoot '.env.helper'), [string[]]$lines, (New-Object System.Text.UTF8Encoding($false)))
    Set-LauncherStatus 'working' 'Starting your private practice database and helper. The first launch downloads Docker images and may take several minutes. Keep Docker Desktop open.'
    $composeArguments = @('compose', '--env-file', (Join-Path $script:InstallRoot '.env.helper'), '-f', (Join-Path $script:InstallRoot 'compose.helper.yaml'), '--project-name', $project)
    if ($database -eq 'Bundled') { $composeArguments += @('--profile', 'bundled') }
    $composeArguments += @('up', '-d', '--build', '--wait', '--wait-timeout', '240')
    $result = Invoke-LauncherDocker $composeArguments
    if ($result.ExitCode -ne 0) {
        # Never echo Docker output: failure output can include local configuration.
        throw 'The helper could not start. Check Docker Desktop has internet access, enough disk space and at least 4 GB of memory. Check its Containers page for this installation, then choose Start helper to retry. If you configured an existing MySQL server, check its connection settings in .env.helper. Your saved configuration has been kept.'
    }
    $helperUrl = "http://127.0.0.1:$Port"
    Assert-HelperPortOwner $Port $project
    Set-LauncherStatus 'working' 'Checking MySQL is ready for challenges...'
    $ready = $false
    $deadline = [DateTime]::UtcNow.AddSeconds(90)
    while ([DateTime]::UtcNow -lt $deadline) {
        try {
            $status = Invoke-RestMethod -Uri ($helperUrl + '/api/helper/status') -TimeoutSec 8
            if ($status.mode -eq 'helper' -and $status.protocol_version -eq 1 -and $status.database.connected -eq $true) { $ready = $true; break }
        } catch { $lastError = $_.Exception.Message }
        Start-Sleep -Seconds 2
    }
    if (-not $ready) { throw "The helper started but MySQL is not ready. Open $helperUrl/api/helper/status for details, check Docker Desktop, then choose Start helper to retry. Your pairing code remains private until MySQL is ready." }
    Set-LauncherStatus 'ready' 'Ready. Return to QueryLab, keep the Helper URL shown below, paste your pairing code and choose Pair helper.' $helperUrl
    return @{ HelperUrl = $helperUrl; ProjectName = $project }
}

function Show-HelperLauncher {
    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing
    [System.Windows.Forms.Application]::EnableVisualStyles()
    $form = New-Object System.Windows.Forms.Form
    $form.Text = 'QueryLab Helper - Windows preview 0.4.1'
    $form.ClientSize = New-Object System.Drawing.Size(660, 620)
    $form.MinimumSize = New-Object System.Drawing.Size(676, 659)
    $form.StartPosition = 'CenterScreen'
    $form.Font = New-Object System.Drawing.Font('Segoe UI', 10)
    $title = New-Object System.Windows.Forms.Label
    $title.Text = 'Connect your private SQL workspace'
    $title.Font = New-Object System.Drawing.Font('Segoe UI', 17, [System.Drawing.FontStyle]::Bold)
    $title.SetBounds(24, 20, 610, 40)
    $intro = New-Object System.Windows.Forms.Label
    $intro.Text = "1. Open Docker Desktop and wait for Engine running.`r`n2. On QueryLab choose Copy website address, then paste it below.`r`n3. Choose Start helper. First launch downloads images; allow several minutes."
    $intro.SetBounds(24, 68, 610, 82)
    $siteLabel = New-Object System.Windows.Forms.Label
    $siteLabel.Text = 'QueryLab website address (only trust a site you recognise)'
    $siteLabel.SetBounds(24, 156, 610, 26)
    $site = New-Object System.Windows.Forms.TextBox
    $site.SetBounds(24, 184, 610, 30)
    $site.Text = $WebsiteOrigin
    if (-not $site.Text) {
        $saved = Get-HelperConfiguration
        if ($saved['QUERYLAB_HELPER_ALLOWED_ORIGINS']) { $site.Text = @($saved['QUERYLAB_HELPER_ALLOWED_ORIGINS'].Split(','))[-1] }
    }
    $start = New-Object System.Windows.Forms.Button
    $start.Text = 'Start helper'
    $start.SetBounds(24, 226, 160, 36)
    $dockerLink = New-Object System.Windows.Forms.LinkLabel
    $dockerLink.Text = 'Install Docker Desktop'
    $dockerLink.SetBounds(204, 234, 320, 30)
    $dockerLink.Add_LinkClicked({ Start-Process $script:DockerHelp })
    $message = New-Object System.Windows.Forms.Label
    $message.Text = 'Your SQL database stays on this computer. Docker Desktop is the only prerequisite; no Git, Node or Python installation is needed.'
    $message.SetBounds(24, 280, 610, 110)
    $urlLabel = New-Object System.Windows.Forms.Label
    $urlLabel.Text = 'Helper URL - keep this address in QueryLab'
    $urlLabel.SetBounds(24, 394, 610, 25)
    $url = New-Object System.Windows.Forms.TextBox
    $url.ReadOnly = $true
    $url.SetBounds(24, 422, 610, 29)
    $codeLabel = New-Object System.Windows.Forms.Label
    $codeLabel.Text = 'Pairing code - paste into QueryLab, then choose Pair helper'
    $codeLabel.SetBounds(24, 463, 610, 25)
    $code = New-Object System.Windows.Forms.TextBox
    $code.ReadOnly = $true
    $code.UseSystemPasswordChar = $true
    $code.SetBounds(24, 492, 438, 30)
    $copy = New-Object System.Windows.Forms.Button
    $copy.Text = 'Copy pairing code'
    $copy.Enabled = $false
    $copy.SetBounds(474, 490, 160, 34)
    $copy.Add_Click({
        try { [System.Windows.Forms.Clipboard]::SetText($code.Text); $message.Text = 'Code copied. Return to QueryLab, paste it into Pairing code and choose Pair helper.' }
        catch { $message.Text = 'Clipboard is busy. Try Copy code again.' }
    })
    $footer = New-Object System.Windows.Forms.Label
    $footer.Text = "Closing this window keeps the helper running. Reopen this launcher and choose Start helper to reconnect. To stop it, stop this installation in Docker Desktop. Keep your pairing code and .env.helper private."
    $footer.SetBounds(24, 542, 610, 70)
    $form.Controls.AddRange(@($title, $intro, $siteLabel, $site, $start, $dockerLink, $message, $urlLabel, $url, $codeLabel, $code, $copy, $footer))
    $state = @{ Process = $null; StatusFile = ''; LastState = ''; LastMessage = '' }
    $timer = New-Object System.Windows.Forms.Timer
    $timer.Interval = 500
    $start.Add_Click({
        $copy.Enabled = $false
        $code.Text = ''
        $url.Text = ''
        try {
            $origin = Get-WebsiteOrigin $site.Text
            $cache = Join-Path $script:InstallRoot '.querylab'
            New-Item -ItemType Directory -Path $cache -Force | Out-Null
            $state.StatusFile = Join-Path $cache ('launcher-' + [Guid]::NewGuid().ToString('N') + '.json')
            # Validated origins cannot contain quotes; Windows paths cannot contain them either.
            $launcherPath = Join-Path $script:InstallRoot 'scripts/launch-helper.ps1'
            $arguments = '-NoProfile -ExecutionPolicy Bypass -File "' + $launcherPath + '" -Headless -Quiet -WebsiteOrigin "' + $origin + '" -StatusPath "' + $state.StatusFile + '"'
            if ($HelperPort) { $arguments += ' -HelperPort ' + $HelperPort }
            $state.Process = Start-Process -FilePath 'powershell.exe' -ArgumentList $arguments -WindowStyle Hidden -PassThru
            $message.Text = 'Checking Docker Desktop...'
            $start.Enabled = $false
            $site.Enabled = $false
            $timer.Start()
        } catch { $message.Text = $_.Exception.Message }
    })
    $timer.Add_Tick({
        try {
            if (Test-Path -LiteralPath $state.StatusFile) {
                $progress = Get-Content -LiteralPath $state.StatusFile -Raw | ConvertFrom-Json
                $message.Text = $progress.message
                if ($progress.state -eq 'ready') {
                    $config = Get-HelperConfiguration
                    $url.Text = $progress.helperUrl
                    $code.Text = $config['QUERYLAB_PAIRING_TOKEN']
                    $copy.Enabled = $true
                }
            }
            if ($state.Process.HasExited) {
                if ($state.Process.ExitCode -ne 0) {
                    $copy.Enabled = $false
                    $code.Text = ''
                    if (-not (Test-Path -LiteralPath $state.StatusFile) -or $progress.state -ne 'error') { $message.Text = 'The launcher could not start. Extract the complete ZIP into a writable folder, check Docker Desktop is running, then choose Start helper to retry.' }
                }
                $start.Enabled = $true
                $site.Enabled = $true
                $timer.Stop()
                if (Test-Path -LiteralPath $state.StatusFile) { Remove-Item -LiteralPath $state.StatusFile -Force }
            }
        } catch { $message.Text = 'Waiting for helper startup...'; }
    })
    $form.Add_FormClosed({ $timer.Stop(); $timer.Dispose() })
    if ($ValidateUI) {
        $form.CreateControl()
        if ($PreviewPath) {
            # This form has never started a helper or read a pairing code.
            foreach ($control in $form.Controls) { $null = $control.Handle }
            $bitmap = New-Object System.Drawing.Bitmap($form.Width, $form.Height)
            try {
                $form.DrawToBitmap($bitmap, (New-Object System.Drawing.Rectangle(0, 0, $form.Width, $form.Height)))
                # A never-shown parent hides native child windows; render each
                # child explicitly so validation does not flash a desktop window.
                $border = [int](($form.Width - $form.ClientSize.Width) / 2)
                $caption = $form.Height - $form.ClientSize.Height - $border
                foreach ($control in $form.Controls) {
                    $rectangle = New-Object System.Drawing.Rectangle(($control.Left + $border), ($control.Top + $caption), $control.Width, $control.Height)
                    $control.DrawToBitmap($bitmap, $rectangle)
                }
                $bitmap.Save([System.IO.Path]::GetFullPath($PreviewPath), [System.Drawing.Imaging.ImageFormat]::Png)
            } finally { $bitmap.Dispose() }
        }
        $form.Dispose()
        $timer.Dispose()
        Write-Output 'Launcher UI constructed successfully.'
        return
    }
    [void]$form.ShowDialog()
    $form.Dispose()
}

if ($LibraryOnly) { return }
$script:WorkerStatusPath = $StatusPath
if ($Headless) {
    try {
        $result = Start-LocalHelper $WebsiteOrigin $HelperPort
        if (-not $Quiet) { Write-Output ('Helper ready at ' + $result.HelperUrl + '. Use the launcher Copy code button or scripts/show-helper-code.ps1 to pair.') }
        exit 0
    } catch {
        Set-LauncherStatus 'error' $_.Exception.Message
        if (-not $Quiet) { Write-Error $_.Exception.Message }
        exit 1
    }
}
try { Show-HelperLauncher }
catch {
    try { Add-Type -AssemblyName System.Windows.Forms; [void][System.Windows.Forms.MessageBox]::Show($_.Exception.Message, 'QueryLab Helper could not open') } catch {}
    exit 1
}

