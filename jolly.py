"""
Jolly v3.1 - Stadbundid vedurspalikan fyrir Egilsstadi (stod 571 / BIEG)

Skraarnafn hja Claude er "jolly_v19" en thad er BARA vinnuheiti. Raunveruleg
utgafa er JOLLY_VERSION her ad nedan. Hun er prentud efst i hverri
keyrslu svo audvelt se ad sja hvada utgafa er i gangi.

SAGA I STUTTU MALI:
  v2.0  eiginleg spastadfesting (Jolly geymd og staðfest gegn maelingum)
  v2.3  thyngdir ser fyrir hverja breytu (hiti/vindur/att/urkoma/sky)
  v2.5  langtimasafn i manadarskiptar CSV (arstidaskilyrding)
  v2.6  vindatt fimmta breytan, hringlaga reikningur
  v2.7  restleidretting a Jolly sjalfri (safnstyring)
  v2.8  skilyrt bias (vindatt x dagur/nott) med shrinkage
  v3.0  urkomuthroskuldur (F1), adlagandi LR, bruun milli spalengdarholfa
  v3.1  skilyrt bias veikist med spalengd (attarspa ovissari langt fram),
        SSL-varaleid fyrir apis.is, einskiptis-hreinsun a mengadri sogu
  v3.2  OPINBERT api.vedur.is i stad apis.is (stod 4271) - raunhiti aftur,
        engin vottordsvandamal, raki+thrystingur+haest/laegst hiti fylgja
  v3.3  SPA-GREINING: prentar blondu vs restbias vs lokaspa fyrir eina
        klst, til ad finna hvers vegna Jolly tapar (greining, ekki lagfaering)
  v3.4  SPA-GREINING utvikkud: allar breytur + hrair medlimir, adeins fyrir
        LIDANDI stund svo haegt se ad bera beint saman vid maelingu
  v3.5  ROTIN FUNDIN: Jolly fekk bias lagt a TVISVAR vid mat (hun er geymd
        fullleidrett en var medhondlud eins og hrair medlimir). Thad var
        jakvaed afturvirkni sem let restbias vaxa og eydilagdi spana.
        Lagfaert + einskiptis-hreinsun a menguðu jolly_bias.
  v3.6  FALL-EINKUNN: likan sem er oreglulega skakkt (> FAIL_RATIO x besta)
        faer 0 vaegi en er AFRAM MAELT og kemst inn aftur eftir 3 godar
        spar i rod. Maelt a leidrettu MAE svo stodug hlutdraegni - sem
        bias lagar - se ekki refsad.
  v3.7  METAR-VILLA LAGFAERD: vid tokum obs[-1] sem "nyjustu" faerslu en
        aviationweather skilar nyjustu FYRST, svo vid fengum alltaf 24 klst
        gamla skyjahulu. Jolly laerdi skyjahulu af gaerdeginum. Nu radad
        eftir tima + vidvorun ef gognin eru eldri en 3 klst.
  v3.8  TVENNT: (1) SANNLEIKSMAELIR - hlaupandi 24 klst gluggi a HRAUM
        tolum, oblekkjanlegur, svo vid sjaum hvort skill-taflan logi.
        (2) TILRAUN: restleidretting EKKI notud (APPLY_JOLLY_RESIDUAL=False)
        thvi hun rann i thakid og gerdi Jolly verri en medaltal medlima.
        Hun er laerd afram svo vid sjaum hver raunveruleg skekkja er.
  v3.9  SANNLEIKSMAELIR baettur: synir NU BAEDI samanburd vid HRAA medlimi
        (er Jolly betri en likan ur kassanum?) OG vid LEIDRETTA medlimi
        (baetir blondun einhverju vid MOS a einu likani?). Fyrri utgafa bar
        adeins hraa medlimi vid leidretta Jolly - ojafn samanburdur.
  v4.0  NAKVAEMNI FRAM YFIR ALLT:
        - Sannleiksmaelirinn notar NU NAKVAEMLEGA sama bias-fall og spain
          (member_bias), svo samanburdurinn se hnitmiadadur.
        - THRIHYRNINGSVORN: hropar sjalfkrafa ef Jolly verdur verri en
          medaltal medlima sinna - thad er staerdfraedilega omogulegt.
        - SUNDURLIDUN eftir vindatt x dagur/nott, thvi medaltal fela mynstur.
        - TILRAUN: hita-bias a medlimi SLOKKT (APPLY_MEMBER_BIAS) thvi
          maelingar syndu ad thad gerdi 8 af 9 likonum verri.
  v4.1  SKILYRTAR THYNGDIR - staersta breytingin hingad til:
        Ekki bara "hver er bestur i hita" heldur "hver er bestur i hita I
        NORDANATT AD NOTTU". Thyngdir laerast per reit med shrinkage
        (thunnur reitur fellur a almennu thyngdirnar). Fall-einkunn gildir
        LIKA per reit - likan sem er onytt i einni att heldur vaegi i
        annarri. URKOMA faer sinn eigin reit: att x THRYSTITHROUN
        (fall/jafn/ris) thvi urkoma raest af synoptiskri thvingun, ekki
        solarhringssveiflu.
  v4.2  THRIHYRNINGSVORNIN LAGFAERD: bar adur vegna blondu vid OVEGID
        medaltal - ekki gild ojafna. Notar nu raunverulegar thyngdir Jolly.
        + KRUFNING: synir EINA stadfestingu i heild (hver medlimur, thyngd,
        reiknud blanda, geymd Jolly-spa) svo se haegt ad sja hvort geymda
        gildid passi vid blonduna. Vornin greip a skyi og vindi 19.ag.
"""


# ═══════════════════════════════════════════════════════════════════════
#  EFNISYFIRLIT - leitadu ad [TAGGI] til ad stokkva beint a kafla
#
#  Daemi: skrifadu [SKY] i leit og thu ferd beint i skyjahlutann.
#  Sama gildir thegar thu segir Claude "farðu í [SPA]".
#
#    [STADUR]         STADSETNING OG GRUNNSTILLINGAR
#    [GJAFAR]         GJAFAR OG LIKON
#    [STILLINGAR]     STILLIFASTAR - THYNGDIR, THROSKULDAR, ROFAR
#    [VOKTUN]         SJALFSVOKTUN
#    [VERKFAERI]      ALMENN VERKFAERI
#    [TAKN]           TAKN OG LYSINGAR
#    [BIAS]           BIAS-LEIDRETTING (hiti / vindur / att)
#    [URKOMA]         URKOMA
#    [SKY]            SKYJAHULA
#    [MAELING]        RAUNMAELINGAR - METAR OG VEDUR.IS
#    [SOKN]           GAGNASOKN FRA GJOFUM
#    [SAFN]           SPASAFN - GEYMSLA TIL STADFESTINGAR
#    [LIKAN]          LIKANSKRAIN - UPPBYGGING, HLEDSLA, HREINSANIR
#    [REITIR]         REITIR - VINDATT x DAGUR/NOTT x THRYSTITHROUN
#    [LANGTIMASAFN]   LANGTIMASAFN (CSV)
#    [SANNLEIKUR]     SANNLEIKSMAELIR
#    [STADFESTING]    STADFESTING OG NAM  <-- STAERSTI KAFLINN
#    [SPA]            SPAGERD  <-- HER VERDUR SPAIN TIL
#    [YFIRLIT]        YFIRLIT I LOGG
#    [KEYRSLA]        VISTUN OG KEYRSLA
#
# ═══════════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════════
#  JOLLY UTGAFA - eina talan sem skiptir mali. Skraarnafnid (jolly_v19)
#  er bara vinnuheiti; ÞETTA er raunveruleg utgafa kodans.
# ═══════════════════════════════════════════════════════════════════════
JOLLY_VERSION = "5.4"

import json, math, re, sys
import urllib.request, urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path
import xml.etree.ElementTree as ET
from collections import Counter

# --- STILLINGAR ------------------------------------------------------------
LAT, LON   = 65.2620, -14.4035
# ═══════════════════════════════════════════════════════════════════════
#  [STADUR]  STADSETNING OG GRUNNSTILLINGAR
#  Hnit, stodvarnumer, moppur. Breyta HER til ad faera Jolly a annan stad.
# ═══════════════════════════════════════════════════════════════════════

STATION_ID = 571
ICAO       = "BIEG"
DATA_DIR   = Path("docs/data")
DATA_DIR.mkdir(exist_ok=True, parents=True)

OBS_HISTORY_HOURS = 720     # 30 dagar - VINNUSETT til samsvorunar
# 72 klst i stad 12: their ver okkur ef Actions liggur nidri i nokkra daga.
# Med 12 klst var hver ostadfest spa horfin ad eilifu eftir halfan dag.
ARCHIVE_KEEP_PAST = 72

# --- LANGTIMAGAGNASAFN ---------------------------------------------------
# Stadfest por eru skrifud i manadarskiptar CSV-skrar sem eru ALDREI
# hreinsadar. Thetta er thjalfunargagnasettid sjalft - forsenda fyrir
# arstidaskilyrdingu sidar (sunnanatt i januar hegdar ser allt annad en
# sunnanatt i juli). Bias-talan ein getur ekki greint thau, og skilyrding
# tharf 2+ ar til ad hafa nog tilvik i hverjum reit.
#
# Manadarskrar i stad einnar: adeins skra thessa manadar breytist i hverri
# keyrslu, svo git-vidbaeturnar eru smaar og eldri manudir frjosa.
VERIFY_DIR = DATA_DIR / "verify"
VERIFY_COLS = ["valid_time", "lead", "src", "month", "hour",
               "wd_ob", "ws_ob",
               "t_fc", "t_ob", "w_fc", "w_ob",
               "d_fc", "d_ob", "p_fc", "p_ob", "c_fc", "c_ob"]
ARCHIVE_HORIZON   = 48      # hversu langt fram vid geymum spa til stadfestingar
LEAD_BUCKETS      = [1, 3, 6, 12, 24, 48]
LR                = 0.12    # grunn-laerdomshraedi
LR_MAX            = 0.45    # thak thegar skekkjan er kerfisbundin
LR_RUN_GAIN       = 0.50    # hversu hratt LR vex per samfellt formerki

def adaptive_lr(model, key, err):
    """
    Haekkar laerdomshradann thegar skekkjan hefur SAMA FORMERKI margar
    keyrslur i rod - tha er hun kerfisbundin (nytt vedurkerfi) en ekki sud.
    Fast LR=0.12 tekur ~14 klst ad na ser eftir kerfisskipti; adlagandi
    tekur ~7 klst og gefur um 8% laegra MAE i heild.
    """
    st = model.setdefault("lr_state", {}).setdefault(key, {"run": 0, "last": 0.0})
    if err * st["last"] > 0:
        st["run"] = min(8, st["run"] + 1)
    else:
        st["run"] = 0
    st["last"] = err
    return min(LR_MAX, LR * (1.0 + LR_RUN_GAIN * st["run"]))

# Likon sott gegnum Open-Meteo
# ═══════════════════════════════════════════════════════════════════════
#  [GJAFAR]  GJAFAR OG LIKON
#  Hvada spalikon vid sakjum og hvad thau heita innanhuss.
# ═══════════════════════════════════════════════════════════════════════

MODELS = {
    # UWC-West HARMONIE AROME - sama kerfi sem Vedurstofan notar, 2 km
    "dmi":   "dmi_seamless",
    "knmi":  "knmi_seamless",
    # Hnattlikon
    "ecmwf": "ecmwf_ifs025",
    "icon":  "icon_seamless",
    "ukmo":  "ukmo_seamless",
    "mfr":   "meteofrance_seamless",
    "gfs":   "gfs_seamless",
}

# Gjafar med eigin API - hver med sina fetch-adferd
EXTRA_KEYS = ["harmonie", "metno"]
ALL_KEYS   = list(MODELS.keys()) + EXTRA_KEYS

# Jolly sjalf er stadfest eins og hver annar gjafi, en hun fer ALDREI
# i thyngdarutdeilingu ne bias-leidrettingu - hun ER nidurstadan.
# An thessa hofum vid engan malikvarda a hvort Jolly se betri en
# besta einstaka likanid.
JOLLY_KEY   = "jolly"
VERIFY_KEYS = ALL_KEYS + [JOLLY_KEY]

# Skyjahula: lagmarksfjoldi i hverjum flokki adur en flokkabundin
# leidretting er notud i stad flatrar
MIN_CLOUD_N = 6

# --- THYNGDIR ERU SER FYRIR HVERJA BREYTU --------------------------------
# GFS getur verid lelegt i hita en gott i vindi. Ad nota hitaskekkju til ad
# vega vindspa er villa - hver breyta faer sina eigin rodun.
# ═══════════════════════════════════════════════════════════════════════
#  [STILLINGAR]  STILLIFASTAR - THYNGDIR, THROSKULDAR, ROFAR
#  Allt sem vid fikrum i thegar vid stillum. Nam, foll og throskuldar.
# ═══════════════════════════════════════════════════════════════════════

WEIGHT_VARS = ["hiti", "vindur", "att", "urkoma", "sky"]

# EPS ver okkur gegn 1/MAE -> uendanlegt og VERDUR ad passa vid kvarda
# breytunnar: hiti/vindur i einingum ~1, urkoma i mm ~0.1, sky i % ~10.
EPS_BY_VAR = {"hiti": 0.05, "vindur": 0.05, "att": 3.0,
              "urkoma": 0.02, "sky": 2.0}

# Urkoma er strjal (mest nullur) svo hun tharf fleiri samanburdi
# adur en rodun er marktaek.
MIN_N_BY_VAR = {"hiti": 4, "vindur": 4, "att": 6, "urkoma": 12, "sky": 6}

# --- FALL-EINKUNN: likan sem er OREGLULEGA skakkt faer 0 vaegi ------------
# [MIKILVAEGT] Vid maelum a MAE EFTIR bias-leidrettingu, ekki hrau MAE.
# Likan sem er STODUGT skakkt i somu att (t.d. alltaf +20% sky) er
# VERDMAETT - bias lagar thad fullkomlega. Thad sem vid viljum fella ut er
# likan sem er OREGLULEGT: haavadi sem enginn bias getur lagad.
#
# Fallid er AFTURKRAEFT: likanid er maelt afram og kemst sjalfkrafa inn
# aftur eftir RECOVER_N samfelldar godar spar. Vid geymum ALDREI ut gogn.
# Throskuldar stilltir a RAUNGOGNUM (16.ag): 2.8x a skyi fellir 3 verstu
# (dmi/ukmo/knmi) en heldur 6 likonum - nog fjolbreytni. Haerri throskuldur
# a hita/vindi thvi thar eru likonin thett saman og fall vaeri of hart.
FAIL_RATIO   = {"hiti": 3.5, "vindur": 3.5, "att": 3.0,
                "urkoma": 4.0, "sky": 2.8}   # x MAE besta likans

# --- RESTLEIDRETTING: TILRAUN v3.8 --------------------------------------
# Medlimir eru THEGAR bias-leidrettir adur en their blandast. Ef su
# leidretting virkar aetti restbias ad falla i kringum null. Hun gerir thad
# EKKI - hun rennur i thakid (sky -12.0, att -10.2) og situr thar. Thad
# bendir til ad hun se ekki ad leidretta kerfisbundna skekkju heldur ad
# ELTA HAVADA - hun fittar sig ad sidustu maelingum.
#
# Sonnun: Jolly hiti @6klst = 1.10 en MEDALTAL medlima = 0.81. Vegin
# blanda a ALLTAF ad vera betri en medaltal hlutanna. Ad vera verri thydir
# ad eitthvad er lagt vid EFTIR blondun sem eydileggur hana.
#
# Med False laerum vid restbias afram (thad segir okkur hver raunveruleg
# eftirstandandi skekkja er) en BEITUM henni EKKI a spana.
# --- RESTLEIDRETTING: v4.7 - KVEIKT A HITA, SLOKKT A HINUM ---------------
# Fjogurra daga tilraun (slokkt a ollu) syndi:
#   - vindur/att/sky: Jolly batnadi an leidrettingar -> ENN slokkt
#   - hiti: restbias SAT FAST A THAKINU (-1.50) dag eftir dag. Thad thydir
#     hun sa VIDVARANDI hlyhlutdraegni sem vid vorum ekki ad leidretta -
#     og 21.ag STADFESTIST thad: Jolly +5.1° of hly thegar utgeislunar-
#     kolnun i logni/heidskiru kvoldi let hitann falla hratt en modelin
#     (og thvi Jolly-blandan) elta ekki. Kveikt a hita, thak RYMKAD ur
#     1.5 i 4.0 thvi 1.5 dugdi audsjaanlega ekki vid theim adstaedum.
APPLY_JOLLY_RESIDUAL = {"hiti": True, "vindur": False,
                        "att": False, "sky": False}

# Thok a restleidrettingu. Voru adur hardkodud inni i lykkjunni svo
# sjalfsvoktunin gat ekki vitad hver thau eru - thad olli NameError og
# felldi keyrsluna. Nu ein uppspretta sem baedi namid og voktunin nota.
JOLLY_BIAS_CAP = {"hiti": 4.0, "vindur": 1.5, "att": 12.0, "sky": 12.0}

# --- MEDLIMA-BIAS: TILRAUN v4.0 -----------------------------------------
# Sannleiksmaelirinn (19.ag) syndi ad ALMENNA hita-biasid gerir 8 af 9
# likonum VERRI: medaltal 1.52 -> 1.72 (+13%). Adeins harmonie batnar -
# og thad er eina likanid med naestum null skilyrt bias.
#
# Med False fyrir breytu er EKKERT bias lagt a medlimi i theirri breytu
# (hvorki almennt ne skilyrt). Vid maelum svo hvort Jolly batni.
APPLY_MEMBER_BIAS = {"hiti": False, "vindur": True, "att": True,
                     "urkoma": True, "sky": True}

# --- SKILYRTAR THYNGDIR -------------------------------------------------
# Ekki bara "hver er bestur i hita" heldur "hver er bestur i hita I
# NORDANATT AD NOTTU". Likan sem er frabaert i sudlaegri att getur verid
# onytt i nordanatt - medaltal fela thad.
#
# Shrinkage: thunnur reitur fellur aftur a almennu thyngdirnar svo vid
# laerum ekki havada. Vid fullt traust tharf CELLW_FULL_N por.
CELLW_MIN_N   = 12     # undir thessu: nota EINGONGU almennar thyngdir
CELLW_FULL_N  = 60     # yfir thessu: nota EINGONGU reit-thyngdir
CELLW_LR      = 0.10   # veldisjofnun a reit-MAE

def cell_weight_blend(n):
    """Hlutfall reit-thyngda a moti almennum. 0 = almennar, 1 = reitur."""
    if n <= CELLW_MIN_N:  return 0.0
    if n >= CELLW_FULL_N: return 1.0
    return (n - CELLW_MIN_N) / float(CELLW_FULL_N - CELLW_MIN_N)

# ══════════════════════════════════════════════════════════════════════
#  SJALFSVOKTUN
#
#  Jolly keyrir 24x a dag en vid litum a hana stopult. Villur sem koma
#  upp kl 3 um nott hafa adur legid odagreindar i marga daga - tvofalda
#  leidrettingin, 24-klst gamli METAR, tapadar keyrslur.
#
#  Her safnar hun vidvorunum i gegnum keyrsluna og prentar STODU-blokk
#  EFST i loggnum. Ein lina til ad lita a: "OK" eda listi af thvi sem
#  tharf ad skoda. Hun man lika sidustu keyrslur (health.json) svo hun
#  geti greint THROUN - t.d. restbias sem vex jafnt og thett.
# ══════════════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════════════
#  [VOKTUN]  SJALFSVOKTUN
#  Vidvaranir, STODU-blokk, souguminni milli keyrslna (health.json).
# ═══════════════════════════════════════════════════════════════════════

_HEALTH = []          # vidvaranir thessarar keyrslu

def warn(msg, alvarlegt=False):
    """Skrair vidvorun sem birtist efst i loggnum."""
    _HEALTH.append(("!!" if alvarlegt else " *", msg))

def health_history(cur):
    """
    Vistar lykiltolur og ber saman vid fyrri keyrslur.
    Skilar lista af throunar-vidvorunum.
    """
    path = DATA_DIR / "health.json"
    st = load_json(path, {"runs": []})
    out = []
    prev = st.get("runs", [])

    # Restbias sem VEX jafnt og thett er merki um jakvaeda afturvirkni -
    # nakvaemlega thad sem tvofalda leidrettingin olli. Grip thad snemma.
    for var in ("hiti", "vindur", "att", "sky"):
        seq = [r.get("rb", {}).get(var) for r in prev[-3:]]
        seq = [abs(x) for x in seq if x is not None]
        now_v = abs(cur.get("rb", {}).get(var) or 0.0)
        if len(seq) >= 3 and now_v > 0.05:
            if all(seq[i] < seq[i+1] for i in range(len(seq)-1)) and now_v > seq[-1]:
                out.append(f"restbias {var} VEX jafnt og thett "
                           f"({' -> '.join(f'{x:.2f}' for x in seq)} -> {now_v:.2f})")

    # Engin ny por lengi = kerfid laerir ekki
    no_new = 0
    for r in reversed(prev):
        if r.get("np", 0) > 0: break
        no_new += 1
    if cur.get("np", 0) == 0 and no_new >= 6:
        out.append(f"engin ny por i {no_new+1} keyrslur - laerir ekki")

    st["runs"] = (prev + [cur])[-40:]
    save_json(path, st)
    return out

def health_block():
    """STODU-blokkin sem fer EFST i loggnum."""
    if not _HEALTH:
        return "STADA  OK - ekkert athugavert\n"
    alv = sum(1 for t, _ in _HEALTH if t == "!!")
    hdr = (f"STADA  {len(_HEALTH)} ATRIDI"
           + (f" ({alv} ALVARLEG)" if alv else "") + ":")
    lines = [hdr] + [f"  {t} {m}" for t, m in _HEALTH]
    return "\n".join(lines) + "\n"

def corrected_member(model, m, bs, cell, var, raw):
    """
    NAKVAEMLEGA sama leidretting og spain notar - fyrir hverja breytu.

    [MIKILVAEGT] Sky fer EKKI i gegnum einfalda samlagningu heldur
    correct_cloud() sem er flokkabundid OG klemmir i 0-100. Adur notudu
    sannleiksmaelirinn og krufningin einfalda samlagningu og fengu tha
    NEIKVAEDA skyjahulu (-34.8%) sem er edlisfraedilega omoguleg. Thad
    var gervi i maelitaekinu, ekki villa i spanni - en thad let
    thrihyrningsvornina hropa ad osekju.

    Vindur er klemmdur vid 0 og att vafid i 0-360, eins og i spanni.
    """
    if raw is None:
        return None
    if var == "sky":
        return correct_cloud(raw, model, m, bs)
    gen = ((model.get("bias", {}).get(m, {}) or {})
           .get(bs) or {}).get(var, 0.0) or 0.0
    b = member_bias(model, m, bs, cell, var, gen)
    if var == "att":
        return wrap360(raw + b)
    if var == "vindur":
        return max(0.0, raw + b)
    return raw + b

def member_bias(model, m, bs, cell, var, general):
    """
    Bias sem er raunverulega lagt a medlim. Ein leid inn - svo
    sannleiksmaelirinn geti notad NAKVAEMLEGA sama utreikning og spain.
    """
    if not APPLY_MEMBER_BIAS.get(var, True):
        return 0.0
    return cond_bias_value(model, m, bs, cell, var, general)
FAIL_MIN_N   = 10      # ekki fella ut fyrr en nogu morg por
RECOVER_N    = 3       # samfelldar godar spar til ad koma aftur inn
RECOVER_TOL  = 1.5     # "god spa" = innan 1.5x af besta thann tima

# Undir thessu er MAE svo lag ad hlutfallsbati er merkingarlaus
# (samsvarar um thad bil maelinakvaemni stodvarinnar)
SKILL_FLOOR = {"hiti": 0.15, "vindur": 0.20, "att": 5.0,
               "urkoma": 0.05, "sky": 3.0}

# --- MET Norway (api.met.no) --------------------------------------------
# Skilmalar krefjast einkennandi User-Agent med tengilid. Almennur eda
# vantandi UA gefur 403 Forbidden - ekki haegingu. Hnit mest 4 aukastafir.
METNO_UA  = ("Jolly-Weather/2.1 "
             "(+https://github.com/Blodnasir10/jolly-weather)")
METNO_URL = ("https://api.met.no/weatherapi/locationforecast/2.0/complete"
             f"?lat={LAT:.4f}&lon={LON:.4f}&altitude=23")   # BIEG er i 23 m

# HARMONIE-kerfid er a 2 km yfir Island, hnattlikonin a 9-25 km
# Bonus SER FYRIR HVERJA BREYTU. Uppl0usnarforskotid a 2 km gildir fyrir
# hita og vind - en HARMONIE-skyjahulan er ekki maeling heldur thydd ur
# islenskum vedurtexta ("skyjad" -> 70%), svo hun faer engan bonus.
# Sama gildir um vindatt sem kemur sem bokstafir (22.5 grada upplausn).
MODEL_BONUS = {
    "hiti":   {"harmonie": 1.20, "dmi": 1.15, "knmi": 1.10},
    "vindur": {"harmonie": 1.15, "dmi": 1.15, "knmi": 1.10},
    "urkoma": {"harmonie": 1.10, "dmi": 1.15, "knmi": 1.10},
    "sky":    {"dmi": 1.15, "knmi": 1.10},     # harmonie: texti, enginn bonus
    # HARMONIE-attin kemur sem bokstafir (22.5 gr upplausn) - enginn bonus
    "att":    {"dmi": 1.15, "knmi": 1.10},
}

HOURLY_VARS = ",".join([
    "temperature_2m", "dew_point_2m", "relative_humidity_2m",
    "windspeed_10m", "winddirection_10m", "windgusts_10m",
    "precipitation", "weathercode",
    "cloud_cover", "cloud_cover_low", "cloud_cover_mid", "cloud_cover_high",
    "visibility", "cape", "is_day",
    "surface_pressure",          # fyrir thrystiþroun (urkomuskilyrding)
])

# --- LOGGUN ----------------------------------------------------------------
# ═══════════════════════════════════════════════════════════════════════
#  [VERKFAERI]  ALMENN VERKFAERI
#  Netkoll, skraarvinnsla, stardfraedi, hringlaga reikningur, timastimplar.
# ═══════════════════════════════════════════════════════════════════════

class Tee:
    """
    Prentar a stdout (svo Actions sjai thad) OG safnar i minni,
    svo loggin se vistud i repoinu. Actions eydir loggum eftir 90 dogum -
    thessi lifir jafn lengi sem repoid.
    """
    def __init__(self):
        self.lines = []

    def write(self, txt):
        sys.__stdout__.write(txt)
        self.lines.append(txt)

    def flush(self):
        sys.__stdout__.flush()

    def text(self):
        return "".join(self.lines)


# --- HJALPARFOLL -----------------------------------------------------------
def fetch_url(url, as_text=False, timeout=30, headers=None, with_meta=False):
    """
    Saekir slod. Med with_meta=True skilar (gogn, svarhofud) i stad gagna,
    og skilar (None, {"status": 304}) ef efnid hefur ekki breyst.
    """
    hdr = {"User-Agent": "Jolly-Weather/2.1"}
    if headers: hdr.update(headers)
    req = urllib.request.Request(url, headers=hdr)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa
            raw = r.read().decode("utf-8", errors="replace")
            data = raw if as_text else json.loads(raw)
            if with_meta:
                return data, {"status": r.status,
                              "last_modified": r.headers.get("Last-Modified"),
                              "expires": r.headers.get("Expires")}
            return data
    except urllib.error.HTTPError as e:
        if e.code == 304 and with_meta:
            return None, {"status": 304}
        raise

def load_json(path, default):
    if not path.exists():
        return default
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return default

def save_json(path, obj):
    with open(path, "w") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)

def mean(v):
    x = [a for a in v if a is not None]
    return sum(x) / len(x) if x else None

def mae(pairs):
    v = [(a, b) for a, b in pairs if a is not None and b is not None]
    return sum(abs(a - b) for a, b in v) / len(v) if v else None

def bias(pairs):
    """Skilar (spa - maeling). Positift = likanid ofmetur."""
    v = [(a, b) for a, b in pairs if a is not None and b is not None]
    return sum(b - a for a, b in v) / len(v) if v else None

def parse_t(s):
    """'2026-07-23T14:00' -> datetime (UTC)"""
    return datetime.strptime(s, "%Y-%m-%dT%H:00").replace(tzinfo=timezone.utc)

def fmt_t(dt):
    return dt.strftime("%Y-%m-%dT%H:00")

def wrap360(a):
    return a % 360.0

def ang_diff(fc, ob):
    """
    Formerkt hornaskekkja i [-180,180). 350 gr a moti 10 gr = +20, ekki -340.
    Thetta er astaedan fyrir thvi ad vindatt tharf sina eigin reikninga -
    venjulegt frádrag gefur rugl vid nordurpunktinn.
    """
    return ((fc - ob + 180.0) % 360.0) - 180.0

def circ_mae(pairs):
    """MAE fyrir horn - medaltal af algildri hornaskekkju."""
    v = [(o, f) for o, f in pairs if o is not None and f is not None]
    if not v: return None
    return sum(abs(ang_diff(f, o)) for o, f in v) / len(v)

def circ_bias(pairs):
    """
    Kerfisbundid vik i hornum, reiknad sem hringmedaltal af skekkjunni.
    Positift = likanid snyr attinni rangsaelis vid raunveruleikann.
    """
    v = [(o, f) for o, f in pairs if o is not None and f is not None]
    if not v: return None
    errs = [math.radians(ang_diff(f, o)) for o, f in v]
    ss = sum(math.sin(e) for e in errs) / len(errs)
    cs = sum(math.cos(e) for e in errs) / len(errs)
    return math.degrees(math.atan2(ss, cs))

def deg_to_dir(d):
    if d is None: return None
    dirs = ["N","NNA","NA","ANA","A","ASA","SA","SSA",
            "S","SSV","SV","VSV","V","VNV","NV","NNV"]
    return dirs[round(d / 22.5) % 16]

def dir_to_deg(d):
    m = {"N":0,"NNA":22.5,"NA":45,"ANA":67.5,"A":90,"ASA":112.5,"SA":135,
         "SSA":157.5,"S":180,"SSV":202.5,"SV":225,"VSV":247.5,"V":270,
         "VNV":292.5,"NV":315,"NNV":337.5,
         "NNE":22.5,"NE":45,"ENE":67.5,"E":90,"ESE":112.5,"SE":135,
         "SSE":157.5,"SSW":202.5,"SW":225,"WSW":247.5,"W":270,"WNW":292.5,
         "NW":315,"NNW":337.5}
    return m.get(str(d).strip().upper())

def beaufort(ms):
    if ms is None: return None
    lim = [0.5,1.6,3.4,5.5,8.0,10.8,13.9,17.2,20.8,24.5,28.5,32.7]
    for i, l in enumerate(lim):
        if ms < l: return i
    return 12

def lead_interp(h):
    """
    Skilar (nedra_holf, efra_holf, hlutfall) fyrir linulega bruun.
    Bias vex jafnt med spalengd, svo ad nota naesta holf gefur stall:
    spa vid 9 klst notar 6-klst bias en aetti ad vera naer 12-klst.
    Bruun faer ~93% af thvi sem finni holf gefa, an thess ad deila gognum.
    """
    if h <= LEAD_BUCKETS[0]:
        return str(LEAD_BUCKETS[0]), str(LEAD_BUCKETS[0]), 0.0
    if h >= LEAD_BUCKETS[-1]:
        return str(LEAD_BUCKETS[-1]), str(LEAD_BUCKETS[-1]), 0.0
    for i in range(len(LEAD_BUCKETS) - 1):
        lo, hi = LEAD_BUCKETS[i], LEAD_BUCKETS[i + 1]
        if lo <= h <= hi:
            f = (h - lo) / (hi - lo)
            return str(lo), str(hi), f
    return str(LEAD_BUCKETS[-1]), str(LEAD_BUCKETS[-1]), 0.0


def blend2(lo_val, hi_val, f, angle=False):
    """Bruar milli tveggja gilda. Horn eru bruud hringlaga."""
    if lo_val is None: return hi_val
    if hi_val is None: return lo_val
    if not angle:
        return lo_val * (1 - f) + hi_val * f
    d = ang_diff(hi_val, lo_val)
    return wrap360(lo_val + d * f)


def lead_bucket(h):
    """Naesta spalengdarhólf fyrir spalengd h (klst)."""
    if h <= 2:  return 1
    if h <= 4:  return 3
    if h <= 9:  return 6
    if h <= 18: return 12
    if h <= 36: return 24
    return 48

# --- TAKNAVAL --------------------------------------------------------------
# ═══════════════════════════════════════════════════════════════════════
#  [TAKN]  TAKN OG LYSINGAR
#  Hvada takn og ordalag birtist a vefnum fyrir gefnar adstaedur.
# ═══════════════════════════════════════════════════════════════════════

def determine_icon(cloud, precip, temp, is_day, vis, wind, cape=None):
    dn = "day" if is_day else "night"
    p  = precip or 0
    if vis is not None and vis < 1000:
        return "fog" if vis < 400 else f"fog-{dn}"
    if (temp is not None and temp < 1 and wind is not None and wind > 10
            and p < 0.2 and vis is not None and vis < 5000):
        return "extreme-snow"
    if cape is not None and cape > 500 and p > 1.0:
        return f"thunderstorms-{dn}-rain" if (cloud is not None and cloud < 85) \
               else "thunderstorms-rain"
    if p > 0.05:
        if   temp is None:  pt = "rain"
        elif temp <= -0.5:  pt = "snow"
        elif temp <= 2.0:   pt = "sleet"
        else:               pt = "rain"
        showery = cloud is not None and cloud < 80
        if pt == "rain" and p < 0.25 and not showery: return "drizzle"
        if p > 2.5: return f"extreme-{pt}"
        if showery: return f"partly-cloudy-{dn}-{pt}"
        return f"overcast-{pt}"
    if vis is not None and vis < 5000: return "mist"
    c = cloud if cloud is not None else 0
    if c >= 95: return "overcast"
    if c >= 80: return f"mostly-cloudy-{dn}"
    if c >= 55: return f"half-cloudy-{dn}"
    if c >= 30: return f"mostly-clear-{dn}"
    if c >= 10: return f"partly-cloudy-{dn}"
    return f"clear-{dn}"

def describe(cloud, precip, temp, vis, wind, cape=None):
    p = precip or 0
    if vis is not None and vis < 1000:
        return "Frostþoka" if (temp is not None and temp < 0) else "Þoka"
    if (temp is not None and temp < 1 and wind is not None and wind > 10
            and p < 0.2 and vis is not None and vis < 5000):
        return "Skafrenningur"
    if cape is not None and cape > 500 and p > 1.0:
        return "Þrumuveður"
    if p > 0.05:
        showery = cloud is not None and cloud < 80
        if temp is not None and temp <= -0.5:
            if showery:  return "Él"
            if p > 2.5:  return "Mikil snjókoma"
            return "Snjókoma"
        if temp is not None and temp <= 2.0:
            return "Slydduél" if showery else "Slydda"
        if p < 0.25 and not showery: return "Súld"
        if showery:  return "Skúrir"
        if p > 2.5:  return "Mikil rigning"
        return "Rigning"
    if vis is not None and vis < 5000: return "Mistur"
    c = cloud if cloud is not None else 0
    if c >= 95: return "Alskýjað"
    if c >= 80: return "Að mestu skýjað"
    if c >= 55: return "Hálfskýjað"
    if c >= 30: return "Skýjað að hluta"
    if c >= 10: return "Léttskýjað"
    return "Heiðskírt"

# Traust a SPADA vindatt eftir spalengd. Skilyrt bias velur reit eftir
# spadri att - en su spa er ovissari eftir thvi sem lengra er spad. A 48
# klst getur attin verid ollu skokk og tha veljum vid RANGAN reit og
# beitum rangri leidrettingu. Thess vegna veikjum vid skilyrt bias med
# spalengd: full ahrif <= 6 klst (attin thekkist vel), fjarandi eftir thad.
# ═══════════════════════════════════════════════════════════════════════
#  [BIAS]  BIAS-LEIDRETTING (hiti / vindur / att)
#  Skilyrt bias eftir reit, shrinkage, spalengdartraust. member_bias() er
#  EINA leidin inn - baedi spain og sannleiksmaelirinn nota hana.
# ═══════════════════════════════════════════════════════════════════════

COND_LEAD_TRUST = {"1": 1.00, "3": 1.00, "6": 0.90,
                   "12": 0.65, "24": 0.40, "48": 0.20}

def cond_bias_value(model, m, bs, cell, var, general):
    """
    Skilyrt bias fyrir reit 'cell' og breytu 'var', blandad vid almenna
    bias-id 'general' med tvennskonar shrinkage:
      1) gagna-shrinkage: w_n = n/(n+K) - thynnri reitur, minna traust
      2) spalengdar-shrinkage: w_lead - lengri spalengd, minna traust a
         SPADA att sem valdi reitinn
    Ef reiturinn er tomur eda naest ekki i hann er almenna bias-id notad.
    Tryggir ad skilyrt bias verdi ALDREI verra en oskilyrt.
    """
    if cell is None:
        return general
    c = (model.get("cond_bias", {}).get(m, {}).get(bs, {}) or {}).get(cell)
    if not c:
        return general
    e = c.get(var)
    if not e or e["n"] < COND_MIN_N:
        return general
    # b_reitur er MEDALSKEKKJA (spa-maeling); leidrettingin er neikvaed
    measured = -(e["sum"] / e["n"])
    n = e["n"]
    w_n    = n / (n + COND_SHRINK_K)
    w_lead = COND_LEAD_TRUST.get(bs, 0.5)
    w = w_n * w_lead
    return w * measured + (1 - w) * general

# --- URKOMUTHROSKULDUR ---------------------------------------------------
# Likon spa oft litilli urkomu sem aldrei fellur ("drizzle bias"). Ad laera
# adeins KVARDA lagar thad ekki - flot 0.2 mm allan solarhringinn faer godan
# heildarkvarda en er gagnslaus. Vid laerum thvi throskuld: undir honum er
# spain sett i null.
#
# ATH: throskuldurinn er valinn a F1, EKKI MAE. MAE heldur afram ad lakka
# eftir thvi sem throskuldurinn haekkar (a endanum "alltaf thurrt" = lagsta
# MAE thegar urkoma er strjal) - en tha missir spain raunverulega urkomu.
# F1 jafnvaegir "missa ekki" og "spa ekki folsku".
PRECIP_GRID   = [0.0, 0.05, 0.10, 0.15, 0.20, 0.30, 0.40, 0.50, 0.70, 1.00]
PRECIP_WET    = 0.05     # mm - hvad telst "urkoma" vid mat
PRECIP_MIN_N  = 40       # por adur en laerdur throskuldur er notadur

# ═══════════════════════════════════════════════════════════════════════
#  [URKOMA]  URKOMA
#  Throskuldur fintilltur a F1 (ekki MAE), kvardi, og eigin reitur:
#  vindatt x THRYSTITHROUN, thvi urkoma raest af laegdum en ekki
#  solarhringssveiflu.
# ═══════════════════════════════════════════════════════════════════════

def update_precip_threshold(model, m, bs, pairs):
    """Uppfaerir tp/fp/fn talningar fyrir hvern kandidat-throskuld."""
    if not pairs: return
    store = model.setdefault("precip_thr", {}) \
                 .setdefault(m, {}).setdefault(bs, {})
    for ob, fcv in pairs:
        if ob is None or fcv is None: continue
        wet_ob = ob >= PRECIP_WET
        for t in PRECIP_GRID:
            k = f"{t:.2f}"
            c = store.setdefault(k, {"tp": 0, "fp": 0, "fn": 0, "n": 0})
            wet_fc = fcv >= max(t, PRECIP_WET)
            if   wet_fc and wet_ob: c["tp"] += 1
            elif wet_fc:            c["fp"] += 1
            elif wet_ob:            c["fn"] += 1
            c["n"] += 1

def precip_threshold(model, m, bs):
    """Throskuldur sem hamarkar F1. Fellur a 0 ef gogn eru of thunn."""
    store = (model.get("precip_thr", {}).get(m, {}) or {}).get(bs)
    if not store: return 0.0
    best_t, best_f1 = 0.0, -1.0
    for k, c in store.items():
        if c["n"] < PRECIP_MIN_N: continue
        den = 2 * c["tp"] + c["fp"] + c["fn"]
        f1 = (2 * c["tp"] / den) if den else 0.0
        if f1 > best_f1:
            best_f1, best_t = f1, float(k)
    return best_t if best_f1 >= 0 else 0.0

def apply_precip(raw, scale, thr):
    """Setur i null undir throskuldi, kvardar annars."""
    if raw is None: return None
    if raw < thr:   return 0.0
    return round(max(0.0, raw * scale), 2)


# ═══════════════════════════════════════════════════════════════════════
#  [SKY]  SKYJAHULA
#  Flokkabundin leidretting (EKKI einfold samlagning eins og hinar breyturnar).
#  total_cloud() = HAMARKSSKORUN: lasky 10% + hasky 50% er 50%, ekki 60%.
# ═══════════════════════════════════════════════════════════════════════

def correct_cloud(raw, model, m, bs):
    """
    Leidrettir skyjahulu med flokkabundnu viki. Fellur aftur a flata
    bias-leidrettingu ef flokkurinn hefur ekki nog gogn, og klemmir
    nidurstoduna i 0-100.
    """
    if raw is None:
        return None
    flat = model["bias"][m][bs].get("sky", 0.0)
    fk   = cloud_class(raw)
    e    = (model.get("cloud_map", {}).get(m, {}).get(bs, {}) or {}).get(fk)
    if e and e.get("n", 0) >= MIN_CLOUD_N:
        fc_mean  = e["fc_sum"]  / e["n"]
        obs_mean = e["obs_sum"] / e["n"]
        shift    = obs_mean - fc_mean
    else:
        shift = flat
    return int(round(min(100.0, max(0.0, raw + shift))))


def total_cloud(low, mid, high, fallback=None):
    """
    Heildarskyjahula ur lagskiptingu med HAMARKSSKORUN.

    Sky leggjast EKKI saman. Ef lasky eru 10% og hasky 50% er heildin 50%,
    ekki 60% - hasky liggja OFAN a laskyjum sed fra jordu, svo their deila
    sama himni. Retta samlagningin er hamark, ekki summa.

    Thetta samsvarar lika thvi sem METAR gerir: OKTU-flokkarnir eru
    UPPSAFNADIR og vid tokum max af logunum. Adur notudum vid 'cloud_cover'
    fra likonunum sem nota HAMARKS-SLEMBISKORUN (max-random overlap) og
    skilar KERFISBUNDID HAERRI tolu en METAR gaeti nokkurn tima maelt.
    Nu nota badir sama reglu og samanburdurinn verdur rettur.
    """
    lags = [x for x in (low, mid, high) if x is not None]
    if not lags:
        return fallback
    return max(lags)

def cloud_class(pct):
    if pct is None: return None
    if pct < 10: return "heidskirt"
    if pct < 30: return "lettskyjad"
    if pct < 55: return "skyjad_hluta"
    if pct < 80: return "halfskyjad"
    if pct < 95: return "mestu_skyjad"
    return "alskyjad"

# --- 1. METAR --------------------------------------------------------------
# ═══════════════════════════════════════════════════════════════════════
#  [MAELING]  RAUNMAELINGAR - METAR OG VEDUR.IS
#  METAR (sky, oktur) og api.vedur.is stod 4271 (hiti/vindur/att/thrystingur).
# ═══════════════════════════════════════════════════════════════════════

CLOUD_OKTAS = {"FEW": 19, "SCT": 44, "BKN": 75, "OVC": 100}

def parse_metar(line):
    try:
        if ICAO not in line[:24]: return None
        m = re.search(r"\b(\d{2})(\d{2})(\d{2})Z\b", line)
        if not m: return None
        day, hh = int(m.group(1)), int(m.group(2))
        now = datetime.now(timezone.utc)
        yr, mo = now.year, now.month
        if day > now.day + 5:
            mo -= 1
            if mo == 0: mo, yr = 12, yr - 1
        try:
            dt = datetime(yr, mo, day, hh, 0, tzinfo=timezone.utc)
        except ValueError:
            return None

        layers = [{"type": c.group(1), "base_ft": int(c.group(2)) * 100,
                   "cb": c.group(3) or None}
                  for c in re.finditer(r"\b(FEW|SCT|BKN|OVC)(\d{3})(CB|TCU)?\b", line)]

        if re.search(r"\b(SKC|CLR|NSC|NCD|CAVOK)\b", line):
            cover, base = 0, None
        elif layers:
            cover = max(CLOUD_OKTAS[l["type"]] for l in layers)
            base  = min(l["base_ft"] for l in layers)
        else:
            vv = re.search(r"\bVV(\d{3})\b", line)
            cover, base = (100, int(vv.group(1)) * 100) if vv else (None, None)

        vis = 10000 if "CAVOK" in line else None
        if vis is None:
            vm = re.search(r"\s(\d{4})\s", line)
            if vm:
                vis = int(vm.group(1))
                if vis == 9999: vis = 10000

        temp = dew = None
        tm = re.search(r"\s(M?\d{2})/(M?\d{2})\s", line)
        if tm:
            cv = lambda s: -int(s[1:]) if s.startswith("M") else int(s)
            temp, dew = cv(tm.group(1)), cv(tm.group(2))

        wkt = wdir = None
        wm = re.search(r"\b(\d{3}|VRB)(\d{2,3})(G\d{2,3})?KT\b", line)
        if wm:
            wdir = None if wm.group(1) == "VRB" else int(wm.group(1))
            wkt  = int(wm.group(2))

        return {"time": fmt_t(dt), "cloud_cover": cover, "cloud_base_ft": base,
                "cloud_layers": layers, "visibility": vis, "temperature": temp,
                "dewpoint": dew,
                "windspeed": round(wkt * 0.514444, 1) if wkt is not None else None,
                "winddirection": wdir}
    except Exception:
        return None

def fetch_metar():
    print(f"METAR {ICAO}:")
    url = f"https://aviationweather.gov/api/data/metar?ids={ICAO}&format=raw&hours=24"
    try:
        raw = fetch_url(url, as_text=True, timeout=20)
        obs = [p for p in (parse_metar(l) for l in raw.strip().split("\n") if l.strip()) if p]
        if not obs: raise ValueError("engar faerslur")

        # [MIKILVAEGT] aviationweather skilar faerslum i OSKILGREINDRI rod -
        # i raun NYJUSTU FYRST. Adur tokum vid obs[-1] sem "nyjustu" og
        # fengum tha ELSTU faersluna, nakvaemlega 24 klst gamla. Jolly laerdi
        # thvi skyjahulu af GAERDEGINUM og pardi hana vid spar dagsins.
        # Nu rodum vid EFTIR TIMA svo rodin i svarinu skipti engu mali.
        obs.sort(key=lambda o: o["time"])
        l = obs[-1]

        # Vidvorun ef nyjasta faerslan er ovaenta gomul (t.d. stodin nidri)
        try:
            age_h = (datetime.now(timezone.utc)
                     - parse_t(l["time"])).total_seconds() / 3600.0
        except Exception:
            age_h = None
        aldur = f" | aldur {age_h:.1f} klst" if age_h is not None else ""
        print(f"  OK {len(obs)} faerslur | nyjust {l['time']} "
              f"sky={l['cloud_cover']}% botn={l['cloud_base_ft']}ft{aldur}")
        if age_h is not None and age_h > 3:
            print(f"  VARUD: nyjasti METAR er {age_h:.1f} klst gamall "
                  f"- skyjagogn gaetu verid urelt")
            warn(f"METAR {age_h:.1f} klst gamall (aetti <1) - "
                 f"skyjalaerdomur i haettu", alvarlegt=(age_h > 12))
        return obs
    except Exception as e:
        print(f"  VILLA: {e}")
        return []

# --- 2. MAELINGAR ----------------------------------------------------------
def fetch_and_store_observations(metar_obs):
    print("MAELING stod 4271 (Egilsstadaflugvollur):")
    path = DATA_DIR / "obs_history.json"
    hist = load_json(path, [])
    by_t = {h["time"]: h for h in hist}
    fresh = []   # timapunktar sem uppfaerdust nuna

    # OPINBERT API Vedurstofunnar (api.vedur.is). Kom i stad apis.is sem
    # var thridja-adila millilidur med utrunnid vottord og 502-villur.
    # Stodin heitir 4271 i thessu API (sjalfvirk flugvallarstod) en 571 i
    # eldri kerfum - sami stadur, Egilsstadaflugvollur.
    # Reitir: t=hiti, f=vindur, fg=hvida, d=vindatt(gradur), d_txt=att(texti),
    #         r=urkoma, rh=raki, p=thrystingur, tx/tn=haest/laegst hiti.
    AWS_ID = 4271
    url = (f"https://api.vedur.is/weather/observations/aws/hour/latest"
           f"?station_id={AWS_ID}")

    def _num(r, k):
        v = r.get(k)
        if v is None:
            return None
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    got_aws = False
    try:
        data = fetch_url(url)
        # Svar er fylki af stodvum (her bara ein). Finna 4271.
        rows = data if isinstance(data, list) else data.get("results", [])
        row = next((x for x in rows if x.get("station") == AWS_ID), None)
        if row is None and rows:
            row = rows[0]
        if row:
            # Timi kemur t.d. "2026-08-14T07:00:00" (UTC)
            raw_t = str(row.get("time", "")).strip().replace(" ", "T")
            dt = datetime.fromisoformat(raw_t)
            t  = fmt_t(dt.replace(tzinfo=timezone.utc))
            # Vindatt: nota gradur (d) beint ef til, annars texta (d_txt)
            wd = _num(row, "d")
            if wd is None:
                wd = dir_to_deg(row.get("d_txt", ""))
            rec = by_t.get(t, {"time": t})
            rec.update({"temperature": _num(row, "t"),
                        "windspeed": _num(row, "f"),
                        "windgust": _num(row, "fg"),
                        "winddirection": wd,
                        "precipitation": _num(row, "r"),
                        "humidity": _num(row, "rh"),
                        "pressure": _num(row, "p"),
                        "temp_max": _num(row, "tx"),
                        "temp_min": _num(row, "tn"),
                        "dewpoint": _num(row, "td"),
                        "source": "vedur.is-4271"})
            by_t[t] = rec
            fresh.append(t)
            got_aws = True
            print(f"  OK {t} | hiti={rec['temperature']}"
                  f" vindur={rec['windspeed']} att={rec['winddirection']}")
        else:
            print("  Engar nidurstodur fra api.vedur.is")
    except Exception as e:
        print(f"  VILLA api.vedur.is: {e}")

    if not got_aws:
        print("  (nota METAR skyjagogn eingongu thennan hringinn)")
        warn("engin maeling fra stod 4271 - hiti/vindur laerast ekki")

    n_metar = 0
    for m in metar_obs:
        t   = m["time"]
        rec = by_t.get(t, {"time": t})
        for k in ("cloud_cover", "cloud_base_ft", "cloud_layers",
                  "visibility", "dewpoint"):
            rec[k] = m[k]
        for k in ("temperature", "windspeed", "winddirection"):
            if rec.get(k) is None: rec[k] = m[k]
        rec["has_metar"] = True
        by_t[t] = rec
        if t not in fresh: fresh.append(t)
        n_metar += 1
    if n_metar:
        print(f"  METAR skyjagogn a {n_metar} timapunkta")

    hist = sorted(by_t.values(), key=lambda x: x["time"])[-OBS_HISTORY_HOURS:]
    save_json(path, hist)
    n_cloud = sum(1 for h in hist if h.get("cloud_cover") is not None)
    print(f"  {len(hist)} maelingar geymdar ({n_cloud} med skyjahulu)")
    return hist, fresh

# --- 3. SPAGJAFAR ----------------------------------------------------------
# ═══════════════════════════════════════════════════════════════════════
#  [SOKN]  GAGNASOKN FRA GJOFUM
#  Open-Meteo (7 likon), MET Norway, HARMONIE ur XML Vedurstofunnar.
# ═══════════════════════════════════════════════════════════════════════

def fetch_forecasts():
    print("OPEN-METEO:")
    url = (f"https://api.open-meteo.com/v1/forecast"
           f"?latitude={LAT}&longitude={LON}"
           f"&hourly={HOURLY_VARS}"
           f"&models={','.join(MODELS.values())}"
           f"&past_days=1&forecast_days=6"
           f"&timezone=UTC&wind_speed_unit=ms")
    try:
        d = fetch_url(url)
        print(f"  OK {len(d['hourly']['time'])} timapunktar")
        for k, api in MODELS.items():
            t = d["hourly"].get(f"temperature_2m_{api}", [])
            n = len([x for x in t if x is not None])
            print(f"    {k:6s} {n:4d} gildi" + ("" if n else "   <-- ENGIN GOGN"))
        return d
    except Exception as e:
        print(f"  VILLA: {e}")
        return None

WEATHER_TO_CLOUD = {
    "heiðskírt": 5, "léttskýjað": 30, "hálfskýjað": 50, "skýjað": 70,
    "alskýjað": 95, "þoka": 100, "rigning": 90, "skúrir": 70,
    "snjókoma": 90, "él": 70, "slydda": 90, "súld": 85,
}

def fetch_metno():
    """
    Saekir spa fra MET Norway (Vedurstofa Noregs) locationforecast 2.0.

    'complete' gefur skyjahulu i threm haedum, thokuhlutfall og daggarmark -
    einmitt thaer breytur sem vid notum i skyjaspana.

    Skilmalar api.met.no:
      - Einkennandi User-Agent med tengilid, annars 403
      - Hnit mest 4 aukastafir, annars 403
      - If-Modified-Since svo vid saekjum ekki obreytt efni

    Vid geymum THATTAD nidurstodu i skyndiminni (ekki hraa svarid) svo
    skrain se litil, og notum hana ef svarid er 304 Not Modified.
    """
    print("MET NORWAY (api.met.no):")
    cache_path = DATA_DIR / "metno_cache.json"
    cache = load_json(cache_path, {})

    headers = {"User-Agent": METNO_UA}
    if cache.get("last_modified"):
        headers["If-Modified-Since"] = cache["last_modified"]

    try:
        data, meta = fetch_url(METNO_URL, headers=headers, with_meta=True)
    except urllib.error.HTTPError as e:
        hint = ""
        if e.code == 403:
            hint = " (User-Agent eda hnitanakvaemni - sja skilmala)"
        elif e.code == 429:
            hint = " (of margar beidnir)"
        print(f"  VILLA HTTP {e.code}{hint}")
        if cache.get("hourly"):
            print(f"  Nota skyndiminni ({len(cache['hourly']['time'])} timapunktar)")
            return {"hourly": cache["hourly"]}
        return None
    except Exception as e:
        print(f"  VILLA: {e}")
        if cache.get("hourly"):
            print("  Nota skyndiminni")
            return {"hourly": cache["hourly"]}
        return None

    if meta.get("status") == 304:
        if cache.get("hourly"):
            print(f"  304 obreytt - skyndiminni "
                  f"({len(cache['hourly']['time'])} timapunktar)")
            return {"hourly": cache["hourly"]}
        print("  304 en ekkert skyndiminni")
        return None

    try:
        series = data["properties"]["timeseries"]
    except (KeyError, TypeError):
        print("  Ovaent gagnasnid")
        return None

    h = {"time": [], "temperature": [], "windspeed": [], "winddirection": [],
         "precipitation": [], "cloud_cover": [], "cloud_low": [],
         "cloud_mid": [], "cloud_high": [], "fog": [], "dewpoint": []}

    for e in series:
        t = e.get("time", "")
        if not t: continue
        try:
            dt = datetime.fromisoformat(t.replace("Z", "+00:00"))
        except ValueError:
            continue
        det = (e.get("data", {}).get("instant", {}).get("details", {}) or {})
        # Urkoma er i next_1_hours; naest 6 klst eftir ~2.5 daga
        nxt = e.get("data", {}).get("next_1_hours") or {}
        prec = (nxt.get("details", {}) or {}).get("precipitation_amount")
        if prec is None:
            n6 = e.get("data", {}).get("next_6_hours") or {}
            p6 = (n6.get("details", {}) or {}).get("precipitation_amount")
            prec = round(p6 / 6.0, 2) if p6 is not None else None

        h["time"].append(fmt_t(dt.astimezone(timezone.utc)))
        h["temperature"].append(det.get("air_temperature"))
        h["windspeed"].append(det.get("wind_speed"))
        h["winddirection"].append(det.get("wind_from_direction"))
        h["precipitation"].append(prec)
        h["cloud_cover"].append(det.get("cloud_area_fraction"))
        h["cloud_low"].append(det.get("cloud_area_fraction_low"))
        h["cloud_mid"].append(det.get("cloud_area_fraction_medium"))
        h["cloud_high"].append(det.get("cloud_area_fraction_high"))
        h["fog"].append(det.get("fog_area_fraction"))
        h["dewpoint"].append(det.get("dew_point_temperature"))

    if not h["time"]:
        print("  Engir timapunktar")
        return None

    save_json(cache_path, {"last_modified": meta.get("last_modified"),
                           "expires": meta.get("expires"),
                           "fetched": datetime.now(timezone.utc).isoformat(),
                           "hourly": h})
    n_cloud = len([x for x in h["cloud_cover"] if x is not None])
    # Skref eru 1 klst i ~2.5 daga, sidan 6 klst
    print(f"  OK {len(h['time'])} timapunktar ({n_cloud} med skyjahulu)")
    return {"hourly": h}

def fetch_harmonie():
    print("HARMONIE (Vedurstofa):")
    url = (f"https://xmlweather.vedur.is/?op_w=xml&type=forec"
           f"&lang=is&view=xml&ids={STATION_ID}")
    try:
        root = ET.fromstring(fetch_url(url, as_text=True))
        h = {"hourly": {"time": [], "temperature": [], "windspeed": [],
                        "winddirection": [], "precipitation": [], "cloud_cover": []}}
        for fc in (root.findall(".//forecast") or root.findall("forecast")):
            ft = fc.get("ftime") or fc.findtext("ftime", "")
            if not ft: continue
            try:
                dt = datetime.strptime(ft.strip(), "%Y-%m-%d %H:%M:%S")
            except Exception:
                try:
                    dt = datetime.fromisoformat(ft.strip().replace(" ", "T"))
                except Exception:
                    continue
            dt = dt.replace(tzinfo=timezone.utc)
            def gv(tag):
                v = fc.get(tag) or fc.findtext(tag, "")
                try:
                    return float(v) if v and v.strip() not in ("", "-") else None
                except Exception:
                    return None
            h["hourly"]["time"].append(fmt_t(dt))
            h["hourly"]["temperature"].append(gv("T"))
            h["hourly"]["windspeed"].append(gv("F"))
            h["hourly"]["precipitation"].append(gv("R"))
            h["hourly"]["winddirection"].append(
                dir_to_deg(fc.get("D", "") or fc.findtext("D", "")))
            w  = (fc.get("W", "") or fc.findtext("W", "") or "").lower().strip()
            # [VILLA LAGFAERD v4.6] Adur: next(... if k in w) sem skiladi
            # FYRSTU samsvorun i ordabokarrod. "skyjad" er HLUTI af
            # "alskyjad" og kom a undan - svo ALSKYJAD fekk 70% i stad 95%
            # i hvert einasta skipti. Nu tokum vid LENGSTU samsvorun, sem
            # er alltaf su nakvaemasta.
            _hits = [(k, v) for k, v in WEATHER_TO_CLOUD.items() if k in w]
            cc = max(_hits, key=lambda kv: len(kv[0]))[1] if _hits else None
            h["hourly"]["cloud_cover"].append(cc)
            if not h["hourly"]["time"]: raise ValueError("engir timapunktar")
        nc = len([x for x in h["hourly"]["cloud_cover"] if x is not None])
        print(f"  OK {len(h['hourly']['time'])} timapunktar "
              f"({nc} med skyjahulu ur vedurtexta - grof)")
        return h
    except Exception as e:
        print(f"  VILLA: {e}")
        return None

# --- 4. GEYMA SPA TIL STADFESTINGAR ---------------------------------------
# ═══════════════════════════════════════════════════════════════════════
#  [SAFN]  SPASAFN - GEYMSLA TIL STADFESTINGAR
#  Geymir HRAA spa vid utgafu, lyklad a GILDISTIMA. Kjarninn i thvi ad
#  6-klst spa se borin saman vid maelingu 6 klst sidar.
# ═══════════════════════════════════════════════════════════════════════

def archive_forecast(fc, extras):
    """
    Skrifar HRAA likanaspa (an bias-leidrettingar) i forecast_archive.json
    fyrir thaer spalengdir sem vid stadfestum sidar.

    Uppbygging:
      { valid_time: { lead: { issue: str, models: { m: {t,w,p,c} } } } }
    """
    print("SPASAFN:")
    path = DATA_DIR / "forecast_archive.json"
    arch = load_json(path, {})

    now   = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    issue = fmt_t(now)
    ft    = fc["hourly"]["time"] if fc else []
    et    = {k: (v["hourly"]["time"] if v else [])
             for k, v in extras.items()}

    n_new = 0
    for lead in LEAD_BUCKETS:
        vt_dt = now + timedelta(hours=lead)
        vt    = fmt_t(vt_dt)
        models = {}

        if fc and vt in ft:
            i = ft.index(vt)
            for m, api in MODELS.items():
                def g(key):
                    a = fc["hourly"].get(f"{key}_{api}", [])
                    return a[i] if i < len(a) else None
                # Heildarhula med HAMARKSSKORUN ur logunum thremur, svo
                # hun se sambaerileg vid METAR. Fellur a 'cloud_cover'
                # likansins ef login vantar.
                rec = {"t": g("temperature_2m"), "w": g("windspeed_10m"),
                       "d": g("winddirection_10m"),
                       "p": g("precipitation"),
                       "c": total_cloud(g("cloud_cover_low"),
                                        g("cloud_cover_mid"),
                                        g("cloud_cover_high"),
                                        g("cloud_cover"))}
                if any(v is not None for v in rec.values()):
                    models[m] = rec

        for k, src in extras.items():
            if not src or vt not in et[k]: continue
            j = et[k].index(vt)
            def ge(key, _src=src, _j=j):
                a = _src["hourly"].get(key, [])
                return a[_j] if _j < len(a) else None
            rec = {"t": ge("temperature"), "w": ge("windspeed"),
                   "d": ge("winddirection"),
                   "p": ge("precipitation"),
                   "c": total_cloud(ge("cloud_low"), ge("cloud_mid"),
                                    ge("cloud_high"), ge("cloud_cover"))}
            if any(v is not None for v in rec.values()):
                models[k] = rec

        if models:
            slot = arch.setdefault(vt, {}).setdefault(str(lead),
                                    {"issue": issue, "models": {}})
            slot["issue"] = issue
            slot["models"] = models
            # is_day fyrir thennan gildistima (ur fyrsta likani sem hefur hann)
            if fc and vt in ft:
                idx = ft.index(vt)
                a = fc["hourly"].get("is_day", [])
                if idx < len(a) and a[idx] is not None:
                    slot["is_day"] = a[idx]
                # Thrystithroun (hPa/klst yfir 3 klst) fyrir urkomureitinn.
                # Geymt VID UTGAFU svo stadfestingin viti hvada adstaedur
                # spain att vid - alveg eins og is_day.
                pa = fc["hourly"].get("surface_pressure", [])
                if idx - 3 >= 0 and idx < len(pa) \
                   and pa[idx] is not None and pa[idx - 3] is not None:
                    slot["dp_h"] = round((pa[idx] - pa[idx - 3]) / 3.0, 3)
            n_new += 1

    # Hreinsa gamalt - stadfest eda utrunnid
    cutoff = fmt_t(now - timedelta(hours=ARCHIVE_KEEP_PAST))
    horizon = fmt_t(now + timedelta(hours=ARCHIVE_HORIZON + 2))
    before = len(arch)
    arch = {k: v for k, v in arch.items() if cutoff <= k <= horizon}

    save_json(path, arch)
    print(f"  Geymdi {n_new} spalengdir fyrir utgafu {issue}")
    print(f"  Safnid: {len(arch)} gildistimar (hreinsadi {before - len(arch)})")
    return arch

def archive_jolly(arch, fcast):
    """
    Skrair Jolly-spana i sama safn og medlimina, svo hun se stadfest
    med somu adferd. Thetta er kallad EFTIR make_forecast, thvi Jolly
    er ekki til fyrr en thyngdir og bias hafa verid notud.

    Vid skrum thad sem vid raunverulega birtum - ekki endurreiknad gildi.
    """
    if not fcast: return arch
    H = fcast["hourly"]
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    issue = fmt_t(now)
    n = 0
    for i, t in enumerate(H["time"]):
        lead = H["lead_hours"][i]
        if lead not in LEAD_BUCKETS: continue
        rec = {"t": H["temperature"][i], "w": H["windspeed"][i],
               "d": H["winddirection"][i],
               "p": H["precipitation"][i], "c": H["cloud_cover"][i]}
        # is_day er skilyrding - geymt a gildistima svo stadfesting viti thad
        arch.setdefault(t, {}).setdefault(str(lead), {}) \
            ["is_day"] = H["is_day"][i]
        if not any(v is not None for v in rec.values()): continue
        slot = arch.setdefault(t, {}).setdefault(str(lead),
                                                {"issue": issue, "models": {}})
        slot.setdefault("models", {})[JOLLY_KEY] = rec
        # [v5.1] Geyma REITINN sem thyngdir/bias voru RAUNVERULEGA valin
        # ut fra (spad att), svo stadfesting sanni Jolly a moti rettum
        # forsendum i stad thess ad endurreikna reit ur maeldri att.
        c = H.get("cell", [])
        if i < len(c) and c[i]:
            slot["cell"] = c[i]
        # [v5.2] DYPRI lagfaering: geyma SJALFAR THYNGDIRNAR sem voru
        # notadar thessa klukkustund. weights_cell er EMA sem uppfaerist
        # i HVERRI keyrslu (CELLW_LR=0.10) - jafnvel med rettum REIT
        # (v5.1) geta THYNGDIRNAR INNAN hans hafa breyst milli utgafu og
        # stadfestingar, thvi train-skrefid keyrir a milli. Med thvi ad
        # geyma NAKVAEMU thyngdirnar sjalfar lokast thetta gap alveg -
        # samanburdur vid stadfestingu notar SAMA reikning og Jolly gerdi.
        uw = H.get("used_weights", [])
        if i < len(uw) and uw[i]:
            slot["weights"] = uw[i]
        n += 1
    save_json(DATA_DIR / "forecast_archive.json", arch)
    print(f"  Jolly skrad i safnid: {n} spalengdir")
    return arch


# --- 5. STADFESTA OG THJALFA ----------------------------------------------
# ═══════════════════════════════════════════════════════════════════════
#  [LIKAN]  LIKANSKRAIN - UPPBYGGING, HLEDSLA, HREINSANIR
#  jolly_model.json: bias, thyngdir, cell_mae, skill. Einskiptis-hreinsanir.
# ═══════════════════════════════════════════════════════════════════════

def empty_bias():
    return {"hiti": 0.0, "vindur": 0.0, "att": 0.0,
            "sky": 0.0, "urkoma_scale": 1.0}

def empty_cond():
    """Skilyrt bias-safn: {reitur: {breyta: {sum, n}}}."""
    return {}

def init_model():
    return {
        "version": JOLLY_VERSION,
        "created": datetime.now(timezone.utc).isoformat(),
        "runs": 0,
        "verified_pairs": 0,
        "lead_buckets": LEAD_BUCKETS,
        # bias[likan][spalengd] = {hiti, vindur, sky, urkoma_scale}
        "bias": {m: {str(b): empty_bias() for b in LEAD_BUCKETS} for m in ALL_KEYS},
        # weights[breyta][spalengd][likan]
        "weights": {v: {str(b): {m: 1.0 / len(ALL_KEYS) for m in ALL_KEYS}
                        for b in LEAD_BUCKETS} for v in WEIGHT_VARS},
        # lead_mae[spalengd][likan] = {hiti, vindur, sky, n}
        "lead_mae": {str(b): {} for b in LEAD_BUCKETS},
        # skill[breyta][spalengd] = {jolly_mae, best_model, best_mae, skill}
        "skill": {v: {} for v in WEIGHT_VARS},
        # Restleidretting a Jolly sjalfri - jolly_bias[spalengd]
        "jolly_bias": {str(b): empty_bias() for b in LEAD_BUCKETS},
        # Skilyrt bias: cond_bias[likan][spalengd][reitur][breyta]={sum,n}
        "cond_bias": {},
        # cloud_map[likan][spalengd][flokkur] = {n, fc_sum, obs_sum}
        "cloud_map": {},
        "cloud_confusion": {},
        "verify_history": [],
        "last_updated": None,
    }

def migrate_model(old):
    """Faerir flott bias ur v1.x yfir i spalengdaskipt bias v2.0."""
    new = init_model()
    new["created"] = old.get("created", new["created"])
    new["runs"]    = old.get("training_days", 0)
    old_bias = old.get("biases", {})
    seeded = 0
    for m in ALL_KEYS:
        ob = old_bias.get(m)
        if not ob: continue
        for b in LEAD_BUCKETS:
            new["bias"][m][str(b)] = {
                "hiti":  float(ob.get("hiti", 0.0)),
                "vindur": float(ob.get("vindur", 0.0)),
                "sky":   float(ob.get("sky", 0.0)),
                "urkoma_scale": float(ob.get("urkoma_scale", 1.0)),
            }
        seeded += 1
    ow = old.get("weights", {}) or {}
    # Verja gegn skemmdri eda tomri skra
    ow = {k: v for k, v in ow.items()
          if isinstance(v, (int, float)) and v > 0}
    if ow:
        tot = sum(ow.values())
        if tot > 0:
            seed = {m: round(ow.get(m, 0.0) / tot, 4) for m in ALL_KEYS}
            for v in WEIGHT_VARS:
                for b in LEAD_BUCKETS:
                    new["weights"][v][str(b)] = dict(seed)
    new["migrated_from"] = old.get("version", "1.x")
    print(f"  Faerdi {seeded} likon ur v{new['migrated_from']} - "
          f"bias notad sem upphafsgildi fyrir allar spalengdir")
    return new

def load_model():
    path = DATA_DIR / "jolly_model.json"
    raw  = load_json(path, None)
    if raw is None:
        print(f"  Nytt likan v{JOLLY_VERSION}")
        return init_model()
    # [v4.9 LAGFAERT] ADUR var thessi bloklk gaett a bak vid
    # `version.startswith("2.") or startswith("3.")`. Utgafan er nu 4.x,
    # svo su gaett var DAUD - eldri hreinsanir hofdu thegar keyrt medan
    # utgafan var enn 2.x/3.x, en HVER NY hreinsun sem baettist vid eftir
    # ad utgafan for i 4.x GAT ALDREI KEYRT. Hvert flagg ver sig sjalft
    # (if not raw.get(flag)) svo utgafugaettin var ovarleg OG ohaefileg -
    # fjarlaegd svo framtida hreinsanir keyri afram an thess ad muna eftir
    # thessu.
    if True:
        # EINSKIPTIS-HREINSUN v3.0: gamla Jolly-maelingin i lead_mae er
        # menguð af spam fra thvi likanid var hálflaert (safnaðist fra
        # keyrslu 1). Medlimir eru endurmetnir jafnodum en gamla Jolly-
        # spain er fost i safninu. Vid nullstillum Jolly-MAE OG skill einu
        # sinni svo their byggist upp hreint fra v3.0 og skill endurspegli
        # NUVERANDI utgafu, ekki 333 keyrslna sogu.
        # v3.5: jolly_bias var blasid upp af tvofoldu leidrettingunni
        # (sky +9.5, vind -1.47 og VAXANDI). Nullstillum thad einu sinni
        # svo thad byggist upp rett med lagfaerdu matinu. Medlima-bias og
        # thyngdir halda ser - their voru aldrei mengadir.
        # v3.7: ALLUR skyjalaerdomur var byggdur a 24 klst gamalli METAR-
        # maelingu. Bias, skyjakort og fall-einkunn a skyi eru thvi mengud.
        # Nullstillum SKY-hlutann einu sinni - hiti/vindur/att halda ser
        # thvi their laera af vedur.is sem var alltaf rett.
        if not raw.get("v37_sky_reset"):
            for m in ALL_KEYS:
                b = raw.get("bias", {}).get(m)
                if isinstance(b, dict):
                    for bs in list(b.keys()):
                        if isinstance(b[bs], dict) and "sky" in b[bs]:
                            b[bs]["sky"] = 0.0
                cb = raw.get("cond_bias", {}).get(m, {})
                for bs, cells in (cb or {}).items():
                    for cell, vars_ in (cells or {}).items():
                        if isinstance(vars_, dict) and "sky" in vars_:
                            vars_["sky"] = {"sum": 0.0, "n": 0}
            raw["cloud_map"] = {}
            raw["cloud_confusion"] = {}
            raw.setdefault("failed", {})["sky"] = {}
            for b in LEAD_BUCKETS:
                jb = raw.get("jolly_bias", {}).get(str(b))
                if isinstance(jb, dict):
                    jb["sky"] = 0.0
                lm = raw.get("lead_mae", {}).get(str(b), {})
                for m, st in (lm or {}).items():
                    if isinstance(st, dict) and "sky" in st:
                        st["sky"] = None
            raw["skill"]["sky"] = {}
            raw["v37_sky_reset"] = True
            print("  HREINSUN v3.7: skyjalaerdomur nullstilltur (var byggdur")
            print("  a 24 klst gamalli METAR-maelingu). Hiti/vindur halda ser.")

        if not raw.get("v35_jolly_bias_reset"):
            raw["jolly_bias"] = {str(b): empty_bias() for b in LEAD_BUCKETS}
            for b in LEAD_BUCKETS:
                lm = raw.get("lead_mae", {}).get(str(b), {})
                if JOLLY_KEY in lm:
                    del lm[JOLLY_KEY]
            raw["skill"] = {v: {} for v in WEIGHT_VARS}
            raw["v35_jolly_bias_reset"] = True
            print("  HREINSUN v3.5: jolly_bias nullstillt (var mengad af")
            print("  tvofaldri leidrettingu). Medlimir og thyngdir halda ser.")

        # v4.9: HREINSUN A SKILL-SOGUNNI, EKKERT ANNAD.
        #
        # Fra 4.1 til 4.6 gengu THRJAR villur i rod (hrun sem gerdi 4.1-4.4
        # dauda, sky-maelingarvilla i krufningu/sannleiksmaeli, HARMONIE-
        # textavilla). Skill-EMA-id (thad sem birtist i "Jolly ... a moti
        # besta likani") hefur verid ad melta thessa mengun i marga daga.
        #
        # ATH: THETTA SNERTIR ADEINS skill{} og lead_mae[...][jolly].
        # Medlima-bias, thyngdir, reit-thyngdir, cloud_map og OLL hraagogn
        # (langtimasafn, truth.json) eru ALGJORLEGA OSNERT - beir eru thad
        # sem raedur spanni, ekki skill-taflan. Spain a morgun verdur eins
        # OG AN thessarar hreinsunar - adeins talan sem BIRTIST breytist.
        if not raw.get("v49_skill_reset"):
            for b in LEAD_BUCKETS:
                lm = raw.get("lead_mae", {}).get(str(b), {})
                if JOLLY_KEY in lm:
                    del lm[JOLLY_KEY]
            raw["skill"] = {v: {} for v in WEIGHT_VARS}
            raw["v49_skill_reset"] = True
            print("  HREINSUN v4.9: Jolly-skill nullstillt (EMA-id bar enn")
            print("  menguna fra hruni+skyjavillum 4.1-4.6). Medlimir,")
            print("  thyngdir og oll hraagogn eru OSNERT - spain breytist EKKI.")

        if not raw.get("v30_reset_done"):
            for b in LEAD_BUCKETS:
                lm = raw.get("lead_mae", {}).get(str(b), {})
                if JOLLY_KEY in lm:
                    del lm[JOLLY_KEY]
            raw["skill"] = {v: {} for v in WEIGHT_VARS}
            raw["jolly_bias"] = {str(b): empty_bias() for b in LEAD_BUCKETS}
            raw["v30_reset_done"] = True
            print("  EINSKIPTIS-HREINSUN: Jolly-MAE og skill nullstillt")
            print("  (byggist upp hreint - fyrstu skill-tolur eftir ~2 daga)")

        for m in ALL_KEYS:
            raw.setdefault("bias", {}).setdefault(m, {})
            for b in LEAD_BUCKETS:
                raw["bias"][m].setdefault(str(b), empty_bias())
                # 'att' er nytt i v2.6 - eldri skrar hafa thad ekki
                raw["bias"][m][str(b)].setdefault("att", 0.0)
        for b in LEAD_BUCKETS:
            raw.setdefault("jolly_bias", {}).setdefault(str(b), empty_bias())
            raw["jolly_bias"][str(b)].setdefault("att", 0.0)
        raw.setdefault("cond_bias", {})

        # Uppfaersla ur v2.0-2.2: thyngdir voru weights[spalengd][likan],
        # reiknadar EINGONGU ur hitaskekkju og notadar a allar breytur.
        # Nu eru thaer weights[breyta][spalengd][likan]. Vid afritum gomlu
        # rodunina yfir a allar breytur sem upphafsgildi og hver breyta
        # ferist sidan i sina att jafnodum og hun er stadfest.
        w = raw.get("weights", {})
        flat = bool(w) and not any(v in w for v in WEIGHT_VARS)
        if flat:
            raw["weights"] = {v: {b: dict(w.get(b, {})) for b in w}
                              for v in WEIGHT_VARS}
            print("  Uppfaerdi thyngdir: flatar -> ser fyrir hverja breytu")

        for v in WEIGHT_VARS:
            raw.setdefault("weights", {}).setdefault(v, {})
            for b in LEAD_BUCKETS:
                raw["weights"][v].setdefault(
                    str(b), {m: 1.0 / len(ALL_KEYS) for m in ALL_KEYS})
                for m in ALL_KEYS:
                    raw["weights"][v][str(b)].setdefault(m, 0.0)

        sk = raw.get("skill", {})
        if sk and not any(v in sk for v in WEIGHT_VARS):
            raw["skill"] = {"hiti": sk}       # gamla skill var hitabundid
        for v in WEIGHT_VARS:
            raw.setdefault("skill", {}).setdefault(v, {})

        for b in LEAD_BUCKETS:
            raw.setdefault("lead_mae", {}).setdefault(str(b), {})

        print(f"  Hladid v2.x - {raw.get('runs',0)} keyrslur, "
              f"{raw.get('verified_pairs',0)} stadfest por")
        return raw
    return migrate_model(raw)

# ═══════════════════════════════════════════════════════════════════════
#  [REITIR]  REITIR - VINDATT x DAGUR/NOTT x THRYSTITHROUN
#  Skilgreining a thvi hvada adstaedur vid laerum ser fyrir.
# ═══════════════════════════════════════════════════════════════════════

VAR_MAP = [("hiti", "t", "temperature"),
           ("vindur", "w", "windspeed"),
           ("att", "d", "winddirection"),
           ("urkoma", "p", "precipitation"),
           ("sky", "c", "cloud_cover")]

# Breytur sem eru horn - tharfnast hringlaga reiknings
ANGLE_VARS = {"att"}

# --- DAGLEGAR TIMARAUFIR -------------------------------------------------
# Somu timasetningar og Vedurstofan notar i sinni dagaspa. 00:00 tilheyrir
# nottinni SEM LYKUR deginum, thad er midnaetti naesta dags - thess vegna
# synir hun tungl thegar hinar thrjar syna dagsbirtu.
DAY_SLOTS = ["06", "12", "18", "00"]

# --- SKILYRT BIAS --------------------------------------------------------
# Bias er ekki fast - i Egilsstadadal er hitaskekkjan hád vindatt (fohn af
# vestri gefur hlyrra, nordanatt kaldara) og degi/nott (kaldaloftspollun).
# Ein tala finnur medaltalid, sem er rangt fyrir baðar adstaedur.
#
# Vid skiptum i reiti: 4 vindattarfjordungar x 2 (dagur/nott). Hver reitur
# laerir sitt bias EN fellur aftur a almenna bias-id thegar hann er thunnur,
# annars verdur skilyrt bias onakvaemara en oskilyrt. Thetta er "shrinkage":
#   b_reitur = (n/(n+K)) * b_maelt + (K/(n+K)) * b_almennt
# K er hversu morg por tharf adur en reiturinn er treyst ad fullu.
COND_SHRINK_K = 10          # helmingstraust vid 10 por
COND_MIN_N    = 3           # undir thessu: nota adeins almenna bias

def wind_sector(deg):
    """Vindattarfjordungur: 0=N, 1=A, 2=S, 3=V. None ef vantar."""
    if deg is None: return None
    return int(((deg + 45.0) % 360.0) // 90.0)

SECTOR_NAME = {0: "N", 1: "A", 2: "S", 3: "V"}

def cond_key(wd_ob, is_day):
    """Reitlykill: t.d. 'V-dagur'. None ef vindatt vantar."""
    sec = wind_sector(wd_ob)
    if sec is None: return None
    return f"{SECTOR_NAME[sec]}-{'dagur' if is_day else 'nott'}"

# --- THRYSTITHROUN ------------------------------------------------------
# Urkoma raest af synoptiskri thvingun, ekki af solarhringssveiflu. Fallandi
# thrystingur = laegd ad naalgast = urkoma likleg. Haekkandi = ad letta til.
# Thess vegna notum vid ANNAN reit fyrir urkomu: att x thrystithroun,
# i stad att x dagur/nott. Thad er tharfara og heldur reitum faum (12).
PRESS_FALL = -0.7      # hPa/klst - markalina fyrir "fallandi"
PRESS_RISE =  0.7      # hPa/klst - markalina fyrir "haekkandi"

def press_trend(dp_per_h):
    """'fall', 'jafn' eda 'ris' ut fra thrystibreytingu i hPa/klst."""
    if dp_per_h is None: return "jafn"
    if dp_per_h <= PRESS_FALL: return "fall"
    if dp_per_h >= PRESS_RISE: return "ris"
    return "jafn"

def cond_key_precip(wd_ob, dp_per_h):
    """Reitlykill fyrir URKOMU: t.d. 'S-fall'. Att x thrystithroun."""
    sec = wind_sector(wd_ob)
    if sec is None: return None
    return f"{SECTOR_NAME[sec]}-{press_trend(dp_per_h)}"

# ═══════════════════════════════════════════════════════════════════════
#  [LANGTIMASAFN]  LANGTIMASAFN (CSV)
#  docs/data/verify/YYYY-MM.csv - aldrei hreinsad. Grunnur arstidanams.
# ═══════════════════════════════════════════════════════════════════════

def append_verify_rows(rows):
    """
    Skrifar stadfest por i manadarskipta CSV. Vidbotarskrif eingongu -
    thessi gogn eru aldrei hreinsud.

    Hver rod er eitt (gildistimi, spalengd, gjafi) med ollum fjorum
    breytum og skilyrdingarbreytum (manudur, klukkustund, athugud vindatt),
    svo arstidabundin og attabundin greining se moguleg sidar.
    """
    if not rows:
        return 0
    VERIFY_DIR.mkdir(parents=True, exist_ok=True)
    by_month = {}
    for r in rows:
        by_month.setdefault(r["valid_time"][:7], []).append(r)

    total = 0
    for month, rs in by_month.items():
        path = VERIFY_DIR / f"{month}.csv"
        exists = path.exists()
        # Forðast tvitekningu ef keyrsla er endurtekin
        seen = set()
        if exists:
            try:
                with open(path) as f:
                    next(f, None)
                    for line in f:
                        p3 = line.split(",")[:3]
                        if len(p3) == 3:
                            seen.add(tuple(p3))
            except Exception:
                seen = set()
        with open(path, "a") as f:
            if not exists:
                f.write(",".join(VERIFY_COLS) + "\n")
            for r in rs:
                key = (r["valid_time"], str(r["lead"]), r["src"])
                if key in seen:
                    continue
                seen.add(key)
                f.write(",".join(
                    "" if r.get(c) is None else str(r.get(c))
                    for c in VERIFY_COLS) + "\n")
                total += 1
    return total


def verify_dataset_stats():
    """Yfirlit yfir langtimasafnid - hversu langt back og hve morg por."""
    if not VERIFY_DIR.exists():
        return {"months": 0, "rows": 0, "first": None, "last": None}
    files = sorted(VERIFY_DIR.glob("*.csv"))
    rows = 0
    for f in files:
        try:
            with open(f) as fh:
                rows += max(0, sum(1 for _ in fh) - 1)
        except Exception:
            pass
    return {"months": len(files), "rows": rows,
            "first": files[0].stem if files else None,
            "last":  files[-1].stem if files else None}



# ══════════════════════════════════════════════════════════════════════
#  SANNLEIKSMAELIR - hlaupandi 24 klst gluggi
#
#  Skill-taflan hefur logid thrisvar: framsyniskekkja (v1.x), mengud saga
#  (blindu dagarnir), og tvofold leidretting (v3.4). I hvert sinn tok
#  marga daga ad finna thad, thvi EMA-id man gamla sogu og hreinsun
#  skekkir thad.
#
#  Thessi maelir er ODYR OG OBLEKKJANLEGUR:
#    - HRAAR tolur: spa vs maeling, engin bias-leidretting i matinu
#    - ENGIN EMA: einfalt medaltal yfir sidustu 24 klst
#    - Gluggi hreinsast sjalfur, svo gomul saga getur ekki mengad
#    - Sami utreikningur fyrir Jolly OG medlimi - jafn samanburdur
#
#  Ef thessi maelir og skill-taflan segja olika hluti, tha er skill-taflan
#  brotin - EKKI hinn.
# ══════════════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════════════
#  [SANNLEIKUR]  SANNLEIKSMAELIR
#  Hlaupandi 24 klst gluggi a HRAUM tolum. Oblekkjanlegur - engin EMA,
#  engin gomul saga. Inniheldur THRIHYRNINGSVORNINA.
# ═══════════════════════════════════════════════════════════════════════

TRUTH_WINDOW_H = 24
TRUTH_LEAD     = "1"        # maelum stystu spalengd - thad sem notandinn ser

def truth_update(rows_in, model=None):
    """
    Vistar por i hlaupandi glugga MED REIT (vindatt x dagur/nott).

    Leidrett gildi er reiknad med NAKVAEMLEGA sama falli og spain notar
    (member_bias -> cond_bias_value med shrinkage). Adur var notad almennt
    bias sem er EKKI thad sama - tha var samanburdurinn skakkur.

    Med thvi verdur thrihyrningsojafnan gild villuvorn:
      skekkja blondu <= vegid medaltal skekkju medlima, ALLTAF.
    Ef hun brotnar er eitthvad ad - engin undantekning til.
    """
    path = DATA_DIR / "truth.json"
    store = load_json(path, {"rows": []})
    now = datetime.now(timezone.utc)
    stamp = fmt_t(now)
    bs = TRUTH_LEAD

    def _corr(m, var, fc, cell):
        """NAKVAEMLEGA sama leidretting og spain notar."""
        if m == JOLLY_KEY or not model:
            return fc                      # Jolly er thegar leidrett
        v = corrected_member(model, m, bs, cell, var, fc)
        return fc if v is None else v

    for r in rows_in:
        m, var, ob, fc, cell = r["m"], r["v"], r["ob"], r["fc"], r.get("cell")
        if ob is None or fc is None:
            continue
        row = {"t": stamp, "m": m, "v": var,
               "ob": round(ob, 2), "fc": round(fc, 2),
               "fcc": round(_corr(m, var, fc, cell), 2),
               "c": cell or "?"}
        # [v5.2] w_issue = thyngd thessa gjafa EINS OG HUN VAR VID UTGAFU
        # spar (geymd i forecast_archive.json slot["weights"]). Vistad her
        # svo throhyrningsvornin geti notad NAKVAEMU somu thyngd og Jolly
        # notadi, i stad thess ad endurreikna ur current model-stodu sem
        # hefur thegar breyst vegna EMA-uppfaerslu milli utgafu og stadfestingar.
        if r.get("w_issue") is not None:
            row["wi"] = round(r["w_issue"], 4)
        store["rows"].append(row)

    cutoff = now - timedelta(hours=TRUTH_WINDOW_H)
    kept = []
    for r in store["rows"]:
        try:
            if parse_t(r["t"]) >= cutoff:
                kept.append(r)
        except Exception:
            pass
    store["rows"] = kept[-20000:]
    save_json(path, store)

    def _err(v, a, b):
        return abs(ang_diff(a, b)) if v == "att" else abs(a - b)

    # Heildartafla OG sundurlidun eftir reit
    acc, by_cell = {}, {}
    for r in store["rows"]:
        e_raw = _err(r["v"], r["fc"], r["ob"])
        e_cor = _err(r["v"], r.get("fcc", r["fc"]), r["ob"])
        a = acc.setdefault((r["m"], r["v"]), [0.0, 0.0, 0])
        a[0] += e_raw; a[1] += e_cor; a[2] += 1
        k = (r.get("c", "?"), r["m"], r["v"])
        b = by_cell.setdefault(k, [0.0, 0])
        b[0] += e_cor; b[1] += 1
    tbl = {k: (v[0] / v[2], v[1] / v[2], v[2])
           for k, v in acc.items() if v[2] > 0}
    cells = {k: (v[0] / v[1], v[1]) for k, v in by_cell.items() if v[1] > 0}
    globals()["_TRUTH_CELLS"] = cells
    globals()["_TRUTH_ROWS"] = store["rows"]   # fyrir thrihyrningsvornina
    return tbl

def truth_print(tbl):
    """
    Sannleikstafla + sundurlidun eftir reit (vindatt x dagur/nott)
    + THRIHYRNINGSVORN sem gripur omoguleg gildi sjalfkrafa.
    """
    if not tbl:
        return
    VARS = ("hiti", "vindur", "att", "sky")
    print(f"SANNLEIKSMAELIR (hraar tolur, sidustu {TRUTH_WINDOW_H} klst, "
          f"@{TRUTH_LEAD}klst)")
    print("  gjafi        " + "".join(f"{v:>9}" for v in VARS)
          + "   (leidrett eins og spain gerir)")
    n_show = 0
    for m in list(ALL_KEYS) + [JOLLY_KEY]:
        cells, corr, n_max = [], [], 0
        for var in VARS:
            e = tbl.get((m, var))
            if e:
                cells.append(f"{e[0]:>9.2f}")
                corr.append(f"{e[1]:.2f}")
                n_max = max(n_max, e[2])
            else:
                cells.append(f"{'-':>9}"); corr.append("-")
        if n_max == 0:
            continue
        if m == JOLLY_KEY:
            print("  " + "-" * 46)
        nafn = "JOLLY" if m == JOLLY_KEY else m
        print(f"  {nafn:12}" + "".join(cells) + "   (" + " ".join(corr) + ")")
        n_show = max(n_show, n_max)
    print(f"  n = {n_show} por")

    # Domar + THRIHYRNINGSVORN
    for var in VARS:
        j = tbl.get((JOLLY_KEY, var))
        raw = [tbl[(m, var)][0] for m in ALL_KEYS if (m, var) in tbl]
        cor = [tbl[(m, var)][1] for m in ALL_KEYS if (m, var) in tbl]
        if not j or not cor:
            continue
        r_avg, c_avg, c_best = sum(raw)/len(raw), sum(cor)/len(cor), min(cor)
        f = lambda a: (a - j[0]) / a * 100 if a else 0.0
        print(f"    {var:7} Jolly {j[0]:6.2f} | hrair {r_avg:6.2f} "
              f"({f(r_avg):+.0f}%) | leidrettir {c_avg:6.2f} ({f(c_avg):+.0f}%) "
              f"| besti {c_best:6.2f} ({f(c_best):+.0f}%)")
        # THRIHYRNINGSVORN. Ojafnan |sum w*f - o| <= sum w*|f - o| gildir
        # fyrir SOMU thyngdir - svo vid verdum ad nota RAUNVERULEGAR
        # thyngdir Jolly UR HVERJUM REIT, ekki ovegid medaltal.
        #
        # [v4.9 LAGFAERT] Fra v4.1 notar spain STUNDUM reit-thyngdir
        # (weights_cell) i stad almennu thyngdanna, thegar reitur hefur
        # nog gogn (WGT() i make_forecast). Fyrri utgafa vornarinnar bar
        # alltaf saman vid ALMENNU thyngdirnar - ef spain notadi reit-
        # thyngd fyrir eitthvert PAR i glugganum var samanburdurinn ekki
        # lengur gildur ojafna, og vornin gat hropad ad osekju - NAKVAEMLEGA
        # sama tegund villu og vid fundum i sky-krufningunni adur.
        #
        # Nu reiknum vid VEGID MEDALTAL PER ROD med SOMU WGT()-adferd og
        # spain notar - reitur hverrar radar rædur hvada thyngd er beitt.
        # [v5.2 - DYPRI LAGFAERING]
        # v5.1 lagadi HVADA REIT er notadur (spad vs maeld att). En INNAN
        # reits breytast thyngdirnar sjalfar EMA-vegis i HVERRI keyrslu
        # (CELLW_LR=0.10) - milli utgafu spar og stadfestingar keyrir
        # train-skrefid a.m.k. einu sinni. Thvi hoggur endurreiknud thyngd
        # UR CURRENT model EKKI vid thyngdina sem Jolly RAUNVERULEGA notadi.
        #
        # LOKALAUSN: hver rod i truth.json geymir NU "wi" - thyngdina EINS
        # OG HUN VAR VID UTGAFU (geymd alla leid fra make_forecast gegnum
        # forecast_archive.json). Notum hana beint thegar hun er til =
        # FULLKOMLEGA nakvaemur samanburdur, EKKERT tímamisraemi eftir.
        #
        # Fyrir eldri radir (fyrir v5.2, ekkert "wi") follum vid a
        # reit-uppflettingu ur CURRENT model - eins og v4.9/v5.1 gerdu.
        # Thetta sjalfhreinsast a ~1 solarhring thegar glugginn endurnyjast.
        mdl = globals().get("_TRUTH_MODEL")

        def _fallback_w(m, cellname):
            if not mdl: return 0.0
            wc = ((mdl.get("weights_cell", {}).get(var, {})
                       .get(TRUTH_LEAD, {}) or {}).get(cellname) or {})
            if m in wc:
                return wc[m]
            return (mdl.get("weights", {}).get(var, {})
                        .get(TRUTH_LEAD, {}) or {}).get(m, 0.0)

        wsum, acc_w, n_rows, n_exact = 0.0, 0.0, 0, 0
        for r in globals().get("_TRUTH_ROWS", []):
            if r["v"] != var or r["m"] == JOLLY_KEY:
                continue
            if r.get("wi") is not None:
                w = r["wi"]; n_exact += 1
            else:
                w = _fallback_w(r["m"], r.get("c", "?"))
            e = abs(ang_diff(r.get("fcc", r["fc"]), r["ob"])) if var == "att" \
                else abs(r.get("fcc", r["fc"]) - r["ob"])
            wsum += w; acc_w += w * e; n_rows += 1
        if wsum > 0:
            w_avg = acc_w / wsum
            tag = f"n={n_rows}, {n_exact} nakvaem" if n_exact else f"n={n_rows}, allt varaleid"
            if j[0] > w_avg * 1.02:      # 2% svigrum fyrir namundun
                print(f"      OMOGULEGT: Jolly ({j[0]:.2f}) > VEGID "
                      f"medaltal medlima ({w_avg:.2f}, {tag}).")
                print(f"      Thrihyrningsojafnan brotin - blondun eda "
                      f"vistun er rong.")
                warn(f"THRIHYRNINGSVORN brotin a {var}: Jolly {j[0]:.2f} "
                     f"> vegid medaltal {w_avg:.2f}", alvarlegt=True)

    # Sundurlidun eftir reit - thar sem nakvaemnin raunverulega byr
    cells = globals().get("_TRUTH_CELLS") or {}
    if cells:
        reitir = sorted({k[0] for k in cells if k[0] != "?"})
        if reitir:
            print("  EFTIR REIT (leidrett MAE, vindatt x dagur/nott):")
            print("    reitur      " + "".join(f"{v:>9}" for v in VARS) + "     n")
            for rt in reitir:
                row, nmax = [], 0
                for var in VARS:
                    e = cells.get((rt, JOLLY_KEY, var))
                    if e:
                        row.append(f"{e[0]:>9.2f}"); nmax = max(nmax, e[1])
                    else:
                        row.append(f"{'-':>9}")
                if nmax:
                    print(f"    {rt:12}" + "".join(row) + f"{nmax:>6}")

# ═══════════════════════════════════════════════════════════════════════
#  [STADFESTING]  STADFESTING OG NAM  <-- STAERSTI KAFLINN
#  Ber spar saman vid maelingar, laerir bias + thyngdir + reit-thyngdir,
#  reiknar skill, keyrir fall-einkunn og krufningu.
# ═══════════════════════════════════════════════════════════════════════

def verify_and_train(arch, obs_history, model):
    """
    Ber geymdar spar saman vid raunverulegar maelingar og laerir bias
    ser fyrir hverja spalengd. Thetta er eiginleg spastadfesting.
    """
    print("STADFESTING:")
    obs_by_t = {o["time"]: o for o in obs_history}

    # pairs[spalengd][likan][breyta] = [(maeling, spa), ...]
    pairs = {str(b): {m: {v: [] for v, _, _ in VAR_MAP} for m in VERIFY_KEYS}
             for b in LEAD_BUCKETS}
    n_pairs = 0
    verified_times = set()
    csv_rows = []          # fer i langtimasafnid
    # cond_pairs[likan] = [(vars_list, cell), ...] fyrir skilyrt bias
    cond_pairs = {}
    truth_rows = []        # fyrir sannleiksmaelinn, med reit
    cell_rows  = []        # (breyta, spalengd, reitur, likan, skekkja)

    for vt, leads in arch.items():
        o = obs_by_t.get(vt)
        if not o: continue
        for lead_s, entry in leads.items():
            if lead_s not in pairs: continue
            # Hver gjafi er adeins laerdur EINU SINNI a hverjum gildistima.
            # 'done' er listi af gjofum sem thegar hafa verid stadfestir -
            # ekki eitt boolean, thvi Jolly er skrad i safnid EFTIR ad
            # medlimirnir hafa verid stadfestir og maetti annars aldrei.
            done = entry.get("done")
            if done is True:                 # gamalt snid ur v2.0/2.1
                done = list(entry.get("models", {}).keys())
            elif not isinstance(done, list):
                done = []
            # [v5.1] Reitur thessa gildistima.
            #
            # ADUR: alltaf endurreiknad ur MAELDRI att (o.get("winddirection")).
            # EN vid UTGAFU er reiturinn valinn ur SPADRI att (grov_att i
            # make_forecast), thvi mæld att er ekki til fyrirfram. Ef spa og
            # maeling lenda sitt hvorum megin vid 90°-mark (algengt thegar
            # attarspa-skekkja er 30-80° eins og sannleiksmaelirinn synir),
            # thá VELDUR thetta OLIKUM REIT - og bry samanburdurinn vid
            # thrihyrningsvornina verdur OGILDUR (ber saman vid blondu sem
            # aldrei var reiknud). Stadfest með raundaemum 24.ag.
            #
            # NU: nota GEYMDA reitinn (slot["cell"], sett i archive_jolly)
            # ef til - thad ER reiturinn sem raunverulega red thyngdum/bias.
            # Fellur a gomlu adferdina (mæld att) fyrir eldri faerslur sem
            # voru skradar fyrir v5.1 og hafa ekki "cell" geymt.
            entry_is_day = entry.get("is_day")
            if entry_is_day is None:
                entry_is_day = 1   # sjalfgefid dagur ef vantar
            cell = entry.get("cell") or \
                   cond_key(o.get("winddirection"), entry_is_day >= 0.5)
            # Urkomureitur: att x thrystithroun (annar en hinir)
            cell_p = cond_key_precip(o.get("winddirection"),
                                     entry.get("dp_h"))

            for m, fcv in entry.get("models", {}).items():
                if m not in VERIFY_KEYS or m in done: continue
                used = False
                var_pairs = []
                for var, fkey, okey in VAR_MAP:
                    ov, fv = o.get(okey), fcv.get(fkey)
                    if ov is not None and fv is not None:
                        pairs[lead_s][m][var].append((ov, fv))
                        var_pairs.append((var, ov, fv))
                        # Sannleiksmaelir: geyma MED REIT svo haegt se ad
                        # sundurlida eftir vindatt x dagur/nott
                        if lead_s == TRUTH_LEAD and var != "urkoma":
                            # [v5.2] Geyma RAUNVERULEGU thyngdina sem
                            # thessi gjafi hafdi VID UTGAFU thessarar spar,
                            # ur entry["weights"] (v5.2). Fellur a None ef
                            # eldri faersla an thess - throhyrningsvornin
                            # notar tha varaleid (mel. thyngdir CURRENT).
                            _wt = (entry.get("weights", {}).get(var, {})
                                       .get(m))
                            truth_rows.append({"m": m, "v": var, "ob": ov,
                                               "fc": fv, "cell": cell,
                                               "w_issue": _wt})
                        # REIT-MAE: hvada likan er best I THESSUM adstaedum.
                        # Urkoma notar thrystireitinn, hinar att x dagur/nott.
                        _c = cell_p if var == "urkoma" else cell
                        if _c and m != JOLLY_KEY:
                            _e = abs(ang_diff(fv, ov)) if var == "att" \
                                 else abs(fv - ov)
                            cell_rows.append((var, lead_s, _c, m, _e))
                        n_pairs += 1
                        used = True
                # Skilyrt bias adeins fyrir medlimi (ekki Jolly)
                if var_pairs and m != JOLLY_KEY and cell is not None:
                    cond_pairs.setdefault(m, []).append((
                        [(v, ov, fv) for v, ov, fv in var_pairs], cell))
                if used:
                    done.append(m)
                    verified_times.add(vt)
                    # Skra i langtimasafnid med skilyrdingarbreytum
                    csv_rows.append({
                        "valid_time": vt, "lead": lead_s, "src": m,
                        "month": int(vt[5:7]), "hour": int(vt[11:13]),
                        "wd_ob": o.get("winddirection"),
                        "ws_ob": o.get("windspeed"),
                        "t_fc": fcv.get("t"), "t_ob": o.get("temperature"),
                        "w_fc": fcv.get("w"), "w_ob": o.get("windspeed"),
                        "d_fc": fcv.get("d"), "d_ob": o.get("winddirection"),
                        "p_fc": fcv.get("p"), "p_ob": o.get("precipitation"),
                        "c_fc": fcv.get("c"), "c_ob": o.get("cloud_cover"),
                    })
            if done:
                entry["done"] = done
                entry["verified_at"] = fmt_t(datetime.now(timezone.utc))

    if n_pairs == 0:
        n_done = sum(1 for l in arch.values() for e in l.values() if e.get("done"))
        print("  Ekkert nytt til stadfestingar")
        print(f"  (safnid: {len(arch)} gildistimar, {n_done} thegar stadfest, "
              f"maelingar: {len(obs_by_t)})")
        model["runs"] = model.get("runs", 0) + 1
        model["last_updated"] = datetime.now(timezone.utc).isoformat()
        return model

    globals()["_N_NEW_PAIRS"] = n_pairs
    print(f"  {n_pairs} NY stadfest por a {len(verified_times)} gildistimum")
    save_json(DATA_DIR / "forecast_archive.json", arch)   # varðveita "done"

    # --- SJALFGREINING: Jolly a moti medlimum a SOMU nyju porunum ---
    # Ef Jolly tapar her (a ferskum porum) er vandinn raunverulegur.
    # Ef hun vinnur her en tapar i skill (uppsofnu) er vandinn arfleifd
    # fra gomlum gognum sem hverfur med tima.
    for b in [6, 24]:
        bs = str(b)
        jp = pairs[bs].get(JOLLY_KEY, {})
        if not jp.get("hiti"): continue
        jmae = mae(jp["hiti"])
        mem = {}
        for m in ALL_KEYS:
            mp = pairs[bs].get(m, {})
            if mp.get("hiti"):
                mem[m] = mae(mp["hiti"])
        if not mem or jmae is None: continue
        bestm = min(mem, key=mem.get)
        print(f"  [GREINING @{b}klst hiti] Jolly {jmae:.2f} vs "
              f"besti {bestm} {mem[bestm]:.2f} vs "
              f"medaltal-medlima {sum(mem.values())/len(mem):.2f}  "
              f"(n={len(jp['hiti'])})")
        # Er Jolly nalaegt vegnu medaltali medlimanna? (sannreynir blondun)
        import statistics as _st
        jvals = [f for _, f in jp["hiti"]]
        ovals = [o for o, _ in jp["hiti"]]
        print(f"           Jolly-spa bil: {min(jvals):.1f} - {max(jvals):.1f}, "
              f"medaltal {_st.mean(jvals):.1f} | maeling medaltal {_st.mean(ovals):.1f}")
        # Merki-greining: er Jolly kerfisbundid of ha/lag?
        jbias = _st.mean(f - o for o, f in jp["hiti"])
        print(f"           Jolly bias: {jbias:+.2f}  (0 = engin kerfisbundin skekkja)")
        # Bera vid HRAA medlimi - eru their lika svona skakkir?
        for mm in list(mem)[:2]:
            mp = pairs[bs].get(mm, {})
            if mp.get("hiti"):
                mbias = _st.mean(f - o for o, f in mp["hiti"])
                print(f"           {mm} hra-bias: {mbias:+.2f}")

    # SANNLEIKSMAELIR: hraa por, engin leidretting, hlaupandi gluggi.
    # Kallad HER svo hann fai somu por og stadfestingin - jafn samanburdur.
    try:
        _truth = truth_update(truth_rows, model)
        model["_truth"] = True
        globals()["_TRUTH_TBL"] = _truth
        globals()["_TRUTH_MODEL"] = model
    except Exception as e:
        print(f"  (sannleiksmaelir: {e})")

    # --- KRUFNING: EIN stadfesting synd i heild --------------------------
    # Ef geymd Jolly-spa er ekki sama og vegin blanda af geymdum medlimum,
    # tha er eitthvad ad milli blondunar og vistunar. Thetta er eina leidin
    # ad sja thad - allt annad er agiskun.
    try:
        _bs = TRUTH_LEAD
        _j = pairs[_bs].get(JOLLY_KEY, {}).get("sky", [])
        if _j:
            _ob, _jf = _j[0]
            print(f"  KRUFNING @{_bs}klst sky (maeling {_ob:.1f}):")
            _num = _den = 0.0
            for m in ALL_KEYS:
                _mp = pairs[_bs].get(m, {}).get("sky", [])
                if not _mp:
                    continue
                _, _raw = _mp[0]
                _cor = corrected_member(model, m, _bs, cell, "sky", _raw)
                if _cor is None: _cor = _raw
                _w = (model.get("weights", {}).get("sky", {})
                          .get(_bs, {}) or {}).get(m, 0.0)
                _num += _w * _cor; _den += _w
                print(f"    {m:9} hratt {_raw:6.1f} -> leidrett {_cor:6.1f}"
                      f"  x thyngd {_w*100:4.1f}%")
            if _den > 0:
                _blend = _num / _den
                print(f"    REIKNUD BLANDA        {_blend:6.1f}")
                print(f"    GEYMD JOLLY-SPA       {_jf:6.1f}"
                      f"   mismunur {_jf - _blend:+.1f}")
                if abs(_jf - _blend) > 2.0:
                    print(f"    OSAMRAEMI: geymd spa passar EKKI vid blondu.")
                    warn(f"KRUFNING: geymd Jolly-spa ({_jf:.1f}) passar ekki "
                         f"vid blondu ({_blend:.1f})", alvarlegt=True)
    except Exception as _e:
        print(f"  (krufning: {_e})")

    # --- UPPFAERA REIT-MAE: hver er bestur i hverjum adstaedum -----------
    if cell_rows:
        cm = model.setdefault("cell_mae", {})
        agg = {}
        for var, ls, c, m, e in cell_rows:
            a = agg.setdefault((var, ls, c, m), [0.0, 0])
            a[0] += e; a[1] += 1
        for (var, ls, c, m), (tot, n) in agg.items():
            st = cm.setdefault(var, {}).setdefault(ls, {}) \
                   .setdefault(c, {}).setdefault(m, {"mae": None, "n": 0})
            run = tot / n
            st["mae"] = round(run, 3) if st["mae"] is None else \
                        round((1 - CELLW_LR) * st["mae"] + CELLW_LR * run, 3)
            st["n"] = st.get("n", 0) + n

    n_csv = append_verify_rows(csv_rows)
    ds = verify_dataset_stats()
    span = f"{ds['first']} - {ds['last']}" if ds["first"] else "tomt"
    print(f"  Langtimasafn: +{n_csv} radir | {ds['rows']} samtals | "
          f"{ds['months']} man ({span})")

    summary = {}
    for b in LEAD_BUCKETS:
        bs = str(b)
        summary[bs] = {}
        for m in VERIFY_KEYS:
            pv = pairs[bs][m]
            if not any(pv.values()): continue

            # Jolly er MAELD en ekki leidrett - hun er thegar leidrett
            if m == JOLLY_KEY:
                store = model["lead_mae"][bs].setdefault(
                    JOLLY_KEY, {v: None for v in WEIGHT_VARS})
                store.setdefault("n", 0)
                store.setdefault("n_var", {})
                for var in WEIGHT_VARS:
                    v = circ_mae(pv[var]) if var in ANGLE_VARS else mae(pv[var])
                    if v is None: continue
                    prev = store.get(var)
                    store[var] = round(v, 3) if prev is None \
                                 else round((1 - LR) * prev + LR * v, 3)
                    store["n_var"][var] = store["n_var"].get(var, 0) + len(pv[var])
                store["n"] = store.get("n", 0) + len(pv["hiti"])

                # --- RESTLEIDRETTING A JOLLY SJALFRI ---
                # Vegid medaltal af niu leidrettum likonum getur haft SINA
                # eigin kerfisbundnu hlutdraegni sem er ekki summa hlutanna.
                # Adur var Jolly-maelingin adeins stigatafla; nu er hun inntak.
                # Jolly-spain i safninu er ThEGAR leidrett, svo thetta er
                # itrud nalgun sem gengur i nullid (heildstyring).
                jb = model.setdefault("jolly_bias", {}) \
                          .setdefault(bs, empty_bias())

                # ATH: SAFNSTYRING, ekki veldisjofnun.
                #
                # Medlimir eru geymdir OLEIDRETTIR i safninu, svo maeld
                # skekkja their er fast mark og  b <- (1-a)b + a(-nb)
                # gengur i rett gildi.
                #
                # Jolly er geymd THEGAR LEIDRETT. Skekkjan er thvi
                # EFTIRSTANDANDI rest sem inniheldur ahrif b sjalfs:
                #     err = T + b
                # Ad jafna i att ad henni gefur fastapunkt b = -T/2,
                # thad er halfa leidrettingu. Rett form er ad LEGGJA VID:
                #     b <- b + a(-err)   =>   fastapunktur b = -T
                # Safnstyring THARF vindingarvorn. An hennar safnast
                # leidrettingin upp thegar Jolly getur ekki elt raunveruleikann
                # (t.d. vindatt sem sveiflast) og hleypur ut i loftid.
                # Vid klemmum VID HVERT SKREF, ekki bara eftir a, og hofum
                # thakid edlisfraedilega rokstutt: rest yfir thessum morkum
                # er ekki hlutdraegni heldur merki um ad blandan se rong.
                # THRONG THOK. Medlimir eru geymdir HRAIR og metnir med
                # NUVERANDI bias-i; Jolly er geymd EINS OG HUN VAR BIRT.
                # Medan likanid laerir litur Jolly thvi verr ut en efni
                # standa til, og an throngs thaks færi restleidrettingin
                # ad baeta upp fyrir gamalt bias sem er thegar lagad -
                # tvofold leidretting sem getur ordid ostodug.
                # Thokin her leyfa raunverulega blonduhlutdraegni en ekki
                # eltingaleik vid laerdomssveiflur.
                for var, fn, cap in (
                        ("hiti",   bias,      JOLLY_BIAS_CAP["hiti"]),
                        ("vindur", bias,      JOLLY_BIAS_CAP["vindur"]),
                        ("att",    circ_bias, JOLLY_BIAS_CAP["att"]),
                        ("sky",    bias,      JOLLY_BIAS_CAP["sky"])):
                    if not pv[var]: continue
                    err = fn(pv[var]) or 0.0
                    a = adaptive_lr(model, f"jolly|{bs}|{var}", err)
                    step = a * (-err)
                    # Takmarka eitt skref svo einn afbrigdilegur timi
                    # kippi ekki leidrettingunni til
                    step = max(-cap * 0.15, min(cap * 0.15, step))
                    jb[var] = max(-cap, min(cap, jb.get(var, 0.0) + step))
                # (throskuldur laerdur nedar fyrir medlimi)
            # Urkoma er margfoldun: heildarkvardi sem tharf er s*r,
                # thar sem r = maeling/spa a THEGAR kvardadri spa.
                if pv["urkoma"]:
                    om = mean([o for o, _ in pv["urkoma"]])
                    fm = mean([f for _, f in pv["urkoma"]])
                    if om is not None and fm and fm > 0:
                        r = om / fm
                        sc = jb.get("urkoma_scale", 1.0)
                        jb["urkoma_scale"] = max(0.6, min(1.6,
                                                 sc * (1 - LR + LR * r)))
                continue

            bias_rec = model["bias"][m][bs]

            # ATH: merkid i adaptive_lr verdur ad vera EFTIRSTANDANDI skekkja,
            # ekki hraa biasid. Medlimir eru geymdir OLEIDRETTIR svo hraa
            # biasid hefur alltaf sama formerki - thad myndi pinna LR i thak
            # ad eilifu. Eftirstandandi skekkja (nb + núverandi bias) skiptir
            # um formerki thegar leidrettingin er ordin rett.
            for var in ("hiti", "vindur", "sky"):
                if pv[var]:
                    nb = bias(pv[var]) or 0.0
                    resid = nb + bias_rec[var]
                    a = adaptive_lr(model, f"{m}|{bs}|{var}", resid)
                    bias_rec[var] = (1 - a) * bias_rec[var] + a * (-nb)
            # Vindatt: hringmedaltal, thvi 350 gr og 10 gr eru 20 gr a milli
            if pv["att"]:
                nb = circ_bias(pv["att"]) or 0.0
                bias_rec.setdefault("att", 0.0)
                resid = ((nb + bias_rec["att"] + 180.0) % 360.0) - 180.0
                a = adaptive_lr(model, f"{m}|{bs}|att", resid)
                bias_rec["att"] = (1 - a) * bias_rec["att"] + a * (-nb)

            # --- SKILYRT BIAS: safna per reit (vindatt x dagur/nott) ---
            # Uppsafnad summa+n per reit, ekki veldisjofnun - vid tharfnumst
            # fjoldans til ad meta hvort reiturinn se treystandi (shrinkage).
            cond = model.setdefault("cond_bias", {}) \
                        .setdefault(m, {}).setdefault(bs, {})
            for (var_list, cell) in cond_pairs.get(m, []):
                if cell is None: continue
                c = cond.setdefault(cell, {})
                for var, val_o, val_f in var_list:
                    if val_o is None or val_f is None: continue
                    e = c.setdefault(var, {"sum": 0.0, "n": 0})
                    if var == "att":
                        e["sum"] += ang_diff(val_f, val_o)   # spa - maeling
                    else:
                        e["sum"] += (val_f - val_o)
                    e["n"] += 1
            if pv["urkoma"]:
                update_precip_threshold(model, m, bs, pv["urkoma"])
                thr = precip_threshold(model, m, bs)
                # Kvardi laerdur A THEIM SPAM SEM KOMAST YFIR THROSKULD,
                # annars togar flod af nullum kvardann rangt
                kept = [(o, f) for o, f in pv["urkoma"] if f >= thr]
                om = mean([o for o, _ in kept]) if kept else None
                fm = mean([f for _, f in kept]) if kept else None
                if om is not None and fm and fm > 0:
                    # Eftirstandandi: hlutfall eftir ad nuverandi kvardi er notadur
                    resid = (om / (fm * bias_rec["urkoma_scale"])) - 1.0 \
                            if bias_rec["urkoma_scale"] > 0 else 0.0
                    a = adaptive_lr(model, f"{m}|{bs}|urk", resid)
                    bias_rec["urkoma_scale"] = max(0.05, min(20.0,
                        (1 - a) * bias_rec["urkoma_scale"] + a * (om / fm)))

            # --- SKYJAHULA: flokkabundin leidretting ---
            # Prosenta 0-100 hegdar sér EKKI linulega: '+5' sem virkar vid
            # 95% er gagnslaus vid 20%, thvi thakid er 100. Vid laerum thvi
            # ser vik fyrir hvern skyjaflokk, plus confusion matrix til
            # ad sja hvada flokkar ruglast.
            if pv["sky"]:
                cm  = model.setdefault("cloud_map", {}) \
                           .setdefault(m, {}).setdefault(bs, {})
                cf  = model.setdefault("cloud_confusion", {}) \
                           .setdefault(m, {})
                for ov, fv in pv["sky"]:
                    fk = cloud_class(fv)
                    ok = cloud_class(ov)
                    if fk is None or ok is None: continue
                    e = cm.setdefault(fk, {"n": 0, "fc_sum": 0.0, "obs_sum": 0.0})
                    e["n"]      += 1
                    e["fc_sum"] += fv
                    e["obs_sum"] += ov
                    cf.setdefault(fk, {})
                    cf[fk][ok] = cf[fk].get(ok, 0) + 1

            # MAE thessarar keyrslu, eftir bias-leidrettingu.
            #
            # [MIKILVAEGT] Medlimir eru geymdir HRAIR i safninu, svo their
            # tharfnast bias vid mat. JOLLY er hins vegar geymd FULLLEIDRETT
            # (archive_jolly geymir thad sem vid birtum, eftir thyngdir,
            # skilyrt bias OG restbias). Ef vid leggjum bias a hana aftur
            # her verdur TVOFOLD leidretting: maeld skekkja verdur skokk,
            # jolly_bias laerir af thvi, og naest er enn meira lagt a.
            # Thad er jakvaed afturvirkni sem lét restbias vaxa (sky +7.7
            # -> +9.5, vind -1.24 -> -1.47) og eydilagdi Jolly-spana.
            _is_jolly = (m == JOLLY_KEY)
            if _is_jolly:
                corr     = lambda var: list(pv[var])          # ENGIN vidbot
                pr_corr  = list(pv["urkoma"])
                att_corr = list(pv["att"])
            else:
                corr = lambda var: [(o, f + bias_rec[var]) for o, f in pv[var]]
                pr_corr = [(o, f * bias_rec["urkoma_scale"]) for o, f in pv["urkoma"]]
                att_corr = [(o, wrap360(f + bias_rec.get("att", 0.0)))
                            for o, f in pv["att"]]
            run_mae = {"hiti":   mae(corr("hiti")),
                       "vindur": mae(corr("vindur")),
                       "att":    circ_mae(att_corr),
                       "sky":    mae(corr("sky")),
                       "urkoma": mae(pr_corr)}

            # Safna MAE upp milli keyrslna. Hver keyrsla stadfestir adeins
            # einn nyjan gildistima per spalengd, svo eitt maelingasett
            # er alltof lidid til ad reikna thyngd ur. Vid geymum thvi
            # veldisjafnad medaltal og fjolda samanburda.
            store = model["lead_mae"][bs].setdefault(
                m, {v: None for v in WEIGHT_VARS})
            store.setdefault("n", 0)
            # Ser fjoldi per breytu - urkoma og sky berast ekki alltaf
            store.setdefault("n_var", {})
            for var in WEIGHT_VARS:
                v = run_mae.get(var)
                if v is None: continue
                prev = store.get(var)
                store[var] = round(v, 3) if prev is None \
                             else round((1 - LR) * prev + LR * v, 3)
                store["n_var"][var] = store["n_var"].get(var, 0) + len(pv[var])
            store["n"] = store.get("n", 0) + len(pv["hiti"])

            summary[bs][m] = {v: (store.get(v) or 0.0) for v in WEIGHT_VARS}
            summary[bs][m]["n"] = store["n"]

        # Thyngdir: SER RODUN FYRIR HVERJA BREYTU.
        # Hvert likan er metid fjorum sinnum og faer fjorar thyngdir.
        # Likan sem er godt i vindi en lelegt i hita faer ha vindthyngd
        # og laga hitathyngd - i stad einnar thyngdar ur hitaskekkju.
        for var in WEIGHT_VARS:
            eps   = EPS_BY_VAR[var]
            min_n = MIN_N_BY_VAR[var]
            usable = {}
            for m, st in model["lead_mae"][bs].items():
                if m == JOLLY_KEY: continue
                v  = st.get(var)
                nv = (st.get("n_var") or {}).get(var, st.get("n", 0))
                if v is not None and nv >= min_n:
                    usable[m] = v
            if not usable:
                continue

            # --- FALL-EINKUNN ------------------------------------------
            # Likan sem er meira en FAIL_RATIO x besta likanid faer 0
            # vaegi - EN vid haldum afram ad maela thad. Thad kemst inn
            # aftur eftir RECOVER_N samfelldar godar spar.
            fail = model.setdefault("failed", {}).setdefault(var, {}) \
                        .setdefault(bs, {})
            best_mae = min(usable.values())
            ratio_lim = FAIL_RATIO.get(var, 3.0)
            for m, v in list(usable.items()):
                nv = (model["lead_mae"][bs][m].get("n_var") or {}) \
                        .get(var, model["lead_mae"][bs][m].get("n", 0))
                rec = fail.get(m) or {"out": False, "streak": 0}
                ratio = v / best_mae if best_mae > 0 else 1.0

                if rec["out"]:
                    # Er thad ad na ser? Telja samfelldar godar spar.
                    if ratio <= RECOVER_TOL:
                        rec["streak"] = rec.get("streak", 0) + 1
                        if rec["streak"] >= RECOVER_N:
                            rec = {"out": False, "streak": 0}
                            print(f"    {m} kemur AFTUR INN i {var} @{bs}klst "
                                  f"({RECOVER_N} godar spar i rod)")
                    else:
                        rec["streak"] = 0
                elif nv >= FAIL_MIN_N and ratio > ratio_lim:
                    rec = {"out": True, "streak": 0}
                    print(f"    {m} FELLUR UT ur {var} @{bs}klst "
                          f"(MAE {v:.1f} = {ratio:.1f}x besta {best_mae:.1f})")
                fail[m] = rec

            # Fjarlaegja fallin likon UR THYNGDUM (en their eru afram maeld)
            active = {m: v for m, v in usable.items()
                      if not (fail.get(m) or {}).get("out")}
            if not active:          # oryggisventill: aldrei tomt
                active = dict(usable)

            inv = {m: 1.0 / (v + eps) for m, v in active.items()}
            for m, bonus in MODEL_BONUS.get(var, {}).items():
                if m in inv: inv[m] *= bonus
            tot = sum(inv.values())
            base_w = {}
            for m in ALL_KEYS:
                base_w[m] = round(inv[m] / tot, 4) if m in inv else 0.0
                model["weights"][var][bs][m] = base_w[m]

            # --- SKILYRTAR THYNGDIR ---------------------------------------
            # Fyrir hvern reit: hver er bestur I THESSUM adstaedum?
            # Shrinkage ad almennu thyngdunum eftir thvi hve thykkur
            # reiturinn er, svo thunnir reitir laeri ekki havada.
            # Fall-einkunn gildir LIKA per reit: likan sem er onytt i
            # nordanatt ad nottu faer 0 THAR en heldur vaegi annars stadar.
            cells_here = (model.get("cell_mae", {}).get(var, {})
                              .get(bs, {}) or {})
            wc = model.setdefault("weights_cell", {}).setdefault(var, {}) \
                      .setdefault(bs, {})
            for cname, per_m in cells_here.items():
                usable_c = {m: st["mae"] for m, st in per_m.items()
                            if st.get("mae") is not None
                            and st.get("n", 0) >= CELLW_MIN_N
                            and not (fail.get(m) or {}).get("out")}
                if len(usable_c) < 2:
                    continue
                best_c = min(usable_c.values())
                # Fall-einkunn INNAN reits
                keep = {m: v for m, v in usable_c.items()
                        if best_c <= 0 or v / best_c <= ratio_lim}
                if len(keep) < 2:
                    keep = dict(usable_c)
                inv_c = {m: 1.0 / (v + eps) for m, v in keep.items()}
                for m, bonus in MODEL_BONUS.get(var, {}).items():
                    if m in inv_c: inv_c[m] *= bonus
                tot_c = sum(inv_c.values())
                if tot_c <= 0:
                    continue
                n_cell = min((per_m[m].get("n", 0) for m in keep), default=0)
                alpha = cell_weight_blend(n_cell)
                if alpha <= 0:
                    continue
                wc[cname] = {
                    m: round((1 - alpha) * base_w.get(m, 0.0)
                             + alpha * (inv_c[m] / tot_c if m in inv_c else 0.0), 4)
                    for m in ALL_KEYS}

    # --- Malikvardinn: er Jolly betri en besta einstaka likanid? ---
    # Reiknad SER FYRIR HVERJA BREYTU. Jolly getur verid betri i hita en
    # lakari i urkomu - eitt tal myndi fela thad.
    model.setdefault("skill", {})
    for var in WEIGHT_VARS:
        model["skill"].setdefault(var, {})
        for b in LEAD_BUCKETS:
            bs = str(b)
            lm = model["lead_mae"].get(bs, {})
            js = lm.get(JOLLY_KEY)
            if not js or js.get(var) is None:
                continue
            members = {}
            for m, st in lm.items():
                if m == JOLLY_KEY: continue
                v  = st.get(var)
                nv = (st.get("n_var") or {}).get(var, st.get("n", 0))
                if v is not None and nv >= 2:
                    members[m] = v
            if not members:
                continue
            best_m = min(members, key=members.get)
            best   = members[best_m]
            jmae   = js[var]
            # Hlutfallsbati verdur merkingarlaus thegar besta MAE naegir
            # nulli - (best-jolly)/best sprengir upp. Vid notum gólf sem
            # samsvarar maelinakvaemni breytunnar.
            floor = SKILL_FLOOR[var]
            if best < floor:
                skill = 0.0
                meaningful = False
            else:
                skill = (best - jmae) / best
                meaningful = True
            model["skill"][var][bs] = {
                "jolly_mae":   round(jmae, 3),
                "best_model":  best_m,
                "best_mae":    round(best, 3),
                "skill":       round(max(-1.0, min(1.0, skill)), 4),
                "meaningful":  meaningful,
                "mean_member": round(sum(members.values()) / len(members), 3),
                "n":           (js.get("n_var") or {}).get(var, js.get("n", 0)),
            }

    model["runs"]           = model.get("runs", 0) + 1
    model["verified_pairs"] = model.get("verified_pairs", 0) + n_pairs
    model["last_updated"]   = datetime.now(timezone.utc).isoformat()
    model["verify_history"].append({
        "time": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:00"),
        "n_pairs": n_pairs,
        "lead_mae": {b: {m: s["hiti"] for m, s in summary[b].items()}
                     for b in summary},
    })
    model["verify_history"] = model["verify_history"][-720:]

    # Skyrsla: JOLLY A MOTI BESTA MEDLIM, ser fyrir hverja breytu
    UNIT = {"hiti": "C", "vindur": "m/s", "att": "gr",
            "urkoma": "mm", "sky": "%"}
    any_skill = False
    for var in WEIGHT_VARS:
        rows = model.get("skill", {}).get(var, {})
        if not rows: continue
        any_skill = True
        print(f"  [{var}]")
        for b in LEAD_BUCKETS:
            sk = rows.get(str(b))
            if not sk: continue
            if not sk.get("meaningful", True):
                tag = "(MAE undir maelinakvaemni)"
                pct = "     -"
            else:
                tag = "BETRI" if sk["skill"] > 0 else "lakari"
                pct = f"{sk['skill']:+6.1%}"
            print(f"    {b:2d} klst  Jolly {sk['jolly_mae']:6.2f}{UNIT[var]}  "
                  f"besti {sk['best_model']:<8} {sk['best_mae']:6.2f}  "
                  f"-> {pct} {tag}  (n={sk['n']})")
    if not any_skill:
        for b in LEAD_BUCKETS:
            bs = str(b)
            if not summary.get(bs): continue
            best = sorted(summary[bs].items(), key=lambda x: x[1]["hiti"] or 99)
            line = "  ".join(f"{m}={s['hiti']:.2f}" for m, s in best[:4]
                             if s["hiti"] > 0)
            print(f"  {b:2d} klst | {line}  (Jolly ekki stadfest enn)")

    # Bestu likon per breytu vid 6 klst - synir hvort rodun er raunverulega ólik
    b6 = "6"
    tops = []
    for var in WEIGHT_VARS:
        w = model["weights"][var].get(b6, {})
        live = {m: v for m, v in w.items() if v > 0}
        if live:
            bm = max(live, key=live.get)
            tops.append(f"{var}: {bm} {live[bm]:.0%}")
    if tops:
        print("  Haest thyngd @6klst -> " + " | ".join(tops))
    return model

# --- 6. SPA ----------------------------------------------------------------
# ═══════════════════════════════════════════════════════════════════════
#  [SPA]  SPAGERD  <-- HER VERDUR SPAIN TIL
#  Blandar leidrettum medlimum med skilyrtum thyngdum, baetir vid
#  restleidrettingu, byggir klukkustunda- og dagaspa fyrir vefinn.
# ═══════════════════════════════════════════════════════════════════════

def make_forecast(fc, extras, model):
    print("SPA:")
    if fc is None:
        print("  Engin gogn"); return None

    ft  = fc["hourly"]["time"]
    et  = {k: (v["hourly"]["time"] if v else []) for k, v in extras.items()}
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    all_t = set(ft)
    for v in et.values(): all_t |= set(v)
    fut = [t for t in sorted(all_t) if t >= fmt_t(now)]

    J = {"generated": datetime.now(timezone.utc).isoformat(),
         "station": {"lat": LAT, "lon": LON, "id": STATION_ID,
                     "name": "Egilsstaðir", "icao": ICAO},
         "model_name": f"Jolly v{JOLLY_VERSION}",
         "runs": model.get("runs", 0),
         "verified_pairs": model.get("verified_pairs", 0),
         "lead_buckets": LEAD_BUCKETS,
         "weights": model["weights"],
         "lead_mae": model.get("lead_mae", {}),
         "skill": model.get("skill", {}),
         "jolly_bias": model.get("jolly_bias", {}),
         "cond_bias": model.get("cond_bias", {}),
         "cloud_confusion": model.get("cloud_confusion", {}),
         "models_used": ALL_KEYS,
         "attribution": ["Vedurstofa Islands (api.vedur.is, xmlweather)",
                         "MET Norway (api.met.no) CC BY 4.0",
                         "Open-Meteo CC BY 4.0",
                         "NOAA aviationweather.gov METAR"],
         "hourly": {"time": [], "lead_hours": [], "temperature": [], "windspeed": [],
                    "winddirection": [], "windgust": [], "precipitation": [],
                    "cloud_cover": [], "cloud_low": [], "cloud_mid": [],
                    "cloud_high": [], "visibility": [], "is_day": [],
                    "cell": [],  # [v5.1] reiturinn (spadri att) sem RED thyngdum/bias
                    "used_weights": [],  # [v5.2] raunveruleg thyngd HVERS gjafa,
                                          # HVERRAR breytu, thessa klukkustund
                    "icon": [], "condition": [], "beaufort": [],
                    "model_temperatures":   {m: [] for m in ALL_KEYS},
                    "model_windspeeds":     {m: [] for m in ALL_KEYS},
                    "model_winddirections": {m: [] for m in ALL_KEYS},
                    "model_precipitations": {m: [] for m in ALL_KEYS},
                    "model_clouds":         {m: [] for m in ALL_KEYS}},
         # slots[i] = {"06": {icon, condition, temp}, "12":..., "18":..., "00":...}
         "daily_slots": [],
         "slot_hours": DAY_SLOTS,
         "daily": {"date": [], "temp_max": [], "temp_min": [],
                   "precipitation_total": [], "wind_avg": [],
                   "wind_dir_dominant": [], "wind_dir_dominant_deg": [],
                   "cloud_avg": [], "icon": [], "condition": []}}

    for t in fut[:120]:
        lead = max(0, int((parse_t(t) - now).total_seconds() // 3600))
        bs   = str(lead_bucket(lead))          # fyrir thyngdir og talningar
        b_lo, b_hi, b_f = lead_interp(lead)    # fyrir bias - mjuk bruun
        i    = ft.index(t) if t in ft else None
        J["hourly"]["time"].append(t)
        J["hourly"]["lead_hours"].append(lead)

        T, W, P, D, C = [], [], [], [], []

        # Reitur thessarar klukkustundar fyrir skilyrt bias.
        # Vindatt framtidar er ekki maeld, svo vid notum GROFA attarspa
        # (medaltal hravrar attar likananna) + is_day til ad velja reit.
        raw_dirs = []
        for _m, _api in MODELS.items():
            if i is not None:
                _a = fc["hourly"].get(f"winddirection_10m_{_api}", [])
                if i < len(_a) and _a[i] is not None:
                    raw_dirs.append(_a[i])
        if raw_dirs:
            _ss = sum(math.sin(math.radians(d)) for d in raw_dirs)
            _cs = sum(math.cos(math.radians(d)) for d in raw_dirs)
            grov_att = math.degrees(math.atan2(_ss, _cs)) % 360
        else:
            grov_att = None
        _isd = None
        if i is not None:
            _a = fc["hourly"].get("is_day", [])
            if i < len(_a): _isd = _a[i]
        cur_cell = cond_key(grov_att, (_isd is None) or (_isd >= 0.5))
        # [v5.1] Geyma reitinn sem RED thyngdum/bias thessa klukkustund,
        # svo stadfesting geti sannreynt Jolly a moti REITNUM SEM HUN
        # RAUNVERULEGA NOTADI - ekki reit endurreiknudum ur mældri att.
        J["hourly"]["cell"].append(cur_cell)

        # Urkomureitur: att x THRYSTITHROUN (spad thrystifall/ris)
        _dp = None
        if i is not None:
            _pa = fc["hourly"].get("surface_pressure", [])
            if 0 <= i - 3 and i < len(_pa) and _pa[i] is not None \
               and _pa[i - 3] is not None:
                _dp = (_pa[i] - _pa[i - 3]) / 3.0
        cur_cell_p = cond_key_precip(grov_att, _dp)

        def WGT(var, m):
            """
            Thyngd likans i THESSUM adstaedum. Fellur aftur a almennu
            thyngdirnar ef reiturinn hefur ekki nog gogn.
            """
            c = cur_cell_p if var == "urkoma" else cur_cell
            wc = ((model.get("weights_cell", {}).get(var, {})
                       .get(bs, {}) or {}).get(c) or {})
            if m in wc:
                return wc[m]
            return model["weights"][var][bs].get(m, 0.0)

        # [v5.2] Safna RAUNVERULEGUM thyngdum allra gjafa, allra breyta,
        # thessa klukkustund - svo haegt se ad geyma their NAKVAEMLEGA
        # eins og thaer voru VID UTGAFU, ekki endurreikna their seinna ur
        # model-stodu sem hefur thegar breyst (weights_cell er EMA sem
        # uppfaerist i HVERRI keyrslu).
        hour_weights = {v: {} for v in WEIGHT_VARS}

        for m, api in MODELS.items():
            # Fjorar thyngdir - ein per breytu
            wv = {v: WGT(v, m) for v in WEIGHT_VARS}
            for _v in WEIGHT_VARS: hour_weights[_v][m] = wv[_v]
            b  = model["bias"][m][bs]
            bl = model["bias"][m][b_lo]
            bh = model["bias"][m][b_hi]
            # Bias bruad milli spalengdarholfa (mjukt i stad stalls), og
            # sidan skilyrt a vindatt/dag-nott med shrinkage.
            cb_hiti = blend2(
                member_bias(model, m, b_lo, cur_cell, "hiti", bl["hiti"]),
                member_bias(model, m, b_hi, cur_cell, "hiti", bh["hiti"]), b_f)
            cb_vindur = blend2(
                member_bias(model, m, b_lo, cur_cell, "vindur", bl["vindur"]),
                member_bias(model, m, b_hi, cur_cell, "vindur", bh["vindur"]), b_f)
            cb_att = blend2(
                member_bias(model, m, b_lo, cur_cell, "att", bl.get("att",0.0)),
                member_bias(model, m, b_hi, cur_cell, "att", bh.get("att",0.0)),
                b_f, angle=False)
            cb_scale = blend2(bl["urkoma_scale"], bh["urkoma_scale"], b_f)
            cb_thr   = blend2(precip_threshold(model, m, b_lo),
                              precip_threshold(model, m, b_hi), b_f)

            def g(key):
                if i is None: return None
                a = fc["hourly"].get(f"{key}_{api}", [])
                return a[i] if i < len(a) else None

            rt, rw, rp = g("temperature_2m"), g("windspeed_10m"), g("precipitation")
            rd = g("winddirection_10m")
            # Heildarhula med HAMARKSSKORUN - sky leggjast ekki saman
            rc = total_cloud(g("cloud_cover_low"), g("cloud_cover_mid"),
                             g("cloud_cover_high"), g("cloud_cover"))

            ct  = round(rt + cb_hiti, 1)                  if rt is not None else None
            cw  = round(max(0, rw + cb_vindur), 1)        if rw is not None else None
            cp  = apply_precip(rp, cb_scale, cb_thr)
            cc  = correct_cloud(rc, model, m, bs)

            cd_ = round(wrap360(rd + cb_att), 1) \
                  if rd is not None else None
            J["hourly"]["model_temperatures"][m].append(ct)
            J["hourly"]["model_windspeeds"][m].append(cw)
            J["hourly"]["model_winddirections"][m].append(cd_)
            J["hourly"]["model_precipitations"][m].append(cp)
            J["hourly"]["model_clouds"][m].append(cc)

            if ct is not None and wv["hiti"]   > 0: T.append((ct, wv["hiti"]))
            if cw is not None and wv["vindur"] > 0: W.append((cw, wv["vindur"]))
            # Vindatt hefur nu SINA eigin thyngd og sitt eigid bias
            if rd is not None and wv["att"] > 0:
                D.append((wrap360(rd + b.get("att", 0.0)), wv["att"]))
            if cc is not None and wv["sky"]    > 0: C.append((cc, wv["sky"]))
            if cp is not None and wv["urkoma"] > 0: P.append((cp, wv["urkoma"]))

        for k, src in extras.items():
            xv = {v: WGT(v, k) for v in WEIGHT_VARS}
            for _v in WEIGHT_VARS: hour_weights[_v][k] = xv[_v]
            xb = model["bias"][k][bs]
            xl = model["bias"][k][b_lo]; xh = model["bias"][k][b_hi]
            xcb_hiti = blend2(
                member_bias(model, k, b_lo, cur_cell, "hiti", xl["hiti"]),
                member_bias(model, k, b_hi, cur_cell, "hiti", xh["hiti"]), b_f)
            xcb_vindur = blend2(
                member_bias(model, k, b_lo, cur_cell, "vindur", xl["vindur"]),
                member_bias(model, k, b_hi, cur_cell, "vindur", xh["vindur"]), b_f)
            xcb_att = blend2(
                member_bias(model, k, b_lo, cur_cell, "att", xl.get("att",0.0)),
                member_bias(model, k, b_hi, cur_cell, "att", xh.get("att",0.0)), b_f)
            xcb_scale = blend2(xl["urkoma_scale"], xh["urkoma_scale"], b_f)
            xcb_thr   = blend2(precip_threshold(model, k, b_lo),
                               precip_threshold(model, k, b_hi), b_f)
            j  = et[k].index(t) if (src and t in et[k]) else None
            def ge(key, _src=src, _j=j):
                if _j is None or not _src: return None
                a = _src["hourly"].get(key, [])
                return a[_j] if _j < len(a) else None
            xT, xW, xP = ge("temperature"), ge("windspeed"), ge("precipitation")
            xD = ge("winddirection")
            # Hamarksskorun (MET Norway gefur login; HARMONIE gerir thad ekki
            # og fellur tha a sina heildartolu ur vedurtextanum)
            xC = total_cloud(ge("cloud_low"), ge("cloud_mid"),
                             ge("cloud_high"), ge("cloud_cover"))
            ct = round(xT + xcb_hiti, 1)                   if xT is not None else None
            cw = round(max(0, xW + xcb_vindur), 1)         if xW is not None else None
            cp = apply_precip(xP, xcb_scale, xcb_thr)
            cc = correct_cloud(xC, model, k, bs)
            cd_ = round(wrap360(xD + xcb_att), 1) \
                  if xD is not None else None
            J["hourly"]["model_temperatures"][k].append(ct)
            J["hourly"]["model_windspeeds"][k].append(cw)
            J["hourly"]["model_winddirections"][k].append(cd_)
            J["hourly"]["model_precipitations"][k].append(cp)
            J["hourly"]["model_clouds"][k].append(cc)
            if ct is not None and xv["hiti"]   > 0: T.append((ct, xv["hiti"]))
            if cw is not None and xv["vindur"] > 0: W.append((cw, xv["vindur"]))
            if xD is not None and xv["att"] > 0:
                D.append((wrap360(xD + xb.get("att", 0.0)), xv["att"]))
            if cc is not None and xv["sky"]    > 0: C.append((cc, xv["sky"]))
            if cp is not None and xv["urkoma"] > 0: P.append((cp, xv["urkoma"]))

        # [v5.2] Geyma thyngdir thessarar klukkustundar - eitt gildi i
        # J["hourly"]["used_weights"] per klukkustund, sama index og time/cell.
        J["hourly"]["used_weights"].append(hour_weights)

        def wa(p):
            if not p: return None
            tw = sum(w for _, w in p)
            return round(sum(v * w for v, w in p) / tw, 2) if tw > 0 else None

        def wang(p):
            if not p: return None
            tw = sum(w for _, w in p)
            if tw == 0: return None
            ss = sum(math.sin(math.radians(v)) * w for v, w in p)
            cs = sum(math.cos(math.radians(v)) * w for v, w in p)
            return round(math.degrees(math.atan2(ss / tw, cs / tw)) % 360, 1)

        temp, wind, prec = wa(T), wa(W), wa(P)
        wdir, cloud      = wang(D), wa(C)

        # --- RESTLEIDRETTING A JOLLY ---
        # Blondan sjalf getur haft hlutdraegni sem er ekki summa hlutanna.
        # Hun er laerd af Jolly-maelingunni og notud her, svo lykkjan se lokud.
        jbl = (model.get("jolly_bias") or {}).get(b_lo)
        jbh = (model.get("jolly_bias") or {}).get(b_hi)
        jb = None
        if jbl and jbh:
            jb = {k2: blend2(jbl.get(k2, 0.0), jbh.get(k2, 0.0), b_f)
                  for k2 in ("hiti", "vindur", "att", "sky")}
            jb["urkoma_scale"] = blend2(jbl.get("urkoma_scale", 1.0),
                                        jbh.get("urkoma_scale", 1.0), b_f)
        if jb:
            if temp is not None and APPLY_JOLLY_RESIDUAL.get("hiti"):
                temp = round(temp + jb.get("hiti", 0.0), 2)
            if wind is not None and APPLY_JOLLY_RESIDUAL.get("vindur"):
                wind = round(max(0.0, wind + jb.get("vindur", 0.0)), 2)
            if wdir is not None and APPLY_JOLLY_RESIDUAL.get("att"):
                wdir = round(wrap360(wdir + jb.get("att", 0.0)), 1)
            if prec is not None:      # urkoma-skali alltaf notadur (v2.x)
                prec = round(max(0.0, prec * jb.get("urkoma_scale", 1.0)), 2)
            if cloud is not None and APPLY_JOLLY_RESIDUAL.get("sky"):
                cloud = min(100.0, max(0.0, cloud + jb.get("sky", 0.0)))

        # --- GREINING: syna blondu OG restbias fyrir ALLAR breytur ---
        # Adeins fyrir NUVERANDI stund (lead 0-1) svo haegt se ad bera
        # beint saman vid nyjustu maelingu - ekki framtidarspa.
        if lead <= 1 and temp is not None:
            _bt, _bw, _bc = wa(T), wa(W), wa(C)
            _bd = wang(D)
            _jh = jb.get("hiti", 0.0) if jb else 0.0
            _jw = jb.get("vindur", 0.0) if jb else 0.0
            _jc = jb.get("sky", 0.0) if jb else 0.0
            _jd = jb.get("att", 0.0) if jb else 0.0
            print(f"  [SPA-GREINING @{lead}klst - berid saman vid maelingu ofar]")
            print(f"    hiti  : blanda {_bt} {_jh:+.2f} -> {temp}")
            print(f"    vindur: blanda {_bw} {_jw:+.2f} -> {wind}")
            print(f"    att   : blanda {_bd} {_jd:+.1f} -> {wdir}")
            print(f"    sky   : blanda {_bc} {_jc:+.1f} -> "
                  f"{round(cloud) if cloud is not None else None}")
            print(f"    medlimir i blondu: hiti={len(T)} vindur={len(W)} "
                  f"sky={len(C)} att={len(D)} (af {len(ALL_KEYS)})")
            for _nm, _n in (("hiti", len(T)), ("vindur", len(W)),
                            ("sky", len(C)), ("att", len(D))):
                if _n < 4:
                    warn(f"adeins {_n} medlimir i {_nm}-blondu (af "
                         f"{len(ALL_KEYS)}) - fjolbreytni tapast")
            # Hrair medlimir - til ad sja hvort BIAS eda BLONDUN skemmir
            _raw_t = [round(v,1) for v,_ in T]
            _raw_w = [round(v,1) for v,_ in W]
            print(f"    leidrettir medlimir hiti: {_raw_t}")
            print(f"    leidrettir medlimir vind: {_raw_w}")

        def avg_raw(prefix):
            if i is None: return None
            return mean([fc["hourly"].get(f"{prefix}_{a}", [None] * (i + 1))[i]
                         if i < len(fc["hourly"].get(f"{prefix}_{a}", [])) else None
                         for a in MODELS.values()])

        c_low, c_mid  = avg_raw("cloud_cover_low"), avg_raw("cloud_cover_mid")
        c_high, vis   = avg_raw("cloud_cover_high"), avg_raw("visibility")
        cape, gust    = avg_raw("cape"), avg_raw("windgusts_10m")
        isd           = avg_raw("is_day")
        is_day        = (isd is None) or (isd >= 0.5)

        J["hourly"]["temperature"].append(temp)
        J["hourly"]["windspeed"].append(wind)
        J["hourly"]["winddirection"].append(wdir)
        J["hourly"]["windgust"].append(round(gust, 1) if gust is not None else None)
        J["hourly"]["precipitation"].append(prec)
        J["hourly"]["cloud_cover"].append(round(cloud) if cloud is not None else None)
        J["hourly"]["cloud_low"].append(round(c_low) if c_low is not None else None)
        J["hourly"]["cloud_mid"].append(round(c_mid) if c_mid is not None else None)
        J["hourly"]["cloud_high"].append(round(c_high) if c_high is not None else None)
        J["hourly"]["visibility"].append(round(vis) if vis is not None else None)
        J["hourly"]["is_day"].append(1 if is_day else 0)
        J["hourly"]["icon"].append(
            determine_icon(cloud, prec, temp, is_day, vis, wind, cape))
        J["hourly"]["condition"].append(
            describe(cloud, prec, temp, vis, wind, cape))
        J["hourly"]["beaufort"].append(beaufort(wind))

    # Dagleg samantekt
    H, days = J["hourly"], {}
    for i, t in enumerate(H["time"]):
        d = t[:10]
        days.setdefault(d, {"T": [], "W": [], "D": [], "P": [], "C": [],
                            "icons": [], "conds": []})
        for k, arr in (("T", "temperature"), ("W", "windspeed"),
                       ("D", "winddirection"), ("P", "precipitation"),
                       ("C", "cloud_cover")):
            if H[arr][i] is not None: days[d][k].append(H[arr][i])
        if H["is_day"][i] == 1:
            days[d]["icons"].append(H["icon"][i])
            days[d]["conds"].append(H["condition"][i])

    # Uppflettitafla: gildistimi -> vísitala, til ad finna raufirnar
    idx_of = {t: i for i, t in enumerate(H["time"])}

    def slot_data(day_str, slot):
        """
        Saekir tákn/lysingu/hita fyrir eina tímaraut.
        '00' er midnaetti NAESTA dags - thad lykur deginum.
        """
        if slot == "00":
            dt = datetime.strptime(day_str, "%Y-%m-%d") + timedelta(days=1)
            key = dt.strftime("%Y-%m-%d") + "T00:00"
        else:
            key = f"{day_str}T{slot}:00"
        i = idx_of.get(key)
        if i is None:
            return None
        return {
            "icon":      H["icon"][i],
            "condition": H["condition"][i],
            "temp":      H["temperature"][i],
            "precip":    H["precipitation"][i],
            "cloud":     H["cloud_cover"][i],
        }

    for d, v in days.items():
        dom_dir = dom_deg = None
        if v["D"]:
            labels  = [deg_to_dir(x) for x in v["D"]]
            dom_dir = Counter(labels).most_common(1)[0][0]
            match   = [x for x, l in zip(v["D"], labels) if l == dom_dir]
            ss = sum(math.sin(math.radians(x)) for x in match)
            cs = sum(math.cos(math.radians(x)) for x in match)
            dom_deg = round(math.degrees(math.atan2(ss, cs)) % 360, 1)
        cavg = mean(v["C"])
        J["daily"]["date"].append(d)
        J["daily"]["temp_max"].append(round(max(v["T"]), 1) if v["T"] else None)
        J["daily"]["temp_min"].append(round(min(v["T"]), 1) if v["T"] else None)
        J["daily"]["precipitation_total"].append(round(sum(v["P"]), 1) if v["P"] else 0)
        J["daily"]["wind_avg"].append(round(mean(v["W"]), 1) if v["W"] else None)
        J["daily"]["wind_dir_dominant"].append(dom_dir)
        J["daily"]["wind_dir_dominant_deg"].append(dom_deg)
        J["daily"]["cloud_avg"].append(round(cavg) if cavg is not None else None)
        J["daily"]["icon"].append(
            Counter(v["icons"]).most_common(1)[0][0] if v["icons"] else "overcast")
        J["daily"]["condition"].append(
            Counter(v["conds"]).most_common(1)[0][0] if v["conds"] else "")
        J["daily_slots"].append({sl: slot_data(d, sl) for sl in DAY_SLOTS})

    filled = sum(1 for sd in J["daily_slots"]
                 for sl in DAY_SLOTS if sd.get(sl))
    print(f"  OK {len(H['time'])} klst | {len(J['daily']['date'])} dagar | "
          f"{filled} timaraufir fylltar")
    return J

# ═══════════════════════════════════════════════════════════════════════
#  [YFIRLIT]  YFIRLIT I LOGG
#  YFIRLIT-taflan, skilyrt bias, skilyrtar thyngdir, fallin likon.
# ═══════════════════════════════════════════════════════════════════════

def print_coverage(model, fc, extras):
    """
    Yfirlit yfir hvada gjafi skilar hverri breytu og hvada thyngd hann
    hefur fengid. Thetta svarar spurningunni "virkar thetta a oll likonin"
    empiriskt i hverri keyrslu i stad thess ad giska.
    """
    print("YFIRLIT (@6 klst):")
    print("  gjafi      hiti        vindur      att         urkoma      sky")

    RAW = {"hiti": "temperature_2m", "vindur": "windspeed_10m",
           "att": "winddirection_10m",
           "urkoma": "precipitation", "sky": "cloud_cover"}
    bs = "6"
    lm = model.get("lead_mae", {}).get(bs, {})

    def has_raw(m):
        """Skilar hvada breytur gjafinn skilar i HRAU spanni."""
        out = {}
        if m in MODELS and fc:
            api = MODELS[m]
            for v, key in RAW.items():
                arr = fc["hourly"].get(f"{key}_{api}", [])
                out[v] = any(x is not None for x in arr)
        elif m in extras and extras.get(m):
            src = extras[m]["hourly"]
            keymap = {"hiti": "temperature", "vindur": "windspeed",
                      "att": "winddirection",
                      "urkoma": "precipitation", "sky": "cloud_cover"}
            for v, key in keymap.items():
                out[v] = any(x is not None for x in src.get(key, []))
        else:
            out = {v: False for v in WEIGHT_VARS}
        return out

    dead = []
    for m in ALL_KEYS:
        raw  = has_raw(m)
        cells = []
        for v in WEIGHT_VARS:
            w  = model["weights"].get(v, {}).get(bs, {}).get(m, 0.0)
            st = lm.get(m, {})
            n  = (st.get("n_var") or {}).get(v, 0)
            e  = st.get(v)
            if not raw.get(v):
                cells.append("  --gogn   ")
            elif e is None or n < MIN_N_BY_VAR[v]:
                cells.append(f" bid n={n:<3} ")
            else:
                cells.append(f"{e:5.1f} {w:4.0%} ")
        if not any(raw.values()):
            dead.append(m)
        print(f"  {m:9s} " + "".join(cells))

    # Jolly sjalf - til samanburdar, an thyngdar
    jst = lm.get(JOLLY_KEY)
    if jst:
        cells = []
        for v in WEIGHT_VARS:
            e = jst.get(v)
            cells.append(f"{e:5.1f}   -  " if e is not None else "  bid     ")
        print("  " + "-" * 62)
        print(f"  {'JOLLY':9s} " + "".join(cells))
        jb = (model.get("jolly_bias") or {}).get(bs)
        if jb:
            # Restbias a thakinu = leidrettingin naer ekki jafnvaegi
            for _v, _cap in (("hiti", JOLLY_BIAS_CAP.get("hiti", 1.5)),
                             ("vindur", JOLLY_BIAS_CAP.get("vindur", 1.5)),
                             ("att", JOLLY_BIAS_CAP.get("att", 12.0)),
                             ("sky", JOLLY_BIAS_CAP.get("sky", 12.0))):
                _val = abs(jb.get(_v, 0.0) or 0.0)
                if _cap and _val >= _cap * 0.95:
                    warn(f"restbias {_v} a thakinu ({jb.get(_v,0):+.2f} af "
                         f"{_cap}) - naer ekki jafnvaegi")
            _on  = [v for v in ("hiti","vindur","att","sky")
                    if APPLY_JOLLY_RESIDUAL.get(v)]
            _off = [v for v in ("hiti","vindur","att","sky")
                    if not APPLY_JOLLY_RESIDUAL.get(v)]
            _tag = (f"  (VIRK: {','.join(_on) or '-'} | "
                    f"OVIRK: {','.join(_off) or '-'})")
            print(f"  restbias{_tag}   hiti {jb.get('hiti',0):+.2f}  "
                  f"vind {jb.get('vindur',0):+.2f}  "
                  f"att {jb.get('att',0):+.1f}  "
                  f"urk x{jb.get('urkoma_scale',1):.2f}  "
                  f"sky {jb.get('sky',0):+.1f}")

    if dead:
        print(f"  ENGIN GOGN: {', '.join(dead)} -> thyngd 0 a ollum breytum")

    # [v5.3] YFIRLIT VIÐ ALLAR SPALENGDIR - adur var ADEINS synt vid 6klst
    # (thessi 'bs = "6"' fastlyklun ofar), svo vid vissum ALDREI hvernig
    # Jolly og medlimir stodu sig vid 1/3/12/24/48 klst - nam var i lagi
    # (cell_mae/weights_cell/cond_bias eru RETT lyklud eftir spalengd), en
    # SKYRSLUGERDIN sjalf var blind. Nu: eitt yfirlit per spalengd, hiti.
    print()
    print("YFIRLIT HITA VID ALLAR SPALENGDIR (MAE í °C, þyngd í svigum):")
    print("  gjafi    " + "".join(f"{str(b)+'kl':>11}" for b in LEAD_BUCKETS))
    for m in list(ALL_KEYS) + [JOLLY_KEY]:
        row = []
        for b in LEAD_BUCKETS:
            _bs = str(b)
            _lm = model.get("lead_mae", {}).get(_bs, {}).get(m, {})
            _n  = (_lm.get("n_var") or {}).get("hiti", 0)
            _e  = _lm.get("hiti")
            if m == JOLLY_KEY:
                # [v5.4] SYNA 'n' fyrir JOLLY LIKA - adur sast adeins MAE,
                # svo tolur eins og 3.08 vid 24kl gatu verid 1 hávaðapar
                # eda 200 stodug pör, og vid höfðum ENGA leið að greina þar á milli.
                row.append(f"{_e:5.2f}(n{_n:<3})" if _e is not None else "  bid n=0  ")
            else:
                _w = model.get("weights", {}).get("hiti", {}).get(_bs, {}).get(m, 0.0)
                if _e is None or _n < MIN_N_BY_VAR["hiti"]:
                    row.append(f"  bid n={_n:<3}")
                else:
                    row.append(f"{_e:5.2f}({_w:3.0%})")
        if m == JOLLY_KEY:
            print("  " + "-"*(9+11*len(LEAD_BUCKETS)))
        print(f"  {m:9s}" + "".join(f"{c:>11}" for c in row))

    # [v5.3] Skilyrt bias VID ALLAR SPALENGDIR - adur adeins @6klst.
    # Nam sjalft var alltaf rett lyklad (cb[m][bs][cell][var]) - thetta
    # var eingongu skyrslugerd sem faldi 1/3/12/24/48 klst.
    cb = model.get("cond_bias", {})
    if cb:
        for _bs in [str(b) for b in LEAD_BUCKETS]:
            print(f"  SKILYRT HITABIAS (@{_bs} klst, reitir med >= "
                  f"{COND_MIN_N} por):")
            shown = False
            for m in ALL_KEYS:
                cells = (cb.get(m, {}) or {}).get(_bs, {})
                parts = []
                for cell in ["N-dagur","A-dagur","S-dagur","V-dagur",
                             "N-nott","A-nott","S-nott","V-nott"]:
                    e = (cells.get(cell) or {}).get("hiti")
                    if e and e["n"] >= COND_MIN_N:
                        parts.append(f"{cell} {-(e['sum']/e['n']):+.1f}(n{e['n']})")
                if parts:
                    print(f"    {m:9s} " + "  ".join(parts))
                    shown = True
            if not shown:
                print("    (reitir enn ad byggjast upp - tharf fleiri stadfestingar)")
    print("  ('--gogn' = gjafinn skilar ekki breytunni | "
          "'bid' = of fair samanburdir enn)")

    # [v5.3] SKILYRTAR THYNGDIR VID ALLAR SPALENGDIR - adur adeins @6klst.
    # weights_cell er RETT lyklad eftir spalengd nu thegar (v4.1) - thetta
    # var eingongu skyrslugerd sem faldi 1/3/12/24/48 klst algjorlega.
    wc_all = model.get("weights_cell", {})
    if wc_all:
        for _bs in [str(b) for b in LEAD_BUCKETS]:
            any_shown = False
            lines = []
            for var in WEIGHT_VARS:
                cells = (wc_all.get(var, {}).get(_bs, {}) or {})
                if not cells:
                    continue
                for cname in sorted(cells):
                    w = cells[cname]
                    top = sorted(((v, k) for k, v in w.items() if v > 0),
                                 reverse=True)[:3]
                    if top:
                        txt = " | ".join(f"{k} {v*100:.0f}%" for v, k in top)
                        lines.append(f"    {var:7} {cname:10} {txt}")
                        any_shown = True
            if any_shown:
                print(f"  SKILYRTAR THYNGDIR @{_bs}klst (hver er bestur i hvada adstaedum):")
                for ln in lines: print(ln)
    # Sannleiksmaelirinn - obrengladur samanburdur
    try:
        truth_print(globals().get("_TRUTH_TBL") or {})
    except Exception as e:
        print(f"  (sannleikstafla: {e})")
    # [v5.3] Fallin likon VID ALLAR SPALENGDIR - adur adeins @6klst.
    # failed{} er RETT lyklad eftir spalengd nu thegar - eingongu
    # skyrslugerdin var blind a 1/3/12/24/48 klst.
    _f = model.get("failed", {})
    for _bs in [str(b) for b in LEAD_BUCKETS]:
        _lines = []
        for _v in WEIGHT_VARS:
            _o = sorted(m for m, r in (_f.get(_v, {}).get(_bs, {}) or {}).items()
                        if r.get("out"))
            if _o:
                _lines.append(f"    {_v}: {', '.join(_o)}")
        if _lines:
            print(f"  FALLIN LIKON @{_bs}klst (0 vaegi, enn maeld, geta komid aftur):")
            for _l in _lines:
                print(_l)


# --- 7. VISTA --------------------------------------------------------------
# ═══════════════════════════════════════════════════════════════════════
#  [KEYRSLA]  VISTUN OG KEYRSLA
#  Skrifar JSON + logg med STODU-blokk efst. main() og _run().
# ═══════════════════════════════════════════════════════════════════════

def save_log(tee):
    """
    Vistar loggann i repoid, MED STODU-BLOKK EFST.
    Blokkin er sett fremst svo eitt augnablik nagi til ad sja hvort
    eitthvad se ad - i stad thess ad lesa 200 linur.
    """
    if tee is None: return
    try:
        body = tee.text()
        (DATA_DIR / "last_run.log").write_text(
            health_block() + body, encoding="utf-8")
    except Exception as e:
        sys.__stdout__.write(f"  Gat ekki vistad logg: {e}\n")


def append_mae_history(model):
    """
    Geymir EITT snapshot a dag af MAE hvers gjafa (@6klst, allar breytur)
    + Jolly sjalfrar, i docs/data/mae_history.json. Thetta er ADSKILID
    fra jolly_model.json - engin ahrif a spa eda naam, adeins gagnasafn
    fyrir bakvirka throun-graf a vefnum (Nanar-sidan).

    Eitt gildi A DAG (ekki a klst fresti) - annars vex skrain of hratt og
    dag-fyrir-dag throun er hvort ed er thad sem skiptir mali, ekki
    klukkustunda-suð.
    """
    path = DATA_DIR / "mae_history.json"
    hist = load_json(path, {"days": []})
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    row = {"d": today}
    for var in WEIGHT_VARS:
        lm = model.get("lead_mae", {}).get("6", {})
        row[var] = {}
        for m in list(ALL_KEYS) + [JOLLY_KEY]:
            v = (lm.get(m) or {}).get(var)
            if v is not None:
                row[var][m] = round(v, 3)

    if hist["days"] and hist["days"][-1]["d"] == today:
        hist["days"][-1] = row           # uppfaera daginn i stad thess ad tvitaka
    else:
        hist["days"].append(row)
    hist["days"] = hist["days"][-90:]    # 90 daga gluggi - nog fyrir throun
    save_json(path, hist)


def save(model, fcast):
    save_json(DATA_DIR / "jolly_model.json", model)
    try:
        append_mae_history(model)
    except Exception as e:
        print(f"  (mae_history: {e})")
    if fcast:
        save_json(DATA_DIR / "jolly_forecast.json", fcast)
    log = load_json(DATA_DIR / "run_log.json", [])
    log.append({"time": datetime.now(timezone.utc).isoformat(),
                "runs": model.get("runs", 0),
                "verified_pairs": model.get("verified_pairs", 0),
                "status": "ok" if fcast else "partial",
                "version": JOLLY_VERSION})
    save_json(DATA_DIR / "run_log.json", log[-168:])
    print("VISTAD")

# --- MAIN ------------------------------------------------------------------
def main():
    tee = Tee()
    sys.stdout = tee
    try:
        _run()
    finally:
        sys.stdout = sys.__stdout__
        save_log(tee)


def _run():
    print("=" * 64)
    print(f"JOLLY v{JOLLY_VERSION}  "
          f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("Eiginleg spastadfesting eftir spalengd | 9 gjafar | stod 571 + BIEG")
    print("=" * 64)

    metar        = fetch_metar()
    obs, _fresh  = fetch_and_store_observations(metar)
    fc           = fetch_forecasts()
    extras       = {"harmonie": fetch_harmonie(),
                    "metno":    fetch_metno()}

    print("LIKAN:")
    model = load_model()

    arch  = archive_forecast(fc, extras)
    model = verify_and_train(arch, obs, model)
    fcast = make_forecast(fc, extras, model)
    arch  = archive_jolly(arch, fcast)      # eftir spa - Jolly er nidurstadan
    print_coverage(model, fc, extras)
    save(model, fcast)

    print("=" * 64)
    for var in WEIGHT_VARS:
        w6 = model["weights"].get(var, {}).get("6", {})
        top = sorted(((m, v) for m, v in w6.items() if v > 0),
                     key=lambda x: -x[1])[:4]
        if top:
            print(f"Thyngdir {var:7s} @6klst: "
                  + " | ".join(f"{m} {v:.0%}" for m, v in top))
    # Sogusamanburdur: throun milli keyrslna (t.d. restbias sem vex)
    try:
        _jb6 = (model.get("jolly_bias") or {}).get("6") or {}
        for _m in health_history({
                "t": fmt_t(datetime.now(timezone.utc)),
                "v": JOLLY_VERSION,
                "np": globals().get("_N_NEW_PAIRS", 0),
                "rb": {k: _jb6.get(k) for k in ("hiti","vindur","att","sky")}}):
            warn(_m, alvarlegt=True)
    except Exception as _e:
        print(f"  (heilsusaga: {_e})")

    print()
    print(health_block().rstrip())
    print()
    print(f"Keyrslur {model.get('runs',0)} | "
          f"stadfest por {model.get('verified_pairs',0)}")
    sk = model.get("skill", {})
    shown = False
    for var in WEIGHT_VARS:
        rows = sk.get(var, {})
        if not rows: continue
        parts = [f"{b}kl {rows[str(b)]['skill']:+.0%}"
                 for b in LEAD_BUCKETS if str(b) in rows]
        if parts:
            print(f"Jolly {var:7s} a moti besta likani: " + " | ".join(parts))
            shown = True
    if not shown:
        print("Jolly ekki stadfest enn - kemur eftir naestu klukkustund")
    print("=" * 64)

if __name__ == "__main__":
    main()
