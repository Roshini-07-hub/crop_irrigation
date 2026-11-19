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

CROP_DISPLAY_NAMES = {
    "Mirchi": "Mirchi (Chilli / Red Chilli)",
    "Paddy": "Paddy (Rice)",
    "Gram (Chana)": "Gram / Chana (Chickpea)",
    "Arhar/Tur": "Arhar / Tur (Red Gram)",
    "Moong (Green Gram)": "Moong (Green Gram)",
    "Urad": "Urad (Black Gram)",
    "Mustard": "Mustard / Sarson (Rai)",
    "Cotton": "Cotton (Kapas)",
    "Groundnut": "Groundnut / Peanut (Mungfali)",
    "Wheat": "Wheat (Gehun)",
    "Maize": "Maize / Corn (Makka)",
    "Jowar": "Jowar (Sorghum)",
    "Bajra": "Bajra (Pearl Millet)",
    "Ragi": "Ragi (Finger Millet)",
    "Sugarcane": "Sugarcane (Ganna)",
    "Khesari": "Khesari (Grass Pea / Lathyrus)",
    "Cowpea(Lobia)": "Cowpea / Lobia",
    "Horse-gram": "Horse Gram (Kulthi)",
    "Sesamum": "Sesamum / Til (Sesame)",
    "Soyabean": "Soyabean (Soybean)",
    "Sunflower": "Sunflower (Surajmukhi)",
    "Linseed": "Linseed / Flaxseed (Alsi)",
    "Castor seed": "Castor Seed (Arandi)",
    "Onion": "Onion (Pyaz)",
    "Potato": "Potato (Aloo)",
    "Garlic": "Garlic (Lahsun)",
    "Ginger": "Ginger (Adrak)",
    "Turmeric": "Turmeric (Haldi)",
    "Coriander": "Coriander (Dhaniya)",
    "Black pepper": "Black Pepper (Kali Mirch)",
    "Cardamom": "Cardamom (Elaichi)",
    "Cashewnut": "Cashewnut (Kaju)",
    "Coconut": "Coconut (Nariyal)",
    "Arecanut": "Arecanut (Supari)",
    "Barley": "Barley (Jau)",
    "Moth": "Moth Bean (Matki)",
    "Guar seed": "Guar Seed (Gavar)",
    "Masoor": "Masoor (Red Lentil)",
    "Sweet potato": "Sweet Potato (Shakarkand)",
    "Tapioca": "Tapioca / Cassava (Sabudana)",
    "Tobacco": "Tobacco (Tambaku)",
    "Jute": "Jute (Patson)",
    "Mesta": "Mesta (Roselle)",
    "Sannhamp": "Sunn Hemp (Sanai)",
    "Safflower": "Safflower (Kusum / Kardi)",
    "Niger seed": "Niger Seed (Ramtil)",
    "Small millets": "Small Millets (Kodo / Kutki)",
    "Other Oilseeds": "Other Oilseeds",
    "Oilseeds total": "Total Oilseeds",
    "Other Cereals": "Other Cereals",
    "Other Kharif pulses": "Other Kharif Pulses",
    "Other Rabi pulses": "Other Rabi Pulses",
    "Other Summer Pulses": "Other Summer Pulses",
    "Peas & beans (Pulses)": "Peas & Beans (Matar)",
    "Banana": "Banana (Kela)"
}

CROP_SEARCH_KEYWORDS = {
    "Mirchi": ["mirchi", "red chillies", "dry chillies", "chilli", "chillies", "pepper", "lal mirch"],
    "Paddy": ["paddy", "rice", "rice paddy", "dhan"],
    "Gram (Chana)": ["gram", "chana", "chickpea", "bengal gram"],
    "Mustard": ["mustard", "sarson", "rai", "rapeseed", "rapeseed &mustard"],
    "Cotton": ["cotton", "kapas", "cotton(lint)"],
    "Wheat": ["wheat", "gehun"],
    "Arhar/Tur": ["arhar", "tur", "red gram", "toor dal", "pigeon pea"],
    "Moong (Green Gram)": ["moong", "green gram", "mung"],
    "Urad": ["urad", "black gram", "urad dal"],
    "Groundnut": ["groundnut", "peanut", "mungfali"],
    "Jowar": ["jowar", "sorghum", "jowari"],
    "Bajra": ["bajra", "pearl millet", "kambu"],
    "Ragi": ["ragi", "finger millet", "nachni"],
    "Maize": ["maize", "corn", "makka"],
    "Sugarcane": ["sugarcane", "ganna"],
    "Soyabean": ["soyabean", "soybean", "soya"],
    "Sunflower": ["sunflower", "surajmukhi"],
    "Onion": ["onion", "pyaz"],
    "Potato": ["potato", "aloo"],
    "Garlic": ["garlic", "lahsun"],
    "Ginger": ["ginger", "adrak"],
    "Turmeric": ["turmeric", "haldi"],
    "Coriander": ["coriander", "dhaniya"],
    "Khesari": ["khesari", "grass pea", "lathyrus"],
    "Cowpea(Lobia)": ["cowpea", "lobia", "chawli"],
    "Horse-gram": ["horse gram", "kulthi"],
    "Sesamum": ["sesamum", "sesame", "til"],
    "Linseed": ["linseed", "flaxseed", "alsi"],
    "Castor seed": ["castor", "arandi"]
}


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

            display_name = CROP_DISPLAY_NAMES.get(crop_name, crop_name)
            aliases = CROP_SEARCH_KEYWORDS.get(crop_name, [crop_name.lower()])

            crops_list.append({
                "crop": crop_name,
                "display_name": display_name,
                "aliases": aliases,
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

        # Sort alphabetically by crop
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
