"""
Jolly v2.0 - Stadbundid vedurspalikan fyrir Egilsstadi (stod 571 / BIEG)

NYTT I v2.0: EIGINLEG SPASTADFESTING
  Jolly geymir nu sina eigin spa vid utgafu i forecast_archive.json og
  stadfestir hana sidar gegn raunverulegum maelingum. Thad fjarlaegir
  framsynisskekkjuna sem var i v1.x, thar sem borid var saman vid nyjustu
  likanutgafu fyrir lidna tima - likan sem hafdi thegar innbyrt maelingarnar.

  Bias og thyngdir eru nu laerd SER FYRIR HVERJA SPALENGD (1/3/6/12/24/48 klst),
  thvi skekkja i 48 klst spa er allt onnur en i 1 klst spa.
"""

import json, math, re
import urllib.request, urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path
import xml.etree.ElementTree as ET
from collections import Counter

# --- STILLINGAR ------------------------------------------------------------
LAT, LON   = 65.2620, -14.4035
STATION_ID = 571
ICAO       = "BIEG"
DATA_DIR   = Path("docs/data")
DATA_DIR.mkdir(exist_ok=True, parents=True)

OBS_HISTORY_HOURS = 720     # 30 dagar af maelingum
ARCHIVE_KEEP_PAST = 12      # klst aftur sem safnid heldur ostadfestum spam
ARCHIVE_HORIZON   = 48      # hversu langt fram vid geymum spa til stadfestingar
LEAD_BUCKETS      = [1, 3, 6, 12, 24, 48]
LR                = 0.12    # laerdomshraedi

# Likon sott gegnum Open-Meteo
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

# --- MET Norway (api.met.no) --------------------------------------------
# Skilmalar krefjast einkennandi User-Agent med tengilid. Almennur eda
# vantandi UA gefur 403 Forbidden - ekki haegingu. Hnit mest 4 aukastafir.
METNO_UA  = ("Jolly-Weather/2.1 "
             "(+https://github.com/Blodnasir10/jolly-weather)")
METNO_URL = ("https://api.met.no/weatherapi/locationforecast/2.0/complete"
             f"?lat={LAT:.4f}&lon={LON:.4f}&altitude=23")   # BIEG er i 23 m

# HARMONIE-kerfid er a 2 km yfir Island, hnattlikonin a 9-25 km
MODEL_BONUS = {"harmonie": 1.20, "dmi": 1.15, "knmi": 1.10}

HOURLY_VARS = ",".join([
    "temperature_2m", "dew_point_2m", "relative_humidity_2m",
    "windspeed_10m", "winddirection_10m", "windgusts_10m",
    "precipitation", "weathercode",
    "cloud_cover", "cloud_cover_low", "cloud_cover_mid", "cloud_cover_high",
    "visibility", "cape", "is_day",
])

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
        with urllib.request.urlopen(req, timeout=timeout) as r:
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

def lead_bucket(h):
    """Naesta spalengdarhólf fyrir spalengd h (klst)."""
    if h <= 2:  return 1
    if h <= 4:  return 3
    if h <= 9:  return 6
    if h <= 18: return 12
    if h <= 36: return 24
    return 48

# --- TAKNAVAL --------------------------------------------------------------
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

def cloud_class(pct):
    if pct is None: return None
    if pct < 10: return "heidskirt"
    if pct < 30: return "lettskyjad"
    if pct < 55: return "skyjad_hluta"
    if pct < 80: return "halfskyjad"
    if pct < 95: return "mestu_skyjad"
    return "alskyjad"

# --- 1. METAR --------------------------------------------------------------
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
        l = obs[-1]
        print(f"  OK {len(obs)} faerslur | nyjust {l['time']} "
              f"sky={l['cloud_cover']}% botn={l['cloud_base_ft']}ft")
        return obs
    except Exception as e:
        print(f"  VILLA: {e}")
        return []

# --- 2. MAELINGAR ----------------------------------------------------------
def fetch_and_store_observations(metar_obs):
    print("MAELING stod 571:")
    path = DATA_DIR / "obs_history.json"
    hist = load_json(path, [])
    by_t = {h["time"]: h for h in hist}
    fresh = []   # timapunktar sem uppfaerdust nuna

    url = f"https://apis.is/weather/observations/is?stations={STATION_ID}&time=1h"
    try:
        res = fetch_url(url).get("results", [])
        if res:
            r  = res[0]
            dt = datetime.strptime(r.get("time", "").strip(), "%Y-%m-%d %H:%M:%S")
            t  = fmt_t(dt.replace(tzinfo=timezone.utc))
            def gv(k):
                try:
                    v = r.get(k, "")
                    return float(v) if v and str(v).strip() not in ("", "-") else None
                except Exception:
                    return None
            rec = by_t.get(t, {"time": t})
            rec.update({"temperature": gv("T"), "windspeed": gv("F"),
                        "windgust": gv("FG"),
                        "winddirection": dir_to_deg(r.get("D", "")),
                        "precipitation": gv("R"), "humidity": gv("RH"),
                        "pressure": gv("P"), "weather_desc": r.get("W", ""),
                        "source": "apis.is-571"})
            by_t[t] = rec
            fresh.append(t)
            print(f"  OK {t} | T={rec['temperature']} F={rec['windspeed']}")
        else:
            print("  Engar nidurstodur")
    except Exception as e:
        print(f"  VILLA apis.is: {e}")

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
            cc = next((v for k, v in WEATHER_TO_CLOUD.items() if k in w), None)
            h["hourly"]["cloud_cover"].append(cc)
        if not h["hourly"]["time"]: raise ValueError("engir timapunktar")
        print(f"  OK {len(h['hourly']['time'])} timapunktar")
        return h
    except Exception as e:
        print(f"  VILLA: {e}")
        return None

# --- 4. GEYMA SPA TIL STADFESTINGAR ---------------------------------------
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
                rec = {"t": g("temperature_2m"), "w": g("windspeed_10m"),
                       "p": g("precipitation"),  "c": g("cloud_cover")}
                if any(v is not None for v in rec.values()):
                    models[m] = rec

        for k, src in extras.items():
            if not src or vt not in et[k]: continue
            j = et[k].index(vt)
            def ge(key, _src=src, _j=j):
                a = _src["hourly"].get(key, [])
                return a[_j] if _j < len(a) else None
            rec = {"t": ge("temperature"), "w": ge("windspeed"),
                   "p": ge("precipitation"), "c": ge("cloud_cover")}
            if any(v is not None for v in rec.values()):
                models[k] = rec

        if models:
            arch.setdefault(vt, {})[str(lead)] = {"issue": issue, "models": models}
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

# --- 5. STADFESTA OG THJALFA ----------------------------------------------
def empty_bias():
    return {"hiti": 0.0, "vindur": 0.0, "sky": 0.0, "urkoma_scale": 1.0}

def init_model():
    return {
        "version": "2.1",
        "created": datetime.now(timezone.utc).isoformat(),
        "runs": 0,
        "verified_pairs": 0,
        "lead_buckets": LEAD_BUCKETS,
        # bias[likan][spalengd] = {hiti, vindur, sky, urkoma_scale}
        "bias": {m: {str(b): empty_bias() for b in LEAD_BUCKETS} for m in ALL_KEYS},
        # weights[spalengd][likan]
        "weights": {str(b): {m: 1.0 / len(ALL_KEYS) for m in ALL_KEYS}
                    for b in LEAD_BUCKETS},
        # lead_mae[spalengd][likan] = {hiti, vindur, sky, n}
        "lead_mae": {str(b): {} for b in LEAD_BUCKETS},
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
    ow = old.get("weights", {})
    if ow:
        tot = sum(v for v in ow.values() if v)
        if tot > 0:
            for b in LEAD_BUCKETS:
                new["weights"][str(b)] = {m: round(ow.get(m, 0.0) / tot, 4)
                                          for m in ALL_KEYS}
    new["migrated_from"] = old.get("version", "1.x")
    print(f"  Faerdi {seeded} likon ur v{new['migrated_from']} - "
          f"bias notad sem upphafsgildi fyrir allar spalengdir")
    return new

def load_model():
    path = DATA_DIR / "jolly_model.json"
    raw  = load_json(path, None)
    if raw is None:
        print("  Nytt likan v2.1")
        return init_model()
    if raw.get("version", "").startswith("2."):
        # tryggja ad allir lyklar seu til
        for m in ALL_KEYS:
            raw.setdefault("bias", {}).setdefault(m, {})
            for b in LEAD_BUCKETS:
                raw["bias"][m].setdefault(str(b), empty_bias())
        for b in LEAD_BUCKETS:
            raw.setdefault("weights", {}).setdefault(
                str(b), {m: 1.0 / len(ALL_KEYS) for m in ALL_KEYS})
            raw.setdefault("lead_mae", {}).setdefault(str(b), {})
            for m in ALL_KEYS:
                raw["weights"][str(b)].setdefault(m, 0.0)
        print(f"  Hladid v2.x - {raw.get('runs',0)} keyrslur, "
              f"{raw.get('verified_pairs',0)} stadfest por")
        return raw
    return migrate_model(raw)

VAR_MAP = [("hiti", "t", "temperature"),
           ("vindur", "w", "windspeed"),
           ("urkoma", "p", "precipitation"),
           ("sky", "c", "cloud_cover")]

def verify_and_train(arch, obs_history, model):
    """
    Ber geymdar spar saman vid raunverulegar maelingar og laerir bias
    ser fyrir hverja spalengd. Thetta er eiginleg spastadfesting.
    """
    print("STADFESTING:")
    obs_by_t = {o["time"]: o for o in obs_history}

    # pairs[spalengd][likan][breyta] = [(maeling, spa), ...]
    pairs = {str(b): {m: {v: [] for v, _, _ in VAR_MAP} for m in ALL_KEYS}
             for b in LEAD_BUCKETS}
    n_pairs = 0
    verified_times = set()

    for vt, leads in arch.items():
        o = obs_by_t.get(vt)
        if not o: continue
        for lead_s, entry in leads.items():
            if lead_s not in pairs: continue
            # Hvert par er adeins laert EINU SINNI. Annars ytir sama
            # maelingin bias-inu itrekad, thvi safnid heldur faerslum
            # i ARCHIVE_KEEP_PAST klst eftir gildistima.
            if entry.get("done"): continue
            used = False
            for m, fcv in entry.get("models", {}).items():
                if m not in ALL_KEYS: continue
                for var, fkey, okey in VAR_MAP:
                    ov, fv = o.get(okey), fcv.get(fkey)
                    if ov is not None and fv is not None:
                        pairs[lead_s][m][var].append((ov, fv))
                        n_pairs += 1
                        used = True
            if used:
                entry["done"] = True
                entry["verified_at"] = fmt_t(datetime.now(timezone.utc))
                verified_times.add(vt)

    if n_pairs == 0:
        n_done = sum(1 for l in arch.values() for e in l.values() if e.get("done"))
        print("  Ekkert nytt til stadfestingar")
        print(f"  (safnid: {len(arch)} gildistimar, {n_done} thegar stadfest, "
              f"maelingar: {len(obs_by_t)})")
        model["runs"] = model.get("runs", 0) + 1
        model["last_updated"] = datetime.now(timezone.utc).isoformat()
        return model

    print(f"  {n_pairs} NY stadfest por a {len(verified_times)} gildistimum")
    save_json(DATA_DIR / "forecast_archive.json", arch)   # varðveita "done"

    summary = {}
    for b in LEAD_BUCKETS:
        bs = str(b)
        summary[bs] = {}
        for m in ALL_KEYS:
            pv = pairs[bs][m]
            if not any(pv.values()): continue
            bias_rec = model["bias"][m][bs]

            for var in ("hiti", "vindur", "sky"):
                if pv[var]:
                    nb = bias(pv[var]) or 0.0
                    bias_rec[var] = (1 - LR) * bias_rec[var] + LR * (-nb)
            if pv["urkoma"]:
                om = mean([o for o, _ in pv["urkoma"]])
                fm = mean([f for _, f in pv["urkoma"]])
                if om is not None and fm and fm > 0:
                    bias_rec["urkoma_scale"] = ((1 - LR) * bias_rec["urkoma_scale"]
                                                + LR * (om / fm))

            # MAE thessarar keyrslu, eftir bias-leidrettingu
            corr = lambda var: [(o, f + bias_rec[var]) for o, f in pv[var]]
            run_mae = {"hiti":   mae(corr("hiti")),
                       "vindur": mae(corr("vindur")),
                       "sky":    mae(corr("sky"))}

            # Safna MAE upp milli keyrslna. Hver keyrsla stadfestir adeins
            # einn nyjan gildistima per spalengd, svo eitt maelingasett
            # er alltof lidid til ad reikna thyngd ur. Vid geymum thvi
            # veldisjafnad medaltal og fjolda samanburda.
            store = model["lead_mae"][bs].setdefault(
                m, {"hiti": None, "vindur": None, "sky": None, "n": 0})
            for var in ("hiti", "vindur", "sky"):
                v = run_mae[var]
                if v is None: continue
                prev = store.get(var)
                store[var] = round(v, 3) if prev is None \
                             else round((1 - LR) * prev + LR * v, 3)
            store["n"] = store.get("n", 0) + len(pv["hiti"])

            summary[bs][m] = {"hiti": store["hiti"] or 0.0,
                              "vindur": store["vindur"] or 0.0,
                              "sky": store["sky"] or 0.0,
                              "n": store["n"]}

        # Thyngdir fyrir thessa spalengd, ur uppsofnudu MAE.
        # MIN_N: nog margir samanburdir til ad talan se marktaek.
        # EPS: kemur i veg fyrir ad 1/MAE sprengi upp thegar MAE -> 0.
        MIN_N, EPS = 4, 0.05
        usable = {m: st["hiti"] for m, st in model["lead_mae"][bs].items()
                  if st.get("hiti") is not None and st.get("n", 0) >= MIN_N}
        if usable:
            inv = {m: 1.0 / (v + EPS) for m, v in usable.items()}
            for m, bonus in MODEL_BONUS.items():
                if m in inv: inv[m] *= bonus
            tot = sum(inv.values())
            for m in ALL_KEYS:
                model["weights"][bs][m] = round(inv[m] / tot, 4) if m in inv else 0.0

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

    # Skyrsla
    for b in LEAD_BUCKETS:
        bs = str(b)
        if not summary.get(bs): continue
        best = sorted(summary[bs].items(), key=lambda x: x[1]["hiti"] or 99)
        line = "  ".join(f"{m}={s['hiti']:.2f}" for m, s in best[:4] if s["hiti"] > 0)
        print(f"  {b:2d} klst | {line}")
    return model

# --- 6. SPA ----------------------------------------------------------------
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
         "model_name": "Jolly v2.1",
         "runs": model.get("runs", 0),
         "verified_pairs": model.get("verified_pairs", 0),
         "lead_buckets": LEAD_BUCKETS,
         "weights": model["weights"],
         "lead_mae": model.get("lead_mae", {}),
         "models_used": ALL_KEYS,
         "attribution": ["Vedurstofa Islands (apis.is, xmlweather)",
                         "MET Norway (api.met.no) CC BY 4.0",
                         "Open-Meteo CC BY 4.0",
                         "NOAA aviationweather.gov METAR"],
         "hourly": {"time": [], "lead_hours": [], "temperature": [], "windspeed": [],
                    "winddirection": [], "windgust": [], "precipitation": [],
                    "cloud_cover": [], "cloud_low": [], "cloud_mid": [],
                    "cloud_high": [], "visibility": [], "is_day": [],
                    "icon": [], "condition": [], "beaufort": [],
                    "model_temperatures":   {m: [] for m in ALL_KEYS},
                    "model_windspeeds":     {m: [] for m in ALL_KEYS},
                    "model_precipitations": {m: [] for m in ALL_KEYS},
                    "model_clouds":         {m: [] for m in ALL_KEYS}},
         "daily": {"date": [], "temp_max": [], "temp_min": [],
                   "precipitation_total": [], "wind_avg": [],
                   "wind_dir_dominant": [], "wind_dir_dominant_deg": [],
                   "cloud_avg": [], "icon": [], "condition": []}}

    for t in fut[:120]:
        lead = max(0, int((parse_t(t) - now).total_seconds() // 3600))
        bs   = str(lead_bucket(lead))
        i    = ft.index(t) if t in ft else None
        J["hourly"]["time"].append(t)
        J["hourly"]["lead_hours"].append(lead)

        T, W, P, D, C = [], [], [], [], []

        for m, api in MODELS.items():
            w = model["weights"][bs].get(m, 0.0)
            b = model["bias"][m][bs]

            def g(key):
                if i is None: return None
                a = fc["hourly"].get(f"{key}_{api}", [])
                return a[i] if i < len(a) else None

            rt, rw, rp = g("temperature_2m"), g("windspeed_10m"), g("precipitation")
            rd, rc     = g("winddirection_10m"), g("cloud_cover")

            ct  = round(rt + b["hiti"], 1)                if rt is not None else None
            cw  = round(max(0, rw + b["vindur"]), 1)      if rw is not None else None
            cp  = round(max(0, rp * b["urkoma_scale"]), 2) if rp is not None else None
            cc  = round(min(100, max(0, rc + b["sky"])))   if rc is not None else None

            J["hourly"]["model_temperatures"][m].append(ct)
            J["hourly"]["model_windspeeds"][m].append(cw)
            J["hourly"]["model_precipitations"][m].append(cp)
            J["hourly"]["model_clouds"][m].append(cc)

            if w > 0:
                if ct is not None: T.append((ct, w))
                if cw is not None: W.append((cw, w))
                if rd is not None: D.append((rd, w))
                if cc is not None: C.append((cc, w))
                if cp is not None: P.append((cp, w))

        for k, src in extras.items():
            xw = model["weights"][bs].get(k, 0.0)
            xb = model["bias"][k][bs]
            j  = et[k].index(t) if (src and t in et[k]) else None
            def ge(key, _src=src, _j=j):
                if _j is None or not _src: return None
                a = _src["hourly"].get(key, [])
                return a[_j] if _j < len(a) else None
            xT, xW, xP = ge("temperature"), ge("windspeed"), ge("precipitation")
            xD, xC     = ge("winddirection"), ge("cloud_cover")
            ct = round(xT + xb["hiti"], 1)                 if xT is not None else None
            cw = round(max(0, xW + xb["vindur"]), 1)       if xW is not None else None
            cp = round(max(0, xP * xb["urkoma_scale"]), 2) if xP is not None else None
            cc = round(min(100, max(0, xC + xb["sky"])))   if xC is not None else None
            J["hourly"]["model_temperatures"][k].append(ct)
            J["hourly"]["model_windspeeds"][k].append(cw)
            J["hourly"]["model_precipitations"][k].append(cp)
            J["hourly"]["model_clouds"][k].append(cc)
            if xw > 0:
                if ct is not None: T.append((ct, xw))
                if cw is not None: W.append((cw, xw))
                if xD is not None: D.append((xD, xw))
                if cc is not None: C.append((cc, xw))
                if cp is not None: P.append((cp, xw))

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

    print(f"  OK {len(H['time'])} klst | {len(J['daily']['date'])} dagar")
    return J

# --- 7. VISTA --------------------------------------------------------------
def save(model, fcast):
    save_json(DATA_DIR / "jolly_model.json", model)
    if fcast:
        save_json(DATA_DIR / "jolly_forecast.json", fcast)
    log = load_json(DATA_DIR / "run_log.json", [])
    log.append({"time": datetime.now(timezone.utc).isoformat(),
                "runs": model.get("runs", 0),
                "verified_pairs": model.get("verified_pairs", 0),
                "status": "ok" if fcast else "partial",
                "version": "2.1"})
    save_json(DATA_DIR / "run_log.json", log[-168:])
    print("VISTAD")

# --- MAIN ------------------------------------------------------------------
def main():
    print("=" * 64)
    print(f"JOLLY v2.1  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
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
    save(model, fcast)

    print("=" * 64)
    w6 = model["weights"].get("6", {})
    top = sorted(((m, v) for m, v in w6.items() if v > 0), key=lambda x: -x[1])[:4]
    if top:
        print("Thyngdir 6 klst: " + " | ".join(f"{m} {v:.0%}" for m, v in top))
    print(f"Keyrslur {model.get('runs',0)} | "
          f"stadfest por {model.get('verified_pairs',0)}")
    print("=" * 64)

if __name__ == "__main__":
    main()
