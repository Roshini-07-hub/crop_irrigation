"""
Crops Information Blueprint

Returns metadata for the 55 supported crops from crop_water_parameters.csv,
including crop groups, Kc parameters across growth stages, and water need guidelines.
"""

from flask import Blueprint, jsonify
from pathlib import Path
import pandas as pd

crops_bp = Blueprint("crops", __name__, url_prefix="/api/crops")

BASE_DIR = Path(__file__).resolve().parents[1]
CROPS_FILE = BASE_DIR / "datasets" / "processed" / "crop_water_parameters.csv"


@crops_bp.route("/", methods=["GET"])
def get_crops():
    """Return all 55 crops and their parameters grouped by category."""
    try:
        if not CROPS_FILE.exists():
            return jsonify({
                "success": False,
                "error": "Crop parameters dataset not found."
            }), 404

        df = pd.read_csv(CROPS_FILE)
        df = df.fillna("")

        crops_list = []
        groups_set = set()

        for _, row in df.iterrows():
            crop_name = str(row["Crop"]).strip()
            crop_group = str(row["Crop_Group"]).strip()
            groups_set.add(crop_group)

            min_need = row["Water_Need_Min_mm"]
            max_need = row["Water_Need_Max_mm"]

            crops_list.append({
                "crop": crop_name,
                "crop_group": crop_group,
                "kc_initial": float(row["Kc_Initial"]) if row["Kc_Initial"] != "" else None,
                "kc_development": float(row["Kc_Development"]) if row["Kc_Development"] != "" else None,
                "kc_mid": float(row["Kc_Mid"]) if row["Kc_Mid"] != "" else None,
                "kc_late": float(row["Kc_Late"]) if row["Kc_Late"] != "" else None,
                "water_need_min_mm": float(min_need) if min_need != "" else None,
                "water_need_max_mm": float(max_need) if max_need != "" else None,
                "reference_source": str(row["Reference_Source"]),
                "parameter_status": str(row["Parameter_Status"])
            })

        # Sort alphabetically
        crops_list.sort(key=lambda x: x["crop"])

        return jsonify({
            "success": True,
            "total_crops": len(crops_list),
            "groups": sorted(list(groups_set)),
            "crops": crops_list
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Failed to load crop parameters.",
            "details": str(e)
        }), 500
