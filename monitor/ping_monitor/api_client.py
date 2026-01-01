"""
Async Rails API client with JSON:API support and JWT authentication
"""

import httpx
import logging
import time
from typing import Optional, Dict, Any
from .models import MeasurementBatch
from .jsonapi import format_measurement_batch, parse_jsonapi_response

logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Raised when authentication fails"""

    pass


class RailsAPIClient:
    """
    Async HTTP client for posting measurements to Rails API
    Implements JSON:API specification with JWT authentication
    """

    # Refresh token 5 minutes before expiry
    TOKEN_REFRESH_BUFFER = 300

    def __init__(
        self,
        base_url: str,
        site_name: str,
        site_secret: str,
        timeout: float = 10.0,
        max_retries: int = 3,
    ):
        """
        Initialize API client

        Args:
            base_url: Base URL of Rails API (e.g., https://monitoring.example.com)
            site_name: Site identifier for authentication
            site_secret: Site secret for authentication
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.base_url = base_url.rstrip("/")
        self.site_name = site_name
        self.site_secret = site_secret
        self.timeout = timeout
        self.max_retries = max_retries

        # JWT tokens
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._token_expires_at: float = 0

        # Create httpx client with retry transport
        transport = httpx.AsyncHTTPTransport(retries=max_retries)
        self.client = httpx.AsyncClient(
            transport=transport,
            timeout=timeout,
            headers={
                "Content-Type": "application/vnd.api+json",
                "Accept": "application/vnd.api+json",
            },
        )

    @property
    def is_authenticated(self) -> bool:
        """Check if we have a valid (non-expired) access token"""
        if not self._access_token:
            return False
        return time.time() < (self._token_expires_at - self.TOKEN_REFRESH_BUFFER)

    async def authenticate(self) -> bool:
        """
        Authenticate with the Rails API using site credentials

        Returns:
            True if authentication succeeded, False otherwise
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/auth/token",
                json={"site_id": self.site_name, "secret": self.site_secret},
            )

            if response.status_code == 200:
                data = response.json().get("data", {})
                self._access_token = data.get("access_token")
                self._refresh_token = data.get("refresh_token")
                expires_in = data.get("expires_in", 3600)
                self._token_expires_at = time.time() + expires_in

                logger.info(f"Authenticated as site '{self.site_name}'")
                return True

            logger.error(
                f"Authentication failed: {response.status_code} - {response.text}"
            )
            return False

        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False

    async def refresh_access_token(self) -> bool:
        """
        Refresh the access token using the refresh token

        Returns:
            True if refresh succeeded, False otherwise
        """
        if not self._refresh_token:
            logger.warning("No refresh token available, re-authenticating")
            return await self.authenticate()

        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/auth/refresh",
                json={"refresh_token": self._refresh_token},
            )

            if response.status_code == 200:
                data = response.json().get("data", {})
                self._access_token = data.get("access_token")
                self._refresh_token = data.get("refresh_token")
                expires_in = data.get("expires_in", 3600)
                self._token_expires_at = time.time() + expires_in

                logger.debug("Access token refreshed")
                return True

            # Refresh failed, try full re-authentication
            logger.warning("Token refresh failed, re-authenticating")
            return await self.authenticate()

        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            return await self.authenticate()

    async def _ensure_authenticated(self) -> None:
        """Ensure we have a valid access token, refreshing if needed"""
        if not self.is_authenticated:
            if self._refresh_token:
                success = await self.refresh_access_token()
            else:
                success = await self.authenticate()

            if not success:
                raise AuthenticationError("Failed to authenticate with Rails API")

    def _get_auth_headers(self) -> Dict[str, str]:
        """Get headers with current access token"""
        return {"Authorization": f"Bearer {self._access_token}"}

    async def post_measurements(self, batch: MeasurementBatch) -> Dict[str, Any]:
        """
        Post a measurement batch to Rails API

        Args:
            batch: MeasurementBatch to post

        Returns:
            Response dictionary with success status and data/errors
        """
        await self._ensure_authenticated()

        payload = format_measurement_batch(batch)

        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/measurements",
                json=payload,
                headers=self._get_auth_headers(),
            )

            logger.debug(
                f"POST /api/v1/measurements - Status: {response.status_code}"
            )

            # Handle 401 by refreshing token and retrying once
            if response.status_code == 401:
                logger.debug("Got 401, refreshing token and retrying")
                if await self.refresh_access_token():
                    response = await self.client.post(
                        f"{self.base_url}/api/v1/measurements",
                        json=payload,
                        headers=self._get_auth_headers(),
                    )

            response.raise_for_status()

            response_data = response.json()
            parsed = parse_jsonapi_response(response_data)

            logger.info(
                f"Posted {batch.count} measurements for site '{batch.site}' - "
                f"Success: {parsed['success']}"
            )

            return parsed

        except httpx.HTTPStatusError as e:
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
            logger.error(f"Network error posting measurements: {e}")
            return {
                "success": False,
                "errors": [
                    {"status": "0", "title": "Network Error", "detail": str(e)}
                ],
            }

        except AuthenticationError as e:
            logger.error(f"Authentication error: {e}")
            return {
                "success": False,
                "errors": [
                    {"status": "401", "title": "Authentication Error", "detail": str(e)}
                ],
            }

        except Exception as e:
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

        await self._ensure_authenticated()

        try:
            payload = json.loads(payload_json)

            response = await self.client.post(
                f"{self.base_url}/api/v1/measurements",
                json=payload,
                headers=self._get_auth_headers(),
            )

            # Handle 401 by refreshing token and retrying once
            if response.status_code == 401:
                if await self.refresh_access_token():
                    response = await self.client.post(
                        f"{self.base_url}/api/v1/measurements",
                        json=payload,
                        headers=self._get_auth_headers(),
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
            response = await self.client.get(f"{self.base_url}/up")
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
