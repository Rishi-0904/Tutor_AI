"""
expert_service.py
-----------------
Subject-specific LoRA Expert abstraction layer for TutorAI.

Responsibilities:
  - Detect whether a question is numerical or conceptual (pure regex, zero model calls)
  - Provide a unified Expert interface: generate(question, history, context) -> ExpertResult
  - ExpertRegistry singleton: maps subject -> appropriate expert at startup
  - Confidence heuristic scoring
  - Automatic fallback to GeminiTutor when confidence < CONFIDENCE_THRESHOLD
"""

from __future__ import annotations

import re
import json
import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any

# ─────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────

CONFIDENCE_THRESHOLD = 0.35

# Signals that strongly suggest a problem-solving / numerical question
_NUMERICAL_PATTERNS = [
    r"\b(calculate|find|solve|compute|determine|evaluate|prove|derive)\b",
    r"\b(how much|how many|what is the value|what will be)\b",
    r"\b\d+\.?\d*\s*(m/?s\b|kg\b|N\b|J\b|eV\b|mol\b|Pa\b|°C\b|rad\b|s\b|cm\b|km\b|W\b|A\b|V\b|T\b|Hz\b|nm\b)",
    r"=\s*[\?]",                     # "= ?" pattern
    r"\(\s*[A-D]\s*\)",              # MCQ options marker
    r"\\frac|\\sqrt|\\int|\\sum|\\prod|\\lim",   # LaTeX math operators
    r"\b(numerical|value|answer is|result is)\b",
    r"\b(ratio|magnitude|distance|speed|energy|momentum|force|charge|voltage|resistance)\s+(of|is|=)\b",
    r"\b(mcq|multiple choice|jee|neet)\b",
]

# Signals that strongly suggest an explanation / conceptual question
_CONCEPTUAL_PATTERNS = [
    r"\b(explain|why|what is|describe|define|tell me|teach me|give intuition|elaborate)\b",
    r"\b(difference between|compare|contrast|how does|what happens|reason|mechanism)\b",
    r"\b(concept|theory|principle|law|postulate|theorem)\b",
    r"\b(intuitively|intuitively speaking|conceptually)\b",
]

_NUMERICAL_RE   = [re.compile(p, re.IGNORECASE) for p in _NUMERICAL_PATTERNS]
_CONCEPTUAL_RE  = [re.compile(p, re.IGNORECASE) for p in _CONCEPTUAL_PATTERNS]

# ─────────────────────────────────────────────────────────────
# QUESTION TYPE DETECTOR
# ─────────────────────────────────────────────────────────────

def detect_question_type(question: str) -> str:
    """
    Returns "numerical", "conceptual", or "ambiguous".

    Strategy:
      - Count regex hits for numerical signals vs conceptual signals
      - Whichever side has more hits wins
      - Tie or both-zero → "ambiguous" (Gemini handles it)
    """
    num_hits  = sum(1 for pat in _NUMERICAL_RE  if pat.search(question))
    conc_hits = sum(1 for pat in _CONCEPTUAL_RE if pat.search(question))

    if num_hits > conc_hits:
        return "numerical"
    if conc_hits > num_hits:
        return "conceptual"
    return "ambiguous"


# ─────────────────────────────────────────────────────────────
# CONFIDENCE SCORER
# ─────────────────────────────────────────────────────────────

_CONFUSION_RE = re.compile(
    r"(i don.t know|i cannot|i.m not sure|i am unable|i can.t|"
    r"unfortunately|i apologize|as an ai|as a language model)",
    re.IGNORECASE
)

def compute_confidence(answer: str) -> float:
    """
    Heuristic confidence score for a LoRA-generated answer.
    Range: [0.0, 1.0]

    Since Phi-4-mini with 4-bit quantisation does not expose logprobs via
    generate(), we derive confidence from structural signals:
      +0.25  answer contains \\boxed{...}            (has a final answer)
      +0.15  answer contains <think>...</think>       (shows reasoning)
      +0.10  answer length > 80 characters            (substantive)
      -0.40  confusion phrase detected                (model uncertain)
       0.50  base score
       0.00  empty answer
    """
    if not answer or not answer.strip():
        return 0.0

    score = 0.50

    if re.search(r"\\boxed\{", answer):
        score += 0.25
    if re.search(r"<think>.*?</think>", answer, re.DOTALL):
        score += 0.15
    if len(answer.strip()) > 80:
        score += 0.10
    if _CONFUSION_RE.search(answer):
        score -= 0.40

    return round(min(max(score, 0.0), 1.0), 3)


# ─────────────────────────────────────────────────────────────
# EXPERT RESULT
# ─────────────────────────────────────────────────────────────

@dataclass
class ExpertResult:
    answer: str
    reasoning_steps: str   # extracted <think>...</think> block
    final_result: str      # extracted \boxed{...} content
    confidence: float
    expert_used: str       # "physics_grpo" | "chemistry_grpo" | "math_grpo" | "gemini"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _extract_think(text: str) -> str:
    """Extract content inside <think>...</think> tags."""
    m = re.search(r"<think>(.*?)</think>", text, re.DOTALL | re.IGNORECASE)
    return m.group(1).strip() if m else ""


def _extract_boxed(text: str) -> str:
    """Extract content inside \\boxed{...} — handles nested braces."""
    idx = text.find(r"\boxed{")
    if idx == -1:
        return ""
    start = idx + len(r"\boxed{")
    depth = 1
    i = start
    while i < len(text) and depth > 0:
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
        i += 1
    return text[start : i - 1].strip()


# ─────────────────────────────────────────────────────────────
# EXPERT ABSTRACTIONS
# ─────────────────────────────────────────────────────────────

class BaseExpert(ABC):
    """Common interface all experts must implement."""

    @abstractmethod
    def generate(
        self,
        question: str,
        history: list,
        learning_context: Optional[str] = None,
    ) -> ExpertResult:
        ...


class LoRAExpert(BaseExpert):
    """
    Wraps the existing generate_answer() from llm_service.
    Responsible for:
      - Hot-swapping the LoRA adapter to the correct subject
      - Parsing <think> and \\boxed{} from raw output
      - Computing confidence
      - Returning a structured ExpertResult
    """

    def __init__(self, subject: str, adapter_name: str):
        self.subject = subject           # "physics" | "chemistry" | "mathematics"
        self.adapter_name = adapter_name # same as subject, maps to PEFT adapter name
        self._expert_label = f"{subject}_lora"

    def generate(
        self,
        question: str,
        history: list,
        learning_context: Optional[str] = None,
    ) -> ExpertResult:
        # Import here to avoid circular imports and ensure models are loaded
        from app.services.llm_service import (
            _peft_model, _tokenizer, _is_loaded,
            SUBJECT_SYSTEM_PROMPTS, extract_topic_tags
        )
        import torch

        if not _is_loaded or _peft_model is None or _tokenizer is None:
            print(f"[Expert:{self.subject}] Models not loaded, returning empty result")
            return ExpertResult(
                answer="", reasoning_steps="", final_result="",
                confidence=0.0, expert_used=self._expert_label
            )

        # Switch to our adapter
        if hasattr(_peft_model, "set_adapter"):
            try:
                _peft_model.set_adapter(self.adapter_name)
                print(f"[Expert] Switched adapter → {self.adapter_name}")
            except ValueError as e:
                print(f"[Expert] Adapter swap failed ({e}), using current adapter")

        sys_prompt = SUBJECT_SYSTEM_PROMPTS.get(self.subject, SUBJECT_SYSTEM_PROMPTS["general"])

        # Inject learning context if available
        if learning_context:
            sys_prompt = f"{sys_prompt}\n\n[Student Context]:\n{learning_context}"

        # Build prompt
        prompt = f"System: {sys_prompt}\n"
        for msg in history:
            role = getattr(msg, "role", "user")
            content = getattr(msg, "content", str(msg))
            prompt += f"{role.capitalize()}: {content}\n"
        prompt += f"User: {question}\nAssistant:"

        try:
            inputs = _tokenizer(prompt, return_tensors="pt").to(_peft_model.device)
            with torch.no_grad():
                outputs = _peft_model.generate(
                    **inputs,
                    max_new_tokens=1024,
                    temperature=0.3,
                    top_p=0.9,
                    do_sample=True,
                    pad_token_id=_tokenizer.pad_token_id,
                )
            raw = _tokenizer.decode(
                outputs[0][inputs.input_ids.shape[1]:],
                skip_special_tokens=True
            ).strip()
        except Exception as e:
            print(f"[Expert:{self.subject}] Generation error: {e}")
            return ExpertResult(
                answer="", reasoning_steps="", final_result="",
                confidence=0.0, expert_used=self._expert_label
            )

        reasoning = _extract_think(raw)
        final     = _extract_boxed(raw)
        conf      = compute_confidence(raw)

        print(f"[Expert] {self._expert_label} answered | conf={conf:.2f} | boxed={bool(final)} | len={len(raw)}")

        return ExpertResult(
            answer=raw,
            reasoning_steps=reasoning,
            final_result=final,
            confidence=conf,
            expert_used=self._expert_label,
        )


class GeminiTutor(BaseExpert):
    """
    Direct Gemini call — used for conceptual questions and as a fallback.
    Confidence is always 1.0 (Gemini is the trusted fallback).
    Returns a bare answer string so generate_answer_stream() can format it.
    """

    def generate(
        self,
        question: str,
        history: list,
        learning_context: Optional[str] = None,
    ) -> ExpertResult:
        # We return empty here; the actual Gemini call happens in run_agent_stream
        # via generate_answer_stream() as before. This class exists for registry
        # completeness and explicit logging.
        print(f"[Expert] gemini selected for this query")
        return ExpertResult(
            answer="",          # signal: Gemini will handle in stream
            reasoning_steps="",
            final_result="",
            confidence=1.0,
            expert_used="gemini",
        )


# ─────────────────────────────────────────────────────────────
# EXPERT REGISTRY
# ─────────────────────────────────────────────────────────────

class ExpertRegistry:
    """
    Singleton registry.  Maps subject name → Expert instance.
    Call ExpertRegistry.initialize() once at startup (inside FastAPI lifespan).
    Then call ExpertRegistry.get() anywhere to retrieve the singleton.
    """

    _instance: Optional["ExpertRegistry"] = None

    def __init__(self):
        self._experts: Dict[str, BaseExpert] = {}
        self._gemini = GeminiTutor()
        self.threshold = CONFIDENCE_THRESHOLD

    @classmethod
    def initialize(cls) -> "ExpertRegistry":
        """Create and store the singleton. Call once at app startup."""
        if cls._instance is not None:
            return cls._instance

        reg = cls()
        reg._experts = {
            "physics":     LoRAExpert("physics",     "physics"),
            "chemistry":   LoRAExpert("chemistry",   "chemistry"),
            "mathematics": LoRAExpert("mathematics", "mathematics"),
            # Alias
            "maths":       LoRAExpert("mathematics", "mathematics"),
            "math":        LoRAExpert("mathematics", "mathematics"),
            "general":     reg._gemini,
        }
        cls._instance = reg
        print("[ExpertRegistry] Initialized with 3 LoRA experts + GeminiTutor")
        return reg

    @classmethod
    def get(cls) -> "ExpertRegistry":
        if cls._instance is None:
            return cls.initialize()
        return cls._instance

    def get_expert(self, subject: str) -> BaseExpert:
        """
        Return the appropriate expert for a subject.
        Falls back to GeminiTutor if subject is unknown.
        """
        return self._experts.get(subject.lower(), self._gemini)

    def get_gemini(self) -> GeminiTutor:
        return self._gemini
