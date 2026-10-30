"""Build the list of contiguous district pairs across the Rajasthan state border.

Uses the Census 2011 district map (datameet/maps). These are the same 641
districts as NFHS-4, so pairs join to NFHS on census state + district codes.
Two districts are a pair if their boundaries are within 500 m (absorbs tiny
digitisation gaps along the shared border).

Output: data/clean/border_pairs.csv  (one row per Rajasthan-neighbour pair)
Requires: geopandas (only this script; the analysis reads the CSV)
"""
import urllib.request
from pathlib import Path

import geopandas as gpd

ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT / "data" / "raw" / "map"
MAP.mkdir(parents=True, exist_ok=True)
BASE = "https://raw.githubusercontent.com/datameet/maps/master/Districts/Census_2011/2011_Dist"
for ext in ["shp", "shx", "dbf", "prj"]:
    f = MAP / f"2011_Dist.{ext}"
    if not f.exists():
        urllib.request.urlretrieve(f"{BASE}.{ext}", f)

g = gpd.read_file(MAP / "2011_Dist.shp").to_crs(32643)  # UTM 43N, metres
raj, other = g[g.ST_NM == "Rajasthan"].copy(), g[g.ST_NM != "Rajasthan"]
raj["geometry"] = raj.buffer(500)
pairs = gpd.sjoin(raj, other, predicate="intersects")[
    ["DISTRICT_left", "ST_CEN_CD_left", "DT_CEN_CD_left",
     "DISTRICT_right", "ST_NM_right", "ST_CEN_CD_right", "DT_CEN_CD_right"]
]
pairs.columns = ["raj_district", "raj_st", "raj_dt", "nb_district", "nb_state", "nb_st", "nb_dt"]
# Length of shared border (km): flags corner-only touches
geom = g.set_index(["ST_CEN_CD", "DT_CEN_CD"]).geometry
pairs["shared_km"] = [
    geom[(r.raj_st, r.raj_dt)].buffer(500).intersection(geom[(r.nb_st, r.nb_dt)].boundary).length / 1000
    for r in pairs.itertuples()
]
pairs = pairs.sort_values(["nb_state", "raj_district"]).reset_index(drop=True)
pairs["pair_id"] = range(1, len(pairs) + 1)
pairs.to_csv(ROOT / "data" / "clean" / "border_pairs.csv", index=False)
print(f"{len(pairs)} pairs: {pairs.raj_district.nunique()} Rajasthan districts, "
      f"{pairs.nb_district.nunique()} neighbour districts")
print(pairs.groupby("nb_state").size().to_string())

# Map of the border sample
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

g4 = g.to_crs(4326)
raj_codes = set(zip(pairs.raj_st, pairs.raj_dt))
nb_codes = set(zip(pairs.nb_st, pairs.nb_dt))
code = list(zip(g4.ST_CEN_CD, g4.DT_CEN_CD))
g4["role"] = ["Rajasthan border (treated)" if c in raj_codes else "Neighbour border (control)" if c in nb_codes
              else "Rajasthan interior (excluded)" if s == "Rajasthan" else "other"
              for c, s in zip(code, g4.ST_NM)]
colors = {"Rajasthan border (treated)": "#c0504d", "Neighbour border (control)": "#1f4e79",
          "Rajasthan interior (excluded)": "#f2dcdb", "other": "#f2f2f2"}
fig, ax = plt.subplots(figsize=(6.5, 6.5))
view = g4.cx[68:80.5, 20.5:31.5]
for role, c in colors.items():
    part = view[view.role == role]
    if len(part):
        part.plot(ax=ax, color=c, edgecolor="white", linewidth=0.4, label=role)
view[view.ST_NM == "Rajasthan"].dissolve().boundary.plot(ax=ax, color="black", linewidth=0.9)
for _, r in view[view.role != "other"].iterrows():
    p = r.geometry.representative_point()
    ax.text(p.x, p.y, r.DISTRICT, fontsize=5, ha="center", color="white" if "border" in r.role else "#555")
handles = [plt.Rectangle((0, 0), 1, 1, color=colors[k]) for k in list(colors)[:3]]
ax.legend(handles, list(colors)[:3], loc="lower left", fontsize=7, frameon=False)
ax.set_axis_off()
ax.set_title(f"Border sample: {len(raj_codes)} Rajasthan and {len(nb_codes)} neighbour districts (2011 boundaries)", fontsize=9)
fig.tight_layout()
(ROOT / "output" / "insurance").mkdir(parents=True, exist_ok=True)
fig.savefig(ROOT / "output" / "insurance" / "fig_border_map.png", dpi=220)
