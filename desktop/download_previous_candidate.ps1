$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$target = Join-Path $root 'dist\VitriFit_Setup_2.0.0-rc.1_x64.exe'
$uri = 'https://github.com/khoabui0311-dev/K-Vitrimer-Analysis/releases/download/v2.0.0-rc.1/VitriFit_Setup_2.0.0-rc.1_x64.exe'
Invoke-WebRequest -Uri $uri -OutFile $target
$expected = 'bdba63c777d7e7e3a16f6f456c5e0a00237270e57de0738961858fc3d40614ed'
if ((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected) {
    throw 'Previous published installer checksum mismatch.'
}
