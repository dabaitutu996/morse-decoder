# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick start

```bash
./start.sh                           # creates .venv, installs deps, starts on :9000, opens browser
# Or manually:
source .venv/bin/activate
python -m server.main                # FastAPI + WebSocket on http://127.0.0.1:9000
```

## Project overview

A local desktop tool that captures system/MIC audio, decodes Morse code in real time, and visualizes it with a PCB-style SVG decoding tree in the browser. Transcoding is done with DeepSeek API (translator module exists but isn't wired into the WebSocket pipeline yet — `server/main.py` doesn't import `DeepSeekTranslator`).

## Architecture

```
Browser (SVG tree + terminal-style text) ← WebSocket → FastAPI ← AudioCapture → MorseDecoder → (Translator not wired)
```

- **Backend**: Python + FastAPI + WebSocket on port 9000. One route (`/ws`) handles all real-time communication. Static files served from `web/` via `StaticFiles` mounts and `FileResponse`.
- **Frontend**: Pure HTML + Tailwind CDN + vanilla JS. No build step, no framework.
- **No database, no auth** — fully local, single-user tool.

## Key files

| File | Role |
|---|---|
| `server/main.py` | FastAPI app, WebSocket handler, lifecycle glue |
| `server/audio_capture.py` | `sounddevice` input stream → 50ms chunks → `RingBuffer` (3s window) |
| `server/decoder.py` | Full DSP pipeline: Butterworth bandpass → envelope → adaptive threshold → ON/OFF state machine → Morse lookup |
| `server/translator.py` | `DeepSeekTranslator` class calling `api.deepseek.com/v1/chat/completions` (not yet wired into main.py) |
| `web/js/tree.js` | `MorseTree` class — radial binary tree in SVG (left=dah, right=dit), path animation, ripple effects |
| `web/js/app.js` | WebSocket client, settings management (localStorage), control UI glue |

## Testing individual modules

```bash
source .venv/bin/activate
python -m server.decoder          # runs self-test: generates synthetic Morse audio, decodes, checks against expected
python -m server.audio_capture    # lists available audio input devices
```

## Configuration

- **API key**: `server/.env` with `DEEPSEEK_API_KEY=sk-xxx` (loaded by `python-dotenv` in `translator.py`)
- **Audio device**: selectable in the settings panel (fetched from `/api/devices`). For capturing system audio on macOS, install BlackHole.
- **Decoder params**: center frequency (800 Hz), WPM (20), gain, squelch — adjustable via WebSocket messages or the settings panel. Persisted partially in `localStorage`.
- **WebSocket messages** accepted by backend: `start`, `stop`, `set_wpm`, `set_frequency`, `set_gain`.

## Planned but incomplete

- **Translator integration**: `translator.py` is fully implemented but `main.py` doesn't instantiate or call it. The WebSocket pipeline only does decode → push letters/words. Translation messages (`{"type": "translation", ...}`) are defined in `PLAN.md` but not emitted.
- State machine gap detection uses hardcoded 0.1s/0.3s defaults when `dit_length` is `None` (lines 131-136 in `decoder.py`), which is a fallback that doesn't adapt to WPM.
