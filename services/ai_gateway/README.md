# AI Gateway

Future AI and RAG service.

Responsibilities:
- retrieval across approved source tiers
- prompt assembly
- policy enforcement for pedagogical help
- no full solution by default in foundation phases

Run locally:

```bash
export ANTHROPIC_API_KEY=your-key
uvicorn app.main:app --reload --port "${AI_GATEWAY_PORT:-8100}"
```

Mentor responses use the Anthropic SDK directly and fall back to a static pedagogical response if the API key is missing, the request fails, or Claude returns malformed JSON.
