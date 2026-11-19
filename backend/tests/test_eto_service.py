import math
from backend.services.eto_service import (
    calculate_fao56_eto,
    saturation_vapour_pressure,
    slope_vapour_pressure_curve,
    wind_speed_to_2m,
)

def test_basic_physics():
    assert saturation_vapour_pressure(20) > 0
    assert slope_vapour_pressure_curve(20) > 0
    assert 0.5 <= wind_speed_to_2m(2.0) < 2.0

def test_fao56_returns_realistic_nonnegative_value():
    result = calculate_fao56_eto(
        tmax_c=32.0,
        tmin_c=22.0,
        relative_humidity_mean_pct=60.0,
        wind_speed_10m_ms=3.0,
        shortwave_radiation_mj_m2_day=20.0,
        surface_pressure_kpa=100.0,
        latitude_deg=17.385,
        day_of_year=260,
        elevation_m=500.0,
    )
    assert result["method"] == "FAO-56 Penman-Monteith"
    assert math.isfinite(result["eto_mm_day"])
    assert result["eto_mm_day"] >= 0

if __name__ == "__main__":
    test_basic_physics()
    test_fao56_returns_realistic_nonnegative_value()
    print("Local FAO-56 calculation tests: PASS")
