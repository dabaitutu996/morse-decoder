from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn
from pathlib import Path

app = FastAPI(title="Morse Code Decoder Demo")

BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = BASE_DIR / "web"

app.mount("/css", StaticFiles(directory=WEB_DIR / "css"), name="css")
app.mount("/js", StaticFiles(directory=WEB_DIR / "js"), name="js")

@app.get("/")
async def root():
    return FileResponse(WEB_DIR / "index.html")

@app.get("/api/devices")
async def list_devices():
    return {"devices": []}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            message = await websocket.receive_json()
            await websocket.send_json({"type": "status", "state": "connected", "received": message})
    except WebSocketDisconnect:
        pass

if __name__ == "__main__":
    uvicorn.run("server.main:app", host="127.0.0.1", port=9000, reload=True)
