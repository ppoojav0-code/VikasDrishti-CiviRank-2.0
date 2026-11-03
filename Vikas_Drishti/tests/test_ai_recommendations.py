"""Unit and integration tests for AI recommendations and budget feature."""
import io
import json
import os
import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
from PIL import Image

import Vikas_Drishti.ai_development_recommendations as aidr


class TestAIRecommendations(unittest.TestCase):

    def test_clean_json_response(self):
        # Raw json
        raw = '{"key": "value"}'
        self.assertEqual(aidr._clean_json_response(raw), '{"key": "value"}')

        # Markdown wrapped
        wrapped = '```json\n{"key": "value"}\n```'
        self.assertEqual(aidr._clean_json_response(wrapped), '{"key": "value"}')

        # Text around markdown
        surrounded = 'Here is the result:\n```\n{"key": "value"}\n```\nDone'
        self.assertEqual(aidr._clean_json_response(surrounded), '{"key": "value"}')

    def test_image_bytes_processing(self):
        # Create a test PIL image in memory
        img = Image.new("RGB", (100, 100), color="blue")
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        buf.seek(0)

        processed_img, raw_bytes = aidr._image_bytes(buf)
        self.assertIsInstance(processed_img, Image.Image)
        self.assertGreater(len(raw_bytes), 0)

    def test_export_excel_budget(self):
        df = pd.DataFrame([
            {
                "Development Activity": "Road resurfacing",
                "Infrastructure Category": "Roads & Transportation",
                "Estimated Quantity": 500,
                "Unit": "sq. metre",
                "Unit Cost (₹)": 1200,
                "Total Cost (₹)": 600000,
                "Priority": "High",
                "Reason for Expenditure": "Resurface road",
            }
        ])
        subtotal = 600000.0
        contingency = 10.0
        total = 660000.0
        excel_bytes = aidr._export_excel_budget(df, subtotal, contingency, total)
        self.assertIsInstance(excel_bytes, bytes)
        self.assertGreater(len(excel_bytes), 100)

        # Read back with openpyxl
        read_df = pd.read_excel(io.BytesIO(excel_bytes), sheet_name="Budget Estimate")
        self.assertEqual(len(read_df), 1)
        self.assertEqual(read_df.iloc[0]["Development Activity"], "Road resurfacing")

    def test_friendly_error_messages(self):
        class MockAPIError(Exception):
            status_code = 401

        err_401 = MockAPIError("Incorrect API key provided")
        msg = aidr._friendly_error(err_401)
        self.assertIn("HTTP 401", msg)

        class MockQuotaError(Exception):
            status_code = 429

        err_429 = MockQuotaError("insufficient_quota")
        msg_429 = aidr._friendly_error(err_429)
        self.assertIn("HTTP 429", msg_429)

    @patch("Vikas_Drishti.ai_development_recommendations._setting")
    def test_analyze_site_mock(self, mock_setting):
        mock_setting.return_value = "gpt-4.1-mini"
        mock_client = MagicMock()
        mock_response = MagicMock()
        sample_ai_output = {
            "identified_problems": [
                {
                    "category": "Roads",
                    "problem": "Unpaved damaged road",
                    "explanation": "Severe potholes and mud visible throughout the main accessway",
                    "urgency": "Critical",
                },
                {
                    "category": "Drainage",
                    "problem": "Open drainage ditch",
                    "explanation": "Stagnant greywater overflowing along the road shoulder",
                    "urgency": "High",
                }
            ],
            "recommendations": [
                {
                    "category": "Roads",
                    "action": "Construct all-weather bitumen concrete road",
                    "priority": "Critical",
                    "impact": "Enables safe vehicle and ambulance transit",
                }
            ],
            "interventions": [
                "Road resurfacing",
                "Covered drainage"
            ],
            "design_prompt": "Transform scene with paved roads and covered drains",
        }
        mock_response.choices = [
            MagicMock(message=MagicMock(content=json.dumps(sample_ai_output)))
        ]
        mock_client.chat.completions.create.return_value = mock_response

        # Test dummy jpeg bytes
        img = Image.new("RGB", (50, 50), color="red")
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        raw_bytes = buf.getvalue()

        analysis = aidr._analyze_site(mock_client, raw_bytes, "Ward 12")
        self.assertIn("identified_problems", analysis)
        self.assertEqual(len(analysis["identified_problems"]), 2)
        self.assertEqual(analysis["identified_problems"][0]["urgency"], "Critical")
        self.assertIn("recommendations", analysis)
        self.assertIn("Road resurfacing", analysis["interventions"])
        self.assertEqual(analysis["design_prompt"], "Transform scene with paved roads and covered drains")

    @patch("Vikas_Drishti.ai_development_recommendations._setting")
    def test_generate_future_image_mock(self, mock_setting):
        mock_setting.return_value = "gpt-image-1"
        mock_client = MagicMock()
        mock_response = MagicMock()

        dummy_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        b64_str = aidr.base64.b64encode(dummy_png).decode("ascii")

        mock_image_item = MagicMock(b64_json=b64_str, url=None)
        mock_response.data = [mock_image_item]
        mock_client.images.edit.return_value = mock_response

        raw_bytes = b"fake-jpeg-bytes"
        analysis = {
            "identified_problems": [{"problem": "Potholes", "explanation": "Deep road depressions"}],
            "recommendations": [{"action": "Paved road"}],
            "interventions": ["Road resurfacing"],
            "design_prompt": "Clean paved road",
        }

        result = aidr._generate_future_image(mock_client, raw_bytes, "Dharavi", analysis)
        self.assertEqual(result, dummy_png)
        mock_client.images.edit.assert_called()


if __name__ == "__main__":
    unittest.main()
