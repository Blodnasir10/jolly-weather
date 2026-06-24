"""
Jolly - Staðbundið veðurspálíkan fyrir Egilsstaði
Sækir gögn frá Open-Meteo og apis.is/Veðurstofu, þjálfar MOS leiðréttingu
"""

import json
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path
import math

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
}

# ─── HJÁLPARFÖLL ─────────────────────────────────────────────────────────────
def fetch_url(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Jolly-Weather/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())

def mean(vals):
    v = [x for x in vals if x is not None]
    return sum(v) / len(v) if v else None

def mae(pairs):
    v = [(a, b) for a, b in pairs if a is not None and b is not None]
    return sum(abs(a - b) for a, b in v) / len(v) if v else None

def bias(pairs):
    v = [(a, b) for a, b in pairs if a is not None and b is not None]
    return sum(b - a for a, b in v) / len(v) if v else None  # model - obs

# ─── 1. SÆKJA LÍKANSSPÁR FRÁ OPEN-METEO ─────────────────────────────────────
def fetch_forecasts():
    print("📡 Sæki líkansspár frá Open-Meteo...")
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
        print(f"  ✅ Tókst - {len(data['hourly']['time'])} tímapunktar")
        return data
    except Exception as e:
        print(f"  ❌ Villa: {e}")
        return None

# ─── 2. SÆKJA MÆLINGAR FRÁ APIS.IS (Veðurstofa) ─────────────────────────────
def fetch_observations():
    print("🌡️  Sæki mælingar frá apis.is (Veðurstofa Íslands)...")

    # Sækja síðustu 7 daga með 1h upplausn
    url = f"https://apis.is/weather/observations/is?stations={STATION_ID}&time=1h"
    try:
        data = fetch_url(url)
        results = data.get("results", [])
        if not results:
            raise ValueError("Engar niðurstöður")

        # apis.is skilar nýjustu mælingunni - við þurfum fleiri
        # Prófum líka með 3h og dagleg gögn
        print(f"  ✅ Tókst - {len(results)} mælingar frá apis.is")

        # Umbreyta í staðlað snið
        obs = {"source": "apis.is", "hourly": {
            "time": [], "temperature": [], "windspeed": [],
            "winddirection": [], "precipitation": []
        }}

        for r in results:
            t = r.get("time", "")
            if t:
                # Staðla tímasnið
                try:
                    dt = datetime.fromisoformat(t.replace("Z", "+00:00"))
                    obs["hourly"]["time"].append(dt.strftime("%Y-%m-%dT%H:00"))
                    obs["hourly"]["temperature"].append(float(r.get("T", 0) or 0))
                    obs["hourly"]["windspeed"].append(float(r.get("F", 0) or 0))
                    obs["hourly"]["winddirection"].append(r.get("D", ""))
                    obs["hourly"]["precipitation"].append(float(r.get("R", 0) or 0))
                except (ValueError, TypeError):
                    continue

        if obs["hourly"]["time"]:
            print(f"  ✅ {len(obs['hourly']['time'])} tímapunktar úr apis.is")
            return obs
        else:
            raise ValueError("Ekki tókst að þátta gögn")

    except Exception as e:
        print(f"  ⚠️  apis.is villa: {e}")
        print("  🔄 Reyni Open-Meteo best_match sem staðgengil...")
        return fetch_observations_openmeteo()

def fetch_observations_openmeteo():
    """Nota Open-Meteo best_match sem staðgengil"""
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={LAT}&longitude={LON}"
        f"&hourly=temperature_2m,windspeed_10m,winddirection_10m,precipitation"
        f"&models=best_match"
        f"&past_days=7&forecast_days=0"
        f"&timezone=UTC"
        f"&wind_speed_unit=ms"
    )
    try:
        data = fetch_url(url)
        obs = {"source": "open-meteo-best", "hourly": {}}
        obs["hourly"]["time"]         = data["hourly"]["time"]
        obs["hourly"]["temperature"]  = data["hourly"]["temperature_2m"]
        obs["hourly"]["windspeed"]    = data["hourly"]["windspeed_10m"]
        obs["hourly"]["winddirection"]= data["hourly"].get("winddirection_10m", [])
        obs["hourly"]["precipitation"]= data["hourly"]["precipitation"]
        print(f"  ✅ Open-Meteo staðgengill tókst - {len(obs['hourly']['time'])} tímapunktar")
        return obs
    except Exception as e:
        print(f"  ❌ Open-Meteo staðgengill villa: {e}")
        return None

# ─── 3. ÞJÁLFA JOLLY LÍKANIÐ ─────────────────────────────────────────────────
def train_jolly(forecasts, observations):
    print("🧠 Þjálfar Jolly líkanið...")

    model_path = DATA_DIR / "jolly_model.json"
    if model_path.exists():
        with open(model_path) as f:
            model = json.load(f)
        print(f"  📂 Hlaðið inn fyrra líkani ({model.get('training_days', 0)} þjálfunardagar)")
    else:
        model = {
            "version": "1.1",
            "created": datetime.now(timezone.utc).isoformat(),
            "training_days": 0,
            "obs_source": "unknown",
            "biases": {m: {"hiti": 0.0, "vindur": 0.0, "urkoma_scale": 1.0} for m in MODELS},
            "weights": {m: 1.0 / len(MODELS) for m in MODELS},
            "mae_history": [],
            "last_updated": None,
        }
        print("  🆕 Nýtt líkan stofnað")

    if forecasts is None or observations is None:
        print("  ⚠️  Ekki hægt að þjálfa - gögn vantar")
        return model

    obs_source = observations.get("source", "unknown")
    model["obs_source"] = obs_source
    print(f"  📊 Þjálfunargögn frá: {obs_source}")

    obs_times = observations.get("hourly", {}).get("time", [])
    obs_temp  = observations.get("hourly", {}).get("temperature", [])
    obs_wind  = observations.get("hourly", {}).get("windspeed", [])
    obs_prec  = observations.get("hourly", {}).get("precipitation", [])

    fc_times = forecasts["hourly"]["time"]

    new_pairs = {"hiti": {}, "vindur": {}, "urkoma": {}}
    n_matched = 0

    for i, t in enumerate(fc_times):
        if t not in obs_times:
            continue
        obs_idx = obs_times.index(t)
        obs_t = obs_temp[obs_idx] if obs_idx < len(obs_temp) else None
        obs_w = obs_wind[obs_idx] if obs_idx < len(obs_wind) else None
        obs_p = obs_prec[obs_idx] if obs_idx < len(obs_prec) else None

        for m_key, m_api in MODELS.items():
            t_key = f"temperature_2m_{m_api}"
            w_key = f"windspeed_10m_{m_api}"
            p_key = f"precipitation_{m_api}"

            fc_t = forecasts["hourly"].get(t_key, [None]*len(fc_times))
            fc_w = forecasts["hourly"].get(w_key, [None]*len(fc_times))
            fc_p = forecasts["hourly"].get(p_key, [None]*len(fc_times))

            if m_key not in new_pairs["hiti"]:
                new_pairs["hiti"][m_key] = []
                new_pairs["vindur"][m_key] = []
                new_pairs["urkoma"][m_key] = []

            if obs_t is not None and i < len(fc_t) and fc_t[i] is not None:
                new_pairs["hiti"][m_key].append((obs_t, fc_t[i]))
            if obs_w is not None and i < len(fc_w) and fc_w[i] is not None:
                new_pairs["vindur"][m_key].append((obs_w, fc_w[i]))
            if obs_p is not None and i < len(fc_p) and fc_p[i] is not None:
                new_pairs["urkoma"][m_key].append((obs_p, fc_p[i]))

        n_matched += 1

    if n_matched == 0:
        print("  ⚠️  Engar samsvörun fundust milli gagna")
        return model

    print(f"  📊 {n_matched} tímapunktar bornir saman")

    LR = 0.3
    mae_summary = {}

    for m_key in MODELS:
        h_pairs = new_pairs["hiti"].get(m_key, [])
        v_pairs = new_pairs["vindur"].get(m_key, [])
        p_pairs = new_pairs["urkoma"].get(m_key, [])

        if h_pairs:
            new_bias_h = bias(h_pairs) or 0
            model["biases"][m_key]["hiti"] = (
                (1 - LR) * model["biases"][m_key]["hiti"] + LR * (-new_bias_h)
            )
        if v_pairs:
            new_bias_v = bias(v_pairs) or 0
            model["biases"][m_key]["vindur"] = (
                (1 - LR) * model["biases"][m_key]["vindur"] + LR * (-new_bias_v)
            )
        if p_pairs:
            obs_mean = mean([o for o, _ in p_pairs])
            fc_mean  = mean([f for _, f in p_pairs])
            if obs_mean and fc_mean and fc_mean > 0:
                new_scale = obs_mean / fc_mean
                model["biases"][m_key]["urkoma_scale"] = (
                    (1 - LR) * model["biases"][m_key]["urkoma_scale"] + LR * new_scale
                )

        corrected_h = [(o, f + model["biases"][m_key]["hiti"]) for o, f in h_pairs]
        corrected_v = [(o, f + model["biases"][m_key]["vindur"]) for o, f in v_pairs]

        mae_summary[m_key] = {
            "hiti":   round(mae(corrected_h) or 0, 3),
            "vindur": round(mae(corrected_v) or 0, 3),
        }

    # Uppfæra þyngdir
    hiti_maes = {m: mae_summary[m]["hiti"] for m in MODELS if mae_summary[m]["hiti"] > 0}
    if hiti_maes:
        inv = {m: 1.0 / v for m, v in hiti_maes.items()}
        total = sum(inv.values())
        for m in MODELS:
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

    print(f"  ✅ Líkan uppfært - {model['training_days']} þjálfunardagar")
    for m, s in mae_summary.items():
        b = model["biases"][m]
        print(f"     {m:10s}: MAE hiti={s['hiti']:.2f}°C  bias={b['hiti']:+.2f}°C  vind bias={b['vindur']:+.2f}m/s")

    return model

# ─── 4. BÚA TIL JOLLY SPÁ ────────────────────────────────────────────────────
def make_jolly_forecast(forecasts, model):
    print("🔮 Bý til Jolly spá...")

    if forecasts is None:
        print("  ❌ Engar spágögn")
        return None

    fc_times = forecasts["hourly"]["time"]
    now = datetime.now(timezone.utc)
    future_times = [t for t in fc_times if t >= now.strftime("%Y-%m-%dT%H:00")]

    jolly_forecast = {
        "generated": now.isoformat(),
        "station": {"lat": LAT, "lon": LON, "id": STATION_ID, "name": "Egilsstaðir"},
        "model_name": "Jolly v1.1",
        "training_days": model.get("training_days", 0),
        "obs_source": model.get("obs_source", "unknown"),
        "weights": model["weights"],
        "hourly": {
            "time": [], "temperature": [], "windspeed": [],
            "winddirection": [], "precipitation": [],
            "model_temperatures": {},
            "model_windspeeds": {},
            "model_winddirections": {},
        },
    }

    for m_key in MODELS:
        jolly_forecast["hourly"]["model_temperatures"][m_key] = []
        jolly_forecast["hourly"]["model_windspeeds"][m_key] = []
        jolly_forecast["hourly"]["model_winddirections"][m_key] = []

    for t in future_times[:72]:
        idx = fc_times.index(t)
        jolly_forecast["hourly"]["time"].append(t)

        temps, winds, precs, dirs = [], [], [], []

        for m_key, m_api in MODELS.items():
            t_key  = f"temperature_2m_{m_api}"
            w_key  = f"windspeed_10m_{m_api}"
            p_key  = f"precipitation_{m_api}"
            d_key  = f"winddirection_10m_{m_api}"
            wt = model["weights"].get(m_key, 1.0/len(MODELS))
            b  = model["biases"][m_key]

            fc_t = forecasts["hourly"].get(t_key, [])
            fc_w = forecasts["hourly"].get(w_key, [])
            fc_p = forecasts["hourly"].get(p_key, [])
            fc_d = forecasts["hourly"].get(d_key, [])

            raw_t = fc_t[idx] if idx < len(fc_t) else None
            raw_w = fc_w[idx] if idx < len(fc_w) else None
            raw_p = fc_p[idx] if idx < len(fc_p) else None
            raw_d = fc_d[idx] if idx < len(fc_d) else None

            if raw_t is not None:
                corr_t = raw_t + b["hiti"]
                temps.append((corr_t, wt))
                jolly_forecast["hourly"]["model_temperatures"][m_key].append(round(corr_t, 1))
            else:
                jolly_forecast["hourly"]["model_temperatures"][m_key].append(None)

            if raw_w is not None:
                corr_w = max(0, raw_w + b["vindur"])
                winds.append((corr_w, wt))
                jolly_forecast["hourly"]["model_windspeeds"][m_key].append(round(corr_w, 1))
            else:
                jolly_forecast["hourly"]["model_windspeeds"][m_key].append(None)

            if raw_d is not None:
                dirs.append((raw_d, wt))
                jolly_forecast["hourly"]["model_winddirections"][m_key].append(round(raw_d, 1))
            else:
                jolly_forecast["hourly"]["model_winddirections"][m_key].append(None)

            if raw_p is not None:
                corr_p = max(0, raw_p * b["urkoma_scale"])
                precs.append((corr_p, wt))

        def wavg(pairs):
            if not pairs: return None
            total_w = sum(w for _, w in pairs)
            return round(sum(v * w for v, w in pairs) / total_w, 2) if total_w > 0 else None

        def wavg_angle(pairs):
            """Meðaltal vindátta með circular averaging"""
            if not pairs: return None
            sin_sum = sum(math.sin(math.radians(v)) * w for v, w in pairs)
            cos_sum = sum(math.cos(math.radians(v)) * w for v, w in pairs)
            total_w = sum(w for _, w in pairs)
            if total_w == 0: return None
            angle = math.degrees(math.atan2(sin_sum/total_w, cos_sum/total_w))
            return round(angle % 360, 1)

        jolly_forecast["hourly"]["temperature"].append(wavg(temps))
        jolly_forecast["hourly"]["windspeed"].append(wavg(winds))
        jolly_forecast["hourly"]["winddirection"].append(wavg_angle(dirs))
        jolly_forecast["hourly"]["precipitation"].append(wavg(precs))

    print(f"  ✅ Jolly spá tilbúin - {len(jolly_forecast['hourly']['time'])} tímapunktar")
    return jolly_forecast

# ─── 5. VISTA GÖGN ───────────────────────────────────────────────────────────
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
    })
    log = log[-30:]
    with open(log_path, "w") as f:
        json.dump(log, f, indent=2)

# ─── AÐALFALL ────────────────────────────────────────────────────────────────
def main():
    print("=" * 55)
    print(f"🌦  JOLLY VEÐURLÍKAN v1.1 — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 55)

    forecasts    = fetch_forecasts()
    observations = fetch_observations()
    model        = train_jolly(forecasts, observations)
    forecast     = make_jolly_forecast(forecasts, model)
    save_data(model, forecast)

    print("=" * 55)
    print("✅ Jolly keyrsla lokið!")
    print("=" * 55)

if __name__ == "__main__":
    main()
