@echo off
cd /d "%~dp0"
echo Iniciando ZarpadoSaneado...
if exist "dist\ZarpadoSaneado.exe" (
    start "" "dist\ZarpadoSaneado.exe"
) else if exist "dist\ZarpadoSaneado\ZarpadoSaneado.exe" (
    start "" "dist\ZarpadoSaneado\ZarpadoSaneado.exe"
) else (
    start python SaneadorGUI.py
)
exit
