"""
System Integration Test Suite for Sustainable AI Crop Irrigation System

Tests all REST APIs, calculations, persistence layer, static files, and error handling.
"""

import unittest
from backend.app import app


class SystemIntegrationTestCase(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_01_health_and_status(self):
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["status"], "operational")

        res_status = self.client.get("/api/status")
        self.assertEqual(res_status.status_code, 200)
        status_data = res_status.get_json()
        self.assertTrue(status_data["success"])
        self.assertEqual(status_data["features"]["supported_crops"], 55)

    def test_02_static_pages_served(self):
        for path in ["/", "/pages/dashboard.html", "/pages/water_prediction.html", 
                     "/pages/irrigation_recommendation.html", "/pages/history.html"]:
            res = self.client.get(path)
            self.assertEqual(res.status_code, 200, f"Failed serving {path}")

    def test_03_crops_metadata_endpoint(self):
        res = self.client.get("/api/crops/")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["total_crops"], 55)
        self.assertGreaterEqual(len(data["groups"]), 5)

    def test_04_water_prediction_manual(self):
        payload = {
            "crop": "Wheat",
            "growth_stage": "Flowering",
            "field_area_hectare": 2.0,
            "eto_mm_day": 4.5,
            "rainfall_mm": 0,
            "irrigation_method": "Drip"
        }
        res = self.client.post("/api/predict/water", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertIn("prediction", data)
        self.assertGreater(data["prediction"]["gross_irrigation_litres"], 0)

    def test_05_water_prediction_weather_location(self):
        payload = {
            "crop": "Maize",
            "growth_stage": "Vegetative",
            "field_area_hectare": 1.5,
            "latitude": 17.385,
            "longitude": 78.487,
            "irrigation_method": "Sprinkler"
        }
        res = self.client.post("/api/predict/water/weather", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertIn("prediction", data)
        self.assertIn("eto", data)

    def test_06_irrigation_advisory_weather(self):
        payload = {
            "crop": "Rice",
            "growth_stage": "Flowering",
            "soil_type": "Clay",
            "soil_moisture": 18.0,
            "latitude": 17.385,
            "longitude": 78.487,
            "field_area_hectare": 2.5,
            "irrigation_type": "Canal"
        }
        res = self.client.post("/api/predict/weather/irrigation", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertIn("result", data)
        irr_rec = data["result"].get("irrigation_recommendation", data["result"])
        self.assertIn("irrigation_priority", irr_rec)

    def test_07_complete_prediction(self):
        payload = {
            "crop": "Cotton(lint)",
            "growth_stage": "Flowering",
            "soil_type": "Loamy",
            "soil_moisture": 22.0,
            "temperature_c": 34.0,
            "humidity": 40.0,
            "rainfall_mm": 0.0,
            "sunlight_hours": 8.5,
            "wind_speed_kmh": 14.0,
            "field_area_hectare": 3.0,
            "irrigation_type": "drip",
            "irrigation_need": "high",
            "eto_mm_day": 5.2
        }
        res = self.client.post("/api/predict/complete", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertIn("water_requirement", data)
        self.assertIn("irrigation_recommendation", data)

    def test_08_location_geocoding(self):
        res = self.client.get("/api/location/search?q=Hyderabad")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertGreater(len(data["locations"]), 0)

    def test_09_history_lifecycle(self):
        # 1. Fetch history
        res = self.client.get("/api/history/")
        self.assertEqual(res.status_code, 200)
        records = res.get_json()["history"]
        self.assertGreater(len(records), 0)

        # 2. Delete test record
        record_id = records[0]["id"]
        res_del = self.client.delete(f"/api/history/{record_id}")
        self.assertEqual(res_del.status_code, 200)
        self.assertTrue(res_del.get_json()["success"])

    def test_10_crop_aliases_and_renaming(self):
        # 1. Check metadata endpoint
        res = self.client.get("/api/crops/")
        data = res.get_json()
        crop_names = [c["crop"] for c in data["crops"]]
        self.assertIn("Mirchi", crop_names)
        self.assertIn("Paddy", crop_names)
        mirchi_obj = next(c for c in data["crops"] if c["crop"] == "Mirchi")
        self.assertIn("Chilli", mirchi_obj["display_name"])
        self.assertIn("red chillies", mirchi_obj["aliases"])

        paddy_obj = next(c for c in data["crops"] if c["crop"] == "Paddy")
        self.assertIn("Rice", paddy_obj["display_name"])
        self.assertIn("rice", paddy_obj["aliases"])

        # 2. Test predictions with Mirchi, Paddy, and legacy aliases
        for crop_alias in ["Mirchi", "Dry chillies", "red chillies", "Paddy", "Rice", "Cotton(lint)", "Chana"]:
            payload = {
                "crop": crop_alias,
                "growth_stage": "Flowering",
                "field_area_hectare": 1.0,
                "eto_mm_day": 5.0,
                "irrigation_method": "Drip"
            }
            pred_res = self.client.post("/api/predict/water", json=payload)
            self.assertEqual(pred_res.status_code, 200, f"Failed for {crop_alias}")
            pred_data = pred_res.get_json()
            self.assertTrue(pred_data["success"])
            self.assertGreater(pred_data["prediction"]["gross_irrigation_litres"], 0)


if __name__ == "__main__":
    unittest.main()
