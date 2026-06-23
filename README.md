# 🌦️ Jolly — Staðbundið veðurspálíkan

Jolly er MOS (Model Output Statistics) veðurspálíkan sem:
- Sækir spár frá ICON, GFS og ECMWF sjálfkrafa á 6 klst. fresti
- Ber saman við mælingar frá Veðurstofu Íslands (stöð 571)
- Lærir og leiðréttir sig með tíð og tíma
- Birtir niðurstöður á vefsíðu

---

## 🚀 Uppsetning (einu sinni — ~15 mínútur)

### Skref 1 — Stofna GitHub reikning
1. Farðu á **github.com**
2. Smelltu á **"Sign up"** efst til hægri
3. Fylltu inn netfang, lykilorð, notandanafn
4. Staðfestu netfangið þitt

---

### Skref 2 — Búa til nýtt repository
1. Eftir innskráningu, smelltu á **"+"** efst til hægri → **"New repository"**
2. Gefðu það nafnið: `jolly-weather`
3. Veldu **"Public"** (þarf að vera public til að vefsíðan virki)
4. Smelltu á **"Create repository"**

---

### Skref 3 — Hlaða upp skránum
Þú þarft að hlaða upp þessum skrám í réttri möppubyggingu:

```
jolly-weather/
├── .github/
│   └── workflows/
│       └── jolly.yml        ← GitHub Actions (tímasetningin)
├── data/                    ← Tóm mappa (GitHub býr til sjálfkrafa)
├── docs/
│   └── index.html           ← Vefsíðan
├── jolly.py                 ← Aðalkóðinn
└── README.md
```

**Hvernig á að hlaða upp:**
1. Í repository síðunni þinni, smelltu á **"uploading an existing file"**
2. Dragðu allar skrárnar inn
3. ⚠️ **Mikilvægt:** `.github/workflows/jolly.yml` þarf sérstaka meðhöndlun:
   - Smelltu á **"Create new file"**
   - Nafngiftu það: `.github/workflows/jolly.yml`
   - Límdu innihald `jolly.yml` inn
4. Smelltu á **"Commit changes"**

---

### Skref 4 — Kveikja á GitHub Actions
1. Í repository þínum, smelltu á flipann **"Actions"**
2. Þú sérð skilaboð — smelltu á **"I understand my workflows, go ahead and enable them"**
3. Þú sérð "Jolly - Sjálfvirk veðurspá" í listanum til vinstri
4. Smelltu á hana → smelltu á **"Run workflow"** → **"Run workflow"** (til að prófa strax)
5. Bíddu í ~1 mínútu — þú sérð grænan hak ✅ þegar klárað

---

### Skref 5 — Kveikja á vefsíðunni
1. Í repository þínum, farðu í **Settings** (gírhjólið efst)
2. Í vinstri valmyndinni, smelltu á **"Pages"**
3. Undir "Source", veldu **"Deploy from a branch"**
4. Undir "Branch", veldu **"main"** og **"/docs"**
5. Smelltu á **"Save"**
6. Eftir ~2 mínútur færðu slóðina: `https://NOTENDANAFN.github.io/jolly-weather`

---

## ✅ Það er allt!

Frá þessum tímapunkti:
- **Klukkan 00:00, 06:00, 12:00, 18:00 UTC** keyrir Jolly sjálfkrafa
- Hún sækir nýjustu spár og mælingar
- Leiðréttir sig og uppfærir vefsíðuna
- Þú getur alltaf skoðað stöðuna undir **Actions** flipanum

---

## 📊 Hvernig Jolly lærir

```
Dagur 1-7:   Safnar gögnum, leiðréttingar lítið þróaðar
Dagur 8-30:  Fær skýrari mynd af hvað líkön villa
Dagur 31+:   Tölfræðilega marktækar leiðréttingar
Dagur 90+:   Fullþroskaður — tekur tillit til árstíðabundinna breytinga
```

---

## 🆘 Hjálp

Ef eitthvað gengur ekki — taktu skjámynd af villunni og sýndu Claude!
