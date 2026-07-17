import asyncio
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn

from server.audio_capture import AudioCapture, list_devices as list_audio_devices
from server.decoder import MorseDecoder

app = FastAPI(title="Morse Code Decoder Demo")

WEB_DIR = PROJECT_ROOT / "web"

app.mount("/css", StaticFiles(directory=WEB_DIR / "css"), name="css")
app.mount("/js", StaticFiles(directory=WEB_DIR / "js"), name="js")


@app.get("/")
async def root():
    return FileResponse(WEB_DIR / "index.html")


@app.get("/api/devices")
async def list_devices():
    return {"devices": list_audio_devices()}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    loop = asyncio.get_running_loop()
    capture = None
    decoder = None
    raw_text = []
    running = False

    async def send_message(data: dict):
        try:
            await websocket.send_json(data)
        except Exception:
            pass  # client disconnected; ignore

    def send_message_threadsafe(data: dict):
        asyncio.run_coroutine_threadsafe(send_message(data), loop)

    def on_letter(letter: str):
        raw_text.append(letter)
        send_message_threadsafe({"type": "decoded_letter", "letter": letter})

    def on_word():
        raw_text.append(" ")
        word = decoder.current_word if decoder else ""
        if decoder:
            decoder.current_word = ""
        send_message_threadsafe({"type": "decoded_word", "word": word, "full_text": "".join(raw_text)})

    try:
        while True:
            message = await websocket.receive_json()
            msg_type = message.get("type")

            if msg_type == "start":
                if running:
                    await send_message({"type": "status", "state": "already_running"})
                    continue

                device_id = message.get("device_id")
                if device_id is not None:
                    device_id = int(device_id)
                frequency = float(message.get("frequency", 800))
                wpm = float(message.get("wpm", 20))
                gain = float(message.get("gain", 1.0))
                squelch = float(message.get("squelch", 0.05))

                decoder = MorseDecoder(
                    frequency=frequency,
                    wpm=wpm,
                    gain=gain,
                    squelch=squelch,
                    on_letter=on_letter,
                    on_word=on_word,
                )

                last_signal_time = 0.0
                last_signal_value = -1.0

                def audio_callback(chunk):
                    nonlocal last_signal_time, last_signal_value
                    if decoder:
                        decoder.feed_audio(chunk)
                        now = time.monotonic()
                        level = round(float(decoder.signal_level), 3)
                        if now - last_signal_time > 0.1 or abs(level - last_signal_value) > 0.05:
                            send_message_threadsafe({
                                "type": "signal_level",
                                "value": level,
                            })
                            last_signal_time = now
                            last_signal_value = level

                capture = AudioCapture(callback=audio_callback, device_id=device_id)
                capture.start()
                running = True
                raw_text = []
                await send_message({"type": "status", "state": "listening"})

            elif msg_type == "stop":
                if capture:
                    capture.stop()
                    capture = None
                if decoder:
                    decoder.flush()
                    decoder = None
                running = False
                await send_message({"type": "status", "state": "stopped"})

            elif msg_type == "set_wpm":
                value = float(message.get("value", 20))
                if decoder:
                    decoder.set_wpm(value)
                    await send_message({"type": "wpm", "value": value})

            elif msg_type == "set_frequency":
                value = float(message.get("value", 800))
                if decoder:
                    decoder.set_frequency(value)
                    await send_message({"type": "frequency", "value": value})

            elif msg_type == "set_gain":
                value = float(message.get("value", 1.0))
                if decoder:
                    decoder.set_gain(value)

    except WebSocketDisconnect:
        pass
    finally:
        if capture:
            capture.stop()


if __name__ == "__main__":
    uvicorn.run("server.main:app", host="127.0.0.1", port=9000, reload=True, reload_dirs=[str(PROJECT_ROOT)])
