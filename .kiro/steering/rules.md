---
inclusion: always
---

## Project Overview

This is a Python-based autonomous coding agent (`agent-full-stack`) that receives natural language instructions and generates complete Next.js web applications. It uses **Strands Agents SDK** as the orchestration framework, **AWS Bedrock** (Amazon Nova Pro) as the LLM, **E2B Code Interpreter** as the secure sandbox, and optionally **Gradio** or CLI as the interface.

**Core principle:** Use Strands Agents to handle orchestration (agent loop, tool dispatch, LLM calls, message management) and E2B for sandboxed code execution. Never reimplement what Strands already provides.

## Architecture

```
main.py                  ← Entry point: creates Strands Agent + E2B sandbox
lib/
  tools.py               ← All tools using @tool decorator (E2B as backend)
  context_manager.py     ← Context compression (token counting + summarization)
  prompts.py             ← System prompts
ui/
  gradio_app.py          ← Optional Gradio chat interface
tests/                   ← Unit and integration tests
```

### What Strands Handles (DO NOT reimplement)

| Concern                        | Strands provides it | You write it |
| ------------------------------ | ------------------- | ------------ |
| Agent loop (think → act → observe) | ✅                  | ❌            |
| Tool dispatch                  | ✅                  | ❌            |
| Tool schema generation         | ✅ (from @tool)     | ❌            |
| LLM calls to Bedrock           | ✅ (BedrockModel)   | ❌            |
| Message history management     | ✅                  | ❌            |
| Response normalization         | ✅                  | ❌            |
| Sandbox execution              | ❌                  | ✅ (E2B)      |
| Context compression            | ❌                  | ✅ (manual)   |
| System prompt                  | ❌                  | ✅            |

### Files You Do NOT Need (Strands replaces them)

Do **not** create these — they exist in the example notebooks but Strands eliminates them:

- ~~`bedrock_client.py`~~ → `BedrockModel` from `strands.models.bedrock`
- ~~`schemas.py`~~ → `@tool` decorator auto-generates schemas from docstrings + type hints
- ~~`agent.py` with manual while-loop~~ → `Agent()` class handles the loop
- ~~`_BedrockResponse` / `_TextPart` / `_ToolUsePart`~~ → Strands normalizes internally
- ~~`execute_tool()` dispatcher~~ → Strands dispatches automatically

## Language & Style

- All code is Python 3.12+
- Use type hints on all function signatures
- Docstrings on all public functions (Strands uses them to generate tool descriptions for the LLM)
- Keep functions focused and small; avoid side effects where possible
- The project language for comments, docstrings, and user-facing strings is Spanish

## Strands Agent Setup

### Model Configuration

```python
from strands.models.bedrock import BedrockModel

model = BedrockModel(
    model_id="amazon.nova-pro-v1:0",
    region_name="us-east-1",
    temperature=0.2,
    max_tokens=4096,
)
```

- Always set `temperature=0.2` for code generation (precision over creativity)
- Use `BedrockModel` — never create raw `boto3` clients for the agent LLM
- AWS credentials are read from environment variables automatically by `BedrockModel`

### Agent Instantiation

```python
from strands import Agent

agent = Agent(
    model=model,
    system_prompt=SYSTEM_PROMPT,
    tools=[execute_code, list_directory, read_file, write_file, ...],
    max_handler_calls=30,
)
```

- `max_handler_calls=30` for web dev tasks (equivalent to `max_steps` in manual loop)
- Pass tool **functions** directly — Strands reads `@tool` metadata automatically
- For multi-turn conversations, call `agent("next instruction")` repeatedly; Strands maintains history internally

### Accessing Conversation History (for compression)

When you need to inspect or compress the conversation, access it via:

```python
messages = agent.messages
```

After compression, replace it:

```python
agent.messages = compressed_messages
```

## Key Conventions

### Tool Functions (`lib/tools.py`)

Every tool uses the `@tool` decorator from Strands:

```python
from strands import tool

@tool
def my_tool(param: str, optional_param: int = 10) -> dict:
    """One-line description for the LLM.

    Args:
        param: Description of param (LLM sees this)
        optional_param: Description with default

    Returns:
        Dict with result keys
    """
    ...
```

**Critical rules for @tool functions:**

- The **docstring** becomes the tool description the LLM sees — write it clearly and in English (Bedrock parses it for function calling)
- **Type hints** on all parameters are mandatory — Strands generates the JSON schema from them
- **Args section** in the docstring maps to parameter descriptions — always include it
- Return a plain `dict` with consistent keys
- For expected/recoverable errors, return `{"error": "..."}` so the LLM can retry
- For unexpected errors, let them propagate — Strands catches and reports them to the LLM
- The E2B `Sandbox` instance (`sbx`) is accessed as a **module-level global** initialized at startup, not passed as a parameter (Strands tools only receive

# Final notes:
- In `legacy/` directory there are some examples that can be taken as references but they are not optimized and they don't use strands agents framework.
- In `docs\WorkPackages.md`  there are some guiding ideas, they are not mandatory.
- THe final and ultiamte goal of the project is to satisfy the `docs\FinalGoal.md` document.