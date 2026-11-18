"""Guncellemeyi GitHub'daki gizli depoya gonderir (19vedo11-max/MetinBot).

python yayinla.py "ne degisti"
paylas.py ile temiz paketi uretir, C:\\Users\\19ved\\MetinBot-Dagitim klasorunu (depo) onunla esitler,
commit edip gonderir. Kisisel dosyalar paylas.py'de zaten dislanir."""
import glob
import os
import shutil
import subprocess
import sys
import zipfile

KLASOR = os.path.dirname(os.path.abspath(__file__))
DEPO = os.path.join(os.path.dirname(KLASOR), "MetinBot-Dagitim")
mesaj = sys.argv[1] if len(sys.argv) > 1 else "Guncelleme"

subprocess.run([sys.executable, os.path.join(KLASOR, "paylas.py")], check=True, cwd=KLASOR)
zipler = sorted(glob.glob(os.path.join(KLASOR, "dist", "MetinBot-Paket-*.zip")), key=os.path.getmtime)
paket = zipler[-1]

for ad in os.listdir(DEPO):                      # .git ve .gitignore disindaki her seyi sil, paketten yeniden ac
    if ad in (".git", ".gitignore"):
        continue
    yol = os.path.join(DEPO, ad)
    shutil.rmtree(yol) if os.path.isdir(yol) else os.remove(yol)
with zipfile.ZipFile(paket) as z:
    for u in z.infolist():
        if u.is_dir():
            continue
        hedef = os.path.join(DEPO, u.filename.split("/", 1)[1] if "/" in u.filename else u.filename)
        os.makedirs(os.path.dirname(hedef), exist_ok=True)
        with z.open(u) as kaynak, open(hedef, "wb") as f:
            shutil.copyfileobj(kaynak, f)

subprocess.run(["git", "add", "-A"], cwd=DEPO, check=True)
if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=DEPO).returncode == 0:
    print("degisiklik yok - gonderilmedi")
    sys.exit(0)
subprocess.run(["git", "-c", "user.name=Vedat Mallı", "-c", "user.email=19vedo11@gmail.com", "commit", "-q", "-m", mesaj],
               cwd=DEPO, check=True)
subprocess.run(["git", "push", "-q"], cwd=DEPO, check=True)
print("gonderildi:", mesaj)
