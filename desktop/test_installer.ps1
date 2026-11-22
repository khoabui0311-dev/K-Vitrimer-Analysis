param([string]$Installer = '', [string]$PreviousInstaller = '', [string]$TestName = 'installer-test')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $projectRoot
try {
    $releaseVersion = & .\.venv\Scripts\python.exe -c "from can_relax.version import VERSION; print(VERSION)"
    if ($LASTEXITCODE -ne 0 -or $releaseVersion -notmatch '^\d+\.\d+\.\d+(-[a-z0-9.]+)?$') { throw 'Invalid release version.' }
} finally { Pop-Location }
if (-not $Installer) { $Installer = Join-Path $projectRoot "dist\VitriFit_Setup_${releaseVersion}_x64.exe" }
$registryPath = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\{FE35CE06-96C6-4B7F-A692-6785A084BAF0}_is1'
if (Test-Path -LiteralPath $registryPath) { throw 'An installed copy already exists. Run this integration test on a clean account.' }
if ($TestName -notmatch '^[a-zA-Z0-9-]+$') { throw 'Invalid test name.' }
$testDir = [IO.Path]::GetFullPath((Join-Path $projectRoot ('dist\' + $TestName)))
$allowedRoot = [IO.Path]::GetFullPath((Join-Path $projectRoot 'dist')) + [IO.Path]::DirectorySeparatorChar
if (-not $testDir.StartsWith($allowedRoot, [StringComparison]::OrdinalIgnoreCase)) { throw 'Invalid test directory.' }
if (Test-Path -LiteralPath $testDir) { throw 'The installer test directory already exists; inspect it before testing again.' }
$report = Join-Path $projectRoot ('dist\' + $(if ($PreviousInstaller) { $TestName + '-self-test.json' } else { 'installed-self-test.json' }))
$uninstaller = Join-Path $testDir 'unins000.exe'
$previousPath = $env:PATH
$previousPythonPath = $env:PYTHONPATH
$preserved = @{}
try {
    if ($PreviousInstaller) {
        $old = Start-Process -FilePath $PreviousInstaller -ArgumentList @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/SP-', '/NOICONS', '/TASKS=""', ('/DIR="' + $testDir + '"')) -WindowStyle Hidden -Wait -PassThru
        if ($old.ExitCode -ne 0) { throw 'Previous installer failed.' }
        $oldRegistration = Get-ItemProperty -LiteralPath $registryPath
        $previousVersion = $oldRegistration.DisplayVersion
        if ([IO.Path]::GetFullPath($oldRegistration.InstallLocation).TrimEnd('\') -ne $testDir) { throw 'Old installation is outside the test directory.' }
        # Files made by a user must survive both upgrade and uninstall, including
        # files placed inside the installation folder (not supplied by Setup).
        foreach ($name in @('user-export.csv', 'user-project.vfit', 'user-format.vstyle')) {
            $path = Join-Path $testDir $name
            [IO.File]::WriteAllText($path, ('User file preservation sentinel: ' + $name))
            $preserved[$path] = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash
        }
    }
    $installArgs = @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/SP-', '/NOICONS', '/TASKS=""')
    # Omitting /DIR during upgrade verifies reuse of the registered location.
    if (-not $PreviousInstaller) { $installArgs += ('/DIR="' + $testDir + '"') }
    $process = Start-Process -FilePath $Installer -ArgumentList $installArgs -WindowStyle Hidden -Wait -PassThru
    if ($process.ExitCode -ne 0) { throw "Installation failed: $($process.ExitCode)" }
    $registered = Get-ItemProperty -LiteralPath $registryPath
    if ([IO.Path]::GetFullPath($registered.InstallLocation).TrimEnd('\') -ne $testDir) { throw 'Installer registration points to an unexpected folder.' }
    if ($registered.DisplayVersion -ne $releaseVersion) { throw 'Installed version registration did not update.' }
    if (Test-Path -LiteralPath (Join-Path $testDir 'K_Vitrimer_Analysis.exe')) { throw 'Upgrade left the obsolete launcher behind.' }
    foreach ($path in $preserved.Keys) {
        if ((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash -ne $preserved[$path]) { throw 'Upgrade altered a user file.' }
    }
    $env:PATH = "$env:SystemRoot\System32;$env:SystemRoot"
    $env:PYTHONPATH = ''
    $installedExe = Join-Path $testDir 'VitriFit.exe'
    $check = Start-Process -FilePath $installedExe -ArgumentList @('--self-test', ('"' + $report + '"')) -WorkingDirectory $env:TEMP -WindowStyle Hidden -Wait -PassThru
    if ($check.ExitCode -ne 0) { throw "Installed application test failed; inspect $report." }
    $result = Get-Content -LiteralPath $report -Raw | ConvertFrom-Json
    if (-not $result.ok -or -not $result.frozen -or $result.version -ne $releaseVersion -or $result.app_name -ne 'VitriFit') { throw 'Installed application identity or self-test failed.' }
} finally {
    $env:PATH = $previousPath
    $env:PYTHONPATH = $previousPythonPath
    if (Test-Path -LiteralPath $uninstaller) {
        $uninstall = Start-Process -FilePath $uninstaller -ArgumentList @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART') -WindowStyle Hidden -Wait -PassThru
        if ($uninstall.ExitCode -ne 0) { throw "Test uninstallation failed: $($uninstall.ExitCode)" }
    }
}
if (Test-Path -LiteralPath (Join-Path $testDir 'VitriFit.exe')) { throw 'Uninstaller left the application executable behind.' }
if (Test-Path -LiteralPath $registryPath) { throw 'Uninstaller left its registration behind.' }
foreach ($path in $preserved.Keys) {
    if ((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash -ne $preserved[$path]) { throw 'Uninstall altered a user file.' }
}
if ($PreviousInstaller) {
    @{
        ok = $true; previous_version = $previousVersion; version = $releaseVersion
        previous_installer_sha256 = (Get-FileHash -LiteralPath $PreviousInstaller -Algorithm SHA256).Hash.ToLowerInvariant()
        installer_sha256 = (Get-FileHash -LiteralPath $Installer -Algorithm SHA256).Hash.ToLowerInvariant()
        location_reused = $true; user_files_preserved_after_upgrade_and_uninstall = $preserved.Count
        installed_self_test = Split-Path -Leaf $report
    } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $projectRoot ('dist\' + $TestName + '.json')) -Encoding utf8
}
Write-Output 'Installation, installed application verification, and uninstallation passed.'
