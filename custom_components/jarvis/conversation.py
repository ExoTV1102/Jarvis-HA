"""Conversation agent backed by Jarvis."""

from __future__ import annotations

import logging
from typing import Literal

from homeassistant.components import conversation
from homeassistant.components.conversation import AssistantContent
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import MATCH_ALL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import JarvisApiClient, JarvisApiError
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Jarvis conversation entity."""
    async_add_entities(
        [JarvisConversationEntity(entry, hass.data[DOMAIN][entry.entry_id])]
    )


class JarvisConversationEntity(
    conversation.ConversationEntity,
    conversation.AbstractConversationAgent,
):
    """Represent Jarvis as a Home Assistant conversation agent."""

    _attr_has_entity_name = True
    _attr_name = "Jarvis"

    def __init__(self, entry: ConfigEntry, client: JarvisApiClient) -> None:
        self._entry = entry
        self._client = client
        self._attr_unique_id = entry.entry_id

    @property
    def supported_languages(self) -> list[str] | Literal["*"]:
        """Return supported languages."""
        return MATCH_ALL

    async def async_added_to_hass(self) -> None:
        """Register Jarvis as a conversation agent."""
        await super().async_added_to_hass()
        conversation.async_set_agent(self.hass, self._entry, self)

    async def async_will_remove_from_hass(self) -> None:
        """Unregister Jarvis as a conversation agent."""
        conversation.async_unset_agent(self.hass, self._entry)
        await super().async_will_remove_from_hass()

    async def _async_handle_message(
        self,
        user_input: conversation.ConversationInput,
        chat_log: conversation.ChatLog,
    ) -> conversation.ConversationResult:
        """Send the message and recent conversation history to Jarvis."""
        history: list[dict[str, str]] = []
        for item in chat_log.content[:-1]:
            role = getattr(item, "role", None)
            content = getattr(item, "content", None)
            if role in ("user", "assistant") and isinstance(content, str) and content:
                history.append({"role": role, "content": content})

        try:
            answer = await self._client.async_chat(user_input.text, history)
        except JarvisApiError:
            _LOGGER.exception("Jarvis failed to answer")
            answer = (
                "Jarvis ist momentan nicht erreichbar. "
                "Bitte prüfe den Memory-Service und Ollama."
            )

        chat_log.async_add_assistant_content_without_tools(
            AssistantContent(agent_id=user_input.agent_id, content=answer)
        )
        return conversation.async_get_result_from_chat_log(user_input, chat_log)

