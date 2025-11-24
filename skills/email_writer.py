"""Email writing agent using the local Ollama LLM."""

from __future__ import annotations

from dataclasses import dataclass

from llm.ollama_client import OllamaClient, OllamaClientError


EMAIL_TEMPLATE = (
    "You are an expert communications assistant. "
    "Compose a concise, professional email that follows the user's request.\n"
    "Rules:\n"
    "- Always include a clear Subject line.\n"
    "- Start with an appropriate greeting.\n"
    "- Use short paragraphs (max 3 sentences each).\n"
    "- Close with a polite sign-off and placeholder name unless provided.\n"
    "- Keep tone confident, friendly, and solution-oriented."
)


@dataclass
class EmailWritingAgent:
    ollama_client: OllamaClient

    def compose(self, instruction: str) -> str:
        body = self.ollama_client.write_email(
            f"{EMAIL_TEMPLATE}\n\nUser instructions:\n{instruction.strip()}",
        )
        return self._format_response(instruction, body)

    @staticmethod
    def _format_response(request: str, email_text: str) -> str:
        header = "✉️ **Email Writing Agent**\n"
        details = f"Request: {request.strip()}\n"
        return f"{header}{details}\n{email_text.strip()}"


_agent = EmailWritingAgent(ollama_client=OllamaClient())


def handle(command: str) -> str:
    """Public interface for the brain."""
    try:
        return _agent.compose(command)
    except OllamaClientError as exc:
        return f"❌ Email drafting failed: {exc}"
    except Exception as exc:
        return f"❌ Unexpected error while drafting email: {exc}"

