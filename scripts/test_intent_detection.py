"""Quick intent-detection regression test."""

import re

def normalize_text(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def keyword_confidence(text: str) -> float:
    keyword_triggers = (
        " song", " music", " youtube", " google", " calculator",
        " notepad", " weather", " reminder", " open ", " launch ",
        " play ", " search ", " find ", " show ", " list ", " email"
    )
    if any(keyword in text for keyword in keyword_triggers):
        return 0.7
    return 0.0

def test_phrase(phrase: str) -> None:
    nl = normalize_text(phrase)
    confidence = keyword_confidence(nl)
    wake_present = "bittu" in nl
    should_process = wake_present or confidence >= 0.6
    print(f"Input: '{phrase}'")
    print(f"  normalized: '{nl}'")
    print(f"  wake_present: {wake_present}")
    print(f"  keyword_confidence: {confidence}")
    print(f"  should_process: {should_process}")
    print()


def main():
    phrases = [
        "Sorry song in YouTube",
        "Bittu play Sorry song in YouTube",
        "open calculator",
        "play lo-fi music on youtube",
    ]
    for phrase in phrases:
        test_phrase(phrase)

if __name__ == "__main__":
    main()

