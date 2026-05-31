@echo off
chcp 65001 > nul
color 0A
title Panel de Control - Syncro

:menu
cls
echo ======================================================================
echo             PANEL DE CONTROL DE SYNCRO (DJANGO + SQL SERVER)
echo ======================================================================
echo.
echo    [1] Iniciar Servidor de Syncro y abrir navegador
echo    [2] Detener Servidor de Syncro (liberar puerto 8000)
echo    [3] Ver logs del servidor en tiempo real (Ctrl+C para salir)
echo    [4] Probar conexión a SQL Server
echo    [5] Abrir página en el navegador
echo    [6] Salir
echo.
echo ======================================================================
set /p opcion="Seleccione una opción [1-6]: "

if "%opcion%"=="1" goto iniciar
if "%opcion%"=="2" goto detener
if "%opcion%"=="3" goto logs
if "%opcion%"=="4" goto conexion
if "%opcion%"=="5" goto abrir
if "%opcion%"=="6" goto salir
goto menu

:iniciar
cls
echo [*] Iniciando servidor Django en segundo plano...
netstat -ano | findstr :8000 > nul
if %errorlevel% equ 0 (
    echo [!] El puerto 8000 ya está ocupado. Deteniendo proceso anterior...
    for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000') do taskkill /F /PID %%a > nul 2>&1
)
:: Iniciar el servidor redireccionando stdout/stderr a server.log
start /B venv\Scripts\python.exe manage.py runserver > server.log 2>&1
echo [+] Servidor iniciado. Logs redirigidos a 'server.log'.
echo [*] Abriendo navegador en http://127.0.0.1:8000/ ...
timeout /t 2 /nobreak > nul
start http://127.0.0.1:8000/
pause
goto menu

:detener
cls
echo [*] Deteniendo servidor Django en el puerto 8000...
netstat -ano | findstr :8000 > nul
if %errorlevel% equ 0 (
    for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000') do taskkill /F /PID %%a
    echo [+] Servidor detenido y puerto 8000 liberado.
) else (
    echo [!] El servidor no parece estar ejecutándose en el puerto 8000.
)
pause
goto menu

:logs
cls
echo ======================================================================
echo             LOGS EN TIEMPO REAL (Presione Ctrl+C para salir)
echo ======================================================================
echo.
if not exist server.log (
    echo [!] Aún no existe el archivo 'server.log'. Inicia el servidor primero.
    pause
    goto menu
)
powershell -Command "Get-Content server.log -Wait"
goto menu

:conexion
cls
echo [*] Ejecutando diagnóstico de conexión...
venv\Scripts\python.exe test_connection.py
pause
goto menu

:abrir
cls
echo [*] Abriendo http://127.0.0.1:8000/ en navegador...
start http://127.0.0.1:8000/
goto menu

:salir
exit
