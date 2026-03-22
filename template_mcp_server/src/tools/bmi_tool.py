"""BMI tool for the Template MCP Server.

This tool calculates Body Mass Index (BMI) based on height and weight inputs,
providing health category classification following WHO standards.
"""

from typing import Any, Dict

from template_mcp_server.utils.pylogger import get_python_logger

logger = get_python_logger()


def bmi_tool(height: str, weight: str) -> Dict[str, Any]:
    """Calculate Body Mass Index (BMI) based on height and weight inputs.

    This tool provides a BMI calculation along with a basic health category classification
    following World Health Organization standards. BMI is a simple screening metric that
    measures body fat based on height and weight, applicable to adult men and women.

    CPU-bound operation - uses def for computational tasks.

    Args:
        height: Height in centimeters (e.g., "175" for 175 cm)
        weight: Weight in kilograms (e.g., "70.5" for 70.5 kg)

    Returns:
        Dictionary containing the result of BMI calculation

    Raises:
        ValueError: If inputs are not valid numbers or are out of reasonable range
    """
    try:
        # Validate and convert inputs
        try:
            height_cm = float(height)
            weight_kg = float(weight)
        except (ValueError, TypeError):
            raise ValueError("Height and weight must be valid numbers")

        # Validate reasonable ranges
        if height_cm <= 0 or height_cm > 300:
            raise ValueError("Height must be between 0 and 300 cm")
        if weight_kg <= 0 or weight_kg > 500:
            raise ValueError("Weight must be between 0 and 500 kg")

        # Convert height from cm to meters
        height_m = height_cm / 100

        # Calculate BMI: weight (kg) / height (m)^2
        bmi = weight_kg / (height_m**2)

        # Determine BMI category based on WHO standards
        if bmi < 18.5:
            category = "Underweight"
        elif bmi < 25.0:
            category = "Normal weight"
        elif bmi < 30.0:
            category = "Overweight"
        else:
            category = "Obese"

        logger.info(
            f"BMI tool called: height={height_cm}cm, weight={weight_kg}kg, "
            f"BMI={bmi:.2f}, category={category}"
        )

        return {
            "status": "success",
            "operation": "bmi_calculation",
            "height_cm": height_cm,
            "weight_kg": weight_kg,
            "bmi": round(bmi, 2),
            "category": category,
            "message": f"BMI calculated: {bmi:.2f} ({category})",
        }

    except Exception as e:
        logger.error(f"Error in BMI tool: {e}")
        return {
            "status": "error",
            "error": str(e),
            "message": "Failed to calculate BMI",
        }
