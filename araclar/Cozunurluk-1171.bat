@echo off
rem Oyun cozunurlugunu pencereye esitler: metin2.cfg HEIGHT 889 -> 937 (125% olcekte 1171 piksel).
rem SAG TIK -> "Yonetici olarak calistir". Oyun KAPALI olmali (oyun kapanirken ayari geri yazar).
net session >nul 2>&1
if errorlevel 1 (
  echo BU PENCERE YONETICI DEGIL. Kapat, dosyaya sag tiklayip "Yonetici olarak calistir" de.
  pause
  exit /b
)
set CFG=C:\Program Files (x86)\Waryong2\metin2.cfg
tasklist /FI "IMAGENAME eq Waryong2.bin" | find /I "Waryong2.bin" >nul
if not errorlevel 1 (
  echo Oyun hala acik. Once oyunu kapat, sonra bu dosyayi yeniden calistir.
  pause
  exit /b
)
copy /Y "%CFG%" "%CFG%.yedek" >nul
powershell -NoProfile -Command "$p='%CFG%'; $t=[IO.File]::ReadAllText($p); $t=[Regex]::Replace($t,'(?m)^(HEIGHT\s+)\d+','${1}937'); [IO.File]::WriteAllText($p,$t)"
findstr /B "WIDTH HEIGHT" "%CFG%"
echo.
echo Tamam: HEIGHT 937 yazildi (yedek: metin2.cfg.yedek). Simdi oyunu ac.
pause
