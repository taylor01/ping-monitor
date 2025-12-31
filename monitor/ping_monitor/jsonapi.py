"""
JSON:API compliant formatter for Rails API
Spec: https://jsonapi.org/format/
"""

from typing import Dict, Any
from .models import MeasurementBatch


def format_measurement_batch(batch: MeasurementBatch) -> Dict[str, Any]:
    """
    Format a measurement batch as JSON:API compliant payload

    JSON:API structure for creating resources:
    {
      "data": {
        "type": "measurement-batches",
        "attributes": {
          "site": "home",
          "timestamp": "2025-12-31T12:00:00Z",
          "measurements": [...]
        }
      }
    }

    Args:
        batch: MeasurementBatch to format

    Returns:
        JSON:API compliant dictionary
    """
    return {
        "data": {
            "type": "measurement-batches",
            "attributes": {
                "site": batch.site,
                "timestamp": batch.timestamp.isoformat(),
                "measurements": [
                    {
                        "host": m.host,
                        "ip": m.ip,
                        "timestamp": m.timestamp.isoformat(),
                        "is_up": m.is_up,
                        "latency_ms": m.latency_ms,
                        "packet_loss": m.packet_loss,
                        "jitter_ms": m.jitter_ms
                    }
                    for m in batch.measurements
                ]
            }
        }
    }


def parse_jsonapi_response(response_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse a JSON:API response

    Handles standard JSON:API response format and extracts relevant data

    Args:
        response_data: JSON:API response dictionary

    Returns:
        Parsed data or error information
    """
    # Check for errors
    if "errors" in response_data:
        errors = response_data["errors"]
        return {
            "success": False,
            "errors": errors
        }

    # Extract data
    if "data" in response_data:
        data = response_data["data"]
        return {
            "success": True,
            "data": data,
            "meta": response_data.get("meta", {})
        }

    # Unexpected format
    return {
        "success": False,
        "errors": [{"title": "Invalid JSON:API response format"}]
    }


def format_error_response(error_message: str, status_code: int = 500) -> Dict[str, Any]:
    """
    Format an error as JSON:API error response

    Args:
        error_message: Error message
        status_code: HTTP status code

    Returns:
        JSON:API error format
    """
    return {
        "errors": [
            {
                "status": str(status_code),
                "title": "Measurement Submission Error",
                "detail": error_message
            }
        ]
    }
