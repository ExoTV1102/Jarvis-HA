# Jarvis for Home Assistant

Home Assistant conversation integration that enriches a native conversation
agent with context from a self-hosted Jarvis memory service.

## Requirements

- A reachable Jarvis backend
- The backend URL, for example `http://10.0.10.23:9000`
- The configured Jarvis API key
- A native Home Assistant conversation agent, for example Ollama with Gemma

## Installation with HACS

1. Open HACS in Home Assistant.
2. Add `https://github.com/ExoTV1102/Jarvis-HA` as a custom repository of type
   **Integration**.
3. Install **Jarvis** and restart Home Assistant.
4. Go to **Settings → Devices & services → Add integration → Jarvis**.
5. Enter the backend URL and API key and select the existing native conversation
   agent that Jarvis should use.
6. Select **Jarvis** as the conversation agent in the desired Assist pipeline.
7. In **Settings → Voice assistants → Expose**, expose only the entities Jarvis
   should be allowed to read or control.

When upgrading from `0.2.x` to `0.3.0`, restart Home Assistant and open
**Settings → Devices & services → Jarvis → Reconfigure** once. Keep the existing
URL and API key and select the native conversation agent. The Jarvis backend does
not need to be redeployed.

## Manual installation

Copy `custom_components/jarvis` to
`/config/custom_components/jarvis` and restart Home Assistant.

## Scope

For every user message, Jarvis retrieves relevant memory context once and adds it
to the selected native Home Assistant conversation agent. The native agent keeps
its streaming, conversation history, and built-in Assist tool handling. Jarvis no
longer runs a second model or a custom tool loop. If the memory service is
temporarily unavailable, the native agent continues without personal context.
For device status and control requests, Jarvis also requires a real Home Assistant
tool call and tells the agent not to report success without a successful tool
result.

Only entities exposed to Assist are available. The memory backend receives no
Home Assistant access token and does not execute Home Assistant tools itself.

Start with low-risk entities such as lights, sensors, scenes, and selected switches.
Do not expose locks, garage doors, or alarm panels until the setup has been tested
carefully.

The public repository does not contain backend source code, deployment
configuration, credentials, or API keys.
