"""
Jolly - Staðbundið veðurspálíkan fyrir Egilsstaði
Sækir gögn frá Open-Meteo og Veðurstofu, þjálfar MOS leiðréttingu
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
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

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
        f"&hourly=temperature_2m,windspeed_10m,precipitation,weathercode"
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

# ─── 2. SÆKJA MÆLINGAR FRÁ VEÐURSTOFU ───────────────────────────────────────
def fetch_observations():
    print("🌡️  Sæki mælingar frá Veðurstofu Íslands...")
    # Veðurstofa open API - observations for station 571
    url = (
        f"https://api.vedur.is/v1/observations/stations/{STATION_ID}"
        f"?param=T,F,R&time_from=-7d"
    )
    try:
        data = fetch_url(url)
        print(f"  ✅ Tókst - Veðurstofa gögn")
        return data
    except Exception as e:
        print(f"  ⚠️  Veðurstofa API villa: {e}")
        print("  🔄 Reyni Open-Meteo ERA5 sem staðgengil...")
        return fetch_observations_era5()

def fetch_observations_era5():
    """Nota Open-Meteo historical sem staðgengil ef Veðurstofa API er ekki tiltæk"""
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={LAT}&longitude={LON}"
        f"&hourly=temperature_2m,windspeed_10m,precipitation"
        f"&models=best_match"
        f"&past_days=7&forecast_days=0"
        f"&timezone=UTC"
        f"&wind_speed_unit=ms"
    )
    try:
        data = fetch_url(url)
        # Format like observations
        obs = {"source": "open-meteo-best", "hourly": {}}
        obs["hourly"]["time"] = data["hourly"]["time"]
        obs["hourly"]["temperature"] = data["hourly"]["temperature_2m"]
        obs["hourly"]["windspeed"] = data["hourly"]["windspeed_10m"]
        obs["hourly"]["precipitation"] = data["hourly"]["precipitation"]
        print(f"  ✅ ERA5 staðgengill tókst")
        return obs
    except Exception as e:
        print(f"  ❌ ERA5 villa líka: {e}")
        return None

# ─── 3. ÞJÁLFA JOLLY LÍKANIÐ ─────────────────────────────────────────────────
def train_jolly(forecasts, observations):
    print("🧠 Þjálfar Jolly líkanið...")

    # Load existing model if available
    model_path = DATA_DIR / "jolly_model.json"
    if model_path.exists():
        with open(model_path) as f:
            model = json.load(f)
        print(f"  📂 Hlaðið inn fyrra líkani ({model.get('training_days', 0)} þjálfunardagar)")
    else:
        model = {
            "version": "1.0",
            "created": datetime.now(timezone.utc).isoformat(),
            "training_days": 0,
            "biases": {m: {"hiti": 0.0, "vindur": 0.0, "urkoma_scale": 1.0} for m in MODELS},
            "weights": {m: 1.0 / len(MODELS) for m in MODELS},
            "mae_history": [],
            "last_updated": None,
        }
        print("  🆕 Nýtt líkan stofnað")

    if forecasts is None or observations is None:
        print("  ⚠️  Ekki hægt að þjálfa - gögn vantar")
        return model

    # Get observation times and values
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

    # Update biases using exponential moving average (learning rate 0.3)
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
        if p_pairs and mean([o for o, _ in p_pairs]) and mean([o for o, _ in p_pairs]) > 0:
            obs_mean = mean([o for o, _ in p_pairs])
            fc_mean  = mean([f for _, f in p_pairs])
            if fc_mean and fc_mean > 0:
                new_scale = obs_mean / fc_mean
                model["biases"][m_key]["urkoma_scale"] = (
                    (1 - LR) * model["biases"][m_key]["urkoma_scale"] + LR * new_scale
                )

        # Compute MAE after correction
        corrected_h = [(o, f + model["biases"][m_key]["hiti"]) for o, f in h_pairs]
        corrected_v = [(o, f + model["biases"][m_key]["vindur"]) for o, f in v_pairs]

        mae_summary[m_key] = {
            "hiti":   round(mae(corrected_h) or 0, 3),
            "vindur": round(mae(corrected_v) or 0, 3),
        }

    # Update model weights based on recent MAE (inverse weighting)
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
        "mae": mae_summary,
    })
    # Keep only last 90 days of history
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
        "model_name": "Jolly v1",
        "training_days": model.get("training_days", 0),
        "weights": model["weights"],
        "hourly": {"time": [], "temperature": [], "windspeed": [], "precipitation": [],
                   "model_temperatures": {}, "model_windspeeds": {}},
    }

    for m_key in MODELS:
        jolly_forecast["hourly"]["model_temperatures"][m_key] = []
        jolly_forecast["hourly"]["model_windspeeds"][m_key] = []

    for t in future_times[:72]:  # 72 klst. spá
        idx = fc_times.index(t)
        jolly_forecast["hourly"]["time"].append(t)

        # Weighted ensemble with bias correction
        temps, winds, precs = [], [], []

        for m_key, m_api in MODELS.items():
            t_key = f"temperature_2m_{m_api}"
            w_key = f"windspeed_10m_{m_api}"
            p_key = f"precipitation_{m_api}"
            w = model["weights"].get(m_key, 1.0/len(MODELS))
            b = model["biases"][m_key]

            fc_t = forecasts["hourly"].get(t_key, [])
            fc_w = forecasts["hourly"].get(w_key, [])
            fc_p = forecasts["hourly"].get(p_key, [])

            raw_t = fc_t[idx] if idx < len(fc_t) else None
            raw_w = fc_w[idx] if idx < len(fc_w) else None
            raw_p = fc_p[idx] if idx < len(fc_p) else None

            if raw_t is not None:
                corr_t = raw_t + b["hiti"]
                temps.append((corr_t, w))
                jolly_forecast["hourly"]["model_temperatures"][m_key].append(round(corr_t, 1))
            else:
                jolly_forecast["hourly"]["model_temperatures"][m_key].append(None)

            if raw_w is not None:
                corr_w = max(0, raw_w + b["vindur"])
                winds.append((corr_w, w))
                jolly_forecast["hourly"]["model_windspeeds"][m_key].append(round(corr_w, 1))
            else:
                jolly_forecast["hourly"]["model_windspeeds"][m_key].append(None)

            if raw_p is not None:
                corr_p = max(0, raw_p * b["urkoma_scale"])
                precs.append((corr_p, w))

        # Weighted average
        def wavg(pairs):
            if not pairs: return None
            total_w = sum(w for _, w in pairs)
            return round(sum(v * w for v, w in pairs) / total_w, 2) if total_w > 0 else None

        jolly_forecast["hourly"]["temperature"].append(wavg(temps))
        jolly_forecast["hourly"]["windspeed"].append(wavg(winds))
        jolly_forecast["hourly"]["precipitation"].append(wavg(precs))

    print(f"  ✅ Jolly spá tilbúin - {len(jolly_forecast['hourly']['time'])} tímapunktar")
    return jolly_forecast

# ─── 5. VISTA GÖGN ───────────────────────────────────────────────────────────
def save_data(model, forecast):
    print("💾 Vista gögn...")

    # Save model
    with open(DATA_DIR / "jolly_model.json", "w") as f:
        json.dump(model, f, indent=2, ensure_ascii=False)
    print("  ✅ Líkan vistað")

    # Save forecast
    if forecast:
        with open(DATA_DIR / "jolly_forecast.json", "w") as f:
            json.dump(forecast, f, indent=2, ensure_ascii=False)
        print("  ✅ Spá vistuð")

    # Save run log
    log_path = DATA_DIR / "run_log.json"
    log = []
    if log_path.exists():
        with open(log_path) as f:
            log = json.load(f)
    log.append({
        "time": datetime.now(timezone.utc).isoformat(),
        "training_days": model.get("training_days", 0),
        "status": "ok" if forecast else "partial",
    })
    log = log[-30:]  # Keep last 30 runs
    with open(log_path, "w") as f:
        json.dump(log, f, indent=2)

# ─── AÐALFALL ────────────────────────────────────────────────────────────────
def main():
    print("=" * 55)
    print(f"🌦  JOLLY VEÐURLÍKAN — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
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
