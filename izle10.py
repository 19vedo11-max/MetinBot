"""Son N dakikanin (varsayilan 10) bot.log ozeti - Vedo'nun duzenli kontrolu icin, kisa cikti.
python izle10.py [dk]"""
import collections
import datetime as dt
import re
import sys

import gece_rapor

dk = int(sys.argv[1]) if len(sys.argv) > 1 else 10
simdi = dt.datetime.now()
sat = gece_rapor.satirlar_araliktaki(simdi - dt.timedelta(minutes=dk), simdi)
tum = open(gece_rapor.LOG, encoding="utf-8", errors="replace").read().splitlines()[-4000:]
# satirlar_araliktaki yalniz zaman damgali satirlari verir; DURAKLAMA bitti satirlari icin ham kuyruga bak
bas_s, simdi_s = (simdi - dt.timedelta(minutes=dk)).strftime("%H:%M:%S"), simdi.strftime("%H:%M:%S")
ham = []
for s in reversed(tum):                         # sondan geriye: pencere basina (ya da gece yarisi gecisine) kadar
    m = re.match(r"(\d\d:\d\d:\d\d)", s)
    if m and (m[1] < bas_s if bas_s <= simdi_s else (simdi_s < m[1] < bas_s)):
        break
    if m and bas_s <= simdi_s and m[1] > simdi_s:
        break
    ham.append(s)
ham.reverse()

say = lambda p: sum(1 for s in sat if re.search(p, s))
slot = say(r"slot bitti \(")
kes = sum(int(m[1]) for s in sat for m in [re.search(r"grup: (\d+) canavar", s)] if m)
d, ds, son = collections.Counter(), collections.Counter(), None
for s in ham:
    m = re.search(r"DURAKLAMA >3 sn: su an '([^']+)'", s)
    if m:
        son = m[1]
        d[son] += 1
    m2 = re.search(r"DURAKLAMA bitti \(([\d.]+) sn\)", s)
    if m2 and son:
        ds[son] += float(m2[1])
ulas = collections.Counter(m[1] for s in sat for m in [re.search(r"hedefe ulasilamadi \[([^\],]+)", s)] if m)
exp = [s for s in sat if "tecrube:" in s]
yeniden = say(r"bot basladi")
print(f"{simdi:%H:%M} son {dk} dk | slot {slot} | kesilen {kes} ({kes / max(1, slot):.1f}/slot) | olum {say(r'oldu [(]')} | "
      f"savunma {say(r'hasar aliyorum')} | grupta kaldi {say(r'slot ici:')} | sekil {say(r'sekil:')} | "
      f"Traceback {say(r'Traceback')} | yeniden acilis {yeniden}")
print("duraklama:", ", ".join(f"{k} {d[k]}x {v:.0f}sn" for k, v in ds.most_common(5)) or "-",
      f"| toplam {sum(ds.values()):.0f} sn")
print("ulasilamadi:", ", ".join(f"{k} {v}" for k, v in ulas.most_common()) or "-",
      "| gezin/alan:", say(r"gezin:|alan: cizilen|kisa yuruyuste hedef yok"),
      "| pot/satici:", say(r"pot al|POT BITTI"))
if exp:
    print("exp:", exp[-1].split("tecrube:")[-1].strip()[:80])
# uzun bosluklar: ardisik zaman damgali satirlar arasi > 20 sn
ts = [(dt.datetime.strptime(s[:8], "%H:%M:%S"), s) for s in sat if re.match(r"\d\d:\d\d:\d\d", s)]
for (t1, s1), (t2, s2) in zip(ts, ts[1:]):
    if (t2 - t1).total_seconds() > 20 and not re.search(r"grup: |slot ici|slot bitti|hasar aliyorum|oldu \(", s2):
        print(f"bosluk {int((t2 - t1).total_seconds())} sn: {s1[:90]}  ->  {s2[:60]}")
