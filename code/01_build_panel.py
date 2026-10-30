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

# Exact indicator name in the district file -> short variable name
DISTRICT_VARS = {
    "Households using clean fuel for cooking (%)": "clean_fuel",
    "Population living in households with electricity (%)": "electricity",
    "Population living in households that use an improved sanitation facility (%)": "sanitation",
    "Population living in households with an improved drinkingwater source (%)": "water",
    "Women who are literate (%)": "women_literate",
    "Women with 10 or more years of schooling (%)": "women_school10",
    "Prevalence of symptoms of acute respiratory infection (ARI) in the 2 weeks preceding the survey (%)": "child_ari",
    "Children under 5 years who are stunted (height for age) (%)": "child_stunted",
    "Children under 5 years who are underweight (weight for age) (%)": "child_underweight",
    "Children age 6-59 months who are anaemic ": "child_anaemic",
    "Nonpregnant women age 15-49 years who are anaemic ": "women_anaemic_np",
    "Institutional births (%)": "inst_births",  # placebo: not plausibly driven by cooking fuel
}

# State file uses numbered indicator prefixes
STATE_VARS = {
    "7.": "electricity",
    "9.": "sanitation",
    "10.": "clean_fuel",
    "65.": "child_ari",
    "125.": "spousal_violence",
}


def to_num(s):
    # Factsheet values can carry footnote markers like "(12.3)" or "*"
    return pd.to_numeric(
        s.astype(str).str.replace(r"[()*,]", "", regex=True).str.strip(), errors="coerce"
    )


# District panel (641 districts; source: SaiSiddhardhaKalla/NFHS, IIPS factsheets)
d = pd.read_csv(RAW / "nfhs_districts_641_kalla.csv", low_memory=False)
# Districts created after NFHS-4 have no DISTRICT id and NFHS-4 coded as 0
d = d[d["DISTRICT"].notna() & d["Indicator"].isin(DISTRICT_VARS)].copy()
d["var"] = d["Indicator"].map(DISTRICT_VARS)
d["nfhs4"], d["nfhs5"] = to_num(d["NFHS 4"]), to_num(d["NFHS 5"])
dw = d.pivot_table(index=["State", "DISTRICT"], columns="var", values=["nfhs4", "nfhs5"], aggfunc="first")
dw.columns = [f"{v}_{r}" for r, v in dw.columns]
dw = dw.reset_index()
# Keep districts observed in both rounds; 0% clean fuel in NFHS-4 is the missing code
dw = dw[(dw["clean_fuel_nfhs4"] > 0) & dw["clean_fuel_nfhs5"].notna()]
dw.to_csv(CLEAN / "district_panel.csv", index=False)
print(f"district_panel: {len(dw)} districts, {dw.State.nunique()} states/UTs")

# State panel
s = pd.read_csv(RAW / "nfhs5_states_with_nfhs4.csv")
parts = []
for prefix, name in STATE_VARS.items():
    sub = s[s["indicator"].str.startswith(prefix + " ")].copy()
    sub["var"] = name
    parts.append(sub)
s = pd.concat(parts)
s["nfhs4"], s["nfhs5"] = to_num(s["nfhs4_total"]), to_num(s["nfhs5_total"])
sw = s.pivot_table(index="state", columns="var", values=["nfhs4", "nfhs5"])
sw.columns = [f"{v}_{r}" for r, v in sw.columns]
sw = sw.reset_index()
sw.to_csv(CLEAN / "state_panel.csv", index=False)
print(f"state_panel: {len(sw)} states/UTs")
