import os
from pathlib import Path

import requests
from dotenv import load_dotenv


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"

load_dotenv(ENV_FILE)


WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")


# ============================================================
# WEATHER SERVICE
# ============================================================

def get_weather(latitude, longitude):

    if not WEATHER_API_KEY:
        raise ValueError(
            "WEATHER_API_KEY is not configured."
        )

    url = "https://api.openweathermap.org/data/2.5/weather"

    params = {
        "lat": latitude,
        "lon": longitude,
        "appid": WEATHER_API_KEY,
        "units": "metric"
    }

    response = requests.get(
        url,
        params=params,
        timeout=10
    )

    response.raise_for_status()

    data = response.json()

    return {
        "temperature_c": data["main"]["temp"],

        "humidity": data["main"]["humidity"],

        "rainfall_mm": data.get(
            "rain",
            {}
        ).get("1h", 0),

        "wind_speed_kmh": round(
            data["wind"]["speed"] * 3.6,
            2
        ),

        "description":
            data["weather"][0]["description"],

        "latitude": latitude,

        "longitude": longitude
    }