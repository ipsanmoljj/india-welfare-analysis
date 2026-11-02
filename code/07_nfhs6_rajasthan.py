"""Extract NFHS-6 (2023-24, provisional) district fact sheets from the official IIPS
state compendiums (PDFs in data/raw/), for Rajasthan and its five neighbours.

Each district sheet starts with a header "<District>, <State> - Key Indicators" and
reports NFHS-6 next to NFHS-5. The state sheet ("<State> - Key Indicators") reports
urban / rural / total NFHS-6 and total NFHS-5. Values in ( ) are based on 25-49
unweighted cases (flagged); * means suppressed (<25 cases).

Outputs (validated by 00_clean_and_checks.py before any analysis uses them):
  data/interim/nfhs6_official_extracted.csv   long: state, district, var, nfhs6, nfhs5, flags
  data/interim/nfhs6_rajasthan_extracted.csv  wide Rajasthan table (as before)
"""
import re
import subprocess
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "interim"
OUT.mkdir(parents=True, exist_ok=True)

STATES = ["Rajasthan", "Gujarat", "Haryana", "Madhya Pradesh", "Punjab", "Uttar Pradesh"]
INDICATORS = {
    "4": ("Population living in households with electricity (%)", "electricity"),
    "7": ("Households with any usual member covered under a health insurance/financing scheme (%)", "insur"),
    "12": ("Women with 10 or more years of schooling (%)", "women_school10"),
    "35": ("Institutional births (%)", "inst"),
    "36": ("Institutional births in public facility (%)", "inst_public"),
}


def parse_value(tok):
    """Return (value, small_sample, suppressed) for a fact-sheet token."""
    if tok in ("*", "na", "NA", "-"):
        return None, False, tok == "*"
    small = tok.startswith("(") and tok.endswith(")")
    return float(tok.strip("()")), small, False


rows = []
for state in STATES:
    pdf = next(RAW.glob(f"NFHS-6_StateFact_{state}__*.pdf"))
    text = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True,
                          check=True).stdout
    current = None
    for line in text.splitlines():
        m = re.match(rf"^\s*(.+?),\s*{re.escape(state)}\s*-\s*Key Indicators\s*$", line)
        if m:
            current = m.group(1).strip()
            continue
        if re.match(rf"^\s*{re.escape(state)}\s*-\s*Key Indicators\s*$", line):
            current = "__STATE__"
            continue
        for num, (label, var) in INDICATORS.items():
            if current and re.match(rf"^\s*{num}\.\s+{re.escape(label)}", line):
                toks = line[line.index(label) + len(label):].split()
                v6, s6, x6 = parse_value(toks[-2])
                v5, s5, x5 = parse_value(toks[-1])
                rows.append(dict(state=state, district=current, var=var, nfhs6=v6, nfhs5=v5,
                                 small6=s6, small5=s5, suppressed6=x6, suppressed5=x5, source=pdf.name))
    n_d = len({r["district"] for r in rows if r["state"] == state and r["district"] != "__STATE__"})
    print(f"{state:15s} {n_d} districts")

df = pd.DataFrame(rows).drop_duplicates(["state", "district", "var"])
df.to_csv(OUT / "nfhs6_official_extracted.csv", index=False)

# Wide Rajasthan table, same layout as before (used by the Rajasthan checks and persistence)
r = df[(df.state == "Rajasthan") & (df.district != "__STATE__")]
wide = r.pivot(index="district", columns="var", values=["nfhs6", "nfhs5"])
wide.columns = [f"{v}_{'6' if c == 'nfhs6' else '5'}" for c, v in wide.columns]
toc_order = r.drop_duplicates("district")["district"].tolist()
wide = wide.reindex(toc_order).reset_index()
wide[["district", "insur_6", "insur_5", "inst_6", "inst_5", "inst_public_6", "inst_public_5",
      "electricity_6", "electricity_5"]].to_csv(OUT / "nfhs6_rajasthan_extracted.csv", index=False)
print(f"wrote {len(df)} rows")
