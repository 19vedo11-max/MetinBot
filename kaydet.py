"""Oyun ondeyken belirli sure boyunca aralikli kare kaydeder (menu adimlarini gormek icin).
Kullanim: python kaydet.py [sure_sn=120] [aralik_sn=1.5]"""
import os
import sys
import time

import win32gui
from PIL import Image

import bot

sure = float(sys.argv[1]) if len(sys.argv) > 1 else 120
aralik = float(sys.argv[2]) if len(sys.argv) > 2 else 1.5
klasor = os.path.join(bot.KLASOR, "goruntu", "kayit")
os.makedirs(klasor, exist_ok=True)
for f in os.listdir(klasor):
    os.remove(os.path.join(klasor, f))
h = bot.pencere_bul("Waryong2")
bitis, n = time.time() + sure, 0
while time.time() < bitis:
    if win32gui.GetForegroundWindow() == h:
        Image.fromarray(bot.kare_al(h)).save(os.path.join(klasor, f"k{n:03d}.jpg"), quality=88)
        n += 1
    time.sleep(aralik)
print("kaydedilen kare:", n)
