"""
Jolly v1.2 - Staðbundið veðurspálíkan fyrir Egilsstaði
Líkön: ICON + GFS + ECMWF + MetNo Nordic + Veðurstofa XML (HARMONIE)
"""

import json
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path
import math
import xml.etree.ElementTree as ET

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
    req = urllib.request.Request(url, headers={"User-Agent": "Jolly-Weather/1.2"})
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

def circular_mean(angles):
    """Reikna meðaltal vindáttar (circular mean)"""
    valid = [a for a in angles if a is not None]
    if not valid:
        return None
    sin_sum = sum(math.sin(math.radians(a)) for a in valid)
    cos_sum = sum(math.cos(math.radians(a)) for a in valid)
    return round(math.degrees(math.atan2(sin_sum, cos_sum)) % 360, 1)

# ─── 1. SÆKJA LÍKANSSPÁR FRÁ OPEN-METEO ─────────────────────────────────────
def fetch_forecasts():
    print("📡 Sæki líkansspár frá Open-Meteo (ICON + GFS + ECMWF + MetNo)...")
    models_str = ",".join(MODELS.values())
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={LAT}&longitude={LON}"
        f"&hourly=temperature_2m,windspeed_10m,winddirection_10m,precipitation,weathercode"
        f"&models={models_str}"
        f"&past_days=7&forecast_days=7"
        f"&timezone=UTC"
        f"&wind_speed_unit=ms"
    )
    try:
        data = fetch_url(url)
        n = len(data["hourly"]["time"])
        print(f"  ✅ Tókst - {n} tímapunktar")
        # Staðfesta MetNo
        metno_temps = data["hourly"].get("temperature_2m_metno_nordic", [])
        valid_metno = [t for t in metno_temps if t is not None]
        print(f"  📊 MetNo Nordic: {len(valid_metno)} gild gildi")
        return data
    except Exception as e:
        print(f"  ❌ Villa: {e}")
        return None

# ─── 2. SÆKJA HARMONIE FRÁ VEÐURSTOFU XML ───────────────────────────────────
def fetch_vedurstofa_harmonie():
    """
    Sækja HARMONIE spá frá Veðurstofu Íslands í gegnum XML API
    Þetta er leiðrétt HARMONIE spá fyrir Egilsstaði (stöð 571)
    """
    print("🇮🇸 Sæki HARMONIE spá frá Veðurstofu Íslands (XML)...")
    url = f"https://xmlweather.vedur.is/?op_w=xml&type=forec&lang=is&view=xml&ids={STATION_ID}"
    try:
        xml_text = fetch_url(url, as_text=True)
        root = ET.fromstring(xml_text)

        harmonie = {
            "source": "vedurstofa-harmonie",
            "hourly": {
                "time": [], "temperature": [], "windspeed": [],
                "winddirection": [], "precipitation": [], "weather_desc": []
            }
        }

        # Þátta XML - Veðurstofa snið
        station = root.find(".//station")
        if station is None:
            raise ValueError("Engin stöð í XML svari")

        forecasts = station.findall(".//forecast")
        if not forecasts:
            # Prófum aðra uppbyggingu
            forecasts = root.findall(".//forecast")

        print(f"  📋 {len(forecasts)} spátímapunktar í XML")

        for fc in forecasts:
            ftime = fc.get("ftime") or fc.findtext("ftime", "")
            if not ftime:
                continue
            try:
                # Breyta "2024-06-24 12:00:00" í "2024-06-24T12:00"
                dt = datetime.strptime(ftime.strip(), "%Y-%m-%d %H:%M:%S")
                t_str = dt.strftime("%Y-%m-%dT%H:00")
            except ValueError:
                try:
                    dt = datetime.fromisoformat(ftime.strip().replace(" ", "T"))
                    t_str = dt.strftime("%Y-%m-%dT%H:00")
                except:
                    continue

            def gval(tag):
                v = fc.get(tag) or fc.findtext(tag, "")
                try:
                    return float(v) if v and v.strip() not in ("", "-") else None
                except:
                    return None

            def gstr(tag):
                return fc.get(tag) or fc.findtext(tag, "") or ""

            harmonie["hourly"]["time"].append(t_str)
            harmonie["hourly"]["temperature"].append(gval("T"))
            harmonie["hourly"]["windspeed"].append(gval("F"))
            harmonie["hourly"]["precipitation"].append(gval("R"))
            harmonie["hourly"]["weather_desc"].append(gstr("W"))

            # Vindátt — Veðurstofa gefur bókstafi (N, SA, osfrv.)
            d_str = gstr("D").strip()
            d_deg = dir_to_deg(d_str) if d_str else None
            harmonie["hourly"]["winddirection"].append(d_deg)

        n = len(harmonie["hourly"]["time"])
        if n == 0:
            raise ValueError("Engir tímapunktar úr XML")

        print(f"  ✅ HARMONIE: {n} tímapunktar frá Veðurstofu")
        return harmonie

    except Exception as e:
        print(f"  ⚠️  Veðurstofa HARMONIE villa: {e}")
        print("  🔄 Prófum apis.is staðgengil...")
        return fetch_apisIs_forecast()

def dir_to_deg(d):
    """Breyta vindáttarbókstöfum í gráður"""
    mapping = {
        "N": 0, "NNA": 22.5, "NA": 45, "ANA": 67.5,
        "A": 90, "ASA": 112.5, "SA": 135, "SSA": 157.5,
        "S": 180, "SSV": 202.5, "SV": 225, "VSV": 247.5,
        "V": 270, "VNV": 292.5, "NV": 315, "NNV": 337.5,
        # Enska nöfn líka
        "NNE": 22.5, "NE": 45, "ENE": 67.5,
        "E": 90, "ESE": 112.5, "SE": 135, "SSE": 157.5,
        "SSW": 202.5, "SW": 225, "WSW": 247.5,
        "W": 270, "WNW": 292.5, "NW": 315, "NNW": 337.5,
        "Logn": None, "Calm": None, "": None,
    }
    return mapping.get(d.upper(), None)

def fetch_apisIs_forecast():
    """apis.is spá sem staðgengill"""
    print("  🔄 Sæki spá frá apis.is...")
    url = f"https://apis.is/weather/forecasts/is?stations={STATION_ID}"
    try:
        data = fetch_url(url)
        results = data.get("results", [])
        if not results:
            raise ValueError("Engar niðurstöður")

        station = results[0]
        forecasts = station.get("forecast", [])

        harmonie = {
            "source": "apis.is-forecast",
            "hourly": {
                "time": [], "temperature": [], "windspeed": [],
                "winddirection": [], "precipitation": [], "weather_desc": []
            }
        }

        for fc in forecasts:
            ftime = fc.get("ftime", "")
            if not ftime:
                continue
            try:
                dt = datetime.strptime(ftime.strip(), "%Y-%m-%d %H:%M:%S")
                t_str = dt.strftime("%Y-%m-%dT%H:00")
            except:
                continue

            def gv(k):
                try:
                    v = fc.get(k, "")
                    return float(v) if v and str(v).strip() not in ("", "-") else None
                except:
                    return None

            harmonie["hourly"]["time"].append(t_str)
            harmonie["hourly"]["temperature"].append(gv("T"))
            harmonie["hourly"]["windspeed"].append(gv("F"))
            harmonie["hourly"]["precipitation"].append(gv("R"))
            harmonie["hourly"]["weather_desc"].append(fc.get("W", ""))
            d_str = fc.get("D", "")
            harmonie["hourly"]["winddirection"].append(dir_to_deg(d_str) if d_str else None)

        n = len(harmonie["hourly"]["time"])
        if n == 0:
            raise ValueError("Engir tímapunktar")
        print(f"  ✅ apis.is spá: {n} tímapunktar")
        return harmonie

    except Exception as e:
        print(f"  ❌ apis.is spá villa: {e}")
        return None

# ─── 3. SÆKJA MÆLINGAR ───────────────────────────────────────────────────────
def fetch_observations():
    print("🌡️  Sæki mælingar frá apis.is (Veðurstofa stöð 571)...")
    url = f"https://apis.is/weather/observations/is?stations={STATION_ID}&time=1h"
    try:
        data = fetch_url(url)
        results = data.get("results", [])
        if not results:
            raise ValueError("Engar niðurstöður")

        obs = {"source": "apis.is-obs", "hourly": {
            "time": [], "temperature": [], "windspeed": [],
            "winddirection": [], "precipitation": []
        }}

        for r in results:
            t = r.get("time", "")
            if not t:
                continue
            try:
                dt = datetime.fromisoformat(t.replace("Z", "+00:00"))
                obs["hourly"]["time"].append(dt.strftime("%Y-%m-%dT%H:00"))
                obs["hourly"]["temperature"].append(float(r.get("T", 0) or 0))
                obs["hourly"]["windspeed"].append(float(r.get("F", 0) or 0))
                obs["hourly"]["precipitation"].append(float(r.get("R", 0) or 0))
                d = r.get("D", "")
                obs["hourly"]["winddirection"].append(dir_to_deg(d) if d else None)
            except:
                continue

        if obs["hourly"]["time"]:
            print(f"  ✅ {len(obs['hourly']['time'])} mælingar")
            return obs
        raise ValueError("Ekki tókst að þátta")

    except Exception as e:
        print(f"  ⚠️  apis.is mæling villa: {e}")
        return fetch_observations_openmeteo()

def fetch_observations_openmeteo():
    print("  🔄 Open-Meteo best_match staðgengill...")
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={LAT}&longitude={LON}"
        f"&hourly=temperature_2m,windspeed_10m,winddirection_10m,precipitation"
        f"&models=best_match&past_days=7&forecast_days=0"
        f"&timezone=UTC&wind_speed_unit=ms"
    )
    try:
        data = fetch_url(url)
        obs = {"source": "open-meteo-best", "hourly": {
            "time":         data["hourly"]["time"],
            "temperature":  data["hourly"]["temperature_2m"],
            "windspeed":    data["hourly"]["windspeed_10m"],
            "winddirection":data["hourly"].get("winddirection_10m", []),
            "precipitation":data["hourly"]["precipitation"],
        }}
        print(f"  ✅ {len(obs['hourly']['time'])} tímapunktar")
        return obs
    except Exception as e:
        print(f"  ❌ Open-Meteo villa: {e}")
        return None

# ─── 4. ÞJÁLFA JOLLY ─────────────────────────────────────────────────────────
def train_jolly(forecasts, observations, harmonie):
    print("🧠 Þjálfar Jolly líkanið...")

    model_path = DATA_DIR / "jolly_model.json"
    all_model_keys = list(MODELS.keys()) + ["harmonie"]

    if model_path.exists():
        with open(model_path) as f:
            model = json.load(f)
        # Bæta við nýjum líkönum ef vantar
        for m in all_model_keys:
            if m not in model["biases"]:
                model["biases"][m] = {"hiti": 0.0, "vindur": 0.0, "urkoma_scale": 1.0}
            if m not in model["weights"]:
                model["weights"][m] = 1.0 / len(all_model_keys)
        print(f"  📂 Hlaðið inn líkani ({model.get('training_days', 0)} þjálfunardagar)")
    else:
        model = {
            "version": "1.2",
            "created": datetime.now(timezone.utc).isoformat(),
            "training_days": 0,
            "obs_source": "unknown",
            "biases": {m: {"hiti": 0.0, "vindur": 0.0, "urkoma_scale": 1.0} for m in all_model_keys},
            "weights": {m: 1.0 / len(all_model_keys) for m in all_model_keys},
            "mae_history": [],
            "last_updated": None,
        }
        print("  🆕 Nýtt líkan stofnað (v1.2 — 5 líkön)")

    if observations is None:
        print("  ⚠️  Engar mælingar — þjálfun sleppt")
        return model

    obs_source = observations.get("source", "unknown")
    model["obs_source"] = obs_source
    obs_times = observations["hourly"]["time"]
    obs_temp  = observations["hourly"]["temperature"]
    obs_wind  = observations["hourly"]["windspeed"]
    obs_prec  = observations["hourly"]["precipitation"]

    # Sameina Open-Meteo og HARMONIE í eina gagnageymslu
    all_sources = {}

    # Open-Meteo líkön
    if forecasts:
        fc_times = forecasts["hourly"]["time"]
        for m_key, m_api in MODELS.items():
            all_sources[m_key] = {
                "times": fc_times,
                "temp":  forecasts["hourly"].get(f"temperature_2m_{m_api}", []),
                "wind":  forecasts["hourly"].get(f"windspeed_10m_{m_api}", []),
                "prec":  forecasts["hourly"].get(f"precipitation_{m_api}", []),
            }

    # HARMONIE
    if harmonie:
        all_sources["harmonie"] = {
            "times": harmonie["hourly"]["time"],
            "temp":  harmonie["hourly"]["temperature"],
            "wind":  harmonie["hourly"]["windspeed"],
            "prec":  harmonie["hourly"]["precipitation"],
        }

    # Þjálfa hvert líkan
    new_pairs = {m: {"hiti": [], "vindur": [], "urkoma": []} for m in all_sources}
    n_matched = 0

    for obs_t, obs_tv, obs_wv, obs_pv in zip(obs_times, obs_temp, obs_wind, obs_prec):
        matched_any = False
        for m_key, src in all_sources.items():
            if obs_t in src["times"]:
                i = src["times"].index(obs_t)
                if obs_tv is not None and i < len(src["temp"]) and src["temp"][i] is not None:
                    new_pairs[m_key]["hiti"].append((obs_tv, src["temp"][i]))
                if obs_wv is not None and i < len(src["wind"]) and src["wind"][i] is not None:
                    new_pairs[m_key]["vindur"].append((obs_wv, src["wind"][i]))
                if obs_pv is not None and i < len(src["prec"]) and src["prec"][i] is not None:
                    new_pairs[m_key]["urkoma"].append((obs_pv, src["prec"][i]))
                matched_any = True
        if matched_any:
            n_matched += 1

    if n_matched == 0:
        print("  ⚠️  Engar samsvörun")
        return model

    print(f"  📊 {n_matched} tímapunktar bornir saman við {len(all_sources)} líkön")

    LR = 0.3
    mae_summary = {}

    for m_key in all_sources:
        h_p = new_pairs[m_key]["hiti"]
        v_p = new_pairs[m_key]["vindur"]
        p_p = new_pairs[m_key]["urkoma"]

        if h_p:
            nb = bias(h_p) or 0
            model["biases"][m_key]["hiti"] = (1 - LR) * model["biases"][m_key]["hiti"] + LR * (-nb)
        if v_p:
            nb = bias(v_p) or 0
            model["biases"][m_key]["vindur"] = (1 - LR) * model["biases"][m_key]["vindur"] + LR * (-nb)
        if p_p:
            om = mean([o for o, _ in p_p])
            fm = mean([f for _, f in p_p])
            if om and fm and fm > 0:
                ns = om / fm
                model["biases"][m_key]["urkoma_scale"] = (1 - LR) * model["biases"][m_key]["urkoma_scale"] + LR * ns

        ch = [(o, f + model["biases"][m_key]["hiti"]) for o, f in h_p]
        cv = [(o, f + model["biases"][m_key]["vindur"]) for o, f in v_p]
        mae_summary[m_key] = {
            "hiti":   round(mae(ch) or 0, 3),
            "vindur": round(mae(cv) or 0, 3),
        }

    # Uppfæra þyngdir — HARMONIE fær upphaflega 20% hærri þyngd ef gögn eru til
    hiti_maes = {m: mae_summary[m]["hiti"] for m in mae_summary if mae_summary[m]["hiti"] > 0}
    if hiti_maes:
        inv = {m: 1.0 / v for m, v in hiti_maes.items()}
        # HARMONIE bonus — íslenskt líkan fær 20% aukið vægi
        if "harmonie" in inv:
            inv["harmonie"] *= 1.2
        total = sum(inv.values())
        for m in all_model_keys:
            if m in inv:
                model["weights"][m] = round(inv[m] / total, 4)

    model["training_days"] = model.get("training_days", 0) + 1
    model["last_updated"] = datetime.now(timezone.utc).isoformat()
    model["mae_history"].append({
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "obs_source": obs_source,
        "mae": mae_summary,
    })
    model["mae_history"] = model["mae_history"][-90:]

    print(f"  ✅ Líkan uppfært — {model['training_days']} þjálfunardagar")
    for m, s in mae_summary.items():
        b = model["biases"][m]
        w = model["weights"].get(m, 0)
        print(f"     {m:12s}: MAE={s['hiti']:.2f}°C  bias={b['hiti']:+.2f}°C  þyngd={w:.0%}")

    return model

# ─── 5. BÚA TIL JOLLY SPÁ ────────────────────────────────────────────────────
def make_jolly_forecast(forecasts, harmonie, model):
    print("🔮 Bý til Jolly spá...")

    if forecasts is None and harmonie is None:
        print("  ❌ Engin spágögn")
        return None

    # Sameina tímalista
    fc_times = forecasts["hourly"]["time"] if forecasts else []
    harm_times = harmonie["hourly"]["time"] if harmonie else []
    all_times = sorted(set(fc_times + harm_times))

    now = datetime.now(timezone.utc)
    future = [t for t in all_times if t >= now.strftime("%Y-%m-%dT%H:00")]

    all_model_keys = list(MODELS.keys()) + ["harmonie"]

    jolly = {
        "generated": now.isoformat(),
        "station": {"lat": LAT, "lon": LON, "id": STATION_ID, "name": "Egilsstaðir"},
        "model_name": "Jolly v1.2",
        "training_days": model.get("training_days", 0),
        "obs_source": model.get("obs_source", "unknown"),
        "weights": model["weights"],
        "models_used": all_model_keys,
        "hourly": {
            "time": [], "temperature": [], "windspeed": [],
            "winddirection": [], "precipitation": [],
            "model_temperatures": {m: [] for m in all_model_keys},
            "model_windspeeds":   {m: [] for m in all_model_keys},
            "model_winddirections":{m: [] for m in all_model_keys},
        },
    }

    def get_fc_val(key, idx, fc_times_local):
        if forecasts is None or idx >= len(fc_times_local):
            return None
        return forecasts["hourly"].get(key, [None]*len(fc_times_local))[idx] if idx < len(forecasts["hourly"].get(key, [])) else None

    def get_harm_val(key, t):
        if harmonie is None or t not in harm_times:
            return None
        i = harm_times.index(t)
        arr = harmonie["hourly"].get(key, [])
        return arr[i] if i < len(arr) else None

    for t in future[:72]:
        jolly["hourly"]["time"].append(t)
        fc_idx = fc_times.index(t) if t in fc_times else None

        temps, winds, precs, dirs = [], [], [], []

        for m_key, m_api in MODELS.items():
            w = model["weights"].get(m_key, 1.0/len(all_model_keys))
            b = model["biases"][m_key]

            raw_t = get_fc_val(f"temperature_2m_{m_api}", fc_idx, fc_times) if fc_idx is not None else None
            raw_w = get_fc_val(f"windspeed_10m_{m_api}", fc_idx, fc_times) if fc_idx is not None else None
            raw_p = get_fc_val(f"precipitation_{m_api}", fc_idx, fc_times) if fc_idx is not None else None
            raw_d = get_fc_val(f"winddirection_10m_{m_api}", fc_idx, fc_times) if fc_idx is not None else None

            if raw_t is not None:
                ct = raw_t + b["hiti"]
                temps.append((ct, w))
                jolly["hourly"]["model_temperatures"][m_key].append(round(ct, 1))
            else:
                jolly["hourly"]["model_temperatures"][m_key].append(None)

            if raw_w is not None:
                cw = max(0, raw_w + b["vindur"])
                winds.append((cw, w))
                jolly["hourly"]["model_windspeeds"][m_key].append(round(cw, 1))
            else:
                jolly["hourly"]["model_windspeeds"][m_key].append(None)

            if raw_d is not None:
                dirs.append((raw_d, w))
                jolly["hourly"]["model_winddirections"][m_key].append(round(raw_d, 1))
            else:
                jolly["hourly"]["model_winddirections"][m_key].append(None)

            if raw_p is not None:
                precs.append((max(0, raw_p * b["urkoma_scale"]), w))

        # HARMONIE
        hw = model["weights"].get("harmonie", 0)
        hb = model["biases"]["harmonie"]
        ht = get_harm_val("temperature", t)
        hws = get_harm_val("windspeed", t)
        hp = get_harm_val("precipitation", t)
        hd = get_harm_val("winddirection", t)

        if ht is not None:
            ct = ht + hb["hiti"]
            temps.append((ct, hw))
            jolly["hourly"]["model_temperatures"]["harmonie"].append(round(ct, 1))
        else:
            jolly["hourly"]["model_temperatures"]["harmonie"].append(None)

        if hws is not None:
            cw = max(0, hws + hb["vindur"])
            winds.append((cw, hw))
            jolly["hourly"]["model_windspeeds"]["harmonie"].append(round(cw, 1))
        else:
            jolly["hourly"]["model_windspeeds"]["harmonie"].append(None)

        if hd is not None:
            dirs.append((hd, hw))
            jolly["hourly"]["model_winddirections"]["harmonie"].append(round(hd, 1))
        else:
            jolly["hourly"]["model_winddirections"]["harmonie"].append(None)

        if hp is not None:
            precs.append((max(0, hp * hb["urkoma_scale"]), hw))

        def wavg(pairs):
            if not pairs: return None
            tw = sum(w for _, w in pairs)
            return round(sum(v*w for v,w in pairs)/tw, 2) if tw > 0 else None

        def wavg_angle(pairs):
            if not pairs: return None
            tw = sum(w for _, w in pairs)
            if tw == 0: return None
            ss = sum(math.sin(math.radians(v))*w for v,w in pairs)
            cs = sum(math.cos(math.radians(v))*w for v,w in pairs)
            return round(math.degrees(math.atan2(ss/tw, cs/tw)) % 360, 1)

        jolly["hourly"]["temperature"].append(wavg(temps))
        jolly["hourly"]["windspeed"].append(wavg(winds))
        jolly["hourly"]["winddirection"].append(wavg_angle(dirs))
        jolly["hourly"]["precipitation"].append(wavg(precs))

    print(f"  ✅ Jolly spá — {len(jolly['hourly']['time'])} tímapunktar, {len([t for t in jolly['hourly']['temperature'] if t is not None])} með hita")
    return jolly

# ─── 6. VISTA ────────────────────────────────────────────────────────────────
def save_data(model, forecast):
    print("💾 Vista gögn...")
    with open(DATA_DIR / "jolly_model.json", "w") as f:
        json.dump(model, f, indent=2, ensure_ascii=False)
    print("  ✅ Líkan vistað")
    if forecast:
        with open(DATA_DIR / "jolly_forecast.json", "w") as f:
            json.dump(forecast, f, indent=2, ensure_ascii=False)
        print("  ✅ Spá vistuð")
    log_path = DATA_DIR / "run_log.json"
    log = []
    if log_path.exists():
        with open(log_path) as f:
            log = json.load(f)
    log.append({
        "time": datetime.now(timezone.utc).isoformat(),
        "training_days": model.get("training_days", 0),
        "obs_source": model.get("obs_source", "unknown"),
        "status": "ok" if forecast else "partial",
        "version": "1.2",
    })
    log = log[-30:]
    with open(log_path, "w") as f:
        json.dump(log, f, indent=2)

# ─── AÐALFALL ────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print(f"🌦  JOLLY v1.2 — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("    ICON + GFS + ECMWF + MetNo Nordic + HARMONIE (Veðurstofa)")
    print("=" * 60)

    forecasts    = fetch_forecasts()
    harmonie     = fetch_vedurstofa_harmonie()
    observations = fetch_observations()
    model        = train_jolly(forecasts, observations, harmonie)
    forecast     = make_jolly_forecast(forecasts, harmonie, model)
    save_data(model, forecast)

    print("=" * 60)
    print("✅ Jolly v1.2 keyrsla lokið!")
    if model.get("weights"):
        print("   Þyngdir:")
        for m, w in sorted(model["weights"].items(), key=lambda x: -x[1]):
            print(f"   {m:12s}: {w:.1%}")
    print("=" * 60)

if __name__ == "__main__":
    main()
