@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
echo === MetinBot kurulum ===
set "PY="
py -3 -c "import sys; sys.exit(0 if sys.version_info>=(3,11) else 1)" >nul 2>&1 && set "PY=py -3"
if not defined PY (
  python -c "import sys; sys.exit(0 if sys.version_info>=(3,11) else 1)" >nul 2>&1 && set "PY=python"
)
if not defined PY (
  echo Python 3.11 veya daha yenisi bulunamadi.
  set /p CEVAP="winget ile Python 3.12 kurulsun mu? (E/H): "
  if /i "%CEVAP%"=="E" (
    winget install -e --id Python.Python.3.12
    echo.
    echo Python kuruldu. Bu pencereyi kapatip Kur.bat'i BIR KEZ DAHA calistir.
  ) else (
    echo Python'u https://www.python.org adresinden kur ^(Add to PATH isaretli^), sonra Kur.bat'i tekrar calistir.
  )
  pause
  exit /b 1
)
echo Python bulundu: %PY%
%PY% -m pip install --upgrade pip
%PY% -m pip install -r requirements.txt
if errorlevel 1 (
  echo Paket kurulumu basarisiz. Interneti kontrol edip tekrar dene.
  pause
  exit /b 1
)
if not exist ayar.json (
  copy /y ayar_ornek.json ayar.json >nul
  echo ayar.json ayar_ornek.json'dan olusturuldu.
)
set "KDIR=%~dp0"
%PY% -c "import sys,os;p=os.path.join(os.path.dirname(sys.executable),'pythonw.exe');open(os.path.join(r'%TEMP%','mb_pyw.txt'),'w').write(p if os.path.exists(p) else sys.executable)"
set /p PYW=<"%TEMP%\mb_pyw.txt"
powershell -NoProfile -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut([IO.Path]::Combine([Environment]::GetFolderPath('Desktop'),'MetinBot.lnk'));$s.TargetPath='%PYW%';$s.Arguments='\"%KDIR%MetinBot.pyw\"';$s.WorkingDirectory='%KDIR%';$s.IconLocation='%KDIR%araclar\metinbot.ico';$s.Save()"
echo Masaustune "MetinBot" kisayolu olusturuldu.
echo.
echo KURULUM TAMAM.
echo  - Botu Bot-Baslat.bat ile YONETICI olarak calistir (sag tik - Yonetici olarak calistir);
echo    oyun yonetici yetkisiyle calistigi icin tuslar aksi halde oyuna ulasmaz.
echo  - Ayarlari masaustundeki MetinBot kisayolundan acilan panelden yap.
echo  - Ayrintilar: BENIOKU.md
pause
