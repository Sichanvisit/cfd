@echo off
setlocal enableextensions enabledelayedexpansion

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
set "UI_DIR=%ROOT%\frontend\next-dashboard"
set "UI_LOG=%ROOT%\logs\ui_dev.log"
set "UI_ERR=%ROOT%\data\logs\ui_dev_check_err.log"
set "PID8010="
set "PID3010="

set "TITLE_MAIN=CFD_MAIN_ENGINE"
set "TITLE_ML=CFD_ML_RETRAIN"
set "TITLE_API=CFD_FASTAPI_8010"
set "TITLE_UI=CFD_NEXT_UI"
set "TITLE_CANDIDATE_WATCH=CFD_STATE25_CANDIDATE_WATCH"
set "TITLE_CALIBRATION_WATCH=CFD_MANUAL_TRUTH_CALIBRATION_WATCH"
set "TITLE_ORCHESTRATOR_WATCH=CFD_CHECKPOINT_IMPROVEMENT_WATCH"
set "TITLE_STORAGE_RETENTION_WATCH=CFD_STORAGE_RETENTION_WATCH"
set "PYTHON_EXE=%LocalAppData%\Programs\Python\Python312\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=python"
set "API_CMD=%PYTHON_EXE% -m uvicorn backend.fastapi.app:app --host 127.0.0.1 --port 8010 --workers 1"
set "RUNTIME_STATUS_PATH=%ROOT%\data\runtime_status.json"
set "FLAT_CHECK_MAX_STATUS_AGE_SEC=180"
set "RUNTIME_FLAT_GUARD_SCRIPT=%ROOT%\scripts\runtime_flat_guard.py"
set "CANDIDATE_WATCH_LOG=%ROOT%\logs\state25_candidate_watch.log"
set "CALIBRATION_WATCH_LOG=%ROOT%\logs\manual_truth_calibration_watch.log"
set "ORCHESTRATOR_WATCH_LOG=%ROOT%\logs\checkpoint_improvement_orchestrator_watch.log"
set "STORAGE_RETENTION_WATCH_LOG=%ROOT%\logs\storage_retention_watch.log"
set "STORAGE_RETENTION_WATCH_INTERVAL_MIN=60"
set "STORAGE_RETENTION_CAP_GB=20"
set "STORAGE_RETENTION_CHECKPOINT_DETAIL_MIN_GB=2"

if /I "%~1"=="stop" goto :stop
if /I "%~1"=="restart" goto :restart
if /I "%~1"=="start_core" goto :start_core
if /I "%~1"=="restart_core" goto :restart_core
if /I "%~1"=="start_ui" goto :start_ui
if /I "%~1"=="status" goto :status
if /I "%~1"=="verify" goto :verify
if /I "%~1"=="smoke" goto :smoke
if /I "%~1"=="smoke_watch" goto :smoke_watch
if /I "%~1"=="candidate_watch" goto :candidate_watch
if /I "%~1"=="calibration_watch" goto :calibration_watch
if /I "%~1"=="orchestrator_watch" goto :orchestrator_watch
if /I "%~1"=="storage_retention" goto :storage_retention
if /I "%~1"=="storage_retention_watch" goto :storage_retention_watch
if /I "%~1"=="precheck" goto :precheck
if /I "%~1"=="deploy" goto :deploy
if /I "%~1"=="start" goto :start
if "%~1"=="" goto :start

echo Usage: manage_cfd.bat [start^|start_ui^|start_core [no_ui]^|candidate_watch^|calibration_watch^|orchestrator_watch^|storage_retention^|storage_retention_watch^|stop^|restart^|restart_core [no_ui] [force]^|status^|verify^|smoke^|smoke_watch^|precheck^|deploy]
exit /b 1

:start
echo [INFO] ROOT: %ROOT%
if not exist "%UI_DIR%" (
  echo [ERROR] UI directory not found: %UI_DIR%
  exit /b 1
)
if not exist "%ROOT%\logs" mkdir "%ROOT%\logs" >nul 2>&1
if not exist "%ROOT%\data\logs" mkdir "%ROOT%\data\logs" >nul 2>&1
set "RUN_TS="
for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "RUN_TS=%%I"
if not defined RUN_TS set "RUN_TS=%RANDOM%"
set "UI_LOG=%ROOT%\logs\ui_dev.%RUN_TS%.log"
echo ==== manage_cfd start %date% %time% ==== > "%UI_LOG%"
echo. > "%UI_ERR%"
echo [INFO] UI log: %UI_LOG%

echo [INFO] pre-clean existing CFD processes/ports...
call :kill_cfd_processes
for %%T in ("%TITLE_MAIN%" "%TITLE_ML%" "%TITLE_API%" "%TITLE_UI%" "%TITLE_CANDIDATE_WATCH%" "%TITLE_CALIBRATION_WATCH%" "%TITLE_ORCHESTRATOR_WATCH%" "%TITLE_STORAGE_RETENTION_WATCH%") do (
  taskkill /FI "WINDOWTITLE eq %%~T" /T /F >nul 2>&1
)
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":8010 .*LISTENING"') do (
  taskkill /PID %%P /T /F >nul 2>&1
)
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":3010 .*LISTENING"') do (
  taskkill /PID %%P /T /F >nul 2>&1
)
timeout /t 1 /nobreak >nul
call :wait_process_cleanup
call :run_storage_retention_preflight

start "%TITLE_MAIN%" /min /d "%ROOT%" "%PYTHON_EXE%" main.py 2>nul
call :start_api_if_needed
start "%TITLE_UI%" cmd /k ""%~f0" start_ui"

echo [OK] started clean: main/api/ui ^(legacy ML disabled^)
call :wait_api_boot
call :wait_core_boot
if errorlevel 1 (
  echo [WARN] core heartbeat missing. restarting main once...
  call :kill_cfd_processes
  timeout /t 1 /nobreak >nul
  call :wait_process_cleanup
  start "%TITLE_MAIN%" /min /d "%ROOT%" "%PYTHON_EXE%" main.py 2>nul
  call :start_api_if_needed
  call :wait_core_boot
)
call :ensure_single_cfd_workers
if errorlevel 1 (
  echo [WARN] duplicate CFD workers detected after boot. retrying clean start once...
  call :kill_cfd_processes
  timeout /t 1 /nobreak >nul
  call :wait_process_cleanup
  start "%TITLE_MAIN%" /min /d "%ROOT%" "%PYTHON_EXE%" main.py 2>nul
  call :start_api_if_needed
  call :wait_api_boot
  call :wait_core_boot
)
call :dedupe_main_workers
call :ensure_single_cfd_workers
call :wait_ui_boot
call :start_candidate_watch_if_needed
call :start_manual_truth_calibration_watch_if_needed
call :start_checkpoint_improvement_orchestrator_watch_if_needed
call :start_storage_retention_watch_if_needed
echo [INFO] bootstrap verify deferred. use: manage_cfd.bat verify
exit /b 0

:start_ui
set "UI_OPTIONAL=0"
if /I "%~2"=="optional" set "UI_OPTIONAL=1"

echo [INFO] checking API health (8010) before UI start...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ok=$false; try { $res=Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:8010/health' -TimeoutSec 3; if([int]$res.StatusCode -eq 200){$ok=$true} } catch {} ; if($ok){ exit 0 } else { exit 1 }" >nul 2>&1
if errorlevel 1 (
  echo [WARN] API health check failed. trying to start API automatically...
  call :start_api_if_needed
  call :wait_api_boot
)

if not exist "%UI_DIR%\package.json" (
  echo [WARN] UI skipped: package.json not found: %UI_DIR%\package.json
  goto :ui_exit_fail
)
cd /d "%UI_DIR%"

set "LOCAL_NODE20=%UI_DIR%\node_modules\node-win-x64\bin\node.exe"
set "UI_NODE=node"
if /I "%UI_FORCE_LOCAL_NODE20%"=="1" (
  if exist "%LOCAL_NODE20%" set "UI_NODE=%LOCAL_NODE20%"
)
if not defined UI_LOG set "UI_LOG=%ROOT%\logs\ui_dev.log"

set "NODE_VER="
set "NODE_MAJOR=0"
for /f %%v in ('"%UI_NODE%" -v 2^>nul') do set "NODE_VER=%%v"
if not defined NODE_VER (
  echo [WARN] UI skipped: Node runtime not found.
  goto :ui_exit_fail
)
set "NODE_MAJOR=%NODE_VER:v=%"
for /f "tokens=1 delims=." %%m in ("%NODE_MAJOR%") do set "NODE_MAJOR=%%m"
if not "%NODE_MAJOR%"=="20" if not "%NODE_MAJOR%"=="22" (
  echo [WARN] UI skipped: Unsupported Node version: %NODE_VER%
  echo [WARN] UI requires Node 20.x or 22.x.
  goto :ui_exit_fail
)
echo [INFO] UI Node runtime: %UI_NODE%

where npm.cmd >nul 2>&1
if errorlevel 1 (
  where npm >nul 2>&1
  if errorlevel 1 (
    echo [WARN] UI skipped: npm not found in PATH.
    goto :ui_exit_fail
  )
)
echo [INFO] starting Next.js dev server on 3010...
if "%UI_OPTIONAL%"=="1" (
  "%UI_NODE%" scripts\ensure-next-manifest.cjs >> "%UI_LOG%" 2>&1
) else (
  "%UI_NODE%" scripts\ensure-next-manifest.cjs
)
if errorlevel 1 (
  echo [WARN] UI skipped: predev failed.
  goto :ui_exit_fail
)
if "%UI_OPTIONAL%"=="1" (
  "%UI_NODE%" node_modules\next\dist\bin\next dev -p 3010 >> "%UI_LOG%" 2>&1
) else (
  "%UI_NODE%" node_modules\next\dist\bin\next dev -p 3010
)
if errorlevel 1 (
  echo [WARN] UI start failed. see spawn/permission policy ^(CFA/EDR^). log=%UI_LOG%
  findstr /I /C:"spawn EPERM" "%UI_LOG%" >nul 2>&1
  if "%ERRORLEVEL%"=="0" (
    echo [WARN] UI spawn EPERM detected. child-process blocked by Windows policy/EDR.
    echo [HINT] Allow node.exe in Defender CFA or run repo from non-protected path ^(e.g. C:\dev\cfd^).
  )
  goto :ui_exit_fail
)
exit /b 0

:ui_exit_fail
if "%UI_OPTIONAL%"=="1" (
  echo [WARN] UI optional mode: continue without UI. log=%UI_LOG%
  exit /b 0
)
pause
exit /b 1

:start_core
echo [INFO] ROOT: %ROOT%
set "CORE_WITH_UI=1"
if /I "%~2"=="no_ui" set "CORE_WITH_UI=0"
if "%CORE_WITH_UI%"=="1" (
  echo [INFO] CORE mode: main/api + UI ensure ^(legacy ML disabled^)
) else (
  echo [INFO] CORE-ONLY mode: main/api ^(UI skipped by no_ui, legacy ML disabled^)
)
echo [INFO] pre-clean existing CFD processes/ports...
call :kill_cfd_processes
for %%T in ("%TITLE_MAIN%" "%TITLE_ML%" "%TITLE_API%" "%TITLE_UI%" "%TITLE_CANDIDATE_WATCH%" "%TITLE_CALIBRATION_WATCH%" "%TITLE_ORCHESTRATOR_WATCH%" "%TITLE_STORAGE_RETENTION_WATCH%") do (
  taskkill /FI "WINDOWTITLE eq %%~T" /T /F >nul 2>&1
)
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":8010 .*LISTENING"') do (
  taskkill /PID %%P /T /F >nul 2>&1
)
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":3010 .*LISTENING"') do (
  taskkill /PID %%P /T /F >nul 2>&1
)
timeout /t 1 /nobreak >nul
call :wait_process_cleanup
call :run_storage_retention_preflight

start "%TITLE_MAIN%" /min /d "%ROOT%" "%PYTHON_EXE%" main.py 2>nul
call :start_api_if_needed

echo [OK] started core-only: main/api ^(legacy ML disabled^)
call :wait_api_boot
call :wait_core_boot
if errorlevel 1 (
  echo [WARN] core heartbeat missing. restarting main once...
  call :kill_cfd_processes
  timeout /t 1 /nobreak >nul
  call :wait_process_cleanup
  start "%TITLE_MAIN%" /min /d "%ROOT%" "%PYTHON_EXE%" main.py 2>nul
  call :start_api_if_needed
  call :wait_core_boot
)
call :ensure_single_cfd_workers
if errorlevel 1 (
  echo [WARN] duplicate CFD workers detected after core boot. retrying clean start once...
  call :kill_cfd_processes
  timeout /t 1 /nobreak >nul
  call :wait_process_cleanup
  start "%TITLE_MAIN%" /min /d "%ROOT%" "%PYTHON_EXE%" main.py 2>nul
  call :start_api_if_needed
  call :wait_api_boot
  call :wait_core_boot
)
call :dedupe_main_workers
call :ensure_single_cfd_workers
echo [INFO] core verify deferred. use: manage_cfd.bat verify
echo [INFO] manual guarded restart: manage_cfd.bat restart_core [no_ui]
if "%CORE_WITH_UI%"=="1" (
  call :ensure_ui_if_needed
)
call :start_candidate_watch_if_needed
call :start_manual_truth_calibration_watch_if_needed
call :start_checkpoint_improvement_orchestrator_watch_if_needed
call :start_storage_retention_watch_if_needed
exit /b 0

:stop
call :kill_cfd_processes
for %%T in ("%TITLE_MAIN%" "%TITLE_ML%" "%TITLE_API%" "%TITLE_UI%" "%TITLE_CANDIDATE_WATCH%" "%TITLE_CALIBRATION_WATCH%" "%TITLE_ORCHESTRATOR_WATCH%" "%TITLE_STORAGE_RETENTION_WATCH%") do (
  taskkill /FI "WINDOWTITLE eq %%~T" /T /F >nul 2>&1
)
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":8010 .*LISTENING"') do (
  taskkill /PID %%P /T /F >nul 2>&1
)
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":3010 .*LISTENING"') do (
  taskkill /PID %%P /T /F >nul 2>&1
)
echo [OK] stop requested
call :wait_process_cleanup
exit /b 0

:restart
call "%~f0" stop
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":8010 .*LISTENING"') do (
  echo [INFO] force-kill stale API PID %%P on 8010
  taskkill /PID %%P /T /F >nul 2>&1
)
timeout /t 2 /nobreak >nul
call "%~f0" start
call :post_restart_health
exit /b 0

:restart_core
set "RESTART_CORE_FORCE=0"
set "RESTART_CORE_ARG="
if /I "%~2"=="force" set "RESTART_CORE_FORCE=1"
if /I "%~2"=="no_ui" set "RESTART_CORE_ARG=no_ui"
if /I "%~3"=="force" set "RESTART_CORE_FORCE=1"
if /I "%~3"=="no_ui" set "RESTART_CORE_ARG=no_ui"
if "%RESTART_CORE_FORCE%"=="1" (
  echo [WARN] restart_core force requested. skipping flat-position guard.
) else (
  call :guard_flat_before_restart
  if errorlevel 1 exit /b 1
)
call "%~f0" stop
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":8010 .*LISTENING"') do (
  echo [INFO] force-kill stale API PID %%P on 8010
  taskkill /PID %%P /T /F >nul 2>&1
)
timeout /t 2 /nobreak >nul
call "%~f0" start_core %RESTART_CORE_ARG%
exit /b 0

:status
echo ==== PORTS ====
netstat -ano | findstr /R /C:":8010 .*LISTENING" 2>nul
netstat -ano | findstr /R /C:":3010 .*LISTENING" 2>nul
echo.
echo ==== PID BY PORT ====
set "PID8010="
set "PID3010="
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":8010 .*LISTENING"') do (
  if not "%%P"=="!PID8010!" (
    set "PID8010=%%P"
    echo [PORT 8010] PID %%P
    tasklist /FI "PID eq %%P" 2>nul
  )
)
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":3010 .*LISTENING"') do (
  if not "%%P"=="!PID3010!" (
    set "PID3010=%%P"
    echo [PORT 3010] PID %%P
    tasklist /FI "PID eq %%P" 2>nul
  )
)
echo.
echo ==== STATE25 CANDIDATE WATCH ====
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$watch=@(Get-CimInstance Win32_Process | Where-Object { ($_.Name -ieq 'python.exe') -and ($_.CommandLine -match 'state25_candidate_watch.py') });" ^
  "if($watch.Count -gt 0){ foreach($p in $watch){ Write-Host ('[WATCH][RUNNING] pid={0} cmd={1}' -f $p.ProcessId,$p.CommandLine) } } else { Write-Host '[WATCH][IDLE] state25 candidate watch not running' }"
echo.
echo ==== MANUAL TRUTH CALIBRATION WATCH ====
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$watch=@(Get-CimInstance Win32_Process | Where-Object { ($_.Name -ieq 'python.exe') -and ($_.CommandLine -match 'manual_truth_calibration_watch.py') });" ^
  "if($watch.Count -gt 0){ foreach($p in $watch){ Write-Host ('[CALIBRATION][RUNNING] pid={0} cmd={1}' -f $p.ProcessId,$p.CommandLine) } } else { Write-Host '[CALIBRATION][IDLE] manual truth calibration watch not running' }"
echo.
echo ==== CHECKPOINT IMPROVEMENT ORCHESTRATOR WATCH ====
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$watch=@(Get-CimInstance Win32_Process | Where-Object { ($_.Name -ieq 'python.exe') -and ($_.CommandLine -match 'checkpoint_improvement_orchestrator_watch.py') });" ^
  "if($watch.Count -gt 0){ foreach($p in $watch){ Write-Host ('[ORCHESTRATOR][RUNNING] pid={0} cmd={1}' -f $p.ProcessId,$p.CommandLine) } } else { Write-Host '[ORCHESTRATOR][IDLE] checkpoint improvement orchestrator watch not running' }"
echo.
echo ==== STORAGE RETENTION WATCH ====
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$watch=@(Get-CimInstance Win32_Process | Where-Object { ($_.Name -ieq 'python.exe') -and ($_.CommandLine -match 'storage_retention_watch.py') });" ^
  "if($watch.Count -gt 0){ foreach($p in $watch){ Write-Host ('[RETENTION][RUNNING] pid={0} cmd={1}' -f $p.ProcessId,$p.CommandLine) } } else { Write-Host '[RETENTION][IDLE] storage retention watch not running' }"
exit /b 0

:verify
echo [INFO] verifying API endpoints...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference='Stop';" ^
  "$base='http://127.0.0.1:8010';" ^
  "$maxWaitSec=45;" ^
  "$intervalSec=2;" ^
  "$started=Get-Date;" ^
  "$apiReady=$false;" ^
  "while(((Get-Date)-$started).TotalSeconds -lt $maxWaitSec){" ^
  "  try {" ^
  "    $null=Invoke-RestMethod -Uri ($base + '/health') -Method Get -TimeoutSec 3;" ^
  "    $apiReady=$true; break;" ^
  "  } catch {" ^
  "    Start-Sleep -Seconds $intervalSec;" ^
  "  }" ^
  "}" ^
  "if(-not $apiReady){" ^
  "  Write-Host ('[VERIFY][FAIL] API bootstrap timeout ({0}s): {1}' -f $maxWaitSec, ($base + '/health'));" ^
  "  return;" ^
  "}" ^
  "$endpoints=@('/health','/trades/summary','/trades/closed_recent?limit=5');" ^
  "foreach($ep in $endpoints){" ^
  "  $url=$base+$ep;" ^
  "  try {" ^
  "    $res=Invoke-RestMethod -Uri $url -Method Get -TimeoutSec 8;" ^
  "    if($ep -eq '/trades/summary'){" ^
  "      $closedCount=0; if($res.summary){ $closedCount=[int]$res.summary.closed_count };" ^
  "      Write-Host ('[VERIFY][OK] {0} closed_count={1}' -f $ep,$closedCount);" ^
  "    } elseif($ep -like '/trades/closed_recent*'){" ^
  "      $itemCount=0; if($res.items){ $itemCount=@($res.items).Count };" ^
  "      Write-Host ('[VERIFY][OK] {0} items={1}' -f $ep,$itemCount);" ^
  "    } else {" ^
  "      Write-Host ('[VERIFY][OK] {0}' -f $ep);" ^
  "    }" ^
  "  } catch {" ^
  "    Write-Host ('[VERIFY][FAIL] {0} {1}' -f $ep, $_.Exception.Message);" ^
  "  }" ^
  "}"
exit /b 0

:smoke
echo [INFO] running entry smoke guard...
cd /d "%ROOT%"
"%PYTHON_EXE%" scripts\entry_smoke_guard.py
set "SMOKE_EXIT=%ERRORLEVEL%"
if not "%SMOKE_EXIT%"=="0" (
  echo [WARN] smoke guard failed. inspect latest report in data\analysis\entry_smoke_guard_*.json
  exit /b %SMOKE_EXIT%
)
echo [OK] smoke guard passed
exit /b 0

:smoke_watch
echo [INFO] running entry smoke auto-recheck ^(15m interval, runtime freshness required^)...
cd /d "%ROOT%"
"%PYTHON_EXE%" scripts\entry_smoke_autorecheck.py --interval-min 15 --max-cycles 8 --require-runtime-fresh --runtime-max-age-sec 180
set "SMOKE_WATCH_EXIT=%ERRORLEVEL%"
if not "%SMOKE_WATCH_EXIT%"=="0" (
  echo [WARN] smoke auto-recheck failed. inspect latest report in data\analysis\entry_smoke_autorecheck_*.json
  exit /b %SMOKE_WATCH_EXIT%
)
echo [OK] smoke auto-recheck passed
exit /b 0

:candidate_watch
call :start_candidate_watch_if_needed
exit /b 0

:calibration_watch
call :start_manual_truth_calibration_watch_if_needed
exit /b 0

:orchestrator_watch
call :start_checkpoint_improvement_orchestrator_watch_if_needed
exit /b 0

:storage_retention
call :run_storage_retention_preflight
exit /b 0

:storage_retention_watch
call :start_storage_retention_watch_if_needed
exit /b 0

:wait_api_boot
echo [INFO] waiting for API bootstrap (/health)...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference='Stop';" ^
  "$base='http://127.0.0.1:8010';" ^
  "$maxWaitSec=45;" ^
  "$intervalSec=2;" ^
  "$started=Get-Date;" ^
  "$apiReady=$false;" ^
  "while(((Get-Date)-$started).TotalSeconds -lt $maxWaitSec){" ^
  "  try {" ^
  "    $null=Invoke-RestMethod -Uri ($base + '/health') -Method Get -TimeoutSec 3;" ^
  "    $apiReady=$true; break;" ^
  "  } catch {" ^
  "    Start-Sleep -Seconds $intervalSec;" ^
  "  }" ^
  "}" ^
  "if($apiReady){ Write-Host '[BOOT][OK] /health ready'; } else { Write-Host ('[BOOT][WARN] /health not ready within {0}s' -f $maxWaitSec); }"
exit /b 0

:wait_core_boot
echo [INFO] waiting for core heartbeat (main.py + runtime_status)...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference='SilentlyContinue';" ^
  "$root='%ROOT%';" ^
  "$mainScript='main\.py';" ^
  "$statusPath=Join-Path $root 'data\runtime_status.json';" ^
  "$maxWaitSec=90;" ^
  "$intervalSec=3;" ^
  "$maxStatusAgeSec=45;" ^
  "$started=Get-Date;" ^
  "$ok=$false;" ^
  "while(((Get-Date)-$started).TotalSeconds -lt $maxWaitSec){" ^
  "  $main = Get-CimInstance Win32_Process | Where-Object { ($_.Name -ieq 'python.exe') -and ($_.CommandLine -match $mainScript) -and ($_.CommandLine -notmatch 'uvicorn') };" ^
  "  $fresh=$false;" ^
  "  if(Test-Path $statusPath){" ^
  "    $age=((Get-Date)-(Get-Item $statusPath).LastWriteTime).TotalSeconds;" ^
  "    if($age -le $maxStatusAgeSec){ $fresh=$true }" ^
  "  }" ^
  "  if($main -and $fresh){ $ok=$true; break }" ^
  "  Start-Sleep -Seconds $intervalSec;" ^
  "}" ^
  "if($ok){ Write-Host '[BOOT][OK] core heartbeat ready'; exit 0 } else { Write-Host ('[BOOT][WARN] core heartbeat not ready within {0}s' -f $maxWaitSec); exit 1 }"
if errorlevel 1 exit /b 1
exit /b 0

:guard_flat_before_restart
echo [INFO] guarded restart check: verifying no open positions...
"%PYTHON_EXE%" "%RUNTIME_FLAT_GUARD_SCRIPT%" --runtime-status-path "%RUNTIME_STATUS_PATH%" --max-status-age-sec %FLAT_CHECK_MAX_STATUS_AGE_SEC%
if errorlevel 1 (
  echo [WARN] guarded restart aborted. use manage_cfd.bat restart_core force only if you have confirmed flat manually.
  exit /b 1
)
exit /b 0

:wait_process_cleanup
echo [INFO] waiting for stale CFD workers to exit...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference='SilentlyContinue';" ^
  "$root='%ROOT%';" ^
  "$mainScript='main\.py';" ^
  "$maxWaitSec=20;" ^
  "$started=Get-Date;" ^
  "$cleared=$false;" ^
  "while(((Get-Date)-$started).TotalSeconds -lt $maxWaitSec){" ^
  "  $workers=@(Get-CimInstance Win32_Process | Where-Object {" ^
  "    ($_.Name -ieq 'python.exe') -and (" ^
  "      ($_.CommandLine -match $mainScript -or $_.CommandLine -match 'ml[/\\\\]retrain_and_deploy.py' -or $_.CommandLine -match 'uvicorn backend.fastapi.app:app' -or $_.CommandLine -match 'state25_candidate_watch.py' -or $_.CommandLine -match 'manual_truth_calibration_watch.py' -or $_.CommandLine -match 'checkpoint_improvement_orchestrator_watch.py' -or $_.CommandLine -match 'storage_retention_watch.py') -or" ^
  "      ($_.CommandLine -match 'CFD_MAIN_ENGINE' -or $_.CommandLine -match 'CFD_ML_RETRAIN' -or $_.CommandLine -match 'CFD_FASTAPI_8010' -or $_.CommandLine -match 'CFD_STATE25_CANDIDATE_WATCH' -or $_.CommandLine -match 'CFD_MANUAL_TRUTH_CALIBRATION_WATCH' -or $_.CommandLine -match 'CFD_CHECKPOINT_IMPROVEMENT_WATCH' -or $_.CommandLine -match 'CFD_STORAGE_RETENTION_WATCH')" ^
  "    )" ^
  "  });" ^
  "  if($workers.Count -eq 0){ $cleared=$true; break }" ^
  "  Start-Sleep -Seconds 1;" ^
  "}" ^
  "if($cleared){ Write-Host '[BOOT][OK] stale workers cleared'; } else { Write-Host '[BOOT][WARN] stale workers still present after cleanup wait'; }"
exit /b 0

:ensure_single_cfd_workers
echo [INFO] verifying single CFD worker set...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference='SilentlyContinue';" ^
  "$root='%ROOT%';" ^
  "$mainScript='main\.py';" ^
  "$main=@(Get-CimInstance Win32_Process | Where-Object { ($_.Name -ieq 'python.exe') -and ($_.CommandLine -match $mainScript) -and ($_.CommandLine -notmatch 'uvicorn') });" ^
  "$ml=@(Get-CimInstance Win32_Process | Where-Object { ($_.Name -ieq 'python.exe') -and ($_.CommandLine -match 'ml[/\\\\]retrain_and_deploy.py') });" ^
  "$api=@(Get-CimInstance Win32_Process | Where-Object { ($_.Name -ieq 'python.exe') -and ($_.CommandLine -match 'uvicorn backend.fastapi.app:app') -and ($_.CommandLine -match '--port 8010') });" ^
  "$watch=@(Get-CimInstance Win32_Process | Where-Object { ($_.Name -ieq 'python.exe') -and ($_.CommandLine -match 'state25_candidate_watch.py') });" ^
  "$cal=@(Get-CimInstance Win32_Process | Where-Object { ($_.Name -ieq 'python.exe') -and ($_.CommandLine -match 'manual_truth_calibration_watch.py') });" ^
  "$orch=@(Get-CimInstance Win32_Process | Where-Object { ($_.Name -ieq 'python.exe') -and ($_.CommandLine -match 'checkpoint_improvement_orchestrator_watch.py') });" ^
  "$ret=@(Get-CimInstance Win32_Process | Where-Object { ($_.Name -ieq 'python.exe') -and ($_.CommandLine -match 'storage_retention_watch.py') });" ^
  "if($main.Count -le 1 -and $ml.Count -eq 0 -and $api.Count -le 1 -and $watch.Count -le 1 -and $cal.Count -le 1 -and $orch.Count -le 1 -and $ret.Count -le 1){ Write-Host '[BOOT][OK] single CFD worker set verified'; exit 0 } else { Write-Host ('[BOOT][WARN] duplicate/stale workers main={0} legacy_ml={1} api={2} candidate_watch={3} calibration_watch={4} orchestrator_watch={5} retention_watch={6}' -f $main.Count,$ml.Count,$api.Count,$watch.Count,$cal.Count,$orch.Count,$ret.Count); exit 1 }"
if errorlevel 1 exit /b 1
exit /b 0

:dedupe_main_workers
echo [INFO] de-duping duplicate main.py workers if needed...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference='SilentlyContinue';" ^
  "$root='%ROOT%';" ^
  "$mainScript='main\.py';" ^
  "$main=@(Get-CimInstance Win32_Process | Where-Object { ($_.Name -ieq 'python.exe') -and ($_.CommandLine -match $mainScript) -and ($_.CommandLine -notmatch 'uvicorn') } | Sort-Object CreationDate);" ^
  "if($main.Count -le 1){ Write-Host '[BOOT][OK] main worker already singular'; exit 0 }" ^
  "$keep=$main[-1];" ^
  "foreach($p in $main){ if([int]$p.ProcessId -ne [int]$keep.ProcessId){ try { Stop-Process -Id ([int]$p.ProcessId) -Force -ErrorAction Stop; Write-Host ('[BOOT][FIX] stopped duplicate main pid={0}' -f $p.ProcessId) } catch {} } }" ^
  "Start-Sleep -Seconds 2;" ^
  "$remaining=@(Get-CimInstance Win32_Process | Where-Object { ($_.Name -ieq 'python.exe') -and ($_.CommandLine -match $mainScript) -and ($_.CommandLine -notmatch 'uvicorn') });" ^
  "if($remaining.Count -le 1){ Write-Host ('[BOOT][OK] main dedupe complete keep_pid={0}' -f $keep.ProcessId); exit 0 } else { Write-Host ('[BOOT][WARN] main dedupe incomplete count={0}' -f $remaining.Count); exit 1 }"
exit /b 0

:wait_ui_boot
echo [INFO] waiting for UI bootstrap (http://127.0.0.1:3010)...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference='SilentlyContinue';" ^
  "$url='http://127.0.0.1:3010';" ^
  "$maxWaitSec=35;" ^
  "$intervalSec=2;" ^
  "$started=Get-Date;" ^
  "$uiReady=$false;" ^
  "while(((Get-Date)-$started).TotalSeconds -lt $maxWaitSec){" ^
  "  try {" ^
  "    $res=Invoke-WebRequest -UseBasicParsing -Uri $url -Method Get -TimeoutSec 4;" ^
  "    if([int]$res.StatusCode -eq 200){ $uiReady=$true; break }" ^
  "  } catch {}" ^
  "  Start-Sleep -Seconds $intervalSec;" ^
  "}" ^
  "if($uiReady){ Write-Host '[BOOT][OK] UI 3010 ready'; } else { Write-Host ('[BOOT][WARN] UI 3010 not ready within {0}s' -f $maxWaitSec); }"
if errorlevel 1 exit /b 0
netstat -ano | findstr /R /C:":3010 .*LISTENING" >nul 2>&1
if errorlevel 1 (
  findstr /I /C:"spawn EPERM" "%UI_LOG%" >nul 2>&1
  if "%ERRORLEVEL%"=="0" (
    echo [BOOT][DIAG] UI failed by spawn EPERM. See %UI_LOG%
  ) else (
    findstr /I /C:"EADDRINUSE" "%UI_LOG%" >nul 2>&1
    if "%ERRORLEVEL%"=="0" (
      echo [BOOT][DIAG] UI failed: port 3010 already in use. See %UI_LOG%
    ) else (
      echo [BOOT][DIAG] UI not listening. tail log:
      powershell -NoProfile -Command "Get-Content '%UI_LOG%' -Tail 40" > "%UI_ERR%" 2>&1
      type "%UI_ERR%"
    )
  )
)
exit /b 0

:ensure_ui_if_needed
echo [INFO] ensuring UI on 3010...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ok=$false; try { $res=Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:3010' -TimeoutSec 4; if([int]$res.StatusCode -eq 200){$ok=$true} } catch {} ; if($ok){ exit 0 } else { exit 1 }" >nul 2>&1
if not errorlevel 1 (
  echo [INFO] UI already healthy on 3010. skip start.
  exit /b 0
)

set "RUN_TS="
for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "RUN_TS=%%I"
if not defined RUN_TS set "RUN_TS=%RANDOM%"
set "UI_LOG=%ROOT%\logs\ui_dev.%RUN_TS%.log"
if not exist "%ROOT%\logs" mkdir "%ROOT%\logs" >nul 2>&1
if not exist "%ROOT%\data\logs" mkdir "%ROOT%\data\logs" >nul 2>&1
echo ==== manage_cfd ensure_ui %date% %time% ==== > "%UI_LOG%"
echo. > "%UI_ERR%"

for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":3010 .*LISTENING"') do (
  echo [WARN] stale UI listener detected on 3010 ^(PID %%P^). restarting UI...
  taskkill /PID %%P /T /F >nul 2>&1
)
timeout /t 1 /nobreak >nul
start "%TITLE_UI%" cmd /k ""%~f0" start_ui optional"
call :wait_ui_boot
exit /b 0

:post_restart_health
echo [INFO] restart health check...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference='Stop';" ^
  "$checks=@(@{name='api';url='http://127.0.0.1:8010/health';wait=45},@{name='ui';url='http://127.0.0.1:3010';wait=45});" ^
  "foreach($c in $checks){" ^
  "  $ok=$false; $started=Get-Date;" ^
  "  while(((Get-Date)-$started).TotalSeconds -lt [int]$c.wait){" ^
  "    try {" ^
  "      $res=Invoke-WebRequest -UseBasicParsing -Uri $c.url -Method Get -TimeoutSec 4;" ^
  "      if([int]$res.StatusCode -eq 200){ $ok=$true; break }" ^
  "    } catch {}" ^
  "    Start-Sleep -Seconds 2;" ^
  "  }" ^
  "  if($ok){ Write-Host ('[HEALTH][OK] {0} {1}' -f $c.name,$c.url) } else { Write-Host ('[HEALTH][FAIL] {0} {1}' -f $c.name,$c.url) }" ^
  "}"
exit /b 0

:start_api_if_needed
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$p=Get-CimInstance Win32_Process | Where-Object { ($_.Name -ieq 'python.exe') -and ($_.CommandLine -match 'uvicorn backend.fastapi.app:app') -and ($_.CommandLine -match '--port 8010') }; if($p){ exit 0 } else { exit 1 }" >nul 2>&1
if not errorlevel 1 (
  echo [INFO] API process already running for 8010. skip duplicate start.
  exit /b 0
)

set "API_PID="
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":8010 .*LISTENING"') do (
  set "API_PID=%%P"
)
if defined API_PID (
  powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$ok=$false; try { $res=Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:8010/health' -TimeoutSec 3; if([int]$res.StatusCode -eq 200){$ok=$true} } catch {} ; if($ok){ exit 0 } else { exit 1 }" >nul 2>&1
  if not errorlevel 1 (
    echo [INFO] API already listening on 8010 ^(PID %API_PID%^). skip duplicate start.
    exit /b 0
  )
  echo [WARN] stale API listener detected on 8010 ^(PID %API_PID%^). restarting...
  taskkill /PID %API_PID% /T /F >nul 2>&1
  timeout /t 1 /nobreak >nul
)
echo [INFO] starting API on 8010...
start "%TITLE_API%" /min /d "%ROOT%" "%PYTHON_EXE%" -m uvicorn backend.fastapi.app:app --host 127.0.0.1 --port 8010 --workers 1 2>nul
exit /b 0

:start_candidate_watch_if_needed
if not exist "%ROOT%\logs" mkdir "%ROOT%\logs" >nul 2>&1
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$watch=@(Get-CimInstance Win32_Process | Where-Object { ($_.Name -ieq 'python.exe') -and ($_.CommandLine -match 'state25_candidate_watch.py') }); if($watch.Count -gt 0){ exit 0 } else { exit 1 }" >nul 2>&1
if not errorlevel 1 (
  echo [INFO] state25 candidate watch already running. skip duplicate start.
  exit /b 0
)
echo [INFO] starting state25 candidate watch ^(15m offline retrain/gate/integration loop^)...
echo ==== manage_cfd candidate_watch %date% %time% ====>> "%CANDIDATE_WATCH_LOG%"
start "%TITLE_CANDIDATE_WATCH%" /min /d "%ROOT%" "%PYTHON_EXE%" scripts\state25_candidate_watch.py --interval-min 15 --max-cycles 0 --require-runtime-fresh --runtime-max-age-sec 180 2>nul
exit /b 0

:start_manual_truth_calibration_watch_if_needed
if not exist "%ROOT%\logs" mkdir "%ROOT%\logs" >nul 2>&1
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$watch=@(Get-CimInstance Win32_Process | Where-Object { ($_.Name -ieq 'python.exe') -and ($_.CommandLine -match 'manual_truth_calibration_watch.py') }); if($watch.Count -gt 0){ exit 0 } else { exit 1 }" >nul 2>&1
if not errorlevel 1 (
  echo [INFO] manual truth calibration watch already running. skip duplicate start.
  exit /b 0
)
echo [INFO] starting manual truth calibration watch ^(15m comparison/bias/current-rich refresh loop^)...
echo ==== manage_cfd manual_truth_calibration_watch %date% %time% ====>> "%CALIBRATION_WATCH_LOG%"
start "%TITLE_CALIBRATION_WATCH%" /min /d "%ROOT%" "%PYTHON_EXE%" scripts\manual_truth_calibration_watch.py --interval-min 15 --max-cycles 0 --require-runtime-fresh --runtime-max-age-sec 180 --step-timeout-sec 600 2>nul
exit /b 0

:start_checkpoint_improvement_orchestrator_watch_if_needed
if not exist "%ROOT%\logs" mkdir "%ROOT%\logs" >nul 2>&1
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$watch=@(Get-CimInstance Win32_Process | Where-Object { ($_.Name -ieq 'python.exe') -and ($_.CommandLine -match 'checkpoint_improvement_orchestrator_watch.py') }); if($watch.Count -gt 0){ exit 0 } else { exit 1 }" >nul 2>&1
if not errorlevel 1 (
  echo [INFO] checkpoint improvement orchestrator watch already running. skip duplicate start.
  exit /b 0
)
echo [INFO] starting checkpoint improvement orchestrator watch ^(60s orchestrator cadence^)...
echo ==== manage_cfd checkpoint_improvement_orchestrator_watch %date% %time% ====>> "%ORCHESTRATOR_WATCH_LOG%"
start "%TITLE_ORCHESTRATOR_WATCH%" /min /d "%ROOT%" "%PYTHON_EXE%" scripts\checkpoint_improvement_orchestrator_watch.py --interval-sec 60 --max-cycles 0 --require-runtime-fresh --runtime-max-age-sec 180 2>nul
exit /b 0

:run_storage_retention_preflight
echo [INFO] running storage retention preflight ^(cap %STORAGE_RETENTION_CAP_GB%GB^)...
cd /d "%ROOT%"
"%PYTHON_EXE%" scripts\storage_retention_watch.py --mode preflight --cap-gb %STORAGE_RETENTION_CAP_GB% --checkpoint-detail-min-gb %STORAGE_RETENTION_CHECKPOINT_DETAIL_MIN_GB% --max-cycles 1
if errorlevel 1 (
  echo [WARN] storage retention preflight failed. continuing boot.
  exit /b 0
)
exit /b 0

:start_storage_retention_watch_if_needed
if not exist "%ROOT%\logs" mkdir "%ROOT%\logs" >nul 2>&1
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$watch=@(Get-CimInstance Win32_Process | Where-Object { ($_.Name -ieq 'python.exe') -and ($_.CommandLine -match 'storage_retention_watch.py') }); if($watch.Count -gt 0){ exit 0 } else { exit 1 }" >nul 2>&1
if not errorlevel 1 (
  echo [INFO] storage retention watch already running. skip duplicate start.
  exit /b 0
)
echo [INFO] starting storage retention watch ^(%STORAGE_RETENTION_WATCH_INTERVAL_MIN%m cap=%STORAGE_RETENTION_CAP_GB%GB^)...
echo ==== manage_cfd storage_retention_watch %date% %time% ====>> "%STORAGE_RETENTION_WATCH_LOG%"
start "%TITLE_STORAGE_RETENTION_WATCH%" /min /d "%ROOT%" "%PYTHON_EXE%" scripts\storage_retention_watch.py --mode background --cap-gb %STORAGE_RETENTION_CAP_GB% --checkpoint-detail-min-gb %STORAGE_RETENTION_CHECKPOINT_DETAIL_MIN_GB% --interval-min %STORAGE_RETENTION_WATCH_INTERVAL_MIN% --max-cycles 0 2>nul
exit /b 0

:kill_cfd_processes
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$root='%ROOT%';" ^
  "$mainScript='main\.py';" ^
  "$targets=Get-CimInstance Win32_Process | Where-Object {" ^
  "  ($_.Name -ieq 'python.exe') -and (" ^
  "    ($_.CommandLine -match $mainScript -or $_.CommandLine -match 'ml[/\\\\]retrain_and_deploy.py' -or $_.CommandLine -match 'uvicorn backend.fastapi.app:app' -or $_.CommandLine -match 'state25_candidate_watch.py' -or $_.CommandLine -match 'manual_truth_calibration_watch.py' -or $_.CommandLine -match 'checkpoint_improvement_orchestrator_watch.py' -or $_.CommandLine -match 'storage_retention_watch.py') -or" ^
  "    ($_.CommandLine -match 'CFD_MAIN_ENGINE' -or $_.CommandLine -match 'CFD_ML_RETRAIN' -or $_.CommandLine -match 'CFD_FASTAPI_8010' -or $_.CommandLine -match 'CFD_NEXT_UI' -or $_.CommandLine -match 'CFD_STATE25_CANDIDATE_WATCH' -or $_.CommandLine -match 'CFD_MANUAL_TRUTH_CALIBRATION_WATCH' -or $_.CommandLine -match 'CFD_CHECKPOINT_IMPROVEMENT_WATCH' -or $_.CommandLine -match 'CFD_STORAGE_RETENTION_WATCH')" ^
  "  )" ^
  "};" ^
  "foreach($p in $targets){" ^
  "  try { Stop-Process -Id ([int]$p.ProcessId) -Force -ErrorAction Stop } catch {}" ^
  "}"
exit /b 0

:precheck
echo [INFO] running pre-deploy ops readiness check...
cd /d "%ROOT%"
"%PYTHON_EXE%" scripts\predeploy_ops_check.py --base-url http://127.0.0.1:8010 --timeout-sec 8 --wait-sec 30 --interval-sec 2
if errorlevel 1 (
  echo [FAIL] precheck failed. abort.
  exit /b 1
)
echo [OK] precheck passed.
exit /b 0

:deploy
echo [INFO] deploy gate: precheck
call "%~f0" precheck
if errorlevel 1 (
  echo [FAIL] deploy blocked by precheck.
  exit /b 1
)
echo [INFO] deploy pipeline: backup/release/tag
cd /d "%ROOT%"
"%PYTHON_EXE%" scripts\deploy_release.py --base-url http://127.0.0.1:8010 --timeout-sec 8
if errorlevel 1 (
  echo [FAIL] deploy pipeline failed.
  exit /b 1
)
echo [OK] deploy pipeline completed.
exit /b 0
