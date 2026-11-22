@echo off
setlocal
pushd "%~dp0" || exit /b 1
set "PATH=%CD%\.tools\uv;%PATH%"
if exist ".tools\uv\uv.exe" (
    set "UV_CACHE_DIR=%CD%\.tools\uv-cache"
    set "UV_PYTHON_INSTALL_DIR=%CD%\.tools\python"
)
where uv >nul 2>nul || (
    echo uv fehlt. Bitte uv wie in README.md beschrieben installieren und erneut starten.
    pause
    exit /b 1
)
uv run --locked -m ausschreibungen.ui
if errorlevel 1 (
    echo Der Start ist fehlgeschlagen. Hinweise zur Einrichtung stehen in README.md.
    pause
    exit /b 1
)
popd
