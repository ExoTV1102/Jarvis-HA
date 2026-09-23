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

## Manual installation

Copy `custom_components/jarvis` to
`/config/custom_components/jarvis` and restart Home Assistant.

## Scope

The integration forwards conversation text and recent chat history to the Jarvis
backend. It does not contain backend source code, deployment configuration,
credentials, or API keys.

