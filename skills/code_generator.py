"""Code generation agent powered by local Ollama models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from llm.ollama_client import OllamaClient, OllamaClientError


LANGUAGE_HINTS = {
    "python": "Python",
    "py ": "Python",
    "javascript": "JavaScript",
    "js ": "JavaScript",
    "typescript": "TypeScript",
    "react": "React (JavaScript)",
    "node": "Node.js",
    "java ": "Java",
    "c#": "C#",
    "c++": "C++",
    "html": "HTML",
    "css": "CSS",
    "sql": "SQL",
    "bash": "Bash",
    "shell": "Shell",
}


@dataclass
class CodeGenerationAgent:
    ollama_client: OllamaClient

    def generate(self, instruction: str) -> str:
        """Generate code for the provided instruction."""
        language_hint = self._detect_language(instruction)
        code = self.ollama_client.generate_code(instruction, language_hint)
        return self._format_response(instruction, code, language_hint)

    @staticmethod
    def _detect_language(text: str) -> Optional[str]:
        lowered = text.lower()
        for keyword, language in LANGUAGE_HINTS.items():
            if keyword in lowered:
                return language
        return None

    @staticmethod
    def _format_response(request: str, code: str, language_hint: Optional[str]) -> str:
        header = "🧠 **Code Generation Agent**\n"
        details = f"Request: {request.strip()}\n"
        if language_hint:
            details += f"Language: {language_hint}\n"
        return f"{header}{details}\n{code.strip()}"


_agent = CodeGenerationAgent(ollama_client=OllamaClient())


def handle(command: str) -> str:
    """Public interface used by the brain."""
    try:
        return _agent.generate(command)
    except OllamaClientError as exc:
        return f"❌ Code generation failed: {exc}"
    except Exception as exc:
        return f"❌ Unexpected error during code generation: {exc}"

