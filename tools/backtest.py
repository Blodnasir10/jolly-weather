"""
Jolly endurspilun (backtest) - prófar blöndunaraðferðir á langtímasafninu.

ORSAKASAMHENGI: til að spá fyrir (gildistíma t, spálengd L) má aðeins nota
pör sem voru ÞEGAR sannreynd á útgáfutíma t-L. Annars svindlar prófið.

Keyrsla:  python3 backtest.py docs/data/verify/*.csv
"""
import sys, math
from collections import defaultdict, deque
import pandas as pd

MEMBERS = ["dmi", "knmi", "ecmwf", "icon", "ukmo", "mfr", "gfs", "harmonie", "metno"]
VARS = {"hiti": ("t_fc", "t_ob"), "vindur": ("w_fc", "w_ob"),
        "att": ("d_fc", "d_ob"), "sky": ("c_fc", "c_ob")}
LEADS = [1, 3, 6, 12, 24, 48]
CUTOFF = pd.Timestamp("2000-01-01")
RB_WINDOWS = (2, 7, 14)
EPS = {"hiti": 0.05, "vindur": 0.05, "att": 3.0, "sky": 1.0}


def angdiff(f, o):
    return ((f - o + 180.0) % 360.0) - 180.0


def err(var, f, o):
    return angdiff(f, o) if var == "att" else f - o


def cmean(var, vals, w=None):
    w = w or [1.0] * len(vals)
    if var == "att":
        s = sum(wi * math.sin(math.radians(v)) for v, wi in zip(vals, w))
        c = sum(wi * math.cos(math.radians(v)) for v, wi in zip(vals, w))
        return math.degrees(math.atan2(s, c)) % 360
    return sum(v * wi for v, wi in zip(vals, w)) / sum(w)


def load(paths):
    d = pd.concat([pd.read_csv(p) for p in paths], ignore_index=True)
    d["t"] = pd.to_datetime(d["valid_time"])
    return d


class Rolling:
    """Keðja af sannreyndum villum per (gjafi, spálengd, breyta), aðeins
    þær sem voru tiltækar á tilteknum útgáfutíma."""
    def __init__(self, window_h):
        self.win = pd.Timedelta(hours=window_h)
        self.q = defaultdict(deque)      # key -> deque[(valid_time, err)]

    def add(self, key, t, e):
        self.q[key].append((t, e))

    def stats(self, key, issue_t):
        q = self.q[key]
        lo = issue_t - self.win
        while q and q[0][0] < lo:
            q.popleft()
        es = [e for t, e in q if t <= issue_t]
        if not es:
            return None, None, 0
        return sum(es) / len(es), sum(abs(e) for e in es) / len(es), len(es)


def run(d, var, window_h=14 * 24, min_n=10):
    """Endurspilar tímaröð fyrir eina breytu. Skilar dict aðferð->lead->[abs villa]."""
    fcol, ocol = VARS[var]
    piv_f = d.pivot_table(index=["t", "lead"], columns="src", values=fcol, aggfunc="first")
    obs = d.groupby(["t", "lead"])[ocol].first()
    roll = Rolling(window_h)
    rbroll = {wd: Rolling(wd * 24) for wd in RB_WINDOWS}
    res = defaultdict(lambda: defaultdict(list))
    # röð eftir gildistíma svo villur verði "sannreyndar" í réttri tímaröð
    for (t, L), row in piv_f.sort_index().iterrows():
        o = obs.get((t, L))
        if o is None or pd.isna(o):
            continue
        issue = t - pd.Timedelta(hours=L)
        mem = {m: row[m] for m in MEMBERS if m in row and pd.notna(row[m])}
        if len(mem) < 5:
            continue
        # --- tölfræði sem var TILTÆK á útgáfutíma ---
        st = {m: roll.stats((m, L), issue) for m in mem}
        ready = all(st[m][2] >= min_n for m in mem)

        def add(name, f):
            if f is not None and t >= CUTOFF:
                res[name][L].append(abs(err(var, f, o)))

        has_j = "jolly" in row and pd.notna(row["jolly"])
        if ready and has_j:
            vals = list(mem.values())
            raw_mean = cmean(var, vals)
            add("medaltal_hratt", raw_mean)
            for wd in RB_WINDOWS:
                rb = rbroll[wd].stats(("blend", L), issue)
                if rb[2] >= min_n:
                    f2 = (raw_mean - rb[0]) % 360 if var == "att" else raw_mean - rb[0]
                    add(f"hratt+restbias_{wd}d", f2)
            # bias-leiðrétt (bias = meðalvilla síðustu daga)
            corr = {}
            for m, f in mem.items():
                b = st[m][0]
                corr[m] = (f - b) % 360 if var == "att" else f - b
            if var == "sky":
                corr = {m: min(100, max(0, f)) for m, f in corr.items()}
            cv = list(corr.values())
            add("medaltal_leidrett", cmean(var, cv))
            # öfug-MAE þyngdir (kjarni Jolly)
            w = [1.0 / (st[m][1] + EPS[var]) for m in corr]
            add("ofugMAE_leidrett", cmean(var, cv, w))
            # besta líkanið hingað til
            best = min(mem, key=lambda m: st[m][1])
            add("besta_hingad_til", corr[best])
            # Jolly eins og hún var birt
            add("jolly_birt", row["jolly"])
            for m, f in mem.items():
                add(f"hratt:{m}", f)
        # --- NÚ er þessi gildistími sannreyndur: skrá villur ---
        if len(mem) >= 5:
            be = err(var, cmean(var, list(mem.values())), o)
            for wd in RB_WINDOWS:
                rbroll[wd].add(("blend", L), t, be)
        for m, f in mem.items():
            roll.add((m, L), t, err(var, f, o))
    return res


def report(res, var):
    names = [n for n in res if not n.startswith("hratt:")]
    best_raw = {}
    for L in LEADS:
        raws = [(sum(v[L]) / len(v[L]), n[6:]) for n, v in res.items()
                if n.startswith("hratt:") and v[L]]
        best_raw[L] = min(raws) if raws else (None, None)
    print(f"\n=== {var.upper()}  (MAE, sama úrtak fyrir allar aðferðir innan spálengdar) ===")
    print(f"  {'aðferð':22}" + "".join(f"{str(L)+'kl':>9}" for L in LEADS))
    for n in names + ["__best_raw"]:
        cells = []
        for L in LEADS:
            if n == "__best_raw":
                v, m = best_raw[L]
                cells.append(f"{v:9.2f}" if v is not None else f"{'-':>9}")
            else:
                v = res[n][L]
                cells.append(f"{sum(v)/len(v):9.2f}" if v else f"{'-':>9}")
        lbl = "besta hráa (eftir á)" if n == "__best_raw" else n
        print(f"  {lbl:22}" + "".join(cells))
    ns = [len(res["medaltal_hratt"][L]) for L in LEADS]
    print(f"  {'n':22}" + "".join(f"{x:9d}" for x in ns))


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--fra=")]
    for a in sys.argv[1:]:
        if a.startswith("--fra="):
            CUTOFF = pd.Timestamp(a[6:])
    paths = args or ["2026-08.csv", "2026-09.csv"]
    d = load(paths)
    for var in ("hiti", "vindur", "att", "sky"):
        report(run(d, var), var)
