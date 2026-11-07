"""MATRIX Voice Activity Detection (VAD) & Speech Endpointing Subsystem.
"""
from voice.vad.engine import vad_engine, SileroVADEngine

__all__ = ["vad_engine", "SileroVADEngine"]
