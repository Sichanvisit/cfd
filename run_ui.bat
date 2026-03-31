@echo off
setlocal enabledelayedexpansion

REM =========================================================
REM CFD UI runner (Next.js dev)
REM Requirements:
REM   - Node 20.x (recommended 20.11.1 per .nvmrc)
REM   - npm installed
REM =========================================================

set "ROOT=%~dp0"
set "UI_DIR=%ROOT%frontend\next-dashboard"
set "UI_LOG=%ROOT%logs\ui_dev.log"
set "UI_ERR=%ROOT%data\logs\ui_dev_check_err.log"

if not exist "%ROOT%logs" mkdir "%ROOT%logs" >nul 2>&1
if not exist "%ROOT%data\logs" mkdir "%ROOT%data\logs" >nul 2>&1

echo [INFO] UI_DIR: %UI_DIR%
echo [INFO] UI_LOG: %UI_LOG%

REM ---- Node existence check
where node >nul 2>&1
if errorlevel 1 (
  echo [ERROR] node not found in PATH.
  echo [HINT] Install or use Node 20.11.1. See frontend\next-dashboard\.nvmrc
  echo [HINT] If using nvm-windows:
  echo [HINT]   nvm install 20.11.1
  echo [HINT]   nvm use 20.11.1
  pause
  exit /b 1
)

for /f "delims=" %%v in ('node -v 2^>nul') do set "NODE_VER=%%v"
set "NODE_MAJOR=%NODE_VER:~1,2%"
REM Handle single-digit majors just in case
if "%NODE_MAJOR:~1,1%"=="" set "NODE_MAJOR=%NODE_VER:~1,1%"

echo [INFO] Detected Node: %NODE_VER%

if not "%NODE_MAJOR%"=="20" (
  echo [ERROR] Unsupported Node version: %NODE_VER%
  echo [ERROR] This project requires Node 20.x to avoid Next.js worker spawn EPERM on Windows.
  echo [HINT] Run:
  echo [HINT]   nvm use 20.11.1
  echo [HINT] Then do a clean reinstall:
  echo [HINT]   cd frontend\next-dashboard
  echo [HINT]   rmdir /s /q node_modules ^& del /q package-lock.json ^& rmdir /s /q .next
  echo [HINT]   npm i
  pause
  exit /b 1
)

REM ---- Move to UI dir
if not exist "%UI_DIR%\package.json" (
  echo [ERROR] package.json not found: %UI_DIR%\package.json
  pause
  exit /b 1
)

pushd "%UI_DIR%"

REM ---- Basic sanity: show versions
where npm >nul 2>&1
if errorlevel 1 (
  echo [ERROR] npm not found in PATH.
  popd
  pause
  exit /b 1
)

for /f "delims=" %%n in ('npm -v 2^>nul') do set "NPM_VER=%%n"
echo [INFO] Detected npm: %NPM_VER%

REM ---- Start dev server and log output
echo [INFO] Starting Next dev server on port 3010...
echo [INFO] Command: npm run dev
echo [INFO] (Logs will be appended to %UI_LOG%)

REM Reset error log
echo. > "%UI_ERR%"

call npm.cmd run dev >> "%UI_LOG%" 2>&1
set "RC=%ERRORLEVEL%"

REM ---- If failed, print actionable hints
if not "%RC%"=="0" (
  echo [ERROR] UI failed to start. ExitCode=%RC%
  echo [INFO] Last 60 lines of log: %UI_LOG%
  powershell -NoProfile -Command "Get-Content '%UI_LOG%' -Tail 60" > "%UI_ERR%" 2>&1
  type "%UI_ERR%"

  findstr /I /C:"spawn EPERM" "%UI_LOG%" >nul 2>&1
  if "%ERRORLEVEL%"=="0" (
    echo [HINT] spawn EPERM detected: likely Windows Defender Controlled Folder Access / EDR blocks child process.
    echo [HINT] Try moving repo to a non-protected path, e.g. C:\dev\cfd
    echo [HINT] Or add node.exe/npm.exe to Defender allowed apps.
  )

  findstr /I /C:"EADDRINUSE" "%UI_LOG%" >nul 2>&1
  if "%ERRORLEVEL%"=="0" (
    echo [HINT] Port 3010 is in use. Stop the process using 3010 or change port.
    echo [HINT] Find PID:
    echo [HINT]   netstat -ano ^| findstr :3010
  )

  popd
  pause
  exit /b %RC%
)

popd
echo [OK] UI dev server started (check http://localhost:3010)
exit /b 0
