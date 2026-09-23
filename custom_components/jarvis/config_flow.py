"""Config flow for Jarvis."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import JarvisApiClient, JarvisApiError, JarvisInvalidAuth
from .const import CONF_API_KEY, CONF_URL, DEFAULT_URL, DOMAIN


def _schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_URL, default=defaults.get(CONF_URL, DEFAULT_URL)
            ): TextSelector(TextSelectorConfig(type=TextSelectorType.URL)),
            vol.Required(
                CONF_API_KEY, default=defaults.get(CONF_API_KEY, "")
            ): TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD)),
        }
    )


class JarvisConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Configure Jarvis through the Home Assistant UI."""

    VERSION = 1

    async def _validate(self, user_input: dict[str, Any]) -> str | None:
        client = JarvisApiClient(
            async_get_clientsession(self.hass),
            user_input[CONF_URL],
            user_input[CONF_API_KEY],
        )
        try:
            await client.async_check()
        except JarvisInvalidAuth:
            return "invalid_auth"
        except JarvisApiError:
            return "cannot_connect"
        return None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle initial setup."""
        errors: dict[str, str] = {}
        if user_input is not None:
            error = await self._validate(user_input)
            if error is None:
                await self.async_set_unique_id("jarvis")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title="Jarvis", data=user_input)
            errors["base"] = error

        return self.async_show_form(
            step_id="user",
            data_schema=_schema(user_input),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Update the backend URL or API key."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            error = await self._validate(user_input)
            if error is None:
                return self.async_update_reload_and_abort(
                    entry,
                    data=user_input,
                )
            errors["base"] = error

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_schema(user_input or dict(entry.data)),
            errors=errors,
        )
