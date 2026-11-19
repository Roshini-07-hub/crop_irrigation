import unittest
from backend.ml.processing.farmer_water_usage import (
    calculate_farmer_water_plan,
    get_crop_archetype,
    CROP_ARCHETYPES
)
from backend.ml.processing.water_require import calculate_water_requirement


class FarmerWaterUsageTestCase(unittest.TestCase):
    def test_khesari_real_farmer_schedule(self):
        """Verify Khesari (Grass Pea) produces realistic pulse schedule instead of daily pumping."""
        plan = calculate_farmer_water_plan(
            crop="Khesari",
            growth_stage="Flowering",
            field_area_hectare=1.01,
            daily_net_etc_mm=4.70,
            daily_gross_mm=6.26,
            irrigation_method="Sprinkler",
            irrigation_efficiency=0.75,
            soil_type="Loamy",
            pump_hp=5.0
        )

        # 1. Must flag over-irrigation danger for daily watering
        self.assertIn("DO NOT IRRIGATE DAILY", plan["danger_warning"])

        # 2. Must recommend 12-14 day interval, not 1 day
        self.assertGreaterEqual(plan["irrigation_interval_days"], 12)
        self.assertIn("12 - 14 Days", plan["irrigation_interval_display"])

        # 3. Event volume must be scheduled event (~500,000 L), not daily 63,246 L
        self.assertGreater(plan["event_volume_litres"], 400000)
        self.assertLess(plan["event_volume_litres"], 700000)

        # 4. Pump runtime must be calculated
        self.assertGreater(plan["pump_hours_per_event"], 8.0)
        self.assertLess(plan["pump_hours_per_event"], 15.0)

        # 5. Seasonal summary must reflect low-irrigation / residual nature
        self.assertIn("0 - 2 Irrigations", plan["seasonal_irrigations_summary"])

    def test_wheat_cereal_schedule(self):
        """Verify Wheat produces staged critical interval."""
        plan = calculate_farmer_water_plan(
            crop="Wheat",
            growth_stage="Flowering",
            field_area_hectare=1.0,
            daily_net_etc_mm=4.5,
            daily_gross_mm=6.0,
            irrigation_method="Surface",
            irrigation_efficiency=0.60,
            soil_type="Clay",
            pump_hp=5.0
        )

        self.assertGreaterEqual(plan["irrigation_interval_days"], 10)
        self.assertIn("CRITICAL", plan["stage_criticality"])
        self.assertIn("4 - 6 Irrigations", plan["seasonal_irrigations_summary"])

    def test_drip_micro_irrigation(self):
        """Verify Drip produces high-frequency daily/alternate-day runtime."""
        plan = calculate_farmer_water_plan(
            crop="Tomato",
            growth_stage="Flowering",
            field_area_hectare=1.0,
            daily_net_etc_mm=4.5,
            daily_gross_mm=5.0,
            irrigation_method="Drip",
            irrigation_efficiency=0.90,
            soil_type="Loamy",
            pump_hp=5.0
        )

        self.assertEqual(plan["irrigation_interval_days"], 1)
        self.assertEqual(plan["irrigation_interval_display"], "Daily")
        self.assertLess(plan["pump_hours_per_event"], 3.0)

    def test_water_require_integration(self):
        """Verify calculate_water_requirement integrates farmer_usage and preserves all legacy keys."""
        res = calculate_water_requirement(
            crop="Khesari",
            growth_stage="Flowering",
            field_area_hectare=1.01,
            eto_mm_day=4.08,
            rainfall_mm=0.0,
            irrigation_efficiency=0.75,
            irrigation_method="Sprinkler",
            soil_type="Loamy",
            pump_hp=5.0
        )

        # Legacy keys preserved
        self.assertIn("gross_irrigation_litres", res)
        self.assertIn("crop_water_requirement_mm", res)
        self.assertIn("kc", res)

        # New real farmer usage keys present
        self.assertIn("farmer_usage", res)
        self.assertIn("event_volume_litres", res)
        self.assertIn("irrigation_interval_display", res)
        self.assertIn("pump_hours_per_event", res)
        self.assertIn("farmer_practical_guideline", res)
        self.assertIn("danger_warning", res)


if __name__ == "__main__":
    unittest.main()

