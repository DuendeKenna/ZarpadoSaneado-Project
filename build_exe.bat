@echo off
echo ========================================
echo Construyendo Saneador standalone EXE...
echo ========================================

:: Limpiar carpetas previas si existen
if exist build rd /s /q build
if exist dist rd /s /q dist

:: Ejecutar PyInstaller
:: --onefile: Un solo ejecutable
:: --noconsole: Sin ventana de comandos (GUI puro)
:: --add-data: Incluir binarios de 7-Zip
:: --icon: Usar icono personalizado
python -m PyInstaller --onedir --noconsole ^
    --add-data "7za.exe;." ^
    --add-data "7za.dll;." ^
    --add-data "7zxa.dll;." ^
    --icon "Saneador.ico" ^
    --name "SaneadorGUI" ^
    "SaneadorGUI.py"

echo ========================================
echo Proceso finalizado.
echo El ejecutable esta en la carpeta 'dist/'
echo ========================================
