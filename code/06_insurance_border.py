"""Bhamashah Swasthya Bima Yojana (BSBY, Rajasthan, launched 13 Dec 2015):
contiguous border-pair DiD (Dube, Lester & Reich 2010) with NFHS-4 -> NFHS-5,
plus a three-round state event study (NFHS-3 -> NFHS-4 -> NFHS-5).

Treatment: Rajasthan's state scheme (BSBY, merged with Ayushman Bharat in 2019
as AB-MGRSBY). Controls: districts across the border, which had RSBY and then
PM-JAY. So beta = effect of Rajasthan's scheme RELATIVE TO the national schemes.

Baseline caveat: Rajasthan's NFHS-4 fieldwork (23 Jan - 21 Jul 2016) started
six weeks after BSBY launched. Early enrolment raises the "pre" level, which
biases beta toward zero, so the estimates are lower bounds.

Reads the cleaned data from code/00_clean_and_checks.py.

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

# Refuse to run on data that has not passed every check in 00_clean_and_checks.py
status = (ROOT / "output" / "checks" / "audit_status.txt")
assert status.exists() and status.read_text().strip() == "PASS", \
    "Run code/00_clean_and_checks.py first; the data audit must PASS before any analysis."

# Cleaned data from code/00_clean_and_checks.py: OOP in real 2019-21 rupees,
# 0 -> missing, 1.5*IQR-capped OOP versions, z-scores (NFHS-4 neighbour reference)
w = pd.read_csv(ROOT / "data" / "clean" / "insurance_district_clean.csv")
OUTCOMES = ["insur", "oop_real", "log_oop", "inst", "inst_public"]
PLACEBOS = ["electricity", "women_school10"]
CAPPED = {"oop_real": "oop_cap", "log_oop": "log_oop_cap"}
ZVAR = {"insur": "insur_z", "oop_real": "oop_cap_z", "log_oop": "log_oop_z", "inst": "inst_z",
        "inst_public": "inst_public_z", "electricity": "electricity_z", "women_school10": "women_school10_z"}
for v in set(OUTCOMES + PLACEBOS + list(CAPPED.values()) + list(ZVAR.values())):
    w[f"d_{v}"] = w[f"{v}_5"] - w[f"{v}_4"]

# ---------------------------------------------------------------- stacked pairs
pairs = pd.read_csv(ROOT / "data" / "clean" / "border_pairs.csv")
raj_side = pairs.merge(w, left_on=["raj_st", "raj_dt"], right_on=["ST_CEN_CD", "dt"]).assign(raj=1)
nb_side = pairs.merge(w, left_on=["nb_st", "nb_dt"], right_on=["ST_CEN_CD", "dt"]).assign(raj=0)
stack = pd.concat([raj_side, nb_side], ignore_index=True)
stack["g_raj"] = stack["raj_district"].astype("category").cat.codes
stack["g_nb"] = stack["nb_district"].astype("category").cat.codes


def pair_did(y, data, base=None):
    """Within-pair DiD; base = column of the NFHS-4 level to control for."""
    sub = data.dropna(subset=[f"d_{y}"] + ([base] if base else []))
    sub = sub[sub.groupby("pair_id")["raj"].transform("nunique") == 2]  # both sides observed
    f = f"d_{y} ~ raj + C(pair_id)" + (f" + {base}" if base else "")
    m = smf.ols(f, sub).fit(cov_type="cluster", cov_kwds={"groups": sub[["g_raj", "g_nb"]].to_numpy()})
    return m, sub


def est(m):
    return m.params["raj"], m.bse["raj"], m.pvalues["raj"]


# ---------------------------------------------------------------- main table
rows = []
for y in OUTCOMES + PLACEBOS:
    m, sub = pair_did(y, stack)
    b, se, p = est(m)
    row = dict(outcome=y, placebo=y in PLACEBOS, pairs=sub.pair_id.nunique(),
               raj_mean_nfhs4=sub.loc[sub.raj == 1, f"{y}_4"].mean(), beta=b, se=se, p=p)
    # (2) drop small-sample (25-49 case) values where flags are recoverable
    flag = f"{y.replace('_real', '').replace('log_', '')}_4_small"
    if flag in stack:
        keep = ~(stack[flag] | stack[flag.replace("_4_", "_5_")])
        n_drop = int((~keep).sum())
        row["beta_no_small"] = est(pair_did(y, stack[keep])[0])[0] if n_drop else b
        row["n_small_dropped"] = n_drop
    # (3) 1.5*IQR-capped OOP
    if y in CAPPED:
        cb, cse, cp = est(pair_did(CAPPED[y], stack)[0])
        row.update(beta_capped=cb, se_capped=cse, p_capped=cp)
    # (4) standardised: effect in SDs of the NFHS-4 neighbour distribution
    zb, zse, zp = est(pair_did(ZVAR[y], stack)[0])
    row.update(beta_std=zb, se_std=zse)
    # (5) control for the NFHS-4 level (response to baseline imbalance / mean reversion)
    ab, ase, ap = est(pair_did(y, stack, base=f"{y}_4")[0])
    row.update(beta_base_ctrl=ab, se_base_ctrl=ase, p_base_ctrl=ap)
    # (6) leave-one-out: each pair, and each Rajasthan district with all its pairs
    loo_pair = [est(pair_did(y, stack[stack.pair_id != i])[0])[0] for i in sub.pair_id.unique()]
    loo_raj = [est(pair_did(y, stack[stack.raj_district != d])[0]) for d in sub.raj_district.unique()]
    row.update(loo_pair_min=min(loo_pair), loo_pair_max=max(loo_pair),
               loo_raj_min=min(x[0] for x in loo_raj), loo_raj_max=max(x[0] for x in loo_raj),
               loo_raj_max_p=max(x[2] for x in loo_raj),
               loo_raj_most_influential=sub.raj_district.unique()[
                   int(np.argmax([abs(x[0] - b) for x in loo_raj]))])
    rows.append(row)
main = pd.DataFrame(rows)
main.to_csv(OUT / "border_pair_did_main.csv", index=False)
print("BORDER-PAIR DiD (cleaned data), two-way clustered SEs")
print(main.round(3).T.to_string())

# ---------------------------------------------------------------- sample robustness
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
        b, se, p = est(m)
        rows.append(dict(sample=label, outcome=y, placebo=y in PLACEBOS, beta=b, se=se, p=p,
                         pairs=sub.pair_id.nunique(), raj_mean_nfhs4=sub.loc[sub.raj == 1, f"{y}_4"].mean()))
res = pd.DataFrame(rows)
res.to_csv(OUT / "border_pair_did.csv", index=False)
print("\nSAMPLE ROBUSTNESS")
print(res.round(3).to_string(index=False))

# Power for OOP: 95% CI and minimum detectable effect (80% power, 5% two-sided)
pw = []
for y in ["oop_real", "log_oop"]:
    r = main.set_index("outcome").loc[y]
    pw.append(f"{y}: beta {r.beta:,.3f}, 95% CI [{r.beta - 1.96 * r.se:,.3f}, {r.beta + 1.96 * r.se:,.3f}], "
              f"MDE {2.8 * r.se:,.3f}, Rajasthan NFHS-4 mean {r.raj_mean_nfhs4:,.3f}")
(OUT / "oop_power.txt").write_text("\n".join(pw) + "\n")
print("\nOOP POWER\n" + "\n".join(pw))

# ---------------------------------------------------------------- state event study
# Cleaned state panel (names harmonised, boundary-changed states dropped)
st = pd.read_csv(ROOT / "data" / "clean" / "state_insurance_clean.csv")
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

# ---------------------------------------------------------------- NFHS-6 persistence (descriptive)
n6 = pd.read_csv(ROOT / "data" / "clean" / "nfhs6_rajasthan_districts.csv")
MAP_NAMES = {"Chittorgarh": "Chittaurgarh", "Dholpur": "Dhaulpur", "Jalore": "Jalor", "Jhunjhunu": "Jhunjhunun"}
n6["border"] = n6["district"].replace(MAP_NAMES).isin(set(pairs.raj_district))
for r in ["5", "6"]:
    n6[f"private_{r}"] = n6[f"inst_{r}"] - n6[f"inst_public_{r}"]
summ = n6.groupby("border")[[f"{v}_{r}" for v in ["insur", "inst_public", "private"] for r in ["5", "6"]]].mean()
summ.index = summ.index.map({True: f"border ({int(n6.border.sum())})", False: f"interior ({int((~n6.border).sum())})"})
txt = "NFHS-5 (2019-21) -> NFHS-6 (2023-24), Rajasthan district means\n" + summ.round(1).T.to_string()
print("\n" + txt)
(OUT / "nfhs6_persistence.txt").write_text(txt + "\n")
