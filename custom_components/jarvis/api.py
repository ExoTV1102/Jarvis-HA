"""Client for the Jarvis memory and chat API."""

from __future__ import annotations

from aiohttp import ClientError, ClientResponse, ClientSession, ClientTimeout


class JarvisApiError(Exception):
    """Base error returned by the Jarvis API client."""


class JarvisCannotConnect(JarvisApiError):
    """The Jarvis backend could not be reached."""


class JarvisInvalidAuth(JarvisApiError):
    """The Jarvis API key was rejected."""


class JarvisInvalidResponse(JarvisApiError):
    """The Jarvis backend returned an invalid response."""


class JarvisApiClient:
    """Small asynchronous client for Jarvis."""

    def __init__(self, session: ClientSession, base_url: str, api_key: str) -> None:
        self._session = session
        self._base_url = base_url.rstrip("/")
        self._headers = {"X-API-Key": api_key}

    async def _raise_for_status(self, response: ClientResponse) -> None:
        if response.status == 401:
            raise JarvisInvalidAuth("The API key was rejected")
        if response.status >= 400:
            detail = await response.text()
            raise JarvisApiError(
                f"Jarvis returned HTTP {response.status}: {detail[:300]}"
            )

    async def async_check(self) -> None:
        """Validate connectivity and authentication."""
        try:
            async with self._session.get(
                f"{self._base_url}/auth/check",
                headers=self._headers,
                timeout=ClientTimeout(total=5),
            ) as response:
                await self._raise_for_status(response)
                data = await response.json()
        except JarvisApiError:
            raise
        except (ClientError, TimeoutError, ValueError) as exc:
            raise JarvisCannotConnect(str(exc)) from exc

        if data.get("status") != "ok":
            raise JarvisInvalidResponse("Jarvis did not report a valid status")

    async def async_context(self, query: str) -> str:
        """Retrieve relevant personal memory context for one user turn."""
        try:
            async with self._session.post(
                f"{self._base_url}/context",
                headers=self._headers,
                json={"query": query},
                timeout=ClientTimeout(total=5),
            ) as response:
                await self._raise_for_status(response)
                data = await response.json()
        except JarvisApiError:
            raise
        except (ClientError, TimeoutError, ValueError) as exc:
            raise JarvisCannotConnect(str(exc)) from exc

        context = data.get("context")
        if not isinstance(context, str):
            raise JarvisInvalidResponse("Jarvis returned invalid memory context")
        return context.strip()
