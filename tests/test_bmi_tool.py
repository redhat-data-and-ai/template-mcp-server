"""Tests for the BMI calculator tool — 100% coverage."""

from template_mcp_server.src.tools.bmi_tool import calculate_bmi


class TestCalculateBmiSuccess:
    """Successful BMI calculations with all WHO categories."""

    def test_normal_weight(self):
        result = calculate_bmi("175", "70")
        assert result["status"] == "success"
        assert result["category"] == "Normal weight"
        assert result["height_cm"] == 175.0
        assert result["weight_kg"] == 70.0
        assert 20 < result["bmi"] < 25

    def test_underweight(self):
        result = calculate_bmi("180", "50")
        assert result["status"] == "success"
        assert result["category"] == "Underweight"
        assert result["bmi"] < 18.5

    def test_overweight(self):
        result = calculate_bmi("170", "80")
        assert result["status"] == "success"
        assert result["category"] == "Overweight"
        assert 25 <= result["bmi"] < 30

    def test_obese(self):
        result = calculate_bmi("160", "100")
        assert result["status"] == "success"
        assert result["category"] == "Obese"
        assert result["bmi"] >= 30

    def test_boundary_normal_weight(self):
        result = calculate_bmi("100", "18.5")
        assert result["status"] == "success"
        assert result["category"] == "Normal weight"

    def test_float_inputs(self):
        result = calculate_bmi("175.5", "72.3")
        assert result["status"] == "success"
        assert result["operation"] == "bmi_calculation"
        assert "message" in result


class TestCalculateBmiValidation:
    """Input validation and error handling."""

    def test_non_numeric_height(self):
        result = calculate_bmi("abc", "70")
        assert result["status"] == "error"
        assert "message" in result

    def test_non_numeric_weight(self):
        result = calculate_bmi("175", "xyz")
        assert result["status"] == "error"

    def test_height_zero(self):
        result = calculate_bmi("0", "70")
        assert result["status"] == "error"

    def test_height_negative(self):
        result = calculate_bmi("-10", "70")
        assert result["status"] == "error"

    def test_height_over_300(self):
        result = calculate_bmi("301", "70")
        assert result["status"] == "error"

    def test_weight_zero(self):
        result = calculate_bmi("175", "0")
        assert result["status"] == "error"

    def test_weight_negative(self):
        result = calculate_bmi("175", "-5")
        assert result["status"] == "error"

    def test_weight_over_500(self):
        result = calculate_bmi("175", "501")
        assert result["status"] == "error"

    def test_none_height(self):
        result = calculate_bmi(None, "70")
        assert result["status"] == "error"

    def test_none_weight(self):
        result = calculate_bmi("175", None)
        assert result["status"] == "error"
