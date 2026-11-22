@echo off
setlocal
pushd "%~dp0technik" || exit /b 1
set "tools=%CD%\.tools"
if not exist "%tools%\uv\uv.exe" if exist "..\.tools\uv\uv.exe" set "tools=%CD%\..\.tools"
set "PATH=%tools%\uv;%PATH%"
if exist "%tools%\uv\uv.exe" (
    set "UV_CACHE_DIR=%tools%\uv-cache"
    set "UV_PYTHON_INSTALL_DIR=%tools%\python"
)
where uv >nul 2>nul || (
    echo uv fehlt. Bitte uv wie in DOKU.md beschrieben installieren und erneut starten.
    pause
    exit /b 1
)
uv run --locked -m ausschreibungen.ui
if errorlevel 1 (
    echo Der Start ist fehlgeschlagen. Hinweise zur Einrichtung stehen in DOKU.md.
    pause
    exit /b 1
)
popd
