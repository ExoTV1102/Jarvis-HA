"""Conversation agent backed by Jarvis."""

from __future__ import annotations

from collections.abc import Callable
import json
import logging
from typing import Any, Literal

from voluptuous_openapi import convert

from homeassistant.components import conversation
from homeassistant.components.conversation import AssistantContent
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import MATCH_ALL
from homeassistant.core import HomeAssistant
from homeassistant.helpers import llm
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.json import json_dumps

from .api import JarvisApiClient, JarvisApiError
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
MAX_TOOL_ITERATIONS = 10
TOOL_COMPLETION_PROMPT = """Home Assistant tool results are authoritative.
After receiving a tool result, answer the user based on that result. Never repeat
the same tool call with the same arguments within one request."""


def _format_tool(
    tool: llm.Tool, custom_serializer: Callable[[Any], Any] | None
) -> dict[str, Any]:
    """Convert a Home Assistant LLM tool to Ollama's tool format."""
    function: dict[str, Any] = {
        "name": tool.name,
        "parameters": convert(tool.parameters, custom_serializer=custom_serializer),
    }
    if tool.description:
        function["description"] = tool.description
    return {"type": "function", "function": function}


def _message_from_content(content: conversation.Content) -> dict[str, Any] | None:
    """Convert Home Assistant chat-log content to an Ollama message."""
    if isinstance(content, conversation.UserContent):
        return {"role": "user", "content": content.content}
    if isinstance(content, conversation.AssistantContent):
        message: dict[str, Any] = {
            "role": "assistant",
            "content": content.content or "",
        }
        if content.tool_calls:
            message["tool_calls"] = [
                {
                    "name": tool_call.tool_name,
                    "arguments": tool_call.tool_args,
                }
                for tool_call in content.tool_calls
                if not tool_call.external
            ]
        return message
    if isinstance(content, conversation.ToolResultContent):
        return {
            "role": "tool",
            "content": json_dumps(content.tool_result),
        }
    return None


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
    _attr_supported_features = conversation.ConversationEntityFeature.CONTROL

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
        """Answer with memory and Home Assistant's exposure-aware tools."""
        try:
            await chat_log.async_provide_llm_data(
                user_input.as_llm_context(DOMAIN),
                llm.LLM_API_ASSIST,
                None,
                user_input.extra_system_prompt,
            )
            assert chat_log.llm_api is not None
            tools = [
                _format_tool(tool, chat_log.llm_api.custom_serializer)
                for tool in chat_log.llm_api.tools
            ]
            seen_tool_calls: set[str] = set()
            requested_tools: list[str] = []

            for _iteration in range(MAX_TOOL_ITERATIONS):
                system_prompt = "\n\n".join(
                    (
                        getattr(chat_log.content[0], "content", ""),
                        TOOL_COMPLETION_PROMPT,
                    )
                )
                messages = [
                    message
                    for content in chat_log.content[1:]
                    if (message := _message_from_content(content)) is not None
                ]
                turn = await self._client.async_chat_turn(
                    user_input.text,
                    system_prompt,
                    messages,
                    tools,
                )
                tool_inputs = [
                    llm.ToolInput(
                        tool_name=tool_call.name,
                        tool_args=tool_call.arguments,
                    )
                    for tool_call in turn.tool_calls
                ]
                signatures = [
                    json.dumps(
                        [tool_input.tool_name, tool_input.tool_args],
                        sort_keys=True,
                        default=str,
                    )
                    for tool_input in tool_inputs
                ]
                if duplicate_tools := [
                    tool_input.tool_name
                    for tool_input, signature in zip(
                        tool_inputs, signatures, strict=True
                    )
                    if signature in seen_tool_calls
                ]:
                    _LOGGER.warning(
                        "Stopped duplicate Home Assistant tool calls: %s",
                        ", ".join(duplicate_tools),
                    )
                    chat_log.async_add_assistant_content_without_tools(
                        AssistantContent(
                            agent_id=user_input.agent_id,
                            content=(
                                "Der Home-Assistant-Befehl wurde bereits verarbeitet."
                            ),
                        )
                    )
                    break
                seen_tool_calls.update(signatures)
                requested_tools.extend(
                    tool_input.tool_name for tool_input in tool_inputs
                )
                assistant_content = AssistantContent(
                    agent_id=user_input.agent_id,
                    content=turn.answer or None,
                    tool_calls=tool_inputs or None,
                )
                async for _tool_result in chat_log.async_add_assistant_content(
                    assistant_content
                ):
                    pass
                if not tool_inputs:
                    break
            else:
                raise JarvisApiError(
                    "Too many Home Assistant tool iterations: "
                    + ", ".join(requested_tools)
                )
        except conversation.ConverseError as err:
            return err.as_conversation_result()
        except JarvisApiError:
            _LOGGER.exception("Jarvis failed to answer")
            chat_log.async_add_assistant_content_without_tools(
                AssistantContent(
                    agent_id=user_input.agent_id,
                    content=(
                        "Jarvis ist momentan nicht erreichbar. "
                        "Bitte prüfe den Memory-Service und Ollama."
                    ),
                )
            )
        return conversation.async_get_result_from_chat_log(user_input, chat_log)
