@echo off
setlocal enabledelayedexpansion

echo ========================================================
echo   Compilando ZarpadoSaneado (Versiones OneFile y OneDir)
echo ========================================================

:: Limpiar carpetas previas si existen
if exist build rd /s /q build
if exist dist rd /s /q dist

echo.
echo [1/3] Compilando version con carpeta _internal (OneDir)...
python -m PyInstaller --onedir --noconsole ^
    --exclude-module tkinter ^
    --add-data "7za.exe;." ^
    --add-data "7za.dll;." ^
    --add-data "7zxa.dll;." ^
    --add-data "assets;assets" ^
    --icon "Saneador.ico" ^
    --name "ZarpadoSaneado" ^
    "SaneadorGUI.py"

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Fallo la compilacion OneDir.
    exit /b %ERRORLEVEL%
)

echo.
echo [2/3] Creando archivo ZIP de la version con _internal...
if exist "7za.exe" (
    7za.exe a -tzip -mx5 "dist\ZarpadoSaneado_Carpeta.zip" ".\dist\ZarpadoSaneado\*"
) else (
    tar -a -c -f "dist\ZarpadoSaneado_Carpeta.zip" -C "dist\ZarpadoSaneado" *
)

echo.
echo [3/3] Compilando version monoejecutable (OneFile)...
python -m PyInstaller --onefile --noconsole ^
    --exclude-module tkinter ^
    --add-data "7za.exe;." ^
    --add-data "7za.dll;." ^
    --add-data "7zxa.dll;." ^
    --add-data "assets;assets" ^
    --icon "Saneador.ico" ^
    --name "ZarpadoSaneado_Standalone" ^
    "SaneadorGUI.py"

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Fallo la compilacion OneFile.
    exit /b %ERRORLEVEL%
)

echo.
echo ========================================================
echo   COMPILACION FINALIZADA EXITOSAMENTE!
echo ========================================================
echo   1. Carpeta con _internal:  dist\ZarpadoSaneado\
echo   2. ZIP listo para enviar:  dist\ZarpadoSaneado_Carpeta.zip
echo   3. Ejecutable unico (EXE): dist\ZarpadoSaneado_Standalone.exe
echo ========================================================
