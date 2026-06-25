"""
Jolly v1.3 - Staðbundið veðurspálíkan fyrir Egilsstaði
Líkön: ICON + GFS + ECMWF + MetNo Nordic + HARMONIE (Veðurstofa)
5 daga spá með daglegum vindáttum
"""

import json
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path
import math
import xml.etree.ElementTree as ET
from collections import Counter

# ─── STILLINGAR ──────────────────────────────────────────────────────────────
LAT = 65.2620
LON = -14.4035
STATION_ID = 571
DATA_DIR = Path("docs/data")
DATA_DIR.mkdir(exist_ok=True, parents=True)

MODELS = {
    "icon":  "icon_seamless",
    "gfs":   "gfs_seamless",
    "ecmwf": "ecmwf_ifs025",
    "metno": "metno_nordic",
}

# ─── HJÁLPARFÖLL ─────────────────────────────────────────────────────────────
def fetch_url(url, as_text=False):
    req = urllib.request.Request(url, headers={"User-Agent": "Jolly-Weather/1.3"})
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read().decode("utf-8", errors="replace")
        return raw if as_text else json.loads(raw)

def mean(vals):
    v = [x for x in vals if x is not None]
    return sum(v) / len(v) if v else None

def mae(pairs):
    v = [(a, b) for a, b in pairs if a is not None and b is not None]
    return sum(abs(a - b) for a, b in v) / len(v) if v else None

def bias(pairs):
    v = [(a, b) for a, b in pairs if a is not None and b is not None]
    return sum(b - a for a, b in v) / len(v) if v else None

def deg_to_dir(deg):
    """Breyta gráðum í vindáttarbókstafi (íslenska)"""
    if deg is None:
        return None
    dirs = ["N","NNA","NA","ANA","A","ASA","SA","SSA",
            "S","SSV","SV","VSV","V","VNV","NV","NNV"]
    return dirs[round(deg / 22.5) % 16]

def dominant_dir(degrees):
    """Finna algengstu vindátt úr lista af gráðum"""
    dirs = [deg_to_dir(d) for d in degrees if d is not None]
    if not dirs:
        return None
    return Counter(dirs).most_common(1)[0][0]

def dir_to_deg(d):
    mapping = {
        "N":0,"NNA":22.5,"NA":45,"ANA":67.5,
        "A":90,"ASA":112.5,"SA":135,"SSA":157.5,
        "S":180,"SSV":202.5,"SV":225,"VSV":247.5,
        "V":270,"VNV":292.5,"NV":315,"NNV":337.5,
        "NNE":22.5,"NE":45,"ENE":67.5,"E":90,
        "ESE":112.5,"SE":135,"SSE":157.5,"SSW":202.5,
        "SW":225,"WSW":247.5,"W":270,"WNW":292.5,
        "NW":315,"NNW":337.5,"Logn":None,"Calm":None,"":None,
    }
    return mapping.get(str(d).upper(), None)

# ─── 1. OPEN-METEO ───────────────────────────────────────────────────────────
def fetch_forecasts():
    print("📡 Sæki líkansspár frá Open-Meteo (ICON + GFS + ECMWF + MetNo)...")
    models_str = ",".join(MODELS.values())
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={LAT}&longitude={LON}"
        f"&hourly=temperature_2m,windspeed_10m,winddirection_10m,precipitation,weathercode"
        f"&models={models_str}"
        f"&past_days=7&forecast_days=5"
        f"&timezone=UTC&wind_speed_unit=ms"
    )
    try:
        data = fetch_url(url)
        print(f"  ✅ Tókst - {len(data['hourly']['time'])} tímapunktar")
        return data
    except Exception as e:
        print(f"  ❌ Villa: {e}")
        return None

# ─── 2. HARMONIE FRÁ VEÐURSTOFU ─────────────────────────────────────────────
def fetch_vedurstofa_harmonie():
    print("🇮🇸 Sæki HARMONIE spá frá Veðurstofu Íslands (XML)...")
    url = f"https://xmlweather.vedur.is/?op_w=xml&type=forec&lang=is&view=xml&ids={STATION_ID}"
    try:
        xml_text = fetch_url(url, as_text=True)
        root = ET.fromstring(xml_text)
        harmonie = {"source":"vedurstofa-harmonie","hourly":{
            "time":[],"temperature":[],"windspeed":[],
            "winddirection":[],"precipitation":[],"weather_desc":[]
        }}
        forecasts = root.findall(".//forecast") or root.findall("forecast")
        for fc in forecasts:
            ftime = fc.get("ftime") or fc.findtext("ftime","")
            if not ftime: continue
            try:
                dt = datetime.strptime(ftime.strip(),"%Y-%m-%d %H:%M:%S")
                t_str = dt.strftime("%Y-%m-%dT%H:00")
            except:
                try:
                    dt = datetime.fromisoformat(ftime.strip().replace(" ","T"))
                    t_str = dt.strftime("%Y-%m-%dT%H:00")
                except: continue

            def gv(tag):
                v = fc.get(tag) or fc.findtext(tag,"")
                try: return float(v) if v and v.strip() not in ("","-") else None
                except: return None

            harmonie["hourly"]["time"].append(t_str)
            harmonie["hourly"]["temperature"].append(gv("T"))
            harmonie["hourly"]["windspeed"].append(gv("F"))
            harmonie["hourly"]["precipitation"].append(gv("R"))
            harmonie["hourly"]["weather_desc"].append(fc.get("W","") or fc.findtext("W","") or "")
            d = fc.get("D","") or fc.findtext("D","") or ""
            harmonie["hourly"]["winddirection"].append(dir_to_deg(d))

        n = len(harmonie["hourly"]["time"])
        if n == 0: raise ValueError("Engir tímapunktar")
        print(f"  ✅ HARMONIE: {n} tímapunktar")
        return harmonie
    except Exception as e:
        print(f"  ⚠️  HARMONIE villa: {e}")
        return fetch_apisIs_forecast()

def fetch_apisIs_forecast():
    print("  🔄 apis.is spá staðgengill...")
    url = f"https://apis.is/weather/forecasts/is?stations={STATION_ID}"
    try:
        data = fetch_url(url)
        results = data.get("results",[])
        if not results: raise ValueError("Engar niðurstöður")
        harmonie = {"source":"apis.is-forecast","hourly":{
            "time":[],"temperature":[],"windspeed":[],
            "winddirection":[],"precipitation":[],"weather_desc":[]
        }}
        for fc in results[0].get("forecast",[]):
            ftime = fc.get("ftime","")
            if not ftime: continue
            try:
                dt = datetime.strptime(ftime.strip(),"%Y-%m-%d %H:%M:%S")
                t_str = dt.strftime("%Y-%m-%dT%H:00")
            except: continue
            def gv(k):
                try:
                    v=fc.get(k,"")
                    return float(v) if v and str(v).strip() not in ("","-") else None
                except: return None
            harmonie["hourly"]["time"].append(t_str)
            harmonie["hourly"]["temperature"].append(gv("T"))
            harmonie["hourly"]["windspeed"].append(gv("F"))
            harmonie["hourly"]["precipitation"].append(gv("R"))
            harmonie["hourly"]["weather_desc"].append(fc.get("W",""))
            harmonie["hourly"]["winddirection"].append(dir_to_deg(fc.get("D","")))
        n = len(harmonie["hourly"]["time"])
        if n == 0: raise ValueError("Engir tímapunktar")
        print(f"  ✅ apis.is: {n} tímapunktar")
        return harmonie
    except Exception as e:
        print(f"  ❌ apis.is villa: {e}")
        return None

# ─── 3. MÆLINGAR ─────────────────────────────────────────────────────────────
def fetch_observations():
    print("🌡️  Sæki mælingar frá apis.is (stöð 571)...")
    url = f"https://apis.is/weather/observations/is?stations={STATION_ID}&time=1h&anytime=1"
    try:
        data = fetch_url(url)
        results = data.get("results",[])
        if not results: raise ValueError("Engar niðurstöður")
        obs = {"source":"apis.is-obs","hourly":{
            "time":[],"temperature":[],"windspeed":[],
            "winddirection":[],"precipitation":[]
        }}
        for r in results:
            t = r.get("time","")
            if not t: continue
            try:
                dt = datetime.fromisoformat(t.replace("Z","+00:00"))
                obs["hourly"]["time"].append(dt.strftime("%Y-%m-%dT%H:00"))
                obs["hourly"]["temperature"].append(float(r.get("T",0) or 0))
                obs["hourly"]["windspeed"].append(float(r.get("F",0) or 0))
                obs["hourly"]["precipitation"].append(float(r.get("R",0) or 0))
                obs["hourly"]["winddirection"].append(dir_to_deg(r.get("D","")))
            except: continue
        if obs["hourly"]["time"]:
            print(f"  ✅ {len(obs['hourly']['time'])} mælingar")
            return obs
        raise ValueError("Tómt")
    except Exception as e:
        print(f"  ⚠️  Mæling villa: {e} — nota Open-Meteo staðgengil")
        return fetch_obs_openmeteo()

def fetch_obs_openmeteo():
    url = (f"https://api.open-meteo.com/v1/forecast"
           f"?latitude={LAT}&longitude={LON}"
           f"&hourly=temperature_2m,windspeed_10m,winddirection_10m,precipitation"
           f"&models=best_match&past_days=7&forecast_days=0"
           f"&timezone=UTC&wind_speed_unit=ms")
    try:
        data = fetch_url(url)
        obs = {"source":"open-meteo-best","hourly":{
            "time":data["hourly"]["time"],
            "temperature":data["hourly"]["temperature_2m"],
            "windspeed":data["hourly"]["windspeed_10m"],
            "winddirection":data["hourly"].get("winddirection_10m",[]),
            "precipitation":data["hourly"]["precipitation"],
        }}
        print(f"  ✅ Open-Meteo: {len(obs['hourly']['time'])} tímapunktar")
        return obs
    except Exception as e:
        print(f"  ❌ {e}")
        return None

# ─── 4. ÞJÁLFUN ──────────────────────────────────────────────────────────────
def train_jolly(forecasts, observations, harmonie):
    print("🧠 Þjálfar Jolly líkanið...")
    model_path = DATA_DIR / "jolly_model.json"
    all_keys = list(MODELS.keys()) + ["harmonie"]

    if model_path.exists():
        with open(model_path) as f:
            model = json.load(f)
        for m in all_keys:
            if m not in model["biases"]:
                model["biases"][m] = {"hiti":0.0,"vindur":0.0,"urkoma_scale":1.0}
            if m not in model["weights"]:
                model["weights"][m] = 1.0/len(all_keys)
        print(f"  📂 Hlaðið inn ({model.get('training_days',0)} þjálfunardagar)")
    else:
        model = {
            "version":"1.3","created":datetime.now(timezone.utc).isoformat(),
            "training_days":0,"obs_source":"unknown",
            "biases":{m:{"hiti":0.0,"vindur":0.0,"urkoma_scale":1.0} for m in all_keys},
            "weights":{m:1.0/len(all_keys) for m in all_keys},
            "mae_history":[],"last_updated":None,
        }
        print("  🆕 Nýtt líkan (v1.3)")

    if observations is None:
        print("  ⚠️  Engar mælingar")
        return model

    model["obs_source"] = observations.get("source","unknown")
    obs_times = observations["hourly"]["time"]
    obs_temp  = observations["hourly"]["temperature"]
    obs_wind  = observations["hourly"]["windspeed"]
    obs_prec  = observations["hourly"]["precipitation"]

    sources = {}
    if forecasts:
        fc_t = forecasts["hourly"]["time"]
        for m_key, m_api in MODELS.items():
            sources[m_key] = {
                "times": fc_t,
                "temp":  forecasts["hourly"].get(f"temperature_2m_{m_api}",[]),
                "wind":  forecasts["hourly"].get(f"windspeed_10m_{m_api}",[]),
                "prec":  forecasts["hourly"].get(f"precipitation_{m_api}",[]),
            }
    if harmonie:
        sources["harmonie"] = {
            "times": harmonie["hourly"]["time"],
            "temp":  harmonie["hourly"]["temperature"],
            "wind":  harmonie["hourly"]["windspeed"],
            "prec":  harmonie["hourly"]["precipitation"],
        }

    pairs = {m:{"hiti":[],"vindur":[],"urkoma":[]} for m in sources}
    n = 0
    for ot,otv,owv,opv in zip(obs_times,obs_temp,obs_wind,obs_prec):
        hit = False
        for m,src in sources.items():
            if ot in src["times"]:
                i = src["times"].index(ot)
                if otv is not None and i<len(src["temp"]) and src["temp"][i] is not None:
                    pairs[m]["hiti"].append((otv,src["temp"][i]))
                if owv is not None and i<len(src["wind"]) and src["wind"][i] is not None:
                    pairs[m]["vindur"].append((owv,src["wind"][i]))
                if opv is not None and i<len(src["prec"]) and src["prec"][i] is not None:
                    pairs[m]["urkoma"].append((opv,src["prec"][i]))
                hit = True
        if hit: n += 1

    if n == 0:
        print("  ⚠️  Engar samsvörun")
        return model

    print(f"  📊 {n} tímapunktar, {len(sources)} líkön")
    LR = 0.3
    mae_summary = {}

    for m in sources:
        hp = pairs[m]["hiti"]; vp = pairs[m]["vindur"]; pp = pairs[m]["urkoma"]
        if hp:
            nb = bias(hp) or 0
            model["biases"][m]["hiti"] = (1-LR)*model["biases"][m]["hiti"] + LR*(-nb)
        if vp:
            nb = bias(vp) or 0
            model["biases"][m]["vindur"] = (1-LR)*model["biases"][m]["vindur"] + LR*(-nb)
        if pp:
            om = mean([o for o,_ in pp]); fm = mean([f for _,f in pp])
            if om and fm and fm>0:
                model["biases"][m]["urkoma_scale"] = (1-LR)*model["biases"][m]["urkoma_scale"] + LR*(om/fm)
        ch = [(o,f+model["biases"][m]["hiti"]) for o,f in hp]
        cv = [(o,f+model["biases"][m]["vindur"]) for o,f in vp]
        mae_summary[m] = {"hiti":round(mae(ch) or 0,3),"vindur":round(mae(cv) or 0,3)}

    hmaes = {m:mae_summary[m]["hiti"] for m in mae_summary if mae_summary[m]["hiti"]>0}
    if hmaes:
        inv = {m:1.0/v for m,v in hmaes.items()}
        if "harmonie" in inv: inv["harmonie"] *= 1.2
        tot = sum(inv.values())
        for m in all_keys:
            if m in inv: model["weights"][m] = round(inv[m]/tot,4)

    model["training_days"] = model.get("training_days",0)+1
    model["last_updated"] = datetime.now(timezone.utc).isoformat()
    model["mae_history"].append({
        "date":datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "obs_source":model["obs_source"],"mae":mae_summary
    })
    model["mae_history"] = model["mae_history"][-90:]

    print(f"  ✅ {model['training_days']} þjálfunardagar")
    for m,s in mae_summary.items():
        b=model["biases"][m]; w=model["weights"].get(m,0)
        print(f"     {m:12s}: MAE={s['hiti']:.2f}°C  bias={b['hiti']:+.2f}°C  þyngd={w:.0%}")
    return model

# ─── 5. JOLLY SPÁ ────────────────────────────────────────────────────────────
def make_jolly_forecast(forecasts, harmonie, model):
    print("🔮 Bý til Jolly spá (5 dagar)...")

    if forecasts is None and harmonie is None:
        print("  ❌ Engin spágögn")
        return None

    fc_times   = forecasts["hourly"]["time"] if forecasts else []
    harm_times = harmonie["hourly"]["time"]  if harmonie  else []
    all_times  = sorted(set(fc_times + harm_times))
    now        = datetime.now(timezone.utc)
    future     = [t for t in all_times if t >= now.strftime("%Y-%m-%dT%H:00")]
    all_keys   = list(MODELS.keys()) + ["harmonie"]

    jolly = {
        "generated": now.isoformat(),
        "station":   {"lat":LAT,"lon":LON,"id":STATION_ID,"name":"Egilsstaðir"},
        "model_name":"Jolly v1.3",
        "training_days": model.get("training_days",0),
        "obs_source":    model.get("obs_source","unknown"),
        "weights":       model["weights"],
        "models_used":   all_keys,
        "hourly":{
            "time":[],"temperature":[],"windspeed":[],
            "winddirection":[],"precipitation":[],
            "model_temperatures":  {m:[] for m in all_keys},
            "model_windspeeds":    {m:[] for m in all_keys},
            "model_winddirections":{m:[] for m in all_keys},
        },
        "daily":{
            "date":[],"temp_max":[],"temp_min":[],
            "precipitation_total":[],"wind_avg":[],
            "wind_dir_dominant":[],"wind_dir_dominant_deg":[],
        }
    }

    def gfc(key, idx):
        if not forecasts or idx is None: return None
        arr = forecasts["hourly"].get(key,[])
        return arr[idx] if idx < len(arr) else None

    def gharm(key, t):
        if not harmonie or t not in harm_times: return None
        i = harm_times.index(t)
        arr = harmonie["hourly"].get(key,[])
        return arr[i] if i < len(arr) else None

    # Klukkustundaspá — 120 klst = 5 dagar
    for t in future[:120]:
        jolly["hourly"]["time"].append(t)
        fc_idx = fc_times.index(t) if t in fc_times else None
        temps,winds,precs,dirs = [],[],[],[]

        for m_key, m_api in MODELS.items():
            w = model["weights"].get(m_key, 1.0/len(all_keys))
            b = model["biases"][m_key]
            rt = gfc(f"temperature_2m_{m_api}", fc_idx)
            rw = gfc(f"windspeed_10m_{m_api}", fc_idx)
            rp = gfc(f"precipitation_{m_api}", fc_idx)
            rd = gfc(f"winddirection_10m_{m_api}", fc_idx)

            ct = round(rt+b["hiti"],1) if rt is not None else None
            cw = round(max(0,rw+b["vindur"]),1) if rw is not None else None
            jolly["hourly"]["model_temperatures"][m_key].append(ct)
            jolly["hourly"]["model_windspeeds"][m_key].append(cw)
            jolly["hourly"]["model_winddirections"][m_key].append(round(rd,1) if rd is not None else None)
            if ct is not None: temps.append((ct,w))
            if cw is not None: winds.append((cw,w))
            if rd is not None: dirs.append((rd,w))
            if rp is not None: precs.append((max(0,rp*b["urkoma_scale"]),w))

        hw = model["weights"].get("harmonie",0)
        hb = model["biases"]["harmonie"]
        ht = gharm("temperature",t); hws = gharm("windspeed",t)
        hp = gharm("precipitation",t); hd = gharm("winddirection",t)
        ct = round(ht+hb["hiti"],1) if ht is not None else None
        cw = round(max(0,hws+hb["vindur"]),1) if hws is not None else None
        jolly["hourly"]["model_temperatures"]["harmonie"].append(ct)
        jolly["hourly"]["model_windspeeds"]["harmonie"].append(cw)
        jolly["hourly"]["model_winddirections"]["harmonie"].append(round(hd,1) if hd is not None else None)
        if ct is not None: temps.append((ct,hw))
        if cw is not None: winds.append((cw,hw))
        if hd is not None: dirs.append((hd,hw))
        if hp is not None: precs.append((max(0,hp*hb["urkoma_scale"]),hw))

        def wavg(p):
            if not p: return None
            tw=sum(w for _,w in p)
            return round(sum(v*w for v,w in p)/tw,2) if tw>0 else None

        def wavg_ang(p):
            if not p: return None
            tw=sum(w for _,w in p)
            if tw==0: return None
            ss=sum(math.sin(math.radians(v))*w for v,w in p)
            cs=sum(math.cos(math.radians(v))*w for v,w in p)
            return round(math.degrees(math.atan2(ss/tw,cs/tw))%360,1)

        jolly["hourly"]["temperature"].append(wavg(temps))
        jolly["hourly"]["windspeed"].append(wavg(winds))
        jolly["hourly"]["winddirection"].append(wavg_ang(dirs))
        jolly["hourly"]["precipitation"].append(wavg(precs))

    # ─── DAGLEG SAMANTEKT ───────────────────────────────────────────────────
    print("  📅 Reikna daglegar vindáttir og samantekt...")
    times  = jolly["hourly"]["time"]
    temps  = jolly["hourly"]["temperature"]
    winds  = jolly["hourly"]["windspeed"]
    dirs   = jolly["hourly"]["winddirection"]
    precs  = jolly["hourly"]["precipitation"]

    days = {}
    for i, t in enumerate(times):
        d = t[:10]  # "2026-06-25"
        if d not in days:
            days[d] = {"temps":[],"winds":[],"dirs":[],"precs":[]}
        if temps[i] is not None: days[d]["temps"].append(temps[i])
        if winds[i] is not None: days[d]["winds"].append(winds[i])
        if dirs[i]  is not None: days[d]["dirs"].append(dirs[i])
        if precs[i] is not None: days[d]["precs"].append(precs[i])

    for d, v in days.items():
        dom_deg = None
        dom_dir = None
        if v["dirs"]:
            # Finna algengustu vindátt með circular clustering
            dir_labels = [deg_to_dir(x) for x in v["dirs"]]
            most_common = Counter(dir_labels).most_common(1)[0][0]
            dom_dir = most_common
            # Meðal gráður fyrir þá átt
            matching = [x for x,lb in zip(v["dirs"],dir_labels) if lb==most_common]
            if matching:
                ss = sum(math.sin(math.radians(x)) for x in matching)
                cs = sum(math.cos(math.radians(x)) for x in matching)
                dom_deg = round(math.degrees(math.atan2(ss,cs))%360,1)

        jolly["daily"]["date"].append(d)
        jolly["daily"]["temp_max"].append(round(max(v["temps"]),1) if v["temps"] else None)
        jolly["daily"]["temp_min"].append(round(min(v["temps"]),1) if v["temps"] else None)
        jolly["daily"]["precipitation_total"].append(round(sum(v["precs"]),1) if v["precs"] else 0)
        jolly["daily"]["wind_avg"].append(round(mean(v["winds"]),1) if v["winds"] else None)
        jolly["daily"]["wind_dir_dominant"].append(dom_dir)
        jolly["daily"]["wind_dir_dominant_deg"].append(dom_deg)

    print(f"  ✅ {len(jolly['hourly']['time'])} klukkustundir, {len(jolly['daily']['date'])} dagar")
    # Prenta daglegar niðurstöður
    for i,d in enumerate(jolly["daily"]["date"]):
        mn=jolly["daily"]["temp_min"][i]; mx=jolly["daily"]["temp_max"][i]
        wr=jolly["daily"]["precipitation_total"][i]
        wa=jolly["daily"]["wind_avg"][i]; wd=jolly["daily"]["wind_dir_dominant"][i]
        print(f"     {d}: {mn}–{mx}°C  💧{wr}mm  💨{wa}m/s  🧭{wd}")

    return jolly

# ─── 6. VISTA ────────────────────────────────────────────────────────────────
def save_data(model, forecast):
    print("💾 Vista gögn...")
    with open(DATA_DIR/"jolly_model.json","w") as f:
        json.dump(model,f,indent=2,ensure_ascii=False)
    print("  ✅ Líkan vistað")
    if forecast:
        with open(DATA_DIR/"jolly_forecast.json","w") as f:
            json.dump(forecast,f,indent=2,ensure_ascii=False)
        print("  ✅ Spá vistuð")
    log_path = DATA_DIR/"run_log.json"
    log = []
    if log_path.exists():
        with open(log_path) as f: log=json.load(f)
    log.append({"time":datetime.now(timezone.utc).isoformat(),
                "training_days":model.get("training_days",0),
                "obs_source":model.get("obs_source","unknown"),
                "status":"ok" if forecast else "partial","version":"1.3"})
    log=log[-30:]
    with open(log_path,"w") as f: json.dump(log,f,indent=2)

# ─── AÐALFALL ────────────────────────────────────────────────────────────────
def main():
    print("="*60)
    print(f"🌦  JOLLY v1.3 — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("    ICON + GFS + ECMWF + MetNo + HARMONIE | 5 daga spá")
    print("="*60)
    forecasts    = fetch_forecasts()
    harmonie     = fetch_vedurstofa_harmonie()
    observations = fetch_observations()
    model        = train_jolly(forecasts,observations,harmonie)
    forecast     = make_jolly_forecast(forecasts,harmonie,model)
    save_data(model,forecast)
    print("="*60)
    print("✅ Jolly v1.3 lokið!")
    if model.get("weights"):
        for m,w in sorted(model["weights"].items(),key=lambda x:-x[1]):
            print(f"   {m:12s}: {w:.1%}")
    print("="*60)

if __name__=="__main__":
    main()
