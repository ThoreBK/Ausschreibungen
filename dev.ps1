# In PowerShell laden: . .\dev.ps1
# Aktiviert die projektlokalen Tools nur fuer das aktuelle Terminal.
$env:PATH = "$PSScriptRoot\.tools\uv;$PSScriptRoot\.tools\node;$PSScriptRoot\node_modules\.bin;$env:PATH"
$env:UV_CACHE_DIR = Join-Path $PSScriptRoot '.tools\uv-cache'
$env:UV_PYTHON_INSTALL_DIR = Join-Path $PSScriptRoot '.tools\python'
$env:npm_config_cache = Join-Path $PSScriptRoot '.tools\npm-cache'
