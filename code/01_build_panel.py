"""Build analysis panels from NFHS-4 (2015-16) and NFHS-5 (2019-21) factsheet CSVs.

Outputs:
  data/clean/district_panel.csv  one row per district (wide: x_nfhs4, x_nfhs5)
  data/clean/state_panel.csv     one row per state (wide)
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW, CLEAN = ROOT / "data" / "raw", ROOT / "data" / "clean"
CLEAN.mkdir(parents=True, exist_ok=True)

# Indicator number prefix in the NFHS-5 factsheets -> short variable name
DISTRICT_VARS = {
    "7.": "electricity",
    "9.": "sanitation",
    "10.": "clean_fuel",
    "65.": "child_ari",
    "73.": "child_stunted",
    "81.": "child_anaemic",
    "82.": "women_anaemic_np",
}
STATE_VARS = {**DISTRICT_VARS, "125.": "spousal_violence"}


def to_num(s):
    # Factsheet values can carry footnote markers like "(12.3)" or "*"
    return pd.to_numeric(
        s.astype(str).str.replace(r"[()*,]", "", regex=True).str.strip(), errors="coerce"
    )


def pick(df, col, mapping):
    out = []
    for prefix, name in mapping.items():
        sub = df[df[col].str.startswith(prefix + " ")].copy()
        sub["var"] = name
        out.append(sub)
    return pd.concat(out)


# District panel
d = pd.read_csv(RAW / "nfhs5_districts_with_nfhs4.csv")
d = pick(d, "Indicator", DISTRICT_VARS)
d["nfhs4"], d["nfhs5"] = to_num(d["NFHS-4"]), to_num(d["NFHS-5"])
dw = d.pivot_table(index=["State", "District"], columns="var", values=["nfhs4", "nfhs5"])
dw.columns = [f"{v}_{r}" for r, v in dw.columns]
dw = dw.reset_index()
# Keep districts observed in both rounds (drops districts created after NFHS-4)
dw = dw.dropna(subset=["clean_fuel_nfhs4", "clean_fuel_nfhs5"])
dw.to_csv(CLEAN / "district_panel.csv", index=False)
print(f"district_panel: {len(dw)} districts, {dw.State.nunique()} states")

# State panel
s = pd.read_csv(RAW / "nfhs5_states_with_nfhs4.csv")
s = pick(s, "indicator", STATE_VARS)
s["nfhs4"], s["nfhs5"] = to_num(s["nfhs4_total"]), to_num(s["nfhs5_total"])
sw = s.pivot_table(index="state", columns="var", values=["nfhs4", "nfhs5"])
sw.columns = [f"{v}_{r}" for r, v in sw.columns]
sw = sw.reset_index()
sw.to_csv(CLEAN / "state_panel.csv", index=False)
print(f"state_panel: {len(sw)} states/UTs")
