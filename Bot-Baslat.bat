@echo off
rem MetinBot baslatici. Oyun yonetici yetkisiyle calistigi icin bu dosyaya
rem SAG TIK -> "Yonetici olarak calistir" denmeli; yoksa tuslar oyuna ulasmaz.
rem Bot kodu guncellenince kendini kapatir (kod 3); bu dosya onu yeni surumle hemen yeniden acar.
cd /d "%~dp0"
net session >nul 2>&1
if errorlevel 1 (
  echo BU PENCERE YONETICI DEGIL. Kapat, dosyaya sag tiklayip "Yonetici olarak calistir" de.
  pause
  exit /b
)
:dongu
python bot.py
if %errorlevel%==3 goto dongu
rem beklenmedik cokus (kod 1): 10 sn sonra yeniden ac; F12/kapat (kod 0) durdurur
if %errorlevel%==1 (
  timeout /t 10 >nul
  goto dongu
)
pause
