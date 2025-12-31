"""
Async Rails API client with JSON:API support
"""

import httpx
import logging
from typing import Optional, Dict, Any
from .models import MeasurementBatch
from .jsonapi import format_measurement_batch, parse_jsonapi_response

logger = logging.getLogger(__name__)


class RailsAPIClient:
    """
    Async HTTP client for posting measurements to Rails API
    Implements JSON:API specification
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: float = 10.0,
        max_retries: int = 3,
    ):
        """
        Initialize API client

        Args:
            base_url: Base URL of Rails API (e.g., https://monitoring.example.com)
            api_key: API authentication key
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries

        # Create httpx client with retry transport
        transport = httpx.AsyncHTTPTransport(retries=max_retries)
        self.client = httpx.AsyncClient(
            transport=transport,
            timeout=timeout,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/vnd.api+json",  # JSON:API media type
                "Accept": "application/vnd.api+json",
            },
        )

    async def post_measurements(self, batch: MeasurementBatch) -> Dict[str, Any]:
        """
        Post a measurement batch to Rails API

        Args:
            batch: MeasurementBatch to post

        Returns:
            Response dictionary with success status and data/errors

        Raises:
            httpx.HTTPError: On network or HTTP errors
        """
        # Format as JSON:API
        payload = format_measurement_batch(batch)

        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/measurements", json=payload
            )

            # Log request/response for debugging
            logger.debug(
                f"POST /api/v1/measurements - Status: {response.status_code}"
            )

            # Raise for HTTP errors
            response.raise_for_status()

            # Parse JSON:API response
            response_data = response.json()
            parsed = parse_jsonapi_response(response_data)

            logger.info(
                f"Posted {batch.count} measurements for site '{batch.site}' - "
                f"Success: {parsed['success']}"
            )

            return parsed

        except httpx.HTTPStatusError as e:
            # HTTP error response (4xx, 5xx)
            logger.error(
                f"HTTP {e.response.status_code} error posting measurements: {e}"
            )
            try:
                error_data = e.response.json()
                parsed = parse_jsonapi_response(error_data)
                return parsed
            except Exception:
                return {
                    "success": False,
                    "errors": [
                        {
                            "status": str(e.response.status_code),
                            "title": "HTTP Error",
                            "detail": str(e),
                        }
                    ],
                }

        except httpx.RequestError as e:
            # Network error, timeout, etc.
            logger.error(f"Network error posting measurements: {e}")
            return {
                "success": False,
                "errors": [
                    {"status": "0", "title": "Network Error", "detail": str(e)}
                ],
            }

        except Exception as e:
            # Unexpected error
            logger.error(f"Unexpected error posting measurements: {e}")
            return {
                "success": False,
                "errors": [
                    {"status": "0", "title": "Unexpected Error", "detail": str(e)}
                ],
            }

    async def post_buffered_measurement(self, payload_json: str) -> Dict[str, Any]:
        """
        Post a pre-formatted JSON:API payload (from buffer)

        Args:
            payload_json: JSON string of JSON:API formatted payload

        Returns:
            Response dictionary with success status
        """
        import json

        try:
            payload = json.loads(payload_json)

            response = await self.client.post(
                f"{self.base_url}/api/v1/measurements", json=payload
            )

            response.raise_for_status()
            response_data = response.json()
            return parse_jsonapi_response(response_data)

        except Exception as e:
            logger.error(f"Error posting buffered measurement: {e}")
            return {
                "success": False,
                "errors": [{"status": "0", "title": "Post Error", "detail": str(e)}],
            }

    async def health_check(self) -> bool:
        """
        Check if Rails API is reachable

        Returns:
            True if API is healthy, False otherwise
        """
        try:
            response = await self.client.get(f"{self.base_url}/api/v1/health")
            return response.status_code == 200
        except Exception as e:
            logger.debug(f"Health check failed: {e}")
            return False

    async def close(self) -> None:
        """Close the HTTP client"""
        await self.client.aclose()

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
