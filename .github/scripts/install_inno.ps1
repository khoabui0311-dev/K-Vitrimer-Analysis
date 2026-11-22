$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$toolsRoot = Join-Path $projectRoot '.build-tools'
$compilerRoot = Join-Path $toolsRoot 'InnoSetup'
$setup = Join-Path $toolsRoot 'innosetup-6.7.3.exe'
$expectedHash = '9C73C3BAE7ED48D44112A0F48E66742C00090BDB5BEF71D9D3C056C66E97B732'
New-Item -ItemType Directory -Path $toolsRoot -Force | Out-Null
Invoke-WebRequest -Uri 'https://github.com/jrsoftware/issrc/releases/download/is-6_7_3/innosetup-6.7.3.exe' -OutFile $setup
if ((Get-FileHash -LiteralPath $setup -Algorithm SHA256).Hash -ne $expectedHash) {
    throw 'The Inno Setup download does not match the reviewed installer.'
}
$signature = Get-AuthenticodeSignature -LiteralPath $setup
if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notlike 'CN=Pyrsys B.V.,*') {
    throw 'The Inno Setup publisher signature could not be verified.'
}
$arguments = @('/CURRENTUSER', '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/SP-', '/NOICONS', ('/DIR="' + $compilerRoot + '"'))
$installation = Start-Process -FilePath $setup -ArgumentList $arguments -WindowStyle Hidden -Wait -PassThru
if ($installation.ExitCode -ne 0 -or -not (Test-Path -LiteralPath (Join-Path $compilerRoot 'ISCC.exe'))) {
    throw 'Inno Setup installation failed.'
}
