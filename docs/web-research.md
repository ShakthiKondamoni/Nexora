# Nexora Web & Research

## Setup

1. Start a self-hosted SearXNG instance and enable its JSON search format. The core provider requires no paid API key.
2. In Nexora, open **Settings → Web & Research**, enter the instance base URL, choose a default result count and timeout, test the connection, then save. A secret-free example is in `docs/searxng-provider.example.json`.
3. In chat, choose **Off**, **Search first**, or **Automatic**. Off stays on the existing local Ollama/context path. Search first supplies extracted sources to the chosen model. Automatic advertises `web_search` and `web_fetch` to Ollama and recommends Search first if the model rejects native tools.

## Security and source handling

Fetched pages are restricted to public HTTP(S) on standard ports. Nexora resolves and pins public IPs, revalidates every redirect, caps time/bytes/text/redirects/pages/concurrency, and rejects local/private/reserved/metadata destinations. Only readable HTML, plain text, and PDF text are accepted. Login, paywall, CAPTCHA and access restrictions are not bypassed. Retrieved content is untrusted; it cannot change system policy or authorize unrelated tools. Extracted HTML is rendered as escaped text/Markdown.

Citations are assigned only to sources retrieved in that chat turn and stored with the assistant message. Source cards show domain, retrieval time, publication date when found, full-page versus snippet-only status, and a readable preview. Saving is explicit and reuses the existing Knowledge Base ingest/index/dedup service.

Search provider adapters are registered in `backend/services/web_research_service.py`; SearXNG is the included no-key provider. Keep provider URLs and any future credentials server-side.

## Verification

Run `python -m compileall -q backend tests` and `python -m unittest discover -s tests/unit -p 'test_web_research.py'`. The included unit tests mock tool cycles and test URL validation, HTML extraction, citation filtering, and call bounds. Live Ollama, SearXNG, browser interaction, authentication, PDF ingestion, cancellation, theme rendering, and actual Knowledge Base save/index behavior require a configured local install and are not represented as live-tested here. Screenshots in `docs/screenshots/` are static UI preview mockups, not captures of a live integration.
