param(
    [string]$Python = '',
    [string]$InnoCompiler = '',
    [switch]$SkipInstaller
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $projectRoot
try {
    if (-not $Python) { $Python = Join-Path $projectRoot '.venv\Scripts\python.exe' }
    if (-not (Test-Path -LiteralPath $Python)) { throw 'Create a Python 3.11+ virtual environment and install requirements-build.txt first.' }
    # OneDrive can mark generated folders read-only, preventing PyInstaller's
    # replacement of a previous build. Clear that attribute only inside our bundle.
    $bundleRoot = [IO.Path]::GetFullPath((Join-Path $projectRoot 'dist\K_Vitrimer_Analysis'))
    if (Test-Path -LiteralPath $bundleRoot) {
        $directories = @(Get-ChildItem -LiteralPath $bundleRoot -Directory -Recurse -Force) + @(Get-Item -LiteralPath $bundleRoot -Force)
        foreach ($directory in $directories) {
            if ($directory.LinkType -or ($directory.FullName -ne $bundleRoot -and -not $directory.FullName.StartsWith(($bundleRoot + '\'), [StringComparison]::OrdinalIgnoreCase))) { throw 'Unexpected link or path in generated bundle.' }
            if ($directory.Attributes -band [IO.FileAttributes]::ReadOnly) {
                $directory.Attributes = $directory.Attributes -band (-bnot [IO.FileAttributes]::ReadOnly)
            }
        }
    }
    & $Python -m PyInstaller --noconfirm desktop/K_Vitrimer_Analysis.spec
    if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed.' }
    $executable = Join-Path $projectRoot 'dist\K_Vitrimer_Analysis\K_Vitrimer_Analysis.exe'
    $report = Join-Path $projectRoot 'dist\desktop-self-test.json'
    if (Test-Path -LiteralPath $report) { Remove-Item -LiteralPath $report }
    # Verify without development tools on PATH or an inherited Python path.
    $previousPath = $env:PATH
    $previousPythonPath = $env:PYTHONPATH
    try {
        $env:PATH = "$env:SystemRoot\System32;$env:SystemRoot"
        $env:PYTHONPATH = ''
        $check = Start-Process -FilePath $executable -ArgumentList @('--self-test', ('"' + $report + '"')) -WindowStyle Hidden -Wait -PassThru
    } finally {
        $env:PATH = $previousPath
        $env:PYTHONPATH = $previousPythonPath
    }
    if ($check.ExitCode -ne 0 -or -not (Test-Path -LiteralPath $report)) { throw "Bundle test failed; inspect $report and the server log." }
    $result = Get-Content -LiteralPath $report -Raw | ConvertFrom-Json
    if (-not $result.ok) { throw "Bundle test failed: $($result.error)" }
    if (-not $SkipInstaller) {
        if (-not $InnoCompiler) {
            $candidates = @(
                (Join-Path $projectRoot '.build-tools\InnoSetup\ISCC.exe'),
                "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
                "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
            )
            $InnoCompiler = $candidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
        }
        if (-not $InnoCompiler) { throw 'Install Inno Setup 6 or pass -InnoCompiler with the path to ISCC.exe.' }
        & $InnoCompiler desktop/installer.iss
        if ($LASTEXITCODE -ne 0) { throw 'Installer compilation failed.' }
        Get-ChildItem -LiteralPath (Join-Path $projectRoot 'dist') -Filter 'K_Vitrimer_Analysis_Setup_*.exe' | ForEach-Object {
            $hash = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
            [IO.File]::WriteAllText(($_.FullName + '.sha256'), ($hash + '  ' + $_.Name + "`n"))
        }
    }
    Write-Output 'Desktop build and bundled application verification completed.'
} finally {
    Pop-Location
}
