# API key handling

Each algorithm reads only its own provider's environment variable when its Processing parameters are initialized:

| Provider | Environment variable |
|---|---|
| Black Forest Labs | `BFL_API_KEY` |
| Google Gemini | `GEMINI_API_KEY` |
| OpenAI | `OPENAI_API_KEY` |

`BaseAIAlgorithm.initAlgorithm()` uses `environ.get(self._api_key_env_var(), "")`. Each provider overrides `_api_key_env_var()`. There is no cross-provider fallback; `PROMPTMAP_API_KEY` is only the base class's generic default, not a fallback for these tools.

Set the appropriate variable in the environment that launches QGIS, or paste a key into the Processing dialog. A variable changed after QGIS starts will not update the running process: restart QGIS with the new environment. Desktop launchers may not inherit shell exports, including on macOS.

## Security

The plugin does not bundle keys, write them into GeoPackage metadata, or maintain a credential store. Environment variables are not encrypted storage, however, and QGIS Processing parameters can appear in execution logs and history. Treat logs and screenshots as potentially sensitive; redact credentials before sharing. Never commit keys, put them into benchmark JSON, or copy them into a public website export. Revoke keys that have been shared.

OpenAI API access and billing are separate from ChatGPT subscriptions. Model access may require organization verification. No automatic retries are made by the OpenAI image client; a timeout or local cancellation does not prove that provider-side processing or billing stopped.

## Tests

`tests/test_openai.py` checks provider-specific prefill using dummy values. The offline API tests never require real credentials or incur API charges. Interactive key handling on macOS and encrypted QGIS Authentication Manager storage have not been implemented or verified.
