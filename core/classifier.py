"""Command classifier to route requests to specialized agents."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class TaskType(str, Enum):
    CODE_GENERATION = "code_generation"
    EMAIL_WRITING = "email_writing"
    GENERAL_AI = "general_ai"


@dataclass
class TaskClassifier:
    """Keyword-based classifier for routing commands."""

    code_keywords = (
        "generate code",
        "write code",
        "write some code",
        "code snippet",
        "python function",
        "typescript function",
        "javascript function",
        "implement",
        "algorithm",
        "build me an api",
        "api endpoint",
        "component code",
        "unit test",
        "refactor this",
        # Voice-friendly patterns (e.g. "python code for leap year")
        "python code",
        "javascript code",
        "java code",
        "c code",
        "c++ code",
        "c# code",
        "html code",
        "css code",
        "sql code",
        "code for",
        "program for",
        "write a program",
        "write program",
        "write a python program",
        "write python program",
    )

    email_keywords = (
        "email",
        "e-mail",
        "write mail",
        "compose mail",
        "compose email",
        "draft mail",
        "draft email",
        "send mail",
        "send email",
        "professional email",
    )

    def classify(self, text: str) -> TaskType:
        text_lower = text.lower().strip()

        if any(keyword in text_lower for keyword in self.email_keywords):
            return TaskType.EMAIL_WRITING

        # Treat common "X code for Y" voice phrases as code generation
        if any(keyword in text_lower for keyword in self.code_keywords):
            return TaskType.CODE_GENERATION
        # Extra heuristic: if the user clearly mentions "code" plus a language,
        # assume they want code even if the exact keyword isn't matched.
        if "code" in text_lower:
            lang_markers = [
                "python", "javascript", "js", "typescript", "java",
                "c#", "c++", "c language", "html", "css", "sql",
                "bash", "shell",
            ]
            if any(lang in text_lower for lang in lang_markers):
                return TaskType.CODE_GENERATION

        if any(keyword in text_lower for keyword in self.code_keywords):
            return TaskType.CODE_GENERATION

        # Enhanced detection for general AI questions
        question_keywords = [
            "what is", "what are", "who is", "who are", "how to", "how do",
            "explain", "tell me about", "define", "meaning of", "what does",
            "why", "when", "where", "can you explain", "what do",
            "difference between", "compare", "advantages", "benefits"
        ]
        if any(q in text_lower for q in question_keywords):
            return TaskType.GENERAL_AI

        return TaskType.GENERAL_AI


classifier = TaskClassifier()


def classify_task(text: str) -> TaskType:
    """Convenience helper for callers."""
    return classifier.classify(text)

