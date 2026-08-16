@echo off
echo ========================================
echo Construyendo ZarpadoSaneado standalone EXE...
echo ========================================

:: Limpiar carpetas previas si existen
if exist build rd /s /q build
if exist dist rd /s /q dist

:: Ejecutar PyInstaller
python -m PyInstaller --onefile --noconsole ^
    --exclude-module tkinter ^
    --add-data "7za.exe;." ^
    --add-data "7za.dll;." ^
    --add-data "7zxa.dll;." ^
    --add-data "assets;assets" ^
    --icon "Saneador.ico" ^
    --name "ZarpadoSaneado" ^
    "SaneadorGUI.py"

echo ========================================
echo Proceso finalizado.
echo El ejecutable esta en la carpeta 'dist/'
echo ========================================
