# hazirla3 bitince set6 ile egitimi dusuk oncelikte baslatir (Claude Code'dan bagimsiz calisir).
param([int]$IsaretPid = 21924)
$k = $PSScriptRoot
while (Get-Process -Id $IsaretPid -ErrorAction SilentlyContinue) { Start-Sleep 20 }
if (-not (Test-Path "$k\veri_yolo\set6\veri.yaml")) {
    "$(Get-Date -Format HH:mm:ss) set6 yok - egitim baslatilmadi" | Out-File "$k\egit_bekle.log" -Append -Encoding utf8
    exit
}
$p = Start-Process -FilePath "$k\yolo_env\Scripts\python.exe" -ArgumentList "yolo_egit.py", "egit", "$k\veri_yolo\set6" `
    -WorkingDirectory $k -WindowStyle Hidden -RedirectStandardOutput "$k\egit6.log" -RedirectStandardError "$k\egit6_hata.log" -PassThru
Start-Sleep 3
$p.PriorityClass = "BelowNormal"
"$(Get-Date -Format HH:mm:ss) egitim basladi, PID $($p.Id)" | Out-File "$k\egit_bekle.log" -Append -Encoding utf8
