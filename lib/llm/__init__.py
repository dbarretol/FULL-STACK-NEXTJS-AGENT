"""
Módulo LLM — re-exporta build_model() desde factory.py.
Uso: from lib.llm import build_model
"""
from lib.llm.factory import build_model

__all__ = ["build_model"]
