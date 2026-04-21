"""BMI tool for the Template MCP Server.

This tool calculates Body Mass Index (BMI) based on height and weight inputs,
providing health category classification following WHO standards.
"""

from typing import Any, Dict

from template_mcp_server.utils.pylogger import get_python_logger

logger = get_python_logger()


def calculate_bmi(height: str, weight: str) -> Dict[str, Any]:
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
    logger.info(
        "calculate_bmi invoked",
        extra={"input": {"height": height, "weight": weight}},
    )

    try:
        # Validate and convert inputs
        try:
            height_cm = float(height)
            weight_kg = float(weight)
            logger.debug(
                "Input conversion successful",
                extra={"height_cm": height_cm, "weight_kg": weight_kg},
            )
        except (ValueError, TypeError) as e:
            error_msg = "Height and weight must be valid numbers"
            logger.error(
                "Input conversion failed",
                extra={
                    "error": error_msg,
                    "input": {"height": height, "weight": weight},
                    "exception": str(e),
                },
            )
            raise ValueError(error_msg)

        # Validate reasonable ranges
        if height_cm <= 0 or height_cm > 300:
            error_msg = "Height must be between 0 and 300 cm"
            logger.error(
                "Height validation failed",
                extra={"error": error_msg, "height_cm": height_cm},
            )
            raise ValueError(error_msg)
        if weight_kg <= 0 or weight_kg > 500:
            error_msg = "Weight must be between 0 and 500 kg"
            logger.error(
                "Weight validation failed",
                extra={"error": error_msg, "weight_kg": weight_kg},
            )
            raise ValueError(error_msg)

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
            "BMI calculation completed successfully",
            extra={
                "input": {"height_cm": height_cm, "weight_kg": weight_kg},
                "output": {"bmi": round(bmi, 2), "category": category},
            },
        )

        output = {
            "status": "success",
            "operation": "bmi_calculation",
            "height_cm": height_cm,
            "weight_kg": weight_kg,
            "bmi": round(bmi, 2),
            "category": category,
            "message": f"BMI calculated: {bmi:.2f} ({category})",
        }

        logger.debug("calculate_bmi output", extra={"output": output})
        return output

    except Exception as e:
        logger.exception(
            "Error in calculate_bmi",
            extra={"input": {"height": height, "weight": weight}, "error": str(e)},
        )
        error_output = {
            "status": "error",
            "error": str(e),
            "message": "Failed to calculate BMI",
        }
        logger.debug("calculate_bmi error output", extra={"output": error_output})
        return error_output
