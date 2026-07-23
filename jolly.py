"""
Jolly v1.6 - Stadbundid vedurspalikan fyrir Egilsstadi
NYTT: Skyjahula, skyjalog, thoka, METAR fra BIEG, Meteocons taknkerfi
Likon: ICON + GFS + ECMWF + MetNo + DMI + HARMONIE
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
OBS_HISTORY_HOURS = 720

MODELS = {
    "icon":  "icon_seamless",
    "gfs":   "gfs_seamless",
    "ecmwf": "ecmwf_ifs025",
    "metno": "metno_nordic",
    "dmi":   "dmi_seamless",
}

HOURLY_VARS = ",".join([
    "temperature_2m","dew_point_2m","relative_humidity_2m",
    "windspeed_10m","winddirection_10m","windgusts_10m",
    "precipitation","weathercode",
    "cloud_cover","cloud_cover_low","cloud_cover_mid","cloud_cover_high",
    "visibility","cape","is_day",
])

# --- HJALPARFOLL -----------------------------------------------------------
def fetch_url(url, as_text=False, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent":"Jolly-Weather/1.6"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read().decode("utf-8", errors="replace")
        return raw if as_text else json.loads(raw)

def mean(v):
    x = [a for a in v if a is not None]
    return sum(x)/len(x) if x else None

def mae(pairs):
    v = [(a,b) for a,b in pairs if a is not None and b is not None]
    return sum(abs(a-b) for a,b in v)/len(v) if v else None

def bias(pairs):
    v = [(a,b) for a,b in pairs if a is not None and b is not None]
    return sum(b-a for a,b in v)/len(v) if v else None

def deg_to_dir(d):
    if d is None: return None
    dirs = ["N","NNA","NA","ANA","A","ASA","SA","SSA",
            "S","SSV","SV","VSV","V","VNV","NV","NNV"]
    return dirs[round(d/22.5)%16]

def dir_to_deg(d):
    m = {"N":0,"NNA":22.5,"NA":45,"ANA":67.5,"A":90,"ASA":112.5,"SA":135,
         "SSA":157.5,"S":180,"SSV":202.5,"SV":225,"VSV":247.5,"V":270,
         "VNV":292.5,"NV":315,"NNV":337.5,
         "NNE":22.5,"NE":45,"ENE":67.5,"E":90,"ESE":112.5,"SE":135,
         "SSE":157.5,"SSW":202.5,"SW":225,"WSW":247.5,"W":270,"WNW":292.5,
         "NW":315,"NNW":337.5}
    return m.get(str(d).strip().upper())

def beaufort(ms):
    """Vindstig eftir Beaufort - fyrir wind-beaufort-N taknid."""
    if ms is None: return None
    limits = [0.5,1.6,3.4,5.5,8.0,10.8,13.9,17.2,20.8,24.5,28.5,32.7]
    for i, lim in enumerate(limits):
        if ms < lim: return i
    return 12

# --- TAKNAVAL (Meteocons slugs) --------------------------------------------
def determine_icon(cloud_pct, precip_mm, temp_c, is_day, visibility_m, wind_ms, cape=None):
    """
    Skilar Meteocons slug, t.d. 'partly-cloudy-day-rain'.
    Slod: https://cdn.meteocons.com/latest/svg/fill/{slug}.svg
    """
    dn = "day" if is_day else "night"
    p  = precip_mm or 0

    # 1. Thoka
    if visibility_m is not None and visibility_m < 1000:
        return "fog" if visibility_m < 400 else f"fog-{dn}"

    # 2. Skafrenningur - kalt, hvasst, litid skyggni
    if (temp_c is not None and temp_c < 1 and wind_ms is not None and wind_ms > 10
            and p < 0.2 and visibility_m is not None and visibility_m < 5000):
        return "extreme-snow"

    # 3. Thrumuvedur
    if cape is not None and cape > 500 and p > 1.0:
        if cloud_pct is not None and cloud_pct < 85:
            return f"thunderstorms-{dn}-rain"
        return "thunderstorms-rain"

    # 4. Urkoma
    if p > 0.05:
        if   temp_c is None:  ptype = "rain"
        elif temp_c <= -0.5:  ptype = "snow"
        elif temp_c <= 2.0:   ptype = "sleet"
        else:                 ptype = "rain"

        showery = cloud_pct is not None and cloud_pct < 80

        if ptype == "rain" and p < 0.25 and not showery:
            return "drizzle"
        if p > 2.5:
            return f"extreme-{ptype}"
        if showery:
            return f"partly-cloudy-{dn}-{ptype}"
        return f"overcast-{ptype}"

    # 5. Mistur an urkomu
    if visibility_m is not None and visibility_m < 5000:
        return "mist"

    # 6. Skyjahula - 6 threp
    c = cloud_pct if cloud_pct is not None else 0
    if c >= 95: return "overcast"
    if c >= 80: return f"mostly-cloudy-{dn}"
    if c >= 55: return f"half-cloudy-{dn}"
    if c >= 30: return f"mostly-clear-{dn}"
    if c >= 10: return f"partly-cloudy-{dn}"
    return f"clear-{dn}"

# --- ISLENSK LYSING --------------------------------------------------------
def describe(cloud_pct, precip_mm, temp_c, visibility_m, wind_ms, cape=None):
    p = precip_mm or 0
    if visibility_m is not None and visibility_m < 1000:
        return "Frostthoka" if (temp_c is not None and temp_c < 0) else "Thoka"
    if (temp_c is not None and temp_c < 1 and wind_ms is not None and wind_ms > 10
            and p < 0.2 and visibility_m is not None and visibility_m < 5000):
        return "Skafrenningur"
    if cape is not None and cape > 500 and p > 1.0:
        return "Thrumuvedur"
    if p > 0.05:
        if   temp_c is None:  base = "Rigning"
        elif temp_c <= -0.5:  base = "Snjokoma"
        elif temp_c <= 2.0:   base = "Slydda"
        else:                 base = "Rigning"
        showery = cloud_pct is not None and cloud_pct < 80
        if base == "Rigning":
            if p < 0.25 and not showery: return "Suld"
            if showery: return "Skurir"
            if p > 2.5: return "Mikil rigning"
            return "Rigning"
        if base == "Snjokoma":
            if showery: return "El"
            if p > 2.5: return "Mikil snjokoma"
            return "Snjokoma"
        if showery: return "Slyddu-el"
        return "Slydda"
    if visibility_m is not None and visibility_m < 5000:
        return "Mistur"
    c = cloud_pct if cloud_pct is not None else 0
    if c >= 95: return "Alskyjad"
    if c >= 80: return "Ad mestu skyjad"
    if c >= 55: return "Halfskyjad"
    if c >= 30: return "Skyjad ad hluta"
    if c >= 10: return "Lettskyjad"
    return "Heidskirt"

def cloud_class(pct):
    if pct is None: return None
    if pct < 10: return "heidskirt"
    if pct < 30: return "lettskyjad"
    if pct < 55: return "skyjad_hluta"
    if pct < 80: return "halfskyjad"
    if pct < 95: return "mestu_skyjad"
    return "alskyjad"

# --- 1. METAR FRA BIEG -----------------------------------------------------
CLOUD_OKTAS = {"FEW":19, "SCT":44, "BKN":75, "OVC":100}

def parse_metar(line):
    try:
        if ICAO not in line[:24]:
            return None
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
        t_str = dt.strftime("%Y-%m-%dT%H:00")

        layers = []
        for cm in re.finditer(r"\b(FEW|SCT|BKN|OVC)(\d{3})(CB|TCU)?\b", line):
            layers.append({"type": cm.group(1),
                           "base_ft": int(cm.group(2)) * 100,
                           "cb": cm.group(3) or None})

        if re.search(r"\b(SKC|CLR|NSC|NCD|CAVOK)\b", line):
            cloud_cover, base_ft = 0, None
        elif layers:
            cloud_cover = max(CLOUD_OKTAS[l["type"]] for l in layers)
            base_ft     = min(l["base_ft"] for l in layers)
        else:
            vv = re.search(r"\bVV(\d{3})\b", line)
            if vv: cloud_cover, base_ft = 100, int(vv.group(1)) * 100
            else:  cloud_cover, base_ft = None, None

        vis_m = None
        if "CAVOK" in line:
            vis_m = 10000
        else:
            vm = re.search(r"\s(\d{4})\s", line)
            if vm:
                vis_m = int(vm.group(1))
                if vis_m == 9999: vis_m = 10000

        temp = dew = None
        tm = re.search(r"\s(M?\d{2})/(M?\d{2})\s", line)
        if tm:
            def conv(s): return -int(s[1:]) if s.startswith("M") else int(s)
            temp, dew = conv(tm.group(1)), conv(tm.group(2))

        wind_kt = wind_dir = None
        wm = re.search(r"\b(\d{3}|VRB)(\d{2,3})(G\d{2,3})?KT\b", line)
        if wm:
            wind_dir = None if wm.group(1) == "VRB" else int(wm.group(1))
            wind_kt  = int(wm.group(2))

        return {"time": t_str, "cloud_cover": cloud_cover, "cloud_base_ft": base_ft,
                "cloud_layers": layers, "visibility": vis_m,
                "temperature": temp, "dewpoint": dew,
                "windspeed": round(wind_kt*0.514444,1) if wind_kt is not None else None,
                "winddirection": wind_dir, "source": "metar-BIEG"}
    except Exception:
        return None

def fetch_metar():
    print("METAR: saeki fra " + ICAO + " ...")
    url = f"https://aviationweather.gov/api/data/metar?ids={ICAO}&format=raw&hours=24"
    try:
        raw   = fetch_url(url, as_text=True, timeout=20)
        lines = [l.strip() for l in raw.strip().split("\n") if l.strip()]
        obs   = [p for p in (parse_metar(l) for l in lines) if p]
        if not obs: raise ValueError("engar faerslur")
        last = obs[-1]
        print(f"  OK - {len(obs)} faerslur | nyjust {last['time']} "
              f"sky={last['cloud_cover']}% botn={last['cloud_base_ft']}ft")
        return obs
    except Exception as e:
        print(f"  VILLA: {e}")
        return []

# --- 2. MAELINGAR ----------------------------------------------------------
def fetch_and_store_observation(metar_obs):
    print("MAELING: saeki fra stod 571 ...")
    obs_path = DATA_DIR / "obs_history.json"
    history = []
    if obs_path.exists():
        try:
            with open(obs_path) as f: history = json.load(f)
        except Exception: history = []
    by_time = {h["time"]: h for h in history}

    url = f"https://apis.is/weather/observations/is?stations={STATION_ID}&time=1h"
    try:
        data = fetch_url(url)
        results = data.get("results", [])
        if results:
            r  = results[0]
            dt = datetime.strptime(r.get("time","").strip(), "%Y-%m-%d %H:%M:%S")
            dt = dt.replace(tzinfo=timezone.utc)
            t_str = dt.strftime("%Y-%m-%dT%H:00")
            def gv(k):
                try:
                    v = r.get(k, "")
                    return float(v) if v and str(v).strip() not in ("","-") else None
                except Exception: return None
            rec = by_time.get(t_str, {"time": t_str})
            rec.update({"temperature": gv("T"), "windspeed": gv("F"),
                        "windgust": gv("FG"),
                        "winddirection": dir_to_deg(r.get("D","")),
                        "precipitation": gv("R"), "humidity": gv("RH"),
                        "pressure": gv("P"), "weather_desc": r.get("W",""),
                        "source": "apis.is-571"})
            by_time[t_str] = rec
            print(f"  OK {t_str} | T={rec['temperature']} F={rec['windspeed']}")
    except Exception as e:
        print(f"  VILLA apis.is: {e}")

    n_metar = 0
    for m in metar_obs:
        t = m["time"]
        rec = by_time.get(t, {"time": t})
        rec["cloud_cover"]   = m["cloud_cover"]
        rec["cloud_base_ft"] = m["cloud_base_ft"]
        rec["cloud_layers"]  = m["cloud_layers"]
        rec["visibility"]    = m["visibility"]
        rec["dewpoint"]      = m["dewpoint"]
        if rec.get("temperature")   is None: rec["temperature"]   = m["temperature"]
        if rec.get("windspeed")     is None: rec["windspeed"]     = m["windspeed"]
        if rec.get("winddirection") is None: rec["winddirection"] = m["winddirection"]
        rec["has_metar"] = True
        by_time[t] = rec
        n_metar += 1
    if n_metar:
        print(f"  METAR skyjagogn bett vid {n_metar} timapunkta")

    history = sorted(by_time.values(), key=lambda x: x["time"])[-OBS_HISTORY_HOURS:]
    with open(obs_path, "w") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)
    n_cloud = sum(1 for h in history if h.get("cloud_cover") is not None)
    print(f"  {len(history)} maelingar geymdar ({n_cloud} med skyjahulu)")
    return history

# --- 3. OPEN-METEO ---------------------------------------------------------
def fetch_forecasts():
    print("OPEN-METEO: saeki 5 likon, 15 breytur ...")
    url = (f"https://api.open-meteo.com/v1/forecast"
           f"?latitude={LAT}&longitude={LON}"
           f"&hourly={HOURLY_VARS}"
           f"&models={','.join(MODELS.values())}"
           f"&past_days=2&forecast_days=5"
           f"&timezone=UTC&wind_speed_unit=ms")
    try:
        d = fetch_url(url)
        print(f"  OK - {len(d['hourly']['time'])} timapunktar")
        for k, api in MODELS.items():
            cc = d["hourly"].get(f"cloud_cover_{api}", [])
            print(f"    {k:8s}: {len([x for x in cc if x is not None])} skyjagildi")
        return d
    except Exception as e:
        print(f"  VILLA: {e}")
        return None

# --- 4. HARMONIE -----------------------------------------------------------
WEATHER_TO_CLOUD = {
    "heidskirt":5, "heiðskírt":5, "lettskyjad":30, "léttskýjað":30,
    "halfskyjad":50, "hálfskýjað":50, "skyjad":70, "skýjað":70,
    "alskyjad":95, "alskýjað":95, "thoka":100, "þoka":100,
    "rigning":90, "skurir":70, "skúrir":70, "snjokoma":90, "snjókoma":90,
    "el":70, "él":70, "slydda":90,
}

def fetch_harmonie():
    print("HARMONIE: saeki fra Vedurstofu ...")
    url = f"https://xmlweather.vedur.is/?op_w=xml&type=forec&lang=is&view=xml&ids={STATION_ID}"
    try:
        root = ET.fromstring(fetch_url(url, as_text=True))
        h = {"source":"vedurstofa-harmonie","hourly":{
             "time":[],"temperature":[],"windspeed":[],"winddirection":[],
             "precipitation":[],"cloud_cover":[]}}
        for fc in (root.findall(".//forecast") or root.findall("forecast")):
            ft = fc.get("ftime") or fc.findtext("ftime","")
            if not ft: continue
            try:
                dt = datetime.strptime(ft.strip(), "%Y-%m-%d %H:%M:%S")
                dt = dt.replace(tzinfo=timezone.utc)
            except Exception:
                try:
                    dt = datetime.fromisoformat(ft.strip().replace(" ","T"))
                    dt = dt.replace(tzinfo=timezone.utc)
                except Exception: continue
            def gv(tag):
                v = fc.get(tag) or fc.findtext(tag,"")
                try:
                    return float(v) if v and v.strip() not in ("","-") else None
                except Exception: return None
            h["hourly"]["time"].append(dt.strftime("%Y-%m-%dT%H:00"))
            h["hourly"]["temperature"].append(gv("T"))
            h["hourly"]["windspeed"].append(gv("F"))
            h["hourly"]["precipitation"].append(gv("R"))
            h["hourly"]["winddirection"].append(
                dir_to_deg(fc.get("D","") or fc.findtext("D","")))
            w  = (fc.get("W","") or fc.findtext("W","") or "").lower().strip()
            cc = None
            for key, val in WEATHER_TO_CLOUD.items():
                if key in w: cc = val; break
            h["hourly"]["cloud_cover"].append(cc)
        n = len(h["hourly"]["time"])
        if n == 0: raise ValueError("engir timapunktar")
        print(f"  OK - {n} timapunktar")
        return h
    except Exception as e:
        print(f"  VILLA: {e}")
        return None

# --- 5. THJALFUN -----------------------------------------------------------
def train_jolly(fc, obs_history, harm):
    print("THJALFUN ...")
    mp   = DATA_DIR / "jolly_model.json"
    keys = list(MODELS.keys()) + ["harmonie"]

    if mp.exists():
        with open(mp) as f: model = json.load(f)
        model.setdefault("biases", {}); model.setdefault("weights", {})
        for m in keys:
            model["biases"].setdefault(m, {"hiti":0.0,"vindur":0.0,
                                           "urkoma_scale":1.0,"sky":0.0})
            model["biases"][m].setdefault("sky", 0.0)
            model["weights"].setdefault(m, 1.0/len(keys))
        model.setdefault("cloud_confusion", {})
        print(f"  Hladid inn: {model.get('training_days',0)} keyrslur, "
              f"{model.get('total_obs',0)} samanburdir")
    else:
        model = {"version":"1.6","created":datetime.now(timezone.utc).isoformat(),
                 "training_days":0,"total_obs":0,"obs_source":"apis.is-571+metar",
                 "biases":{m:{"hiti":0.0,"vindur":0.0,"urkoma_scale":1.0,"sky":0.0}
                           for m in keys},
                 "weights":{m:1.0/len(keys) for m in keys},
                 "cloud_confusion":{},"mae_history":[],"last_updated":None}
        print("  Nytt likan v1.6")

    if not obs_history or not fc:
        print("  Gogn vantar - thjalfun sleppt")
        return model

    src = {}
    ft  = fc["hourly"]["time"]
    for k, api in MODELS.items():
        src[k] = {"times": ft,
                  "temp": fc["hourly"].get(f"temperature_2m_{api}", []),
                  "wind": fc["hourly"].get(f"windspeed_10m_{api}", []),
                  "prec": fc["hourly"].get(f"precipitation_{api}", []),
                  "sky":  fc["hourly"].get(f"cloud_cover_{api}", [])}
    if harm:
        src["harmonie"] = {"times": harm["hourly"]["time"],
                           "temp": harm["hourly"]["temperature"],
                           "wind": harm["hourly"]["windspeed"],
                           "prec": harm["hourly"]["precipitation"],
                           "sky":  harm["hourly"]["cloud_cover"]}

    pairs     = {m:{"hiti":[],"vindur":[],"urkoma":[],"sky":[]} for m in src}
    confusion = {}
    n = 0
    for o in obs_history:
        ot = o.get("time","")
        if not ot: continue
        ov = {"hiti":o.get("temperature"), "vindur":o.get("windspeed"),
              "urkoma":o.get("precipitation"), "sky":o.get("cloud_cover")}
        hit = False
        for m, s in src.items():
            if ot not in s["times"]: continue
            i = s["times"].index(ot)
            for var, arr in (("hiti","temp"),("vindur","wind"),
                             ("urkoma","prec"),("sky","sky")):
                if ov[var] is not None and i < len(s[arr]) and s[arr][i] is not None:
                    pairs[m][var].append((ov[var], s[arr][i]))
            if ov["sky"] is not None and i < len(s["sky"]) and s["sky"][i] is not None:
                a, p = cloud_class(ov["sky"]), cloud_class(s["sky"][i])
                if a and p:
                    confusion.setdefault(m,{}).setdefault(p,{}).setdefault(a,0)
                    confusion[m][p][a] += 1
            hit = True
        if hit: n += 1

    if n == 0:
        print("  Engar samsvorun")
        return model

    print(f"  {n} timapunktar x {len(src)} likon")
    LR = 0.15
    summary = {}
    for m in src:
        b = model["biases"][m]
        if pairs[m]["hiti"]:
            b["hiti"]   = (1-LR)*b["hiti"]   + LR*(-(bias(pairs[m]["hiti"])   or 0))
        if pairs[m]["vindur"]:
            b["vindur"] = (1-LR)*b["vindur"] + LR*(-(bias(pairs[m]["vindur"]) or 0))
        if pairs[m]["sky"]:
            b["sky"]    = (1-LR)*b["sky"]    + LR*(-(bias(pairs[m]["sky"])    or 0))
        if pairs[m]["urkoma"]:
            om = mean([o for o,_ in pairs[m]["urkoma"]])
            fm = mean([f for _,f in pairs[m]["urkoma"]])
            if om is not None and fm and fm > 0:
                b["urkoma_scale"] = (1-LR)*b["urkoma_scale"] + LR*(om/fm)
        summary[m] = {
            "hiti":   round(mae([(o,f+b["hiti"])   for o,f in pairs[m]["hiti"]])   or 0, 3),
            "vindur": round(mae([(o,f+b["vindur"]) for o,f in pairs[m]["vindur"]]) or 0, 3),
            "sky":    round(mae([(o,f+b["sky"])    for o,f in pairs[m]["sky"]])    or 0, 2),
            "n": len(pairs[m]["hiti"]), "n_sky": len(pairs[m]["sky"])}

    hm = {m: summary[m]["hiti"] for m in summary
          if summary[m]["hiti"] > 0 and summary[m]["n"] > 5}
    if hm:
        inv = {m: 1.0/v for m, v in hm.items()}
        if "harmonie" in inv: inv["harmonie"] *= 1.2
        if "dmi"      in inv: inv["dmi"]      *= 1.1
        tot = sum(inv.values())
        for m in keys:
            if m in inv: model["weights"][m] = round(inv[m]/tot, 4)

    for m, cm in confusion.items():
        model["cloud_confusion"].setdefault(m, {})
        for pred, acts in cm.items():
            model["cloud_confusion"][m].setdefault(pred, {})
            for act, cnt in acts.items():
                prev = model["cloud_confusion"][m][pred].get(act, 0)
                model["cloud_confusion"][m][pred][act] = prev + cnt

    model["training_days"] = model.get("training_days", 0) + 1
    model["total_obs"]     = model.get("total_obs", 0) + n
    model["last_updated"]  = datetime.now(timezone.utc).isoformat()
    model["mae_history"].append({
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:00"),
        "n_obs": n, "mae": summary})
    model["mae_history"] = model["mae_history"][-720:]

    print(f"  Keyrsla #{model['training_days']} | {model['total_obs']} samanburdir")
    for m, s in sorted(summary.items(), key=lambda x: x[1]["hiti"] or 99):
        if s["n"] > 0:
            w   = model["weights"].get(m, 0)
            sky = f"sky={s['sky']:.0f}%" if s["n_sky"] > 0 else "sky=--"
            print(f"    {m:9s}: T={s['hiti']:.2f} V={s['vindur']:.2f} {sky} w={w:.0%}")
    return model

# --- 6. SPA ----------------------------------------------------------------
def make_forecast(fc, harm, model):
    print("SPA: byggi Jolly spa ...")
    if fc is None:
        print("  Engin gogn"); return None

    ft   = fc["hourly"]["time"]
    ht   = harm["hourly"]["time"] if harm else []
    now  = datetime.now(timezone.utc)
    fut  = [t for t in sorted(set(ft + ht)) if t >= now.strftime("%Y-%m-%dT%H:00")]
    keys = list(MODELS.keys()) + ["harmonie"]

    J = {"generated": now.isoformat(),
         "station": {"lat":LAT,"lon":LON,"id":STATION_ID,
                     "name":"Egilsstadir","icao":ICAO},
         "model_name":"Jolly v1.7",
         "training_days": model.get("training_days",0),
         "total_obs": model.get("total_obs",0),
         "weights": model["weights"], "models_used": keys,
         "icon_set": "meteocons",
         "hourly": {"time":[],"temperature":[],"windspeed":[],"winddirection":[],
                    "windgust":[],"precipitation":[],"cloud_cover":[],
                    "cloud_low":[],"cloud_mid":[],"cloud_high":[],
                    "visibility":[],"is_day":[],"icon":[],"condition":[],
                    "beaufort":[],
                    "model_temperatures":{m:[] for m in keys},
                    "model_windspeeds":{m:[] for m in keys},
                    "model_precipitations":{m:[] for m in keys},
                    "model_clouds":{m:[] for m in keys}},
         "daily": {"date":[],"temp_max":[],"temp_min":[],
                   "precipitation_total":[],"wind_avg":[],
                   "wind_dir_dominant":[],"wind_dir_dominant_deg":[],
                   "cloud_avg":[],"icon":[],"condition":[]}}

    def g(key, i):
        if i is None: return None
        a = fc["hourly"].get(key, [])
        return a[i] if i < len(a) else None

    def gh(key, t):
        if not harm or t not in ht: return None
        i = ht.index(t); a = harm["hourly"].get(key, [])
        return a[i] if i < len(a) else None

    for t in fut[:120]:
        i = ft.index(t) if t in ft else None
        J["hourly"]["time"].append(t)
        T, W, P, D, C = [], [], [], [], []

        for m, api in MODELS.items():
            w = model["weights"].get(m, 1.0/len(keys)); b = model["biases"][m]
            rt = g(f"temperature_2m_{api}", i);   rw = g(f"windspeed_10m_{api}", i)
            rp = g(f"precipitation_{api}", i);    rd = g(f"winddirection_10m_{api}", i)
            rc = g(f"cloud_cover_{api}", i)
            ct = round(rt + b["hiti"], 1)                if rt is not None else None
            cw = round(max(0, rw + b["vindur"]), 1)      if rw is not None else None
            cc = round(min(100, max(0, rc + b["sky"])))  if rc is not None else None
            cp_ = round(max(0, rp*b["urkoma_scale"]), 2) if rp is not None else None
            J["hourly"]["model_temperatures"][m].append(ct)
            J["hourly"]["model_windspeeds"][m].append(cw)
            J["hourly"]["model_precipitations"][m].append(cp_)
            J["hourly"]["model_clouds"][m].append(cc)
            if ct is not None: T.append((ct, w))
            if cw is not None: W.append((cw, w))
            if rd is not None: D.append((rd, w))
            if cc is not None: C.append((cc, w))
            if cp_ is not None: P.append((cp_, w))

        hw = model["weights"].get("harmonie", 0); hb = model["biases"]["harmonie"]
        hT, hW = gh("temperature", t), gh("windspeed", t)
        hP, hD = gh("precipitation", t), gh("winddirection", t)
        hC = gh("cloud_cover", t)
        ct = round(hT + hb["hiti"], 1)               if hT is not None else None
        cw = round(max(0, hW + hb["vindur"]), 1)     if hW is not None else None
        cc = round(min(100, max(0, hC + hb["sky"]))) if hC is not None else None
        cp_ = round(max(0, hP*hb["urkoma_scale"]), 2) if hP is not None else None
        J["hourly"]["model_temperatures"]["harmonie"].append(ct)
        J["hourly"]["model_windspeeds"]["harmonie"].append(cw)
        J["hourly"]["model_precipitations"]["harmonie"].append(cp_)
        J["hourly"]["model_clouds"]["harmonie"].append(cc)
        if ct is not None: T.append((ct, hw))
        if cw is not None: W.append((cw, hw))
        if hD is not None: D.append((hD, hw))
        if cc is not None: C.append((cc, hw))
        if cp_ is not None: P.append((cp_, hw))

        def wa(p):
            if not p: return None
            tw = sum(w for _, w in p)
            return round(sum(v*w for v, w in p)/tw, 2) if tw > 0 else None

        def wang(p):
            if not p: return None
            tw = sum(w for _, w in p)
            if tw == 0: return None
            ss = sum(math.sin(math.radians(v))*w for v, w in p)
            cs = sum(math.cos(math.radians(v))*w for v, w in p)
            return round(math.degrees(math.atan2(ss/tw, cs/tw)) % 360, 1)

        temp, wind, prec = wa(T), wa(W), wa(P)
        wdir, cloud      = wang(D), wa(C)

        def avg_var(prefix):
            return mean([g(f"{prefix}_{api}", i) for api in MODELS.values()])

        c_low  = avg_var("cloud_cover_low")
        c_mid  = avg_var("cloud_cover_mid")
        c_high = avg_var("cloud_cover_high")
        vis    = avg_var("visibility")
        cape   = avg_var("cape")
        gust   = avg_var("windgusts_10m")
        isd    = avg_var("is_day")
        is_day = (isd is None) or (isd >= 0.5)

        J["hourly"]["temperature"].append(temp)
        J["hourly"]["windspeed"].append(wind)
        J["hourly"]["winddirection"].append(wdir)
        J["hourly"]["windgust"].append(round(gust,1) if gust is not None else None)
        J["hourly"]["precipitation"].append(prec)
        J["hourly"]["cloud_cover"].append(round(cloud) if cloud is not None else None)
        J["hourly"]["cloud_low"].append(round(c_low)  if c_low  is not None else None)
        J["hourly"]["cloud_mid"].append(round(c_mid)  if c_mid  is not None else None)
        J["hourly"]["cloud_high"].append(round(c_high) if c_high is not None else None)
        J["hourly"]["visibility"].append(round(vis) if vis is not None else None)
        J["hourly"]["is_day"].append(1 if is_day else 0)
        J["hourly"]["icon"].append(
            determine_icon(cloud, prec, temp, is_day, vis, wind, cape))
        J["hourly"]["condition"].append(
            describe(cloud, prec, temp, vis, wind, cape))
        J["hourly"]["beaufort"].append(beaufort(wind))

    # Dagleg samantekt
    H = J["hourly"]; days = {}
    for i, t in enumerate(H["time"]):
        d = t[:10]
        days.setdefault(d, {"T":[],"W":[],"D":[],"P":[],"C":[],
                            "icons":[],"conds":[]})
        for k, arr in (("T","temperature"),("W","windspeed"),
                       ("D","winddirection"),("P","precipitation"),
                       ("C","cloud_cover")):
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
        icon = Counter(v["icons"]).most_common(1)[0][0] if v["icons"] else "overcast"
        cond = Counter(v["conds"]).most_common(1)[0][0] if v["conds"] else ""
        J["daily"]["date"].append(d)
        J["daily"]["temp_max"].append(round(max(v["T"]),1) if v["T"] else None)
        J["daily"]["temp_min"].append(round(min(v["T"]),1) if v["T"] else None)
        J["daily"]["precipitation_total"].append(round(sum(v["P"]),1) if v["P"] else 0)
        J["daily"]["wind_avg"].append(round(mean(v["W"]),1) if v["W"] else None)
        J["daily"]["wind_dir_dominant"].append(dom_dir)
        J["daily"]["wind_dir_dominant_deg"].append(dom_deg)
        J["daily"]["cloud_avg"].append(round(cavg) if cavg is not None else None)
        J["daily"]["icon"].append(icon)
        J["daily"]["condition"].append(cond)

    print(f"  OK - {len(H['time'])} klst | {len(J['daily']['date'])} dagar")
    print(f"  Takn i notkun: {', '.join(sorted(set(H['icon'])))}")
    return J

# --- 7. VISTA --------------------------------------------------------------
def save(model, fcast):
    print("VISTA ...")
    with open(DATA_DIR/"jolly_model.json", "w") as f:
        json.dump(model, f, indent=2, ensure_ascii=False)
    if fcast:
        with open(DATA_DIR/"jolly_forecast.json", "w") as f:
            json.dump(fcast, f, indent=2, ensure_ascii=False)
    lp = DATA_DIR/"run_log.json"; log = []
    if lp.exists():
        try:
            with open(lp) as f: log = json.load(f)
        except Exception: log = []
    log.append({"time": datetime.now(timezone.utc).isoformat(),
                "training_days": model.get("training_days",0),
                "total_obs": model.get("total_obs",0),
                "status": "ok" if fcast else "partial", "version":"1.6"})
    with open(lp, "w") as f:
        json.dump(log[-168:], f, indent=2)
    print("  Allt vistad")

# --- MAIN ------------------------------------------------------------------
def main():
    print("=" * 62)
    print(f"JOLLY v1.7 - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("Skyjahula | METAR BIEG | 6 likon | Meteocons takn")
    print("=" * 62)
    metar = fetch_metar()
    obs   = fetch_and_store_observation(metar)
    fc    = fetch_forecasts()
    harm  = fetch_harmonie()
    model = train_jolly(fc, obs, harm)
    fcast = make_forecast(fc, harm, model)
    save(model, fcast)
    print("=" * 62)
    print("JOLLY v1.7 LOKID")
    if model.get("weights"):
        top = sorted(model["weights"].items(), key=lambda x: -x[1])[:3]
        print("  Topp: " + " | ".join(f"{m}: {w:.0%}" for m, w in top))
    print("=" * 62)

if __name__ == "__main__":
    main()
