import pytest

from core import brain
from core.classifier import TaskType, classify_task


@pytest.fixture(autouse=True)
def disable_persona(monkeypatch):
    """Ensure stylization does not hit the LLM during tests."""
    monkeypatch.setattr(brain, "stylize_response", lambda command, text: text)


def test_classifier_detects_code_generation():
    assert classify_task("please generate code for a rest api") == TaskType.CODE_GENERATION


def test_classifier_detects_email():
    assert classify_task("draft an email to postpone the meeting") == TaskType.EMAIL_WRITING


def test_code_generation_routes_to_agent(monkeypatch):
    monkeypatch.setattr(brain.code_generator, "handle", lambda cmd: "CODE_AGENT")
    monkeypatch.setattr(brain.email_writer, "handle", lambda cmd: "EMAIL_AGENT")
    monkeypatch.setattr(brain, "ask_gpt", lambda cmd: "FALLBACK")
    result = brain.process_command("generate code for a fibonacci function")
    assert "CODE_AGENT" in result


def test_email_writing_routes_to_agent(monkeypatch):
    monkeypatch.setattr(brain.email_writer, "handle", lambda cmd: "EMAIL_AGENT")
    monkeypatch.setattr(brain.code_generator, "handle", lambda cmd: "CODE_AGENT")
    monkeypatch.setattr(brain, "ask_gpt", lambda cmd: "FALLBACK")
    result = brain.process_command("write an email to my team about the deadline")
    assert "EMAIL_AGENT" in result


def test_general_prompt_routes_to_local_llm(monkeypatch):
    monkeypatch.setattr(brain, "_general_ai_response", lambda cmd: "GENERAL_AGENT")
    monkeypatch.setattr(brain, "ask_gpt", lambda cmd: "FALLBACK")
    result = brain.process_command("explain what an api gateway does")
    assert "GENERAL_AGENT" in result
