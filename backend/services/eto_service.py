"""
FAO-56 Penman-Monteith reference evapotranspiration (ETo) service.

Weather source:
    Open-Meteo forecast API
    https://open-meteo.com/en/docs

The service deliberately calculates ETo locally from meteorological variables
returned by the API. It does NOT use a hard-coded ETo value.

Daily inputs used:
    - Tmax / Tmin at 2 m
    - mean relative humidity at 2 m
    - mean wind speed at 10 m
    - daily shortwave radiation
    - surface pressure
    - latitude / longitude
    - elevation

FAO-56 daily equation:
    ET0 = [0.408*Delta*(Rn-G) +
           gamma*(900/(T+273))*u2*(es-ea)] /
          [Delta + gamma*(1+0.34*u2)]

For a daily time step, G is taken as 0.
"""

from __future__ import annotations

import math
from datetime import date, datetime
from typing import Any, Dict, Optional

import requests


OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


def _require_number(name: str, value: Any) -> float:
    if value is None:
        raise ValueError(f"{name} is required.")
    try:
        result = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be numeric.")
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite.")
    return result


def saturation_vapour_pressure(temperature_c: float) -> float:
    """Saturation vapour pressure, kPa."""
    t = _require_number("temperature_c", temperature_c)
    return 0.6108 * math.exp((17.27 * t) / (t + 237.3))


def slope_vapour_pressure_curve(temperature_c: float) -> float:
    """Slope of saturation vapour pressure curve, kPa/°C."""
    t = _require_number("temperature_c", temperature_c)
    es = saturation_vapour_pressure(t)
    return 4098.0 * es / ((t + 237.3) ** 2)


def wind_speed_to_2m(wind_speed_10m_ms: float) -> float:
    """Convert wind speed at 10 m to the FAO standard 2 m height."""
    u10 = _require_number("wind_speed_10m_ms", wind_speed_10m_ms)
    if u10 < 0:
        raise ValueError("wind_speed_10m_ms cannot be negative.")

    # FAO-56 logarithmic wind profile conversion.
    u2 = u10 * 4.87 / math.log(67.8 * 10.0 - 5.42)
    # FAO recommends a minimum u2 of about 0.5 m/s for the PM calculation.
    return max(u2, 0.5)


def extraterrestrial_radiation(latitude_deg: float, day_of_year: int) -> float:
    """Daily extraterrestrial radiation Ra, MJ m-2 day-1."""
    lat = _require_number("latitude_deg", latitude_deg)
    if not -90 <= lat <= 90:
        raise ValueError("latitude_deg must be between -90 and 90.")

    j = int(day_of_year)
    if not 1 <= j <= 366:
        raise ValueError("day_of_year must be between 1 and 366.")

    phi = math.radians(lat)
    dr = 1.0 + 0.033 * math.cos((2.0 * math.pi / 365.0) * j)
    delta = 0.409 * math.sin((2.0 * math.pi / 365.0) * j - 1.39)

    acos_arg = -math.tan(phi) * math.tan(delta)
    acos_arg = max(-1.0, min(1.0, acos_arg))
    omega_s = math.acos(acos_arg)

    gsc = 0.0820  # MJ m-2 min-1
    return (
        (24.0 * 60.0 / math.pi)
        * gsc
        * dr
        * (
            omega_s * math.sin(phi) * math.sin(delta)
            + math.cos(phi) * math.cos(delta) * math.sin(omega_s)
        )
    )


def net_radiation(
    *,
    tmax_c: float,
    tmin_c: float,
    relative_humidity_mean_pct: float,
    shortwave_radiation_mj_m2_day: float,
    latitude_deg: float,
    day_of_year: int,
    elevation_m: float,
) -> Dict[str, float]:
    """
    Calculate FAO-56 net radiation Rn from daily shortwave radiation.

    Returns Rns, Rnl, Rn, Ra and Rso.
    """
    tmax = _require_number("tmax_c", tmax_c)
    tmin = _require_number("tmin_c", tmin_c)
    rh = _require_number(
        "relative_humidity_mean_pct", relative_humidity_mean_pct
    )
    rs = _require_number(
        "shortwave_radiation_mj_m2_day", shortwave_radiation_mj_m2_day
    )
    elevation = _require_number("elevation_m", elevation_m)

    if tmax < tmin:
        raise ValueError("tmax_c cannot be lower than tmin_c.")
    if not 0 <= rh <= 100:
        raise ValueError("relative_humidity_mean_pct must be 0..100.")
    if rs < 0:
        raise ValueError("shortwave_radiation_mj_m2_day cannot be negative.")
    if elevation < -500:
        raise ValueError("elevation_m is outside the supported range.")

    ra = extraterrestrial_radiation(latitude_deg, day_of_year)
    rso = (0.75 + (2e-5 * elevation)) * ra

    # FAO-56 shortwave albedo for the reference grass surface.
    albedo = 0.23
    rns = (1.0 - albedo) * rs

    # Mean RH is used when max/min RH or dew point are unavailable.
    ea = (rh / 100.0) * (
        saturation_vapour_pressure(tmax)
        + saturation_vapour_pressure(tmin)
    ) / 2.0

    sigma = 4.903e-9  # MJ K-4 m-2 day-1
    tmax_k = tmax + 273.16
    tmin_k = tmin + 273.16

    if rso <= 0:
        raise ValueError("Calculated clear-sky radiation Rso is not positive.")

    rs_rso = min(max(rs / rso, 0.0), 1.0)

    rnl = (
        sigma
        * ((tmax_k**4 + tmin_k**4) / 2.0)
        * (0.34 - 0.14 * math.sqrt(max(ea, 0.0)))
        * (1.35 * rs_rso - 0.35)
    )

    rn = rns - rnl

    return {
        "ra_mj_m2_day": ra,
        "rso_mj_m2_day": rso,
        "rns_mj_m2_day": rns,
        "rnl_mj_m2_day": rnl,
        "rn_mj_m2_day": rn,
        "actual_vapour_pressure_kpa": ea,
    }


def calculate_fao56_eto(
    *,
    tmax_c: float,
    tmin_c: float,
    relative_humidity_mean_pct: float,
    wind_speed_10m_ms: float,
    shortwave_radiation_mj_m2_day: float,
    surface_pressure_kpa: float,
    latitude_deg: float,
    day_of_year: int,
    elevation_m: float,
) -> Dict[str, float]:
    """Calculate daily reference ETo using FAO-56 Penman-Monteith."""
    tmax = _require_number("tmax_c", tmax_c)
    tmin = _require_number("tmin_c", tmin_c)
    rh = _require_number(
        "relative_humidity_mean_pct", relative_humidity_mean_pct
    )
    pressure = _require_number("surface_pressure_kpa", surface_pressure_kpa)

    if tmax < tmin:
        raise ValueError("tmax_c cannot be lower than tmin_c.")
    if not 0 <= rh <= 100:
        raise ValueError("relative_humidity_mean_pct must be 0..100.")
    if pressure <= 0:
        raise ValueError("surface_pressure_kpa must be positive.")

    tmean = (tmax + tmin) / 2.0
    es = (
        saturation_vapour_pressure(tmax)
        + saturation_vapour_pressure(tmin)
    ) / 2.0

    radiation = net_radiation(
        tmax_c=tmax,
        tmin_c=tmin,
        relative_humidity_mean_pct=rh,
        shortwave_radiation_mj_m2_day=shortwave_radiation_mj_m2_day,
        latitude_deg=latitude_deg,
        day_of_year=day_of_year,
        elevation_m=elevation_m,
    )

    ea = radiation["actual_vapour_pressure_kpa"]
    delta = slope_vapour_pressure_curve(tmean)

    # Psychrometric constant, kPa/°C.
    gamma = 0.000665 * pressure

    u2 = wind_speed_to_2m(wind_speed_10m_ms)

    # FAO-56 daily soil heat flux approximation: G ≈ 0.
    g = 0.0
    rn = radiation["rn_mj_m2_day"]

    numerator = (
        0.408 * delta * (rn - g)
        + gamma
        * (900.0 / (tmean + 273.0))
        * u2
        * (es - ea)
    )
    denominator = delta + gamma * (1.0 + 0.34 * u2)

    if denominator <= 0:
        raise ValueError("Invalid FAO-56 denominator.")

    eto = numerator / denominator

    # Physical guard: negative daily reference ET is not useful for irrigation.
    eto = max(0.0, eto)

    return {
        "eto_mm_day": round(eto, 4),
        "tmean_c": round(tmean, 4),
        "tmax_c": round(tmax, 4),
        "tmin_c": round(tmin, 4),
        "relative_humidity_mean_pct": round(rh, 4),
        "wind_speed_10m_ms": round(
            _require_number("wind_speed_10m_ms", wind_speed_10m_ms), 4
        ),
        "wind_speed_2m_ms": round(u2, 4),
        "surface_pressure_kpa": round(pressure, 4),
        "shortwave_radiation_mj_m2_day": round(
            _require_number(
                "shortwave_radiation_mj_m2_day",
                shortwave_radiation_mj_m2_day,
            ),
            4,
        ),
        "actual_vapour_pressure_kpa": round(ea, 4),
        "saturation_vapour_pressure_kpa": round(es, 4),
        "delta_kpa_per_c": round(delta, 6),
        "psychrometric_constant_kpa_per_c": round(gamma, 6),
        "net_radiation_mj_m2_day": round(rn, 4),
        "method": "FAO-56 Penman-Monteith",
    }


def fetch_open_meteo_daily(
    latitude: float,
    longitude: float,
    target_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Fetch one day's meteorological data from Open-Meteo.

    If target_date is omitted, today's local date is used by Open-Meteo.
    """
    lat = _require_number("latitude", latitude)
    lon = _require_number("longitude", longitude)

    if not -90 <= lat <= 90:
        raise ValueError("latitude must be between -90 and 90.")
    if not -180 <= lon <= 180:
        raise ValueError("longitude must be between -180 and 180.")

    if target_date is None:
        target_date = date.today().isoformat()

    # Open-Meteo provides the variables required to reproduce the daily
    # FAO-56 calculation and also provides its own FAO-56 ET0 for comparison.
    daily_variables = ",".join(
        [
            "temperature_2m_max",
            "temperature_2m_min",
            "relative_humidity_2m_mean",
            "wind_speed_10m_mean",
            "shortwave_radiation_sum",
            "surface_pressure_mean",
            "precipitation_sum",
            "et0_fao_evapotranspiration",
        ]
    )

    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": target_date,
        "end_date": target_date,
        "daily": daily_variables,
        "timezone": "auto",
        "wind_speed_unit": "ms",
        "precipitation_unit": "mm",
    }

    response = requests.get(OPEN_METEO_URL, params=params, timeout=20)
    response.raise_for_status()
    payload = response.json()

    daily = payload.get("daily")
    if not daily or not daily.get("time"):
        raise ValueError("Open-Meteo returned no daily weather data.")

    def first(name: str) -> Any:
        values = daily.get(name)
        if not values or values[0] is None:
            raise ValueError(
                f"Open-Meteo did not return required variable: {name}"
            )
        return values[0]

    return {
        "latitude": payload["latitude"],
        "longitude": payload["longitude"],
        "elevation_m": payload.get("elevation"),
        "timezone": payload.get("timezone"),
        "date": daily["time"][0],
        "tmax_c": first("temperature_2m_max"),
        "tmin_c": first("temperature_2m_min"),
        "relative_humidity_mean_pct": first(
            "relative_humidity_2m_mean"
        ),
        "wind_speed_10m_ms": first("wind_speed_10m_mean"),
        "shortwave_radiation_mj_m2_day": first(
            "shortwave_radiation_sum"
        ),
        "surface_pressure_hpa": first("surface_pressure_mean"),
        "precipitation_mm": first("precipitation_sum"),
        # Open-Meteo's own FAO-56 value is retained only for validation.
        "open_meteo_eto_mm_day": first("et0_fao_evapotranspiration"),
    }


def get_eto(
    latitude: float,
    longitude: float,
    target_date: Optional[str] = None,
) -> Dict[str, Any]:
    """Fetch real weather data and calculate FAO-56 ETo locally."""
    weather = fetch_open_meteo_daily(latitude, longitude, target_date)

    day_of_year = datetime.strptime(
        weather["date"], "%Y-%m-%d"
    ).timetuple().tm_yday

    surface_pressure_kpa = (
        float(weather["surface_pressure_hpa"]) / 10.0
    )

    result = calculate_fao56_eto(
        tmax_c=weather["tmax_c"],
        tmin_c=weather["tmin_c"],
        relative_humidity_mean_pct=weather[
            "relative_humidity_mean_pct"
        ],
        wind_speed_10m_ms=weather["wind_speed_10m_ms"],
        shortwave_radiation_mj_m2_day=weather[
            "shortwave_radiation_mj_m2_day"
        ],
        surface_pressure_kpa=surface_pressure_kpa,
        latitude_deg=weather["latitude"],
        day_of_year=day_of_year,
        elevation_m=weather["elevation_m"],
    )

    provider_eto = float(weather["open_meteo_eto_mm_day"])
    local_eto = float(result["eto_mm_day"])

    result.update(
        {
            "date": weather["date"],
            "latitude": weather["latitude"],
            "longitude": weather["longitude"],
            "elevation_m": weather["elevation_m"],
            "timezone": weather["timezone"],
            "precipitation_mm": weather["precipitation_mm"],
            "open_meteo_eto_mm_day": round(provider_eto, 4),
            "eto_difference_mm_day": round(local_eto - provider_eto, 4),
            "weather_source": "Open-Meteo",
        }
    )

    return result


if __name__ == "__main__":
    # Example location only. The ETo is fetched/calculated from live weather;
    # no ETo value is hard-coded.
    print(get_eto(17.3850, 78.4867))
