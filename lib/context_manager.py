"""
Compresión de contexto para conversaciones largas.
Cuando el historial supera el umbral configurado, resume el 70% más antiguo con el LLM.
Los parámetros se leen desde lib.config.cfg.context.
"""
import json
from strands import Agent
from lib.config import cfg

_SUMMARY_PROMPT = """Eres un asistente que resume conversaciones técnicas de desarrollo web.
Resume la siguiente conversación entre un usuario y un agente de código.
Incluye: qué archivos se crearon/modificaron, qué comandos se ejecutaron,
qué errores hubo y cómo se resolvieron, y el estado actual del proyecto.
Sé conciso pero no pierdas información crítica sobre la estructura del proyecto."""


def count_tokens(messages: list) -> int:
    """Estima el número de tokens en el historial de mensajes.

    Usa la aproximación configurada en cfg.context.chars_per_token.

    Args:
        messages: Lista de mensajes en formato Strands/Bedrock.

    Returns:
        Número estimado de tokens.
    """
    chars_per_token = cfg.context.chars_per_token
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
                content = block["toolResult"].get("content", "")
                total_chars += len(json.dumps(content) if not isinstance(content, str) else content)
    return total_chars // chars_per_token


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
                lines.append(f"[{role}][tool:{tu.get('name', '?')}]: {json.dumps(tu.get('input', {}))[:300]}")
            elif "toolResult" in block:
                content = block["toolResult"].get("content", "")
                if isinstance(content, list):
                    content = json.dumps(content)
                lines.append(f"[{role}][result]: {str(content)[:300]}")
    return "\n".join(lines)


def compress_context(messages: list, model) -> list:
    """Comprime el porcentaje más antiguo del historial en un resumen.

    El porcentaje se configura en cfg.context.compression_ratio.

    Args:
        messages: Historial completo de mensajes.
        model: Instancia del modelo Strands para generar el resumen.

    Returns:
        Lista reducida: [resumen_user, resumen_assistant] + mensajes_recientes.
    """
    if len(messages) < 4:
        return messages

    ratio = cfg.context.compression_ratio
    split = int(len(messages) * ratio)
    if split % 2 != 0:
        split += 1  # Asegurar corte en par user/assistant

    old_msgs = messages[:split]
    recent_msgs = messages[split:]

    conversation_text = _serialize_for_summary(old_msgs)

    summarizer = Agent(model=model, system_prompt=_SUMMARY_PROMPT)
    response = summarizer(f"Resume esta conversación:\n\n{conversation_text}")
    summary_text = str(response)

    return [
        {"role": "user", "content": [{"text": f"[RESUMEN DE CONVERSACIÓN ANTERIOR]\n{summary_text}"}]},
        {"role": "assistant", "content": [{"text": "Entendido. Tengo el contexto de lo trabajado anteriormente. ¿En qué continúo?"}]},
    ] + recent_msgs


def maybe_compress(agent: Agent, model) -> None:
    """Comprime el historial del agente si supera el umbral configurado.

    Modifica agent.messages in-place si se requiere compresión.

    Args:
        agent: Instancia del agente Strands con historial activo.
        model: Instancia del modelo para generar el resumen.
    """
    max_tokens = cfg.context.max_tokens
    tokens = count_tokens(agent.messages)
    if tokens > max_tokens:
        print(f"⚠️  Contexto: {tokens} tokens > {max_tokens}. Comprimiendo...")
        agent.messages = compress_context(agent.messages, model)
        new_tokens = count_tokens(agent.messages)
        print(f"✅  Comprimido: {tokens} → {new_tokens} tokens")
