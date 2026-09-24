"""Config flow for Jarvis."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components import conversation
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import JarvisApiClient, JarvisApiError, JarvisInvalidAuth
from .const import CONF_AGENT_ID, CONF_API_KEY, CONF_URL, DEFAULT_URL, DOMAIN


def _schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    defaults = defaults or {}
    fields: dict[Any, Any] = {
        vol.Required(
            CONF_URL, default=defaults.get(CONF_URL, DEFAULT_URL)
        ): TextSelector(TextSelectorConfig(type=TextSelectorType.URL)),
        vol.Required(
            CONF_API_KEY, default=defaults.get(CONF_API_KEY, "")
        ): TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD)),
    }
    agent_key = vol.Required(CONF_AGENT_ID)
    if defaults.get(CONF_AGENT_ID):
        agent_key = vol.Required(CONF_AGENT_ID, default=defaults[CONF_AGENT_ID])
    fields[agent_key] = EntitySelector(EntitySelectorConfig(domain="conversation"))
    return vol.Schema(fields)


class JarvisConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Configure Jarvis through the Home Assistant UI."""

    VERSION = 1

    async def _validate(
        self, user_input: dict[str, Any], own_entry_id: str | None = None
    ) -> str | None:
        agent_id = user_input[CONF_AGENT_ID]
        if conversation.async_get_agent_info(self.hass, agent_id) is None:
            return "invalid_agent"
        selected = er.async_get(self.hass).async_get(agent_id)
        if selected is not None and selected.config_entry_id == own_entry_id:
            return "invalid_agent"
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
            error = await self._validate(user_input, entry.entry_id)
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
