---
inclusion: always
---

## Project Overview

This is a Python-based autonomous coding agent (`agent-full-stack`) that receives natural language instructions and generates complete Next.js web applications. It uses AWS Bedrock (Amazon Nova Pro) as the LLM, E2B Code Interpreter as the sandbox, and Gradio or CLI as the interface.

## Architecture

```
main.py                  ← Entry point
lib/
  bedrock_client.py      ← LLM client + Bedrock response normalization
  sbx_tools.py           ← Filesystem/sandbox tools (execute_code, read_file, write_file, etc.)
  context_manager.py     ← Context compression (token counting + summarization)
  schemas.py             ← Tool schemas in Bedrock/OpenAI function-calling format
  agent.py               ← Main agent loop with tool dispatch and compression
  prompts.py             ← System prompts
ui/
  gradio_app.py          ← Optional Gradio chat interface
tests/                   ← Unit and integration tests
```

## Language & Style

- All code is Python 3.12+
- Use type hints on all function signatures
- Docstrings on all public functions
- Keep functions focused and small; avoid side effects where possible
- The project language for comments, docstrings, and user-facing strings is Spanish

## Key Conventions

### Tool Functions (`lib/sbx_tools.py`)
- Every tool function returns a plain `dict` with consistent keys
- Raise `ToolError` for expected/recoverable errors (file not found, bad path, etc.)
- Never raise raw exceptions from tool functions — let `execute_tool()` catch unexpected ones
- Use `sbx.files.write()` directly for file writes instead of generating Python code with `repr(content)` to avoid escaping issues
- Always include a `truncated` flag when returning partial content
- Cap reads at `MAX_READ_SIZE = 50_000` chars; cap writes at `MAX_WRITE_SIZE = 1_000_000` chars

### Tool Dispatcher (`execute_tool`)
- Central dispatcher parses JSON args, looks up the tool, calls it, and catches both `ToolError` and unexpected exceptions
- Returns `{"error": "..."}` for all failure cases so the LLM can recover

### Context Manager (`lib/context_manager.py`)
- Token estimation: `total_chars // 4` (1 token ≈ 4 chars)
- Compression threshold: `MAX_TOKENS = 40_000`
- Compress the oldest 70% of messages (`COMPRESSION_RATIO = 0.70`) into a single LLM-generated summary
- Always split at an even index to avoid cutting mid-exchange
- Compressed history is represented as two synthetic messages: a `[RESUMEN]` user message and a short assistant acknowledgment

### Agent Loop (`lib/agent.py`)
- Call `maybe_compress()` before every LLM call
- Append the assistant's `bedrock_message()` to history before processing tool calls
- Collect all tool results in a single `user` message (Bedrock multi-tool pattern)
- Default `max_steps = 30` for web dev tasks
- Return `(messages, last_text)` so callers can continue the conversation

### Bedrock Client (`lib/bedrock_client.py`)
- Normalize all Bedrock responses into `_BedrockResponse` with `.output`, `.output_text`, and `.bedrock_message()`
- Use `inferenceConfig` with `temperature=0.2` and `maxTokens=4096`
- Handle Bedrock exceptions explicitly; never let raw boto3 errors surface to the agent loop

### Schemas (`lib/schemas.py`)
- All tool schemas follow the Bedrock/OpenAI function-calling format: `{"type": "function", "name": ..., "description": ..., "parameters": {...}}`
- Set `"additionalProperties": False` on all parameter objects
- Mark only truly required fields in `"required"`

## Testing

- Unit tests live in `tests/` and cover each tool function individually
- Integration tests cover the full agent loop with a real or mocked sandbox
- Use `pytest`; run with `pytest tests/`
- Tests for `ToolError` propagation must assert the exact error type, not just a truthy error key

## Environment & Dependencies

- Dependencies managed via `pyproject.toml`; runtime deps go in `[project].dependencies`
- new packages are added using uv add <package-name>
- Secrets (AWS credentials, E2B API key) via `.env` file or environment variables — never hardcoded
- Python version pinned in `.python-version`
- only use powershell commands, linux commands tend to fail in windows environment

## What the Agent Generates

The agent targets Next.js 14+ with App Router, TypeScript, and Tailwind CSS. When writing or reviewing generated Next.js code, follow these conventions:
- Use React Server Components by default; add `"use client"` only when necessary
- Write complete files with `write_file` — no partial diffs
- Always verify compilation with `npx next build` or `npx tsc --noEmit` after significant changes
- Read existing files before modifying them
