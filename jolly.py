"""
Jolly v1.4 - Staðbundið veðurspálíkan fyrir Egilsstaði
Keyrir á klukkustundar fresti, safnar raunverulegum mælingum frá stöð 571
Líkön: ICON + GFS + ECMWF + MetNo Nordic + HARMONIE (Veðurstofa)
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
LAT        = 65.2620
LON        = -14.4035
STATION_ID = 571
DATA_DIR   = Path("docs/data")
DATA_DIR.mkdir(exist_ok=True, parents=True)

# Hversu margar klukkustundir af sögulegum mælingum á að geyma
OBS_HISTORY_HOURS = 720   # 30 dagar

MODELS = {
    "icon":  "icon_seamless",
    "gfs":   "gfs_seamless",
    "ecmwf": "ecmwf_ifs025",
    "metno": "metno_nordic",
}

# ─── HJÁLPARFÖLL ─────────────────────────────────────────────────────────────
def fetch_url(url, as_text=False):
    req = urllib.request.Request(url, headers={"User-Agent": "Jolly-Weather/1.4"})
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
    if deg is None: return None
    dirs = ["N","NNA","NA","ANA","A","ASA","SA","SSA",
            "S","SSV","SV","VSV","V","VNV","NV","NNV"]
    return dirs[round(deg / 22.5) % 16]

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
    return mapping.get(str(d).strip().upper(), None)

def now_str():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:00")

# ─── 1. SÆKJA OG GEYMA RAUNVERULEGAR MÆLINGAR ───────────────────────────────
def fetch_and_store_observation():
    """
    Sækir nýjustu mælingu frá stöð 571 í gegnum apis.is
    og bætir henni við obs_history.json
    """
    print("📍 Sæki mælingu frá stöð 571 (apis.is)...")
    
    obs_path = DATA_DIR / "obs_history.json"
    
    # Hlaða inn fyrri mælingum
    history = []
    if obs_path.exists():
        try:
            with open(obs_path) as f:
                history = json.load(f)
        except:
            history = []
    
    # Sækja nýjustu mælingu
    url = f"https://apis.is/weather/observations/is?stations={STATION_ID}&time=1h"
    new_obs = None
    
    try:
        data = fetch_url(url)
        results = data.get("results", [])
        if not results:
            raise ValueError("Engar niðurstöður")
        
        r = results[0]
        t = r.get("time", "")
        if not t:
            raise ValueError("Enginn tími")
        
        dt = datetime.strptime(t.strip(), "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        t_str = dt.strftime("%Y-%m-%dT%H:00")
        
        def gv(k):
            try:
                v = r.get(k, "")
                return float(v) if v and str(v).strip() not in ("", "-") else None
            except: return None
        
        new_obs = {
            "time":         t_str,
            "temperature":  gv("T"),
            "windspeed":    gv("F"),
            "windgust":     gv("FG"),
            "winddirection":dir_to_deg(r.get("D", "")),
            "precipitation":gv("R"),
            "humidity":     gv("RH"),
            "pressure":     gv("P"),
            "source":       "apis.is-571",
        }
        
        # Athuga hvort þessi tímapunktur er þegar til
        existing_times = {h["time"] for h in history}
        if t_str not in existing_times:
            history.append(new_obs)
            print(f"  ✅ Ný mæling bætt við: {t_str} | T={new_obs['temperature']}°C F={new_obs['windspeed']}m/s D={r.get('D','?')}")
        else:
            print(f"  ℹ️  Mæling fyrir {t_str} þegar til")
            
    except Exception as e:
        print(f"  ⚠️  apis.is villa: {e}")
    
    # Hreinsa gamlar mælingar — halda aðeins OBS_HISTORY_HOURS
    if len(history) > OBS_HISTORY_HOURS:
        history = sorted(history, key=lambda x: x["time"])
        history = history[-OBS_HISTORY_HOURS:]
    
    # Vista
    with open(obs_path, "w") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)
    
    print(f"  💾 {len(history)} mælingar geymdar (stöð 571)")
    
    return history, new_obs

# ─── 2. SÆKJA LÍKANSSPÁR FRÁ OPEN-METEO ─────────────────────────────────────
def fetch_forecasts():
    print("📡 Sæki líkansspár frá Open-Meteo...")
    models_str = ",".join(MODELS.values())
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={LAT}&longitude={LON}"
        f"&hourly=temperature_2m,windspeed_10m,winddirection_10m,precipitation,weathercode"
        f"&models={models_str}"
        f"&past_days=2&forecast_days=5"
        f"&timezone=UTC&wind_speed_unit=ms"
    )
    try:
        data = fetch_url(url)
        print(f"  ✅ {len(data['hourly']['time'])} tímapunktar")
        return data
    except Exception as e:
        print(f"  ❌ Villa: {e}")
        return None

# ─── 3. HARMONIE FRÁ VEÐURSTOFU ─────────────────────────────────────────────
def fetch_vedurstofa_harmonie():
    print("🇮🇸 Sæki HARMONIE spá frá Veðurstofu (XML)...")
    url = f"https://xmlweather.vedur.is/?op_w=xml&type=forec&lang=is&view=xml&ids={STATION_ID}"
    try:
        xml_text = fetch_url(url, as_text=True)
        root = ET.fromstring(xml_text)
        harm = {"source":"vedurstofa-harmonie","hourly":{
            "time":[],"temperature":[],"windspeed":[],
            "winddirection":[],"precipitation":[]
        }}
        forecasts = root.findall(".//forecast") or root.findall("forecast")
        for fc in forecasts:
            ftime = fc.get("ftime") or fc.findtext("ftime","")
            if not ftime: continue
            try:
                dt = datetime.strptime(ftime.strip(),"%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                t_str = dt.strftime("%Y-%m-%dT%H:00")
            except:
                try:
                    dt = datetime.fromisoformat(ftime.strip().replace(" ","T")).replace(tzinfo=timezone.utc)
                    t_str = dt.strftime("%Y-%m-%dT%H:00")
                except: continue

            def gv(tag):
                v = fc.get(tag) or fc.findtext(tag,"")
                try: return float(v) if v and v.strip() not in ("","-") else None
                except: return None

            harm["hourly"]["time"].append(t_str)
            harm["hourly"]["temperature"].append(gv("T"))
            harm["hourly"]["windspeed"].append(gv("F"))
            harm["hourly"]["precipitation"].append(gv("R"))
            d = fc.get("D","") or fc.findtext("D","") or ""
            harm["hourly"]["winddirection"].append(dir_to_deg(d))

        n = len(harm["hourly"]["time"])
        if n == 0: raise ValueError("Engir tímapunktar")
        print(f"  ✅ HARMONIE: {n} tímapunktar")
        return harm
    except Exception as e:
        print(f"  ⚠️  HARMONIE villa: {e}")
        return None

# ─── 4. ÞJÁLFUN ──────────────────────────────────────────────────────────────
def train_jolly(forecasts, obs_history, harmonie):
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
        print(f"  📂 Hlaðið inn ({model.get('training_days',0)} þjálfunardagar, {model.get('total_obs',0)} mælingar)")
    else:
        model = {
            "version":"1.4",
            "created":datetime.now(timezone.utc).isoformat(),
            "training_days":0,
            "total_obs":0,
            "obs_source":"apis.is-571",
            "biases":{m:{"hiti":0.0,"vindur":0.0,"urkoma_scale":1.0} for m in all_keys},
            "weights":{m:1.0/len(all_keys) for m in all_keys},
            "mae_history":[],
            "last_updated":None,
        }
        print("  🆕 Nýtt líkan (v1.4)")

    if not obs_history or not forecasts:
        print("  ⚠️  Gögn vantar")
        return model

    # Nota raunverulegar mælingar til þjálfunar
    real_obs = [o for o in obs_history if o.get("source") == "apis.is-571"]
    fallback_obs = obs_history  # nota allt ef engar raunverulegar
    use_obs = real_obs if real_obs else fallback_obs
    
    print(f"  📊 {len(real_obs)} raunverulegar mælingar frá stöð 571 (af {len(obs_history)} samtals)")

    # Sameina spágjafar
    sources = {}
    fc_times = forecasts["hourly"]["time"]
    for m_key, m_api in MODELS.items():
        sources[m_key] = {
            "times": fc_times,
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
    n_matched = 0

    for obs in use_obs:
        ot  = obs.get("time","")
        otv = obs.get("temperature")
        owv = obs.get("windspeed")
        opv = obs.get("precipitation")
        if not ot: continue
        
        hit = False
        for m, src in sources.items():
            if ot in src["times"]:
                i = src["times"].index(ot)
                if otv is not None and i < len(src["temp"]) and src["temp"][i] is not None:
                    pairs[m]["hiti"].append((otv, src["temp"][i]))
                if owv is not None and i < len(src["wind"]) and src["wind"][i] is not None:
                    pairs[m]["vindur"].append((owv, src["wind"][i]))
                if opv is not None and i < len(src["prec"]) and src["prec"][i] is not None:
                    pairs[m]["urkoma"].append((opv, src["prec"][i]))
                hit = True
        if hit: n_matched += 1

    if n_matched == 0:
        print("  ⚠️  Engar samsvörun")
        return model

    print(f"  🎯 {n_matched} tímapunktar bornir saman við {len(sources)} líkön")

    LR = 0.15  # Lægra learning rate — nákvæmari lærdómur
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
            if om is not None and fm and fm > 0:
                model["biases"][m]["urkoma_scale"] = (1-LR)*model["biases"][m]["urkoma_scale"] + LR*(om/fm)
        ch = [(o, f+model["biases"][m]["hiti"]) for o,f in hp]
        cv = [(o, f+model["biases"][m]["vindur"]) for o,f in vp]
        mae_h = mae(ch); mae_v = mae(cv)
        mae_summary[m] = {
            "hiti":   round(mae_h or 0, 3),
            "vindur": round(mae_v or 0, 3),
            "n":      len(hp),
        }

    # Uppfæra þyngdir
    hmaes = {m: mae_summary[m]["hiti"] for m in mae_summary
             if mae_summary[m]["hiti"] > 0 and mae_summary[m]["n"] > 5}
    if hmaes:
        inv = {m: 1.0/v for m,v in hmaes.items()}
        if "harmonie" in inv: inv["harmonie"] *= 1.2
        tot = sum(inv.values())
        for m in all_keys:
            if m in inv:
                model["weights"][m] = round(inv[m]/tot, 4)

    model["training_days"] = model.get("training_days",0) + 1
    model["total_obs"]     = model.get("total_obs",0) + n_matched
    model["last_updated"]  = datetime.now(timezone.utc).isoformat()
    model["obs_source"]    = "apis.is-571" if real_obs else "open-meteo-best"
    
    model["mae_history"].append({
        "date":       datetime.now(timezone.utc).strftime("%Y-%m-%d %H:00"),
        "obs_source": model["obs_source"],
        "n_obs":      n_matched,
        "real_obs":   len(real_obs),
        "mae":        mae_summary,
    })
    model["mae_history"] = model["mae_history"][-720:]  # 30 dagar * 24 klst

    print(f"  ✅ {model['training_days']} keyrsla | {model['total_obs']} heildar samanburðir")
    for m, s in sorted(mae_summary.items(), key=lambda x: x[1]["hiti"]):
        if s["n"] > 0:
            b = model["biases"][m]; w = model["weights"].get(m,0)
            print(f"     {m:12s}: MAE={s['hiti']:.2f}°C bias={b['hiti']:+.2f}°C vind={b['vindur']:+.2f}m/s þyngd={w:.0%} (n={s['n']})")

    return model

# ─── 5. JOLLY SPÁ ────────────────────────────────────────────────────────────
def make_jolly_forecast(forecasts, harmonie, model):
    print("🔮 Bý til Jolly spá (5 dagar)...")

    if forecasts is None:
        print("  ❌ Engin spágögn"); return None

    fc_times   = forecasts["hourly"]["time"]
    harm_times = harmonie["hourly"]["time"] if harmonie else []
    all_times  = sorted(set(fc_times + harm_times))
    now        = datetime.now(timezone.utc)
    future     = [t for t in all_times if t >= now.strftime("%Y-%m-%dT%H:00")]
    all_keys   = list(MODELS.keys()) + ["harmonie"]

    jolly = {
        "generated":    now.isoformat(),
        "station":      {"lat":LAT,"lon":LON,"id":STATION_ID,"name":"Egilsstaðir"},
        "model_name":   "Jolly v1.4",
        "training_days":model.get("training_days",0),
        "total_obs":    model.get("total_obs",0),
        "obs_source":   model.get("obs_source","unknown"),
        "weights":      model["weights"],
        "models_used":  all_keys,
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
        ht  = gharm("temperature",t)
        hws = gharm("windspeed",t)
        hp  = gharm("precipitation",t)
        hd  = gharm("winddirection",t)
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
            tw = sum(w for _,w in p)
            return round(sum(v*w for v,w in p)/tw,2) if tw>0 else None

        def wavg_ang(p):
            if not p: return None
            tw = sum(w for _,w in p)
            if tw == 0: return None
            ss = sum(math.sin(math.radians(v))*w for v,w in p)
            cs = sum(math.cos(math.radians(v))*w for v,w in p)
            return round(math.degrees(math.atan2(ss/tw,cs/tw))%360,1)

        jolly["hourly"]["temperature"].append(wavg(temps))
        jolly["hourly"]["windspeed"].append(wavg(winds))
        jolly["hourly"]["winddirection"].append(wavg_ang(dirs))
        jolly["hourly"]["precipitation"].append(wavg(precs))

    # Dagleg samantekt
    times = jolly["hourly"]["time"]
    temps_h = jolly["hourly"]["temperature"]
    winds_h = jolly["hourly"]["windspeed"]
    dirs_h  = jolly["hourly"]["winddirection"]
    precs_h = jolly["hourly"]["precipitation"]

    days = {}
    for i,t in enumerate(times):
        d = t[:10]
        if d not in days: days[d] = {"temps":[],"winds":[],"dirs":[],"precs":[]}
        if temps_h[i] is not None: days[d]["temps"].append(temps_h[i])
        if winds_h[i] is not None: days[d]["winds"].append(winds_h[i])
        if dirs_h[i]  is not None: days[d]["dirs"].append(dirs_h[i])
        if precs_h[i] is not None: days[d]["precs"].append(precs_h[i])

    for d,v in days.items():
        dom_deg = None; dom_dir = None
        if v["dirs"]:
            dir_labels = [deg_to_dir(x) for x in v["dirs"]]
            most_common = Counter(dir_labels).most_common(1)[0][0]
            dom_dir = most_common
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

    print(f"  ✅ {len(jolly['hourly']['time'])} klst | {len(jolly['daily']['date'])} dagar")
    return jolly

# ─── 6. VISTA ────────────────────────────────────────────────────────────────
def save_data(model, forecast):
    print("💾 Vista gögn...")
    with open(DATA_DIR/"jolly_model.json","w") as f:
        json.dump(model,f,indent=2,ensure_ascii=False)
    if forecast:
        with open(DATA_DIR/"jolly_forecast.json","w") as f:
            json.dump(forecast,f,indent=2,ensure_ascii=False)
    log_path = DATA_DIR/"run_log.json"
    log = []
    if log_path.exists():
        with open(log_path) as f:
            log = json.load(f)
    log.append({
        "time":          datetime.now(timezone.utc).isoformat(),
        "training_days": model.get("training_days",0),
        "total_obs":     model.get("total_obs",0),
        "obs_source":    model.get("obs_source","unknown"),
        "status":        "ok" if forecast else "partial",
        "version":       "1.4",
    })
    log = log[-168:]  # 7 dagar * 24 klst
    with open(log_path,"w") as f:
        json.dump(log,f,indent=2)
    print("  ✅ Allt vistað")

# ─── AÐALFALL ────────────────────────────────────────────────────────────────
def main():
    print("="*60)
    print(f"🌦  JOLLY v1.4 — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("    Klukkustundarlærdómur | Stöð 571 mælingar")
    print("="*60)

    # 1. Sækja og geyma nýjustu mælingu
    obs_history, latest_obs = fetch_and_store_observation()

    # 2. Sækja spálíkön
    forecasts = fetch_forecasts()
    harmonie  = fetch_vedurstofa_harmonie()

    # 3. Þjálfa á sögulegum mælingum
    model = train_jolly(forecasts, obs_history, harmonie)

    # 4. Búa til spá
    forecast = make_jolly_forecast(forecasts, harmonie, model)

    # 5. Vista allt
    save_data(model, forecast)

    print("="*60)
    print("✅ Jolly v1.4 lokið!")
    if model.get("weights"):
        top = sorted(model["weights"].items(), key=lambda x:-x[1])[:3]
        print("   Topp 3 líkön: " + " | ".join(f"{m}: {w:.0%}" for m,w in top))
    print("="*60)

if __name__=="__main__":
    main()
