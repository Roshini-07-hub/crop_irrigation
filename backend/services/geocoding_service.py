import requests

GEOCODING_API_URL = "https://geocoding-api.open-meteo.com/v1/search"


def search_location(query, count=5):
    """
    Search for locations using Open-Meteo Geocoding API.

    Returns location name, state, country, latitude,
    longitude, elevation and timezone.
    """

    if not query or not query.strip():
        raise ValueError("Location search query is required.")

    params = {
        "name": query.strip(),
        "count": count,
        "language": "en",
        "format": "json"
    }

    response = requests.get(
        GEOCODING_API_URL,
        params=params,
        timeout=10
    )

    response.raise_for_status()

    data = response.json()

    results = []

    for location in data.get("results", []):
        results.append({
            "name": location.get("name"),
            "state": location.get("admin1"),
            "country": location.get("country"),
            "country_code": location.get("country_code"),
            "latitude": location.get("latitude"),
            "longitude": location.get("longitude"),
            "elevation_m": location.get("elevation"),
            "timezone": location.get("timezone")
        })

    return results