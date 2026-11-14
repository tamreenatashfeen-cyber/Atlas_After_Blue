# LOCAL_HISTORY_EXPORT_V1
# Generates the Kandia shared-scale History export from three local aligned GeoTIFFs.
# No satellite downloads. No modification of existing flood-analysis outputs.

from pathlib import Path
from datetime import date, datetime, timezone
import hashlib
import json
import zipfile

import numpy as np
import rasterio
from rasterio.features import geometry_mask
from shapely.geometry import shape, mapping
from shapely.ops import transform as shapely_transform
from pyproj import Transformer
from PIL import Image

JULY2 = Path("D:/NSAC/aligned_pre_event_pre=2july.tif")
JULY14 = Path("C:/Users/user/Downloads/New folder (3)/aligned_pre_event.tif")
JULY26 = Path("C:/Users/user/Downloads/New folder (3)/aligned_post_event.tif")
AOI_PATH = Path("C:/Users/user/Downloads/New folder (3)/aoi.geojson")
EXPORT_DIR = Path("D:/NSAC/kandia_history_export")
ZIP_PATH = Path("D:/NSAC/kandia_history_export.zip")

EVENT_DATE = date(2026, 7, 22)
REF_EPSG = 32643
REF_SHAPE = (1001, 1001)
REF_TRANSFORM_TUPLE = (10.0, 0.0, 305460.0, 0.0, -10.0, 3944740.0)
REF_TRANSFORM = rasterio.Affine(*REF_TRANSFORM_TUPLE)

SCENES = {
    "2026-07-02": {
        "granule": "NISAR_L2_PR_GCOV_024_084_A_019_4005_DHDH_A_20260702T002239_20260702T002313_P05023_N_F_J_001",
        "cmr": "https://cmr.earthdata.nasa.gov/search/concepts/G4247635178-ASF.umm_json",
        "role": "earlier_observation",
        "caption": "Earlier reference, 2 July 2026 (20 days before event).",
    },
    "2026-07-14": {
        "granule": "NISAR_L2_PR_GCOV_025_084_A_019_4005_DHDH_A_20260714T002238_20260714T002313_P05023_F_F_J_001",
        "cmr": "https://cmr.earthdata.nasa.gov/search/concepts/G4253183866-ASF.umm_json",
        "role": "nearer_before",
        "caption": "Nearer-before reference, 14 July 2026 (8 days before event).",
    },
    "2026-07-26": {
        "granule": "NISAR_L2_PR_GCOV_026_084_A_019_4005_DHDH_A_20260726T002237_20260726T002312_P05023_N_F_J_001",
        "cmr": "https://cmr.earthdata.nasa.gov/search/concepts/G4263512466-ASF.umm_json",
        "role": "after_event",
        "caption": "Post-event observation, 26 July 2026 (4 days after event).",
    },
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_and_validate_linear_hhhh(path: Path, expected_date: str):
    if not path.exists():
        raise FileNotFoundError(f"Missing required raster: {path}")
    with rasterio.open(path) as ds:
        assert ds.count == 1, f"{path.name}: expected one band"
        assert ds.crs is not None and ds.crs.to_epsg() == REF_EPSG, f"{path.name}: CRS must be EPSG:32643"
        assert ds.shape == REF_SHAPE, f"{path.name}: shape must be 1001x1001"
        assert tuple(ds.transform)[:6] == REF_TRANSFORM_TUPLE, f"{path.name}: grid does not match the event reference grid"
        assert ds.dtypes[0] in ("float32", "float64"), f"{path.name}: expected floating-point linear power"
        tags = ds.tags()
        arr = ds.read(1).astype(np.float32)
        nodata = ds.nodata

    required_tags = {
        "MEASUREMENT_TERM": "HHHH",
        "SCALE_REPRESENTATION": "linear_power_gamma0",
        "UNITS": "1",
        "FREQUENCY_GROUP": "frequencyA",
        "TRACK_NUMBER": "84",
        "FRAME_NUMBER": "19",
        "ORBIT_DIRECTION": "Ascending",
        "SYNTHETIC_TEST_FIXTURE": "False",
    }
    for key, expected in required_tags.items():
        actual = str(tags.get(key, ""))
        assert actual == expected, f"{path.name}: tag {key}={actual!r}, expected {expected!r}"

    acq = str(tags.get("ZERO_DOPPLER_START", ""))
    assert acq.startswith(expected_date), f"{path.name}: acquisition date {acq!r} does not match {expected_date}"

    valid = np.isfinite(arr) & (arr > 0.0)
    if nodata is not None and np.isfinite(nodata):
        valid &= arr != np.float32(nodata)

    db = np.full(arr.shape, np.nan, dtype=np.float32)
    db[valid] = 10.0 * np.log10(arr[valid])
    return {
        "path": path,
        "arr": arr,
        "db": db,
        "valid": valid,
        "tags": tags,
        "acquisition_utc": acq[:19] + "Z",
        "sha256": sha256_file(path),
    }


records = []
for expected_date, raster_path in [
    ("2026-07-02", JULY2),
    ("2026-07-14", JULY14),
    ("2026-07-26", JULY26),
]:
    rec = read_and_validate_linear_hhhh(raster_path, expected_date)
    rec["date"] = expected_date
    records.append(rec)
    print(f"[PASS] {expected_date}: {raster_path.name} | HHHH linear gamma0 | exact reference grid | sha256={rec['sha256'][:12]}...")

aoi_geojson = json.loads(AOI_PATH.read_text(encoding="utf-8"))
feature = aoi_geojson["features"][0] if aoi_geojson.get("type") == "FeatureCollection" else aoi_geojson
geom_wgs84 = shape(feature["geometry"])
to_utm = Transformer.from_crs("EPSG:4326", "EPSG:32643", always_xy=True)
geom_utm = shapely_transform(to_utm.transform, geom_wgs84)
rows, cols = REF_SHAPE
aoi_mask = ~geometry_mask([mapping(geom_utm)], out_shape=(rows, cols), transform=REF_TRANSFORM, invert=False)
aoi_pixel_count = int(np.count_nonzero(aoi_mask))
assert aoi_pixel_count > 0, "AOI mask is empty"
aoi_area_km2 = float(geom_utm.area / 1e6)
assert abs(aoi_area_km2 - 78.5319) < 1.0, f"Unexpected AOI area: {aoi_area_km2} km2"
print(f"[PASS] AOI mask: {aoi_pixel_count} pixels | area={aoi_area_km2:.4f} km2")

for rec in records:
    rec["valid_export"] = aoi_mask & rec["valid"]
    rec["valid_pixels"] = int(np.count_nonzero(rec["valid_export"]))

common_valid_mask = aoi_mask & records[0]["valid"] & records[1]["valid"] & records[2]["valid"]
common_valid_count = int(np.count_nonzero(common_valid_mask))
if common_valid_count == 0:
    raise RuntimeError("No common-valid pixels across all three dates inside the AOI.")

pooled_db = np.concatenate([rec["db"][common_valid_mask] for rec in records])
vmin_db = round(float(np.percentile(pooled_db, 2)), 4)
vmax_db = round(float(np.percentile(pooled_db, 98)), 4)
assert vmax_db > vmin_db, "Shared display range is degenerate"
print(f"[PASS] Shared scale: [{vmin_db:.4f}, {vmax_db:.4f}] dB | common-valid pixels={common_valid_count}")

EXPORT_DIR.mkdir(parents=True, exist_ok=True)


def save_shared_scale_png(rec: dict, out_path: Path):
    db = rec["db"]
    valid = rec["valid_export"]
    rgba = np.zeros((rows, cols, 4), dtype=np.uint8)
    gray = np.zeros((rows, cols), dtype=np.uint8)
    gray[valid] = np.round(np.clip((db[valid] - vmin_db) / (vmax_db - vmin_db), 0.0, 1.0) * 255.0).astype(np.uint8)
    rgba[valid, 0] = gray[valid]
    rgba[valid, 1] = gray[valid]
    rgba[valid, 2] = gray[valid]
    rgba[valid, 3] = 255
    Image.fromarray(rgba, mode="RGBA").save(out_path, format="PNG")


image_records = []
for rec in records:
    d = rec["date"]
    scene = SCENES[d]
    png_name = f"history_{d}.png"
    png_path = EXPORT_DIR / png_name
    save_shared_scale_png(rec, png_path)
    image_records.append({
        "src": png_name,
        "role": scene["role"],
        "caption": scene["caption"],
        "acquisition_utc": rec["acquisition_utc"],
        "days_from_event": (date.fromisoformat(d) - EVENT_DATE).days,
        "source_granule_id": scene["granule"],
        "collection": "NISAR_L2_GCOV_PROVISIONAL_V1",
        "collection_concept_id": "C2854338529-ASF",
        "maturity": "Provisional (CRID P05023)",
        "cmr_metadata": scene["cmr"],
        "source_raster": rec["path"].name,
        "source_raster_sha256": rec["sha256"],
        "valid_pixels": rec["valid_pixels"],
        "aoi_pixels": aoi_pixel_count,
        "valid_fraction": round(rec["valid_pixels"] / max(1, aoi_pixel_count), 4),
        "provenance_tags_checked": [
            "ZERO_DOPPLER_START", "MEASUREMENT_TERM", "SCALE_REPRESENTATION", "UNITS",
            "FREQUENCY_GROUP", "TRACK_NUMBER", "FRAME_NUMBER", "ORBIT_DIRECTION", "SYNTHETIC_TEST_FIXTURE",
        ],
    })
    print(f"[PASS] Rendered {png_name} | valid_pixels={rec['valid_pixels']}/{aoi_pixel_count}")

x_min, y_max = 305460.0, 3944740.0
x_max = x_min + cols * 10.0
y_min = y_max - rows * 10.0

history_manifest = {
    "site_id": "kandia_gol",
    "event_date": "2026-07-22",
    "purpose": "historical_context_only",
    "analysis_modified": False,
    "existing_analysis_outputs_modified": False,
    "no_satellite_download": True,
    "generated_utc": datetime.now(timezone.utc).isoformat(),
    "generated_by": "LOCAL_HISTORY_EXPORT_V1",
    "section_caption": (
        "Three NISAR radar observations of the same Kandia Gol study area, rendered with one shared brightness scale. "
        "Earlier images show features that predate the reported 22 July event. "
        "This history provides visual context, not confirmation of floodwater, damage or unchanged conditions."
    ),
    "aoi": {
        "place": "Kandia Gol study circle, Upper Kohistan, Pakistan",
        "center_longitude": 72.9081,
        "center_latitude": 35.5832,
        "coordinate_order": "longitude, latitude",
        "radius_m": 5000,
        "aoi_area_km2": round(aoi_area_km2, 4),
        "bbox_wgs84_lonlat": list(geom_wgs84.bounds),
        "aoi_polygon_source": "aoi.geojson (64-segment metric circle buffered in EPSG:32643)",
        "aoi_geojson_sha256": sha256_file(AOI_PATH),
    },
    "grid": {
        "crs": "EPSG:32643",
        "dimensions": {"width": cols, "height": rows},
        "pixel_spacing_m": {"x_step_m": 10.0, "y_step_m": -10.0},
        "affine_transform_gdal_order": [x_min, 10.0, 0.0, y_max, 0.0, -10.0],
        "affine_transform_rasterio_order": [10.0, 0.0, x_min, 0.0, -10.0, y_max],
        "upper_left_corner_epsg32643": {"easting_m": x_min, "northing_m": y_max},
        "bounds_epsg32643": {
            "order": "[west_min_x, south_min_y, east_max_x, north_max_y]",
            "values_m": [x_min, y_min, x_max, y_max],
        },
        "orientation": "north_up",
    },
    "measurement": {
        "instrument": "NISAR L-SAR",
        "product_type": "L2_GCOV",
        "track": 84,
        "frame": 19,
        "orbit_direction": "Ascending",
        "frequency": "frequencyA",
        "term": "HHHH",
        "source_units": "1",
        "source_scale_representation": "linear_power_gamma0",
        "conversion_applied": "10 * log10(linear_power_gamma0) -> dB, applied once to positive valid pixels",
    },
    "rendering": {
        "shared_scale": True,
        "vmin_db": vmin_db,
        "vmax_db": vmax_db,
        "colormap": "grayscale (vmin_db -> 0 black, vmax_db -> 255 white)",
        "percentile_method": "2nd_to_98th_percentile_pooled_across_three_date_common_valid_aoi_pixels",
        "invalid_pixel_convention": "transparent_rgba (R=0, G=0, B=0, A=0 for masked/no-data/outside-AOI pixels)",
    },
    "common_valid_pixels": common_valid_count,
    "images": image_records,
}

history_json_path = EXPORT_DIR / "history.json"
history_json_path.write_text(json.dumps(history_manifest, indent=2), encoding="utf-8")

script_path = Path(__file__).resolve()
(EXPORT_DIR / "export_kandia_history.py").write_text(script_path.read_text(encoding="utf-8"), encoding="utf-8")

frontend_note = """ADD OBSERVATION HISTORY BELOW THE REPORT MAP

Use the three enclosed PNGs in chronological order:
1. history_2026-07-02.png
2. history_2026-07-14.png
3. history_2026-07-26.png

Show three cards on desktop and stack them on mobile. Preserve each full image. Do not crop or stretch it.

CAPTIONS
history_2026-07-02.png
2 July 2026 | Earlier reference
20 days before the reported 22 July flood.

history_2026-07-14.png
14 July 2026 | Before the event
8 days before the reported flood.

history_2026-07-26.png
26 July 2026 | After the event
4 days after the reported flood, not a view of its peak.

TEXT TO SHOW BELOW THE GALLERY
"Three NISAR radar observations of the same Kandia Gol study area, rendered with one shared brightness scale. Earlier images show features that predate the reported 22 July event. This history provides visual context, not confirmation of floodwater, damage or unchanged conditions."

LEAVE EVERYTHING ELSE UNCHANGED
Keep the existing map, layers, before/after viewer, analysis, figures and confidence label. This gallery does not replace any source images already used elsewhere on the site.
"""
(EXPORT_DIR / "TO_FRONTEND.txt").write_text(frontend_note, encoding="utf-8")

expected_files = [
    "history_2026-07-02.png",
    "history_2026-07-14.png",
    "history_2026-07-26.png",
    "history.json",
    "export_kandia_history.py",
    "TO_FRONTEND.txt",
]
for rec in image_records:
    p_img = EXPORT_DIR / rec["src"]
    with Image.open(p_img) as im:
        assert im.size == (cols, rows) and im.mode == "RGBA", f"Invalid PNG size/mode: {p_img.name}"
        arr_rgba = np.asarray(im)
        assert int(np.count_nonzero(arr_rgba[:, :, 3] == 255)) == rec["valid_pixels"], f"Alpha mask mismatch: {p_img.name}"
        assert np.all(arr_rgba[arr_rgba[:, :, 3] == 0] == 0), f"Transparent pixels must be RGBA zero: {p_img.name}"
json.loads(history_json_path.read_text(encoding="utf-8"))

with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
    for name in expected_files:
        zf.write(EXPORT_DIR / name, arcname=name)
with zipfile.ZipFile(ZIP_PATH) as zf:
    assert zf.testzip() is None, "ZIP integrity check failed"
    assert sorted(zf.namelist()) == sorted(expected_files), "ZIP contains unexpected entries"
    for name in expected_files:
        assert zf.read(name) == (EXPORT_DIR / name).read_bytes(), f"ZIP content mismatch: {name}"

print("\n=== KANDIA HISTORY EXPORT READY ===")
print(f"Shared dB scale: [{vmin_db:.4f}, {vmax_db:.4f}]")
print(f"Common-valid pixels: {common_valid_count}")
for rec in image_records:
    print(f"  {rec['src']} | {rec['valid_pixels']} valid pixels | {rec['caption']}")
print(f"ZIP: {ZIP_PATH}")
print(f"ZIP size: {ZIP_PATH.stat().st_size / 1e6:.2f} MB")
print("Existing flood-analysis outputs were not modified.")