# Jarvis for Home Assistant

Home Assistant conversation integration for a self-hosted Jarvis memory and chat
backend.

## Requirements

- A reachable Jarvis backend
- The backend URL, for example `http://10.0.10.23:9000`
- The configured Jarvis API key

## Installation with HACS

1. Open HACS in Home Assistant.
2. Add `https://github.com/ExoTV1102/Jarvis-HA` as a custom repository of type
   **Integration**.
3. Install **Jarvis** and restart Home Assistant.
4. Go to **Settings → Devices & services → Add integration → Jarvis**.
5. Enter the backend URL and API key.
6. Select **Jarvis** as the conversation agent in the desired Assist pipeline.
7. In **Settings → Voice assistants → Expose**, expose only the entities Jarvis
   should be allowed to read or control.

## Manual installation

Copy `custom_components/jarvis` to
`/config/custom_components/jarvis` and restart Home Assistant.

## Scope

The integration forwards conversation text, recent chat history, and Home
Assistant's built-in Assist tools to the Jarvis backend. Tool calls are validated
and executed by Home Assistant, not by the backend. Only entities exposed to Assist
are available, and Home Assistant does not expose administrative operations through
this API.

Start with low-risk entities such as lights, sensors, scenes, and selected switches.
Do not expose locks, garage doors, or alarm panels until the setup has been tested
carefully.

The public repository does not contain backend source code, deployment
configuration, credentials, or API keys.
