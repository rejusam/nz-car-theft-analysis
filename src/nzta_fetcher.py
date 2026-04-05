"""
NZTA Motor Vehicle Register data fetcher and processor.

Downloads the full MVR dataset (5M+ rows) from NZTA Waka Kotahi's
open data portal and aggregates fleet counts by make, model, and
territorial authority (region).

Data source: CC-BY 4.0 licensed, updated monthly.
https://www.nzta.govt.nz/resources/new-zealand-motor-vehicle-register-statistics/
"""

import argparse
import io
import os
import sys
import zipfile
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

BASE_URL = "https://wksprdgisopendata.blob.core.windows.net/motorvehicleregister"
ALL_YEARS_ZIP = f"{BASE_URL}/Fleet-data-all-vehicle-years.zip"
YEAR_CSV_TEMPLATE = f"{BASE_URL}/VehicleYear-{{year}}.csv"

# Territorial authority → region mapping
# Based on Local Government (Auckland Council) Act 2009 and regional
# council boundaries
TLA_TO_REGION = {
    "AUCKLAND": "Auckland",
    "AUCKLAND COUNCIL": "Auckland",
    # Canterbury
    "CHRISTCHURCH CITY": "Canterbury",
    "SELWYN DISTRICT": "Canterbury",
    "WAIMAKARIRI DISTRICT": "Canterbury",
    "HURUNUI DISTRICT": "Canterbury",
    "ASHBURTON DISTRICT": "Canterbury",
    "TIMARU DISTRICT": "Canterbury",
    "MACKENZIE DISTRICT": "Canterbury",
    "WAIMATE DISTRICT": "Canterbury",
    "KAIKOURA DISTRICT": "Canterbury",
    # Waikato
    "HAMILTON CITY": "Waikato",
    "HAURAKI DISTRICT": "Waikato",
    "MATAMATA-PIAKO DISTRICT": "Waikato",
    "OTOROHANGA DISTRICT": "Waikato",
    "SOUTH WAIKATO DISTRICT": "Waikato",
    "WAIKATO DISTRICT": "Waikato",
    "WAIPA DISTRICT": "Waikato",
    "WAITOMO DISTRICT": "Waikato",
    "THAMES-COROMANDEL DISTRICT": "Waikato",
    # Wellington
    "WELLINGTON CITY": "Wellington",
    "HUTT CITY": "Wellington",
    "LOWER HUTT CITY": "Wellington",
    "UPPER HUTT CITY": "Wellington",
    "PORIRUA CITY": "Wellington",
    "KAPITI COAST DISTRICT": "Wellington",
    "CARTERTON DISTRICT": "Wellington",
    "MASTERTON DISTRICT": "Wellington",
    "SOUTH WAIRARAPA DISTRICT": "Wellington",
    # Bay of Plenty
    "TAURANGA CITY": "Bay of Plenty",
    "WESTERN BAY OF PLENTY DISTRICT": "Bay of Plenty",
    "WHAKATANE DISTRICT": "Bay of Plenty",
    "KAWERAU DISTRICT": "Bay of Plenty",
    "OPOTIKI DISTRICT": "Bay of Plenty",
    "ROTORUA DISTRICT": "Bay of Plenty",
    # Northland
    "FAR NORTH DISTRICT": "Northland",
    "WHANGAREI DISTRICT": "Northland",
    "KAIPARA DISTRICT": "Northland",
    # Hawke's Bay
    "NAPIER CITY": "Hawke's Bay",
    "HASTINGS DISTRICT": "Hawke's Bay",
    "CENTRAL HAWKE'S BAY DISTRICT": "Hawke's Bay",
    "WAIROA DISTRICT": "Hawke's Bay",
    # Taranaki
    "NEW PLYMOUTH DISTRICT": "Taranaki",
    "STRATFORD DISTRICT": "Taranaki",
    "SOUTH TARANAKI DISTRICT": "Taranaki",
    # Manawatu-Whanganui
    "PALMERSTON NORTH CITY": "Manawatu-Whanganui",
    "MANAWATU DISTRICT": "Manawatu-Whanganui",
    "HOROWHENUA DISTRICT": "Manawatu-Whanganui",
    "TARARUA DISTRICT": "Manawatu-Whanganui",
    "RANGITIKEI DISTRICT": "Manawatu-Whanganui",
    "WHANGANUI DISTRICT": "Manawatu-Whanganui",
    "RUAPEHU DISTRICT": "Manawatu-Whanganui",
    # Otago
    "DUNEDIN CITY": "Otago",
    "QUEENSTOWN-LAKES DISTRICT": "Otago",
    "CENTRAL OTAGO DISTRICT": "Otago",
    "CLUTHA DISTRICT": "Otago",
    "WAITAKI DISTRICT": "Otago",
    # Southland
    "INVERCARGILL CITY": "Southland",
    "SOUTHLAND DISTRICT": "Southland",
    "GORE DISTRICT": "Southland",
    # Nelson/Tasman/Marlborough
    "NELSON CITY": "Nelson-Tasman",
    "TASMAN DISTRICT": "Nelson-Tasman",
    "MARLBOROUGH DISTRICT": "Nelson-Tasman",
    # West Coast
    "BULLER DISTRICT": "West Coast",
    "GREY DISTRICT": "West Coast",
    "WESTLAND DISTRICT": "West Coast",
    # Gisborne
    "GISBORNE DISTRICT": "Gisborne",
}

# Models of interest for theft analysis
TARGET_MODELS = {
    ("TOYOTA", "AQUA"),
    ("TOYOTA", "COROLLA"),
    ("TOYOTA", "HILUX"),
    ("TOYOTA", "VITZ"),
    ("TOYOTA", "WISH"),
    ("TOYOTA", "CALDINA"),
    ("TOYOTA", "RAV4"),
    ("TOYOTA", "MARK X"),
    ("NISSAN", "TIIDA"),
    ("NISSAN", "WINGROAD"),
    ("NISSAN", "X-TRAIL"),
    ("MAZDA", "DEMIO"),
    ("MAZDA", "ATENZA"),
    ("MAZDA", "BOUNTY"),
    ("MAZDA", "CX-5"),
    ("MAZDA", "AXELA"),
    ("MAZDA", "FAMILIA"),
    ("HONDA", "FIT"),
    ("HONDA", "CR-V"),
    ("HONDA", "CRV"),
    ("SUBARU", "LEGACY"),
    ("SUBARU", "IMPREZA"),
    ("FORD", "COURIER"),
    ("FORD", "RANGER"),
    ("SUZUKI", "SWIFT"),
    ("MITSUBISHI", "OUTLANDER"),
}


def download_year_csv(year: int) -> pd.DataFrame:
    """Download a single year's MVR CSV from NZTA."""
    import urllib.request

    url = YEAR_CSV_TEMPLATE.format(year=year)
    print(f"  Downloading {url} ...")
    response = urllib.request.urlopen(url)
    data = response.read()
    return pd.read_csv(io.BytesIO(data), low_memory=False)


def download_all_years() -> pd.DataFrame:
    """Download the full MVR zip and extract to a single DataFrame."""
    import urllib.request

    print(f"Downloading full MVR dataset from {ALL_YEARS_ZIP} ...")
    print("(This is ~500 MB and may take several minutes)")
    response = urllib.request.urlopen(ALL_YEARS_ZIP)
    data = response.read()

    frames = []
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        for name in sorted(zf.namelist()):
            if name.endswith(".csv"):
                print(f"  Extracting {name} ...")
                with zf.open(name) as f:
                    df = pd.read_csv(f, low_memory=False)
                    frames.append(df)

    return pd.concat(frames, ignore_index=True)


def detect_columns(df: pd.DataFrame) -> dict:
    """
    Detect column names in the MVR dataset.

    The NZTA CSV schema has varied slightly across releases, so we
    match columns by pattern rather than assuming exact names.
    """
    cols = {c.upper(): c for c in df.columns}
    mapping = {}

    for candidate in ["MAKE", "VEHICLE_MAKE"]:
        if candidate in cols:
            mapping["make"] = cols[candidate]
            break

    for candidate in ["MODEL", "VEHICLE_MODEL"]:
        if candidate in cols:
            mapping["model"] = cols[candidate]
            break

    for candidate in ["VEHICLE_YEAR", "VEHICLEYEAR", "YEAR_OF_MANUFACTURE"]:
        if candidate in cols:
            mapping["vehicle_year"] = cols[candidate]
            break

    for candidate in ["TLA", "TERRITORIAL_AUTHORITY",
                       "TERRITORIAL_LOCAL_AUTHORITY", "CCLA"]:
        if candidate in cols:
            mapping["tla"] = cols[candidate]
            break

    for candidate in ["MOTIVE_POWER", "FUEL_TYPE", "MOTIVEPOWER"]:
        if candidate in cols:
            mapping["motive_power"] = cols[candidate]
            break

    return mapping


def map_tla_to_region(tla_value: str) -> str:
    """Map a territorial authority string to its region."""
    if pd.isna(tla_value):
        return "Unknown"
    key = str(tla_value).strip().upper()
    return TLA_TO_REGION.get(key, "Other")


def process_mvr(df: pd.DataFrame) -> pd.DataFrame:
    """
    Process raw MVR data into fleet counts by model and region.

    Filters to target models, maps TLA to region, and aggregates.
    """
    col_map = detect_columns(df)
    print(f"Detected columns: {col_map}")

    if "make" not in col_map or "model" not in col_map:
        raise ValueError(
            f"Could not find MAKE/MODEL columns in: {list(df.columns)}"
        )

    make_col = col_map["make"]
    model_col = col_map["model"]
    tla_col = col_map.get("tla")
    year_col = col_map.get("vehicle_year")

    # Normalise make/model to uppercase for matching
    df["_make"] = df[make_col].str.strip().str.upper()
    df["_model"] = df[model_col].str.strip().str.upper()

    # Filter to target models
    mask = df.apply(
        lambda r: (r["_make"], r["_model"]) in TARGET_MODELS, axis=1
    )
    filtered = df[mask].copy()
    print(f"Filtered to {len(filtered):,} rows "
          f"({len(filtered)/len(df)*100:.1f}% of total)")

    # Map TLA to region
    if tla_col:
        filtered["region"] = filtered[tla_col].apply(map_tla_to_region)
    else:
        filtered["region"] = "Unknown"

    # Standardise model names to match our analysis dataset
    model_name_map = {
        "CR-V": "CRV",
        "X-TRAIL": "X-Trail",
        "CX-5": "CX-5",
        "MARK X": "Mark X",
        "RAV4": "RAV4",
    }

    def format_model_name(make, model):
        display_model = model_name_map.get(model, model.title())
        return f"{make.title()} {display_model}"

    filtered["model_display"] = filtered.apply(
        lambda r: format_model_name(r["_make"], r["_model"]), axis=1
    )

    # National fleet counts
    national = (
        filtered.groupby(["_make", "_model", "model_display"])
        .size()
        .reset_index(name="fleet_national")
    )

    # Regional fleet counts
    regional = (
        filtered.groupby(["_make", "_model", "model_display", "region"])
        .size()
        .reset_index(name="fleet_count")
    )

    # Pivot to wide format (one column per region)
    regional_wide = regional.pivot_table(
        index=["_make", "_model", "model_display"],
        columns="region",
        values="fleet_count",
        fill_value=0,
    ).reset_index()

    # Merge national totals
    result = pd.merge(national, regional_wide, on=["_make", "_model", "model_display"])

    # Clean up column names
    result.rename(
        columns={"model_display": "model", "_make": "make_raw", "_model": "model_raw"},
        inplace=True,
    )
    result["make"] = result["make_raw"].str.title()

    # Reorder columns: model info first, then national, then regions
    region_cols = [c for c in result.columns
                   if c not in ("make_raw", "model_raw", "model", "make",
                                "fleet_national")]
    out_cols = ["model", "make", "fleet_national"] + sorted(region_cols)
    result = result[out_cols]
    result.sort_values("fleet_national", ascending=False, inplace=True)

    return result


def process_year_distribution(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute vehicle year distribution for target models.

    Useful for understanding the age profile — critical for the
    security vulnerability analysis (pre-2014 = no encrypted immobiliser).
    """
    col_map = detect_columns(df)
    make_col = col_map["make"]
    model_col = col_map["model"]
    year_col = col_map.get("vehicle_year")

    if not year_col:
        print("Warning: no VEHICLE_YEAR column found, skipping age analysis")
        return pd.DataFrame()

    df["_make"] = df[make_col].str.strip().str.upper()
    df["_model"] = df[model_col].str.strip().str.upper()

    mask = df.apply(
        lambda r: (r["_make"], r["_model"]) in TARGET_MODELS, axis=1
    )
    filtered = df[mask].copy()

    filtered["vehicle_year"] = pd.to_numeric(
        filtered[year_col], errors="coerce"
    )
    filtered = filtered.dropna(subset=["vehicle_year"])
    filtered["vehicle_year"] = filtered["vehicle_year"].astype(int)

    def format_model(make, model):
        return f"{make.title()} {model.title()}"

    filtered["model"] = filtered.apply(
        lambda r: format_model(r["_make"], r["_model"]), axis=1
    )

    # Aggregate by model and vehicle year
    dist = (
        filtered.groupby(["model", "vehicle_year"])
        .size()
        .reset_index(name="count")
    )

    return dist


def fetch_and_process(year_range=None, use_zip=False):
    """
    Main entry point: download MVR data and produce fleet summaries.

    Args:
        year_range: tuple of (start, end) years to download individually,
                    or None to download all
        use_zip: if True, download the single zip file instead of
                 individual year CSVs
    """
    if use_zip:
        raw = download_all_years()
    elif year_range:
        frames = []
        for year in range(year_range[0], year_range[1] + 1):
            try:
                df = download_year_csv(year)
                frames.append(df)
            except Exception as e:
                print(f"  Skipping {year}: {e}")
        raw = pd.concat(frames, ignore_index=True)
    else:
        # Default: download recent years only (lighter weight)
        frames = []
        for year in range(2005, 2027):
            try:
                df = download_year_csv(year)
                frames.append(df)
            except Exception as e:
                print(f"  Skipping {year}: {e}")
        raw = pd.concat(frames, ignore_index=True)

    print(f"\nTotal MVR rows loaded: {len(raw):,}")

    # Fleet by model and region
    fleet_regional = process_mvr(raw)
    out_path = DATA_DIR / "nzta_fleet_regional_summary.csv"
    fleet_regional.to_csv(out_path, index=False)
    print(f"\nFleet regional summary saved to {out_path}")
    print(fleet_regional.to_string(index=False))

    # Vehicle year distribution
    year_dist = process_year_distribution(raw)
    if not year_dist.empty:
        dist_path = DATA_DIR / "nzta_vehicle_year_distribution.csv"
        year_dist.to_csv(dist_path, index=False)
        print(f"\nYear distribution saved to {dist_path}")

    # Update the main fleet file with accurate national counts
    update_fleet_file(fleet_regional)

    return fleet_regional


def update_fleet_file(fleet_regional: pd.DataFrame):
    """
    Update nz_fleet_by_model.csv with accurate MVR-derived fleet counts.

    Preserves the existing metadata columns (age, security, etc.) but
    replaces fleet_registered with the authoritative MVR count.
    """
    existing_path = DATA_DIR / "nz_fleet_by_model.csv"
    if not existing_path.exists():
        return

    existing = pd.read_csv(existing_path)
    mvr_counts = fleet_regional[["model", "fleet_national"]].copy()
    mvr_counts.rename(columns={"fleet_national": "fleet_registered_mvr"}, inplace=True)

    merged = pd.merge(existing, mvr_counts, on="model", how="left")

    updated = 0
    for idx, row in merged.iterrows():
        if pd.notna(row.get("fleet_registered_mvr")):
            merged.at[idx, "fleet_registered"] = int(row["fleet_registered_mvr"])
            updated += 1

    merged.drop(columns=["fleet_registered_mvr"], inplace=True)
    merged.to_csv(existing_path, index=False)
    print(f"\nUpdated fleet counts for {updated} models in {existing_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Fetch and process NZTA Motor Vehicle Register data"
    )
    parser.add_argument(
        "--fetch-nzta", action="store_true",
        help="Download the full MVR dataset (5M+ rows, ~500 MB)"
    )
    parser.add_argument(
        "--years", type=str, default=None,
        help="Year range to download, e.g. '2010-2025'"
    )
    parser.add_argument(
        "--use-zip", action="store_true",
        help="Download the single zip file instead of individual year CSVs"
    )
    args = parser.parse_args()

    if not args.fetch_nzta:
        print("NZTA MVR Fetcher")
        print("=" * 50)
        print()
        print("This script downloads the full NZTA Motor Vehicle Register")
        print("dataset and computes fleet counts by model and region.")
        print()
        print("Usage:")
        print("  python nzta_fetcher.py --fetch-nzta              # all years")
        print("  python nzta_fetcher.py --fetch-nzta --use-zip    # single zip")
        print("  python nzta_fetcher.py --fetch-nzta --years 2010-2025")
        print()
        print("Data source: NZTA Waka Kotahi, CC-BY 4.0")
        print(f"URL: {ALL_YEARS_ZIP}")
        print()
        print("Currently using pre-computed fleet estimates from:")
        print(f"  {DATA_DIR / 'nzta_fleet_regional_summary.csv'}")
        return

    year_range = None
    if args.years:
        parts = args.years.split("-")
        year_range = (int(parts[0]), int(parts[1]))

    fetch_and_process(year_range=year_range, use_zip=args.use_zip)


if __name__ == "__main__":
    main()
