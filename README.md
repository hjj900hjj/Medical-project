# Medical Arrangement - LLM Terminal Chat

An English terminal conversation about symptoms and preliminary impressions. There is no question count or automatic end after an assessment. The patient decides when to leave.

## Setup and run

Paste your OpenAI API key into the api_key field in config.json, then run start.bat or `python cli.py` with Python 3.10+. No third-party packages are required.

```json
{
  "api_key": "PASTE_YOUR_OPENAI_API_KEY_HERE",
  "model": "gpt-4.1-mini"
}
```

A configured file key takes priority; OPENAI_API_KEY is the fallback. config.json contains a plaintext secret and is ignored by Git. Do not share it. The previous max_questions setting is no longer used. Existing credentials are preserved.

## Conversation

Describe symptoms naturally, then continue asking questions or providing details. The assistant can share a tentative explanation and ask relevant follow-ups, including questions about severity and warning signs. It acknowledges missing information in conversation rather than rejecting an assessment because of a readiness flag.

- /assess: ask for a short impression based on the conversation so far; chat remains open afterward.
- /quit or Ctrl+C: end the conversation.
- Assessments are brief conversational paragraphs, with uncertainty, how concerning the symptoms appear and a practical next step. The prompt targets 45-85 words, but does not reject replies for formatting or word count.
- Potential emergencies trigger immediate emergency guidance. The terminal remains open, but the assistant should not delay urgent advice with routine questions.
- Genuine API or malformed-response errors allow manual retry. Declining retry returns to chat; the failed message is not added to history.

There is no application-imposed turn limit. Model context limits, API availability and usage costs still apply. Conversation history is kept only in memory and sent with subsequent requests; it is not written to disk.

## Implementation

cli.py handles terminal interaction. server.py contains configuration, conversational instructions, a small response schema and the OpenAI Responses API client. Despite its historical filename, it does not start a web server. This is direct LLM integration, not RAG. The retained doctor CSV is not used by this flow.

The client follows the [OpenAI Structured Outputs documentation](https://developers.openai.com/api/docs/guides/structured-outputs). Use a model that supports Responses API Structured Outputs. Tests mock API calls; live behavior needs validation with your key.

Patient answers are sent to OpenAI using store=false. The application does not print credentials. This is not a guarantee of zero provider retention. This prototype offers preliminary guidance, not a diagnosis or clinically validated triage.

## Tests

```powershell
..\screen-tutor\.venv\Scripts\python.exe -m unittest -v
```
