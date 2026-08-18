@echo off
setlocal enabledelayedexpansion

echo ========================================================
echo   Compilando ZarpadoSaneado (Optimizada Anti-Falsos Positivos)
echo ========================================================

:: Limpiar carpetas previas si existen
if exist build rd /s /q build
if exist dist rd /s /q dist

echo.
echo [1/4] Compilando version con carpeta _internal (OneDir)...
python -m PyInstaller --onedir --noconsole --noupx ^
    --exclude-module tkinter ^
    --exclude-module markupsafe ^
    --version-file "file_version_info.txt" ^
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
echo [2/4] Limpiando metadatos residuales (.dist-info) para evitar falsos positivos de VirusTotal...
for /d /r "dist\ZarpadoSaneado" %%d in (*.dist-info *.egg-info) do (
    if exist "%%d" (
        echo Eliminando metadato: %%d
        rd /s /q "%%d"
    )
)

echo.
echo [3/4] Creando archivo ZIP estructurado de la version con carpeta...
:: Empaquetamos la carpeta contenedora completa para evitar que VirusTotal lo confunda con un Wheel de Python
cd dist
if exist "..\7za.exe" (
    ..\7za.exe a -tzip -mx5 "ZarpadoSaneado_Carpeta.zip" "ZarpadoSaneado"
) else (
    tar -a -c -f "ZarpadoSaneado_Carpeta.zip" "ZarpadoSaneado"
)
cd ..

echo.
echo [4/4] Compilando version monoejecutable (OneFile)...
python -m PyInstaller --onefile --noconsole --noupx ^
    --exclude-module tkinter ^
    --exclude-module markupsafe ^
    --version-file "file_version_info.txt" ^
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
echo   2. ZIP empaquetado:        dist\ZarpadoSaneado_Carpeta.zip
echo   3. Ejecutable unico (EXE): dist\ZarpadoSaneado_Standalone.exe
echo ========================================================
