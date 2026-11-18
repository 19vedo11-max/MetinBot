@echo off
rem ==================================================================
rem  Kontrol-Ac.bat - isaretlenmis kareleri X-AnyLabeling ile acar.
rem  Klasor  : MetinBot\veri_yolo\kontrol  (her kare + ayni adli .json)
rem  Siniflar: 0 yaratik, 1 metin, 2 npc, 3 oyuncu, 4 pazar, 5 esya
rem  Ayarlar : araclar\xany_calisma\.xanylabelingrc
rem            (yoksa araclar\xany_ayar.yaml'dan kopyalanir)
rem  Nasil kullanilir: araclar\KONTROL-NASIL.md
rem ==================================================================
setlocal
set "ARAC=%~dp0"
set "ARAC=%ARAC:~0,-1%"
for %%I in ("%ARAC%\..") do set "KOK=%%~fI"
set "EXE=%ARAC%\X-AnyLabeling\X-AnyLabeling.exe"
set "KONTROL=%KOK%\veri_yolo\kontrol"
if not "%~1"=="" set "KONTROL=%KOK%\veri_yolo\%~1"
set "CALISMA=%ARAC%\xany_calisma"
set "SINIFLAR=yaratik,metin,npc,oyuncu,pazar,esya"

if not exist "%EXE%" goto kurulu_degil
if not exist "%KONTROL%\" goto klasor_yok

if not exist "%CALISMA%\.xanylabelingrc" (
  if not exist "%CALISMA%\" mkdir "%CALISMA%"
  copy /y "%ARAC%\xany_ayar.yaml" "%CALISMA%\.xanylabelingrc" >nul
)

rem --work-dir: ayar dosyasi ve model indirmeleri araclar\xany_calisma icinde kalir
rem --labels  : sinif listesi (virgullu), --validatelabel exact: baska ad yazilamaz
rem --nosortlabels: liste sirasi = YOLO id sirasi, --autosave: her degisiklik kaydedilir
rem --nodata  : resim JSON'a gomulmez (imageData null)
start "" "%EXE%" --work-dir "%CALISMA%" --filename "%KONTROL%" --labels "%SINIFLAR%" --validatelabel exact --nosortlabels --autosave --nodata --no-auto-update-check
endlocal
exit /b 0

:kurulu_degil
echo.
echo  X-AnyLabeling kurulu degil:
echo    %EXE%
echo  Once araclar\X-AnyLabeling-Kur.bat dosyasini calistir.
echo.
pause
endlocal
exit /b 1

:klasor_yok
echo.
echo  Kontrol klasoru henuz yok:
echo    %KONTROL%
echo  Kareler isaretlenip oraya konunca bu dosyayi tekrar calistir.
echo.
pause
endlocal
exit /b 1
