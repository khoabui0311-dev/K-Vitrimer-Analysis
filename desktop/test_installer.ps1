param([string]$Installer = '')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
if (-not $Installer) { $Installer = Join-Path $projectRoot 'dist\K_Vitrimer_Analysis_Setup_1.0.0_x64.exe' }
$registryPath = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\{FE35CE06-96C6-4B7F-A692-6785A084BAF0}_is1'
if (Test-Path -LiteralPath $registryPath) { throw 'An installed copy already exists. Run this integration test on a clean account.' }
$testDir = [IO.Path]::GetFullPath((Join-Path $projectRoot 'dist\installer-test'))
$allowedRoot = [IO.Path]::GetFullPath((Join-Path $projectRoot 'dist')) + [IO.Path]::DirectorySeparatorChar
if (-not $testDir.StartsWith($allowedRoot, [StringComparison]::OrdinalIgnoreCase)) { throw 'Invalid test directory.' }
if (Test-Path -LiteralPath $testDir) { throw 'The installer test directory already exists; inspect it before testing again.' }
$report = Join-Path $projectRoot 'dist\installed-self-test.json'
$uninstaller = Join-Path $testDir 'unins000.exe'
$previousPath = $env:PATH
$previousPythonPath = $env:PYTHONPATH
try {
    $process = Start-Process -FilePath $Installer -ArgumentList @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/SP-', '/NOICONS', '/TASKS=""', ('/DIR="' + $testDir + '"')) -WindowStyle Hidden -Wait -PassThru
    if ($process.ExitCode -ne 0) { throw "Installation failed: $($process.ExitCode)" }
    $registered = Get-ItemProperty -LiteralPath $registryPath
    if ([IO.Path]::GetFullPath($registered.InstallLocation).TrimEnd('\') -ne $testDir) { throw 'Installer registration points to an unexpected folder.' }
    $env:PATH = "$env:SystemRoot\System32;$env:SystemRoot"
    $env:PYTHONPATH = ''
    $installedExe = Join-Path $testDir 'K_Vitrimer_Analysis.exe'
    $check = Start-Process -FilePath $installedExe -ArgumentList @('--self-test', ('"' + $report + '"')) -WorkingDirectory $env:TEMP -WindowStyle Hidden -Wait -PassThru
    if ($check.ExitCode -ne 0) { throw "Installed application test failed; inspect $report." }
    $result = Get-Content -LiteralPath $report -Raw | ConvertFrom-Json
    if (-not $result.ok -or -not $result.frozen) { throw 'Installed application did not pass its bundled test.' }
} finally {
    $env:PATH = $previousPath
    $env:PYTHONPATH = $previousPythonPath
    if (Test-Path -LiteralPath $uninstaller) {
        $uninstall = Start-Process -FilePath $uninstaller -ArgumentList @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART') -WindowStyle Hidden -Wait -PassThru
        if ($uninstall.ExitCode -ne 0) { throw "Test uninstallation failed: $($uninstall.ExitCode)" }
    }
}
if (Test-Path -LiteralPath (Join-Path $testDir 'K_Vitrimer_Analysis.exe')) { throw 'Uninstaller left the application executable behind.' }
if (Test-Path -LiteralPath $registryPath) { throw 'Uninstaller left its registration behind.' }
Write-Output 'Installation, installed application verification, and uninstallation passed.'
