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
nb_st = st[st.state.isin(NEIGH)].sort_values("y2020")
label_y = []
for _, r in nb_st.iterrows():
    ax.plot(yrs, r[["y2005", "y2015", "y2020"]], color="#9aa7b8", marker="o", ms=3, lw=1)
    y = r["y2020"] if not label_y else max(r["y2020"], label_y[-1] + 4.5)  # keep labels apart
    label_y.append(y)
    ax.text(2020.4, y, f"{r['state']} ({r['y2020']:.0f}%)", fontsize=7, va="center", color="#555")
ax.plot(yrs, raj[["y2005", "y2015", "y2020"]], color="#c0504d", marker="o", lw=2.2)
ax.text(2020.4, raj["y2020"], f"Rajasthan ({raj['y2020']:.0f}%)", fontsize=8, va="center", color="#c0504d", weight="bold")
ax.axvline(2015.95, color="black", ls="--", lw=0.8)
ax.text(2016.1, 92, "BSBY launch\n(Dec 2015)", fontsize=7, va="top")
ax.set_xticks(yrs, ["NFHS-3\n2005-06", "NFHS-4\n2015-16", "NFHS-5\n2019-21"])
ax.set_xlim(2004.5, 2025.5)
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

# ---------------------------------------------------------------- figure: coefficient plot
LABELS = {"insur": "Insurance coverage", "oop_real": "OOP per delivery (real Rs)", "log_oop": "log OOP per delivery",
          "inst": "Institutional births", "inst_public": "Public-facility births",
          "electricity": "Placebo: electricity", "women_school10": "Placebo: women 10+ yrs school"}
fig, (a1, a2) = plt.subplots(1, 2, figsize=(9, 3.8), gridspec_kw={"width_ratios": [1, 1.25]})
# Panel A: insurance coverage (pp) across specifications
spec = [("All borders", res.query("sample == 'all borders' and outcome == 'insur'")),
        ("Drop Gujarat", res.query("sample.str.startswith('drop Gujarat') and outcome == 'insur'")),
        ("MP border only", res.query("sample.str.startswith('MP') and outcome == 'insur'")),
        ("Pairs >= 10 km", res.query("sample.str.startswith('pairs') and outcome == 'insur'"))]
ys = list(range(len(spec) + 1))[::-1]
r0 = main.set_index("outcome").loc["insur"]
pts = [(lab, d.beta.iloc[0], d.se.iloc[0]) for lab, d in spec] + \
      [("Control NFHS-4 level", r0.beta_base_ctrl, r0.se_base_ctrl)]
for y, (lab, bta, se) in zip(ys, pts):
    a1.errorbar(bta, y, xerr=1.96 * se, fmt="o", color="#c0504d", capsize=3, ms=5)
    a1.text(bta + 1.96 * se + 1.5, y, f"{bta:.1f}", va="center", fontsize=7)
a1.set_yticks(ys, [p[0] for p in pts], fontsize=8)
a1.axvline(0, color="black", lw=0.8)
a1.set_xlim(-5, 80)
a1.set_xlabel("Effect on coverage (percentage points)")
a1.set_title("A. Insurance coverage: robustness", fontsize=9)
# Panel B: all outcomes in SD units (NFHS-4 neighbour-border SD)
order = ["oop_real", "log_oop", "inst", "inst_public", "electricity", "women_school10"]
ys = list(range(len(order)))[::-1]
for y, o in zip(ys, order):
    r = main.set_index("outcome").loc[o]
    col = "#9aa7b8" if r.placebo else "#1f4e79"
    a2.errorbar(r.beta_std, y, xerr=1.96 * r.se_std, fmt="o", color=col, capsize=3, ms=5)
a2.set_yticks(ys, [LABELS[o] for o in order], fontsize=8)
a2.axvline(0, color="black", lw=0.8)
a2.set_xlabel("Effect in SD units (95% CI)")
a2.set_title(f"B. Other outcomes (insurance = {r0.beta_std:.1f} SD, off scale)", fontsize=9)
fig.suptitle("Border-pair DiD, NFHS-4 to NFHS-5 (40 pairs, two-way clustered SEs)", fontsize=10)
fig.tight_layout()
fig.savefig(OUT / "fig_coefficients.png", dpi=200)

# ---------------------------------------------------------------- NFHS-6 extension (border sample)
# Cleaned NFHS-6 values for all border districts (00_clean_and_checks.py, section 4b).
# 5->6 changes use the NFHS-5 value printed in the NFHS-6 compendium (same source both
# rounds); 4->6 insurance changes exclude the 3 Gujarat districts whose NFHS-5 insurance
# the compendium revises (documented exception).
n6b_all = pd.read_csv(ROOT / "data" / "clean" / "nfhs6_border_districts.csv")
N6V = ["insur", "inst", "inst_public", "electricity", "women_school10"]
s6 = stack.drop(columns=[c for c in stack.columns if c.endswith("_6") or c.endswith("_n6")], errors="ignore") \
    .merge(n6b_all.drop(columns=["State", "District"]), on=["ST_CEN_CD", "dt"], how="left")
for v in N6V:
    s6[f"d_{v}_56"] = s6[f"{v}_6"] - s6[f"{v}_5_n6"]
    s6[f"d_{v}_46"] = s6[f"{v}_6"] - s6[f"{v}_4"]
s6.loc[s6["gujarat_insur_exception"].fillna(False).astype(bool), "d_insur_46"] = np.nan
rows6 = []
for label, data in {"all borders": s6, "drop Gujarat": s6[s6.nb_state != "Gujarat"]}.items():
    for v in N6V:
        for span, lab in [("56", "NFHS-5 -> NFHS-6 (2019-21 -> 2023-24)"), ("46", "NFHS-4 -> NFHS-6 (long difference)")]:
            m, sub = pair_did(f"{v}_{span}", data)
            b, se, pv = est(m)
            rows6.append(dict(sample=label, outcome=v, placebo=v in PLACEBOS, change=lab, beta=b, se=se, p=pv,
                              pairs=sub.pair_id.nunique()))
res6 = pd.DataFrame(rows6)
res6.to_csv(OUT / "border_pair_did_nfhs6.csv", index=False)
print("\nNFHS-6 EXTENSION (border-pair DiD, two-way clustered SEs)")
print(res6.round(3).to_string(index=False))

# ---------------------------------------------------------------- figure: coverage over three rounds (district means)
main_pairs = set(pair_did("insur", stack)[1].pair_id)
nb_d = stack[(stack.raj == 0) & stack.pair_id.isin(main_pairs)].drop_duplicates("nb_district")
raj_d = stack[stack.raj == 1].drop_duplicates("raj_district")
n6b = n6[n6.border]
nb6 = n6b_all.merge(nb_d[["ST_CEN_CD", "dt"]], on=["ST_CEN_CD", "dt"])
raj_y = [raj_d.insur_4.mean(), raj_d.insur_5.mean(), n6b.insur_6.mean()]
nb_y = [nb_d.insur_4.mean(), nb_d.insur_5.mean(), nb6.insur_6.mean()]
fig, ax = plt.subplots(figsize=(6, 4))
ax.plot([0, 1, 2], raj_y, color="#c0504d", marker="o", lw=2.2, label=f"Rajasthan border districts ({len(raj_d)})")
ax.plot([0, 1, 2], nb_y, color="#1f4e79", marker="o", lw=2.2,
        label=f"Neighbour border districts ({nb_d.insur_4.notna().sum()})")
for x, y in zip([0, 1, 2], raj_y):
    ax.text(x, y + 3, f"{y:.1f}", ha="center", fontsize=8, color="#c0504d")
for x, y in zip([0, 1, 2], nb_y):
    ax.text(x, y - 6, f"{y:.1f}", ha="center", fontsize=8, color="#1f4e79")
ax.set_xticks([0, 1, 2], ["NFHS-4\n2015-16", "NFHS-5\n2019-21", "NFHS-6\n2023-24 (prov.)"])
ax.set_ylim(0, 100)
ax.set_ylabel("Households with any member insured (%)")
ax.set_title("Coverage in border districts over three rounds")
ax.legend(frameon=False, fontsize=8, loc="center left")
fig.text(0.01, 0.01, "NFHS-6 is provisional (official IIPS state compendiums). For 3 Gujarat districts the "
         "NFHS-6 compendium revises NFHS-5 insurance up ~5 pp.", fontsize=5.5, color="#555")
fig.tight_layout(rect=(0, 0.03, 1, 1))
fig.savefig(OUT / "fig_coverage_three_rounds.png", dpi=200)
