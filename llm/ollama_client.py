"""Lightweight client for interacting with local Ollama models."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import requests


class OllamaClientError(RuntimeError):
    """Raised when the Ollama client cannot complete a request."""


@dataclass
class OllamaClientConfig:
    base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    default_code_model: str = os.getenv("OLLAMA_CODE_MODEL", "qwen3-coder:30b")
    # Use Qwen3 coder as the default general model as well so *all* AI
    # (general Q&A + coding) runs through the same fast local model by default.
    # You can override this at runtime with OLLAMA_GENERAL_MODEL.
    default_general_model: str = os.getenv("OLLAMA_GENERAL_MODEL", "qwen3-coder:30b")
    request_timeout: int = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "120"))
    temperature: float = float(os.getenv("OLLAMA_TEMPERATURE", "0.3"))
    max_tokens: int = int(os.getenv("OLLAMA_MAX_TOKENS", "2048"))


class OllamaClient:
    """Simple HTTP client around Ollama's /api/generate endpoint."""

    def __init__(self, config: Optional[OllamaClientConfig] = None) -> None:
        self.config = config or OllamaClientConfig()

    def generate(
        self,
        prompt: str,
        *,
        model: Optional[str] = None,
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Generate text for the given prompt."""
        payload: dict[str, object] = {
            "model": model or self.config.default_general_model,
            "prompt": prompt,
            "stream": False,
        }

        if system:
            payload["system"] = system

        options: dict[str, object] = {}
        if temperature is not None:
            options["temperature"] = max(0.0, float(temperature))
        else:
            options["temperature"] = self.config.temperature

        if max_tokens is not None:
            options["num_predict"] = int(max_tokens)
        elif self.config.max_tokens:
            options["num_predict"] = self.config.max_tokens

        if options:
            payload["options"] = options

        try:
            # Use /api/chat for better conversation handling (if supported)
            # Fallback to /api/generate for older Ollama versions
            try:
                # Try chat API first (better for conversational queries)
                if system:
                    chat_payload = {
                        "model": payload["model"],
                        "messages": [
                            {"role": "system", "content": system},
                            {"role": "user", "content": prompt}
                        ],
                        "stream": False,
                        "options": payload.get("options", {})
                    }
                    response = requests.post(
                        f"{self.config.base_url}/api/chat",
                        json=chat_payload,
                        timeout=self.config.request_timeout,
                    )
                    response.raise_for_status()
                    data = response.json()
                    # Extract from chat format
                    if "message" in data and isinstance(data["message"], dict):
                        text = data["message"].get("content", "").strip()
                        if text:
                            return text
                    elif "choices" in data and data["choices"]:
                        text = data["choices"][0].get("message", {}).get("content", "").strip()
                        if text:
                            return text
            except Exception:
                # Fallback to generate API
                pass
            
            # Use generate API
            response = requests.post(
                f"{self.config.base_url}/api/generate",
                json=payload,
                timeout=self.config.request_timeout,
            )
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as exc:
            raise OllamaClientError(f"Ollama request failed: {exc}") from exc

        text = (data.get("response") or "").strip()
        if not text:
            text = (data.get("output") or "").strip()

        if not text:
            raise OllamaClientError("Ollama returned an empty response.")

        return text

    def general_answer(self, prompt: str) -> str:
        """Generate a general-purpose answer using the default general model with improved intelligence."""
        # Enhanced system prompt for better responses
        system_prompt = """You are Bittu, an intelligent personal AI assistant. 
Provide accurate, comprehensive, and well-structured answers. 
For "what is X" questions, include:
1. Clear definition
2. Key features/characteristics  
3. Practical examples or applications
4. Relevant context when helpful

Be thorough but concise. Focus on accuracy and helpfulness."""
        
        return self.generate(
            prompt=prompt,
            model=self.config.default_general_model,
            system=system_prompt,
            temperature=0.2,
            max_tokens=1024,  # Optimized for speed and quality
        )

    def generate_code(self, requirements: str, language_hint: Optional[str] = None) -> str:
        """Generate code using the default code model."""
        language = language_hint or "the most appropriate language"
        prompt = (
            "You generate production-ready code.\n"
            "Requirements:\n"
            f"{requirements}\n\n"
            f"Language preference: {language}.\n"
            "Respond with clean, well-formatted code blocks only. "
            "Add a short comment header if useful."
        )
        return self.generate(
            prompt=prompt,
            model=self.config.default_code_model,
            temperature=0.1,  # Lower temperature for more deterministic code
            max_tokens=2048,  # Allow longer code generation
        )

    def write_email(self, instructions: str) -> str:
        """Generate a professional email using the general model."""
        prompt = (
            "You craft concise, professional emails.\n"
            "Follow the user's instructions below and return a subject line followed by the email body.\n"
            "Use a friendly, confident tone and keep paragraphs short.\n"
            f"Instructions:\n{instructions}"
        )
        return self.generate(
            prompt=prompt,
            model=self.config.default_general_model,
            temperature=0.2,
            max_tokens=1024,
        )

