# In PowerShell laden: . .\dev.ps1
# Aktiviert die projektlokalen Tools nur fuer das aktuelle Terminal.
$projectTools = Join-Path $PSScriptRoot '.tools'
if (!(Test-Path "$projectTools\uv\uv.exe") -and (Test-Path "$PSScriptRoot\..\.tools\uv\uv.exe")) {
    $projectTools = Join-Path $PSScriptRoot '..\.tools'
}
$env:PATH = "$projectTools\uv;$projectTools\node;$PSScriptRoot\node_modules\.bin;$env:PATH"
$env:UV_CACHE_DIR = Join-Path $projectTools 'uv-cache'
$env:UV_PYTHON_INSTALL_DIR = Join-Path $projectTools 'python'
$env:npm_config_cache = Join-Path $projectTools 'npm-cache'
