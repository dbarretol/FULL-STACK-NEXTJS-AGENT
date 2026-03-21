"""
Compresión de contexto para conversaciones largas.
Cuando el historial supera MAX_TOKENS, resume el 70% más antiguo con el LLM.
"""
import json
from strands import Agent
from strands.models.bedrock import BedrockModel

MAX_TOKENS = 40_000
COMPRESSION_RATIO = 0.70
CHARS_PER_TOKEN = 4  # Aproximación: 1 token ≈ 4 caracteres

_SUMMARY_PROMPT = """Eres un asistente que resume conversaciones técnicas de desarrollo web.
Resume la siguiente conversación entre un usuario y un agente de código.
Incluye: qué archivos se crearon/modificaron, qué comandos se ejecutaron,
qué errores hubo y cómo se resolvieron, y el estado actual del proyecto.
Sé conciso pero no pierdas información crítica sobre la estructura del proyecto."""


def count_tokens(messages: list) -> int:
    """Estima el número de tokens en el historial de mensajes.

    Usa la aproximación de 1 token ≈ 4 caracteres.

    Args:
        messages: Lista de mensajes en formato Strands/Bedrock.

    Returns:
        Número estimado de tokens.
    """
    total_chars = 0
    for msg in messages:
        for block in msg.get("content", []):
            if not isinstance(block, dict):
                continue
            if "text" in block:
                total_chars += len(block["text"])
            elif "toolUse" in block:
                total_chars += len(json.dumps(block["toolUse"]))
            elif "toolResult" in block:
                tr = block["toolResult"]
                content = tr.get("content", "")
                total_chars += len(json.dumps(content) if not isinstance(content, str) else content)
    return total_chars // CHARS_PER_TOKEN


def _serialize_for_summary(messages: list) -> str:
    """Convierte mensajes a texto legible para el LLM de resumen."""
    lines = []
    for msg in messages:
        role = msg["role"]
        for block in msg.get("content", []):
            if not isinstance(block, dict):
                continue
            if "text" in block:
                lines.append(f"[{role}]: {block['text'][:500]}")
            elif "toolUse" in block:
                tu = block["toolUse"]
                inp = json.dumps(tu.get("input", {}))[:300]
                lines.append(f"[{role}][tool:{tu.get('name', '?')}]: {inp}")
            elif "toolResult" in block:
                tr = block["toolResult"]
                # content puede ser lista de bloques o string
                content = tr.get("content", "")
                if isinstance(content, list):
                    content = json.dumps(content)
                lines.append(f"[{role}][result]: {str(content)[:300]}")
    return "\n".join(lines)


def compress_context(messages: list, model: BedrockModel) -> list:
    """Comprime el 70% más antiguo del historial en un resumen.

    Args:
        messages: Historial completo de mensajes.
        model: Instancia BedrockModel para generar el resumen.

    Returns:
        Lista reducida: [resumen_user, resumen_assistant] + mensajes_recientes.
    """
    if len(messages) < 4:
        return messages

    split = int(len(messages) * COMPRESSION_RATIO)
    # Asegurar corte en par user/assistant
    if split % 2 != 0:
        split += 1

    old_msgs = messages[:split]
    recent_msgs = messages[split:]

    conversation_text = _serialize_for_summary(old_msgs)

    # Usar un agente temporal solo para generar el resumen
    summarizer = Agent(model=model, system_prompt=_SUMMARY_PROMPT)
    response = summarizer(f"Resume esta conversación:\n\n{conversation_text}")
    summary_text = str(response)

    compressed = [
        {"role": "user", "content": [{"text": f"[RESUMEN DE CONVERSACIÓN ANTERIOR]\n{summary_text}"}]},
        {"role": "assistant", "content": [{"text": "Entendido. Tengo el contexto de lo trabajado anteriormente. ¿En qué continúo?"}]},
    ]
    return compressed + recent_msgs


def maybe_compress(agent: Agent, model: BedrockModel) -> None:
    """Comprime el historial del agente si supera MAX_TOKENS.

    Modifica agent.messages in-place si se requiere compresión.

    Args:
        agent: Instancia del agente Strands con historial activo.
        model: Instancia BedrockModel para generar el resumen.
    """
    tokens = count_tokens(agent.messages)
    if tokens > MAX_TOKENS:
        print(f"⚠️  Contexto: {tokens} tokens > {MAX_TOKENS}. Comprimiendo...")
        agent.messages = compress_context(agent.messages, model)
        new_tokens = count_tokens(agent.messages)
        print(f"✅  Comprimido: {tokens} → {new_tokens} tokens")
