"""myGenAssist (GMA) v2 chat/completions client for natural-language filters."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any, Callable

# Kuratierte, gegen die MGA v2 API verifizierte Modelle (id, Anzeigename).
# id = exakter Wert fuer "model" im chat/completions-Request.
AVAILABLE_MODELS: list[tuple[str, str]] = [
    ("claude-sonnet-5", "Claude Sonnet 5"),
    ("claude-opus-5.5", "Claude Opus 5.5"),
    ("claude-opus-5", "Claude Opus 5"),
    ("gpt-5.4", "GPT-5.4"),
    ("gpt-5.6-terra-ptu", "GPT-5.6 Terra"),
    ("gemini-3.1-pro", "Gemini 3.1 Pro"),
]


def mga_config() -> dict[str, str]:
    key = (os.environ.get("MGA_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN") or "").strip()
    base = (os.environ.get("MGA_BASE_URL_V2") or "https://chat.int.bayer.com/api/v2").rstrip("/")
    model = (os.environ.get("MGA_CHAT_MODEL") or "claude-sonnet-5").strip()
    return {"key": key, "base": base, "model": model}


def _post_chat_completion(
    cfg: dict[str, str],
    model: str,
    messages: list[dict[str, Any]],
    *,
    tools: list[dict] | None,
    max_tokens: int,
    temperature: float,
    timeout: int,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": False,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{cfg['base']}/chat/completions",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {cfg['key']}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data: dict[str, Any] = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="replace")[:400]
        raise RuntimeError(f"MGA HTTP {exc.code}: {err_body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"MGA Netzwerkfehler: {exc.reason}") from exc

    if data.get("error"):
        err = data["error"]
        msg = err.get("message") if isinstance(err, dict) else err
        raise RuntimeError(f"MGA Fehler: {msg}")

    return data


def _extract_text(message: dict[str, Any]) -> str:
    content = message.get("content")
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text") or "")
            elif isinstance(block, str):
                parts.append(block)
        return "".join(parts).strip()
    if isinstance(content, str):
        return content.strip()
    return ""


def chat_completion(
    messages: list[dict[str, str]],
    *,
    model: str | None = None,
    max_tokens: int = 1024,
    temperature: float = 0.0,
    timeout: int = 60,
) -> str:
    """Non-streaming chat completion; returns assistant text content."""

    cfg = mga_config()
    if not cfg["key"]:
        raise RuntimeError(
            "MGA_API_KEY fehlt. Trage den mga-... Token in .env ein (siehe .env.example)."
        )

    data = _post_chat_completion(
        cfg,
        (model or cfg["model"]).strip(),
        messages,
        tools=None,
        max_tokens=max_tokens,
        temperature=temperature,
        timeout=timeout,
    )

    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError("MGA: leere Antwort (keine choices)")

    content = _extract_text(choices[0].get("message", {}))
    if not content:
        raise RuntimeError("MGA: keine Textantwort")

    return content


def chat_with_tools(
    messages: list[dict[str, Any]],
    tools: list[dict],
    execute_tool: Callable[[str, dict], dict],
    *,
    model: str | None = None,
    max_tokens: int = 1024,
    temperature: float = 0.0,
    timeout: int = 60,
    max_rounds: int = 6,
) -> tuple[str, list[dict[str, Any]]]:
    """Fuehrt eine Tool-Calling-Schleife aus: ruft GMA v2 auf, fuehrt angeforderte
    Tools lokal aus, fuettert Ergebnisse zurueck, bis eine Textantwort kommt.
    Gibt (finale Textantwort, vollstaendiger Nachrichtenverlauf inkl. Tool-Aufrufe) zurueck."""

    cfg = mga_config()
    if not cfg["key"]:
        raise RuntimeError(
            "MGA_API_KEY fehlt. Trage den mga-... Token in .env ein (siehe .env.example)."
        )

    zielmodell = (model or cfg["model"]).strip()
    verlauf = list(messages)

    for _ in range(max_rounds):
        data = _post_chat_completion(
            cfg, zielmodell, verlauf, tools=tools, max_tokens=max_tokens, temperature=temperature, timeout=timeout
        )
        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError("MGA: leere Antwort (keine choices)")

        message = choices[0].get("message", {})
        tool_calls = message.get("tool_calls") or []

        if not tool_calls:
            content = _extract_text(message)
            if not content:
                raise RuntimeError("MGA: keine Textantwort")
            return content, verlauf

        verlauf.append(message)
        for call in tool_calls:
            fn = call.get("function", {})
            name = fn.get("name", "")
            try:
                arguments = json.loads(fn.get("arguments") or "{}")
            except json.JSONDecodeError:
                arguments = {}
            result = execute_tool(name, arguments)
            verlauf.append(
                {
                    "role": "tool",
                    "tool_call_id": call.get("id"),
                    "content": json.dumps(result, ensure_ascii=False, default=str),
                }
            )

    raise RuntimeError("MGA: maximale Anzahl an Tool-Aufrufen erreicht ohne finale Antwort.")


def test_connection(model: str | None = None) -> dict[str, Any]:
    """Schickt eine Mini-Anfrage und meldet Erfolg, tatsaechlich antwortendes Modell und Dauer."""

    cfg = mga_config()
    zielmodell = (model or cfg["model"]).strip()
    start = time.monotonic()
    try:
        antwort = chat_completion(
            [{"role": "user", "content": "Antworte nur mit: ok"}],
            model=zielmodell,
            max_tokens=10,
        )
    except Exception as exc:  # noqa: BLE001 — Fehler wird in der UI angezeigt
        return {
            "ok": False,
            "angefragtes_modell": zielmodell,
            "fehler": str(exc),
            "dauer_s": round(time.monotonic() - start, 2),
        }

    return {
        "ok": True,
        "angefragtes_modell": zielmodell,
        "antwort": antwort,
        "dauer_s": round(time.monotonic() - start, 2),
    }
