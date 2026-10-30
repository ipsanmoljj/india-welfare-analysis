"""Bhamashah Swasthya Bima Yojana (BSBY, Rajasthan, launched 13 Dec 2015):
contiguous border-pair DiD (Dube, Lester & Reich 2010) with NFHS-4 -> NFHS-5,
plus a three-round state event study (NFHS-3 -> NFHS-4 -> NFHS-5).

Treatment: Rajasthan's state scheme (BSBY, merged with Ayushman Bharat in 2019
as AB-MGRSBY). Controls: districts across the border, which had RSBY and then
PM-JAY. So beta = effect of Rajasthan's scheme RELATIVE TO the national schemes.

Baseline caveat: Rajasthan's NFHS-4 fieldwork (23 Jan - 21 Jul 2016) started
six weeks after BSBY launched. Early enrolment raises the "pre" level, which
biases beta toward zero, so the estimates are lower bounds.

Border-pair specification (first differences = district FE, 2 periods):
    dY_ip = beta * Rajasthan_i + pair_p + e_ip
Each district appears once per pair it belongs to, so SEs are two-way
clustered on the Rajasthan district and the neighbour district.
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "insurance"
OUT.mkdir(parents=True, exist_ok=True)

VARS = {
    "Households with any usual member covered under a health insurance/financing scheme (%)": "insur",
    "Average out-of-pocket expenditure per delivery in a public health facility (Rs)": "oop",
    "Institutional births (%)": "inst",
    "Institutional births in public facility (%)": "inst_public",
    # Placebos: should not respond to a health insurance scheme
    "Population living in households with electricity (%)": "electricity",
    "Women with 10 or more years of schooling (%)": "women_school10",
}
OUTCOMES = ["insur", "oop", "log_oop", "inst", "inst_public"]
PLACEBOS = ["electricity", "women_school10"]

# ---------------------------------------------------------------- district data
d = pd.read_csv(ROOT / "data" / "raw" / "nfhs_districts_641_kalla.csv", low_memory=False)
d = d[d["Indicator"].isin(VARS)].copy()
d["dt"] = pd.to_numeric(d["DT_CEN_CD"], errors="coerce")
d = d.dropna(subset=["dt"])
d["v"] = d["Indicator"].map(VARS)
for r, c in [("4", "NFHS 4"), ("5", "NFHS 5")]:
    d[r] = pd.to_numeric(d[c], errors="coerce").replace(0, np.nan)  # 0 = missing code
w = d.pivot_table(index=["ST_CEN_CD", "dt"], columns="v", values=["4", "5"], aggfunc="first")
w.columns = [f"{v}_{r}" for r, v in w.columns]
w = w.reset_index()
w["log_oop_4"], w["log_oop_5"] = np.log(w["oop_4"]), np.log(w["oop_5"])
for v in OUTCOMES + PLACEBOS:
    w[f"d_{v}"] = w[f"{v}_5"] - w[f"{v}_4"]

# ---------------------------------------------------------------- stacked pairs
pairs = pd.read_csv(ROOT / "data" / "clean" / "border_pairs.csv")
raj_side = pairs.merge(w, left_on=["raj_st", "raj_dt"], right_on=["ST_CEN_CD", "dt"]).assign(raj=1)
nb_side = pairs.merge(w, left_on=["nb_st", "nb_dt"], right_on=["ST_CEN_CD", "dt"]).assign(raj=0)
stack = pd.concat([raj_side, nb_side], ignore_index=True)
stack["g_raj"] = stack["raj_district"].astype("category").cat.codes
stack["g_nb"] = stack["nb_district"].astype("category").cat.codes


def pair_did(y, data):
    sub = data.dropna(subset=[f"d_{y}"])
    # keep pairs where both sides are observed
    sub = sub[sub.groupby("pair_id")["raj"].transform("nunique") == 2]
    m = smf.ols(f"d_{y} ~ raj + C(pair_id)", sub).fit(
        cov_type="cluster", cov_kwds={"groups": sub[["g_raj", "g_nb"]].to_numpy()})
    return m, sub


rows = []
samples = {
    "all borders": stack,
    "drop Gujarat (own scheme MA Yojana since 2012)": stack[stack.nb_state != "Gujarat"],
    "MP border only (no RSBY enrolment)": stack[stack.nb_state == "Madhya Pradesh"],
    "pairs sharing >= 10 km of border": stack[stack.shared_km >= 10],
}
for label, data in samples.items():
    for y in OUTCOMES + PLACEBOS:
        m, sub = pair_did(y, data)
        raj_pre = sub.loc[sub.raj == 1, f"{y}_4"].mean()
        rows.append(dict(sample=label, outcome=y, placebo=y in PLACEBOS, beta=m.params["raj"],
                         se=m.bse["raj"], p=m.pvalues["raj"], pairs=sub.pair_id.nunique(),
                         raj_mean_nfhs4=raj_pre))
res = pd.DataFrame(rows)
res.to_csv(OUT / "border_pair_did.csv", index=False)
print("BORDER-PAIR DiD (NFHS-4 -> NFHS-5), two-way clustered SEs")
print(res.round(3).to_string(index=False))

# ---------------------------------------------------------------- state event study
s3 = pd.read_csv(ROOT / "data" / "raw" / "nfhs4_states_ht.csv")
s3 = s3[s3["indicator"].str.contains("health scheme or health insurance", case=False)]
s3 = s3[["state", "total_2005-06", "total"]].rename(columns={"total_2005-06": "y2005", "total": "y2015_ht"})
s5 = pd.read_csv(ROOT / "data" / "raw" / "nfhs5_states_with_nfhs4.csv")
s5 = s5[s5["indicator"].str.contains("health insurance", case=False)]
s5 = s5[["state", "nfhs4_total", "nfhs5_total"]].rename(columns={"nfhs4_total": "y2015", "nfhs5_total": "y2020"})
st = s3.merge(s5, on="state")  # states with the same name in both files
for c in ["y2005", "y2015", "y2020"]:
    st[c] = pd.to_numeric(st[c], errors="coerce")
st = st.dropna(subset=["y2005", "y2015", "y2020"])
st = st[~st.state.isin(["India"])]
st["pre"] = st["y2015"] - st["y2005"]    # 2005-06 -> 2015-16
st["post"] = st["y2020"] - st["y2015"]   # 2015-16 -> 2019-21

NEIGH = ["Gujarat", "Madhya Pradesh", "Haryana", "Punjab", "Uttar Pradesh"]
raj = st[st.state == "Rajasthan"].iloc[0]
lines = ["", "STATE EVENT STUDY: insurance coverage (%)",
         st[st.state.isin(["Rajasthan"] + NEIGH)][["state", "y2005", "y2015", "y2020", "pre", "post"]].to_string(index=False)]
for label, ctrl in [("neighbours", st[st.state.isin(NEIGH)]), ("all other states", st[st.state != "Rajasthan"])]:
    phi2 = raj["pre"] - ctrl["pre"].mean()     # pre-trend DiD (Karan et al. 2017 notation)
    phi3 = raj["post"] - ctrl["post"].mean()   # post DiD
    lines.append(f"vs {label} (n={len(ctrl)}): pre-trend DiD phi2 = {phi2:+.1f} pp, "
                 f"post DiD phi3 = {phi3:+.1f} pp, trend-adjusted phi3 - phi2 = {phi3 - phi2:+.1f} pp")
# Permutation: each state as if treated, against all others
perm = {s: st.loc[st.state == s, "post"].iloc[0] - st.loc[st.state != s, "post"].mean() for s in st.state}
perm = pd.Series(perm).sort_values(ascending=False)
lines.append(f"Permutation: Rajasthan post-DiD ranks {list(perm.index).index('Rajasthan') + 1} of {len(perm)}; "
             f"p = {(perm.abs() >= abs(perm['Rajasthan'])).mean():.3f}")
text = "\n".join(lines)
print(text)
(OUT / "state_event_study.txt").write_text(text + "\n")

fig, ax = plt.subplots(figsize=(6, 4))
yrs = [2005.5, 2015.8, 2020.2]
for _, r in st[st.state.isin(NEIGH)].iterrows():
    ax.plot(yrs, r[["y2005", "y2015", "y2020"]], color="#9aa7b8", marker="o", ms=3, lw=1)
    ax.text(2020.4, r["y2020"], r["state"], fontsize=7, va="center", color="#555")
ax.plot(yrs, raj[["y2005", "y2015", "y2020"]], color="#c0504d", marker="o", lw=2.2)
ax.text(2020.4, raj["y2020"], "Rajasthan", fontsize=8, va="center", color="#c0504d", weight="bold")
ax.axvline(2015.95, color="black", ls="--", lw=0.8)
ax.text(2016.1, 92, "BSBY launch\n(Dec 2015)", fontsize=7, va="top")
ax.set_xticks(yrs, ["NFHS-3\n2005-06", "NFHS-4\n2015-16", "NFHS-5\n2019-21"])
ax.set_xlim(2004.5, 2023.5)
ax.set_ylabel("Households with any member insured (%)")
ax.set_title("Health insurance coverage: Rajasthan vs neighbouring states")
fig.tight_layout()
fig.savefig(OUT / "fig_state_event_study.png", dpi=200)
