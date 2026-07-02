"""
web_server.py — VideoCreatorAI Web Interface

FastAPI backend for the web interface. Provides REST API endpoints
and WebSocket for real-time status updates during video generation.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import config
from script_generator import generate_script, load_script
from audio_generator import generate_audio
from transcription import transcribe_audio
from asset_hunter import fetch_assets
from ffmpeg_assembler import assemble_with_ffmpeg


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(title="VideoCreatorAI", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class GenerateScriptRequest(BaseModel):
    product: str


class GenerateAudioRequest(BaseModel):
    voice_id: str = ""


class PipelineStatus(BaseModel):
    step: str
    status: str
    message: str
    progress: float = 0.0


# ---------------------------------------------------------------------------
# WebSocket connection manager
# ---------------------------------------------------------------------------
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict[str, Any]):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass


manager = ConnectionManager()


# ---------------------------------------------------------------------------
# Helper function for status updates
# ---------------------------------------------------------------------------
async def send_status(step: str, status: str, message: str, progress: float = 0.0):
    """Send status update via WebSocket."""
    await manager.broadcast({
        "step": step,
        "status": status,
        "message": message,
        "progress": progress,
    })


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------
@app.get("/")
async def root():
    """Serve the main web interface."""
    index_path = static_dir / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return JSONResponse({"message": "VideoCreatorAI Web API"})


@app.post("/api/script/generate")
async def api_generate_script(request: GenerateScriptRequest):
    """Generate script from product name/URL."""
    try:
        await send_status("script", "running", f"Generating script for: {request.product}")
        script = generate_script(request.product)
        await send_status("script", "completed", "Script generated successfully", 100.0)
        return JSONResponse({
            "success": True,
            "thumbnail_question": script.thumbnail_question,
            "segments_count": len(script.segments),
            "segments": [
                {
                    "text": seg.text,
                    "visual_prompt": seg.visual_prompt,
                    "search_keywords": seg.search_keywords,
                }
                for seg in script.segments
            ],
        })
    except Exception as e:
        await send_status("script", "error", str(e))
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@app.get("/api/script/load")
async def api_load_script():
    """Load existing script.json."""
    try:
        script = load_script()
        return JSONResponse({
            "success": True,
            "thumbnail_question": script.thumbnail_question,
            "segments_count": len(script.segments),
            "segments": [
                {
                    "text": seg.text,
                    "visual_prompt": seg.visual_prompt,
                    "search_keywords": seg.search_keywords,
                }
                for seg in script.segments
            ],
        })
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@app.post("/api/audio/generate")
async def api_generate_audio(request: GenerateAudioRequest):
    """Generate voiceover from script."""
    try:
        await send_status("audio", "running", "Generating voiceover with ElevenLabs")
        audio_path = generate_audio(voice_id=request.voice_id)
        await send_status("audio", "completed", "Voiceover generated successfully", 100.0)
        return JSONResponse({
            "success": True,
            "audio_path": str(audio_path),
        })
    except Exception as e:
        await send_status("audio", "error", str(e))
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@app.post("/api/transcribe")
async def api_transcribe():
    """Transcribe audio with Whisper."""
    try:
        await send_status("transcription", "running", "Transcribing audio with Whisper")
        ass_path = transcribe_audio()
        await send_status("transcription", "completed", "Transcription completed", 100.0)
        return JSONResponse({
            "success": True,
            "subtitles_path": str(ass_path),
        })
    except Exception as e:
        await send_status("transcription", "error", str(e))
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@app.post("/api/assets/fetch")
async def api_fetch_assets():
    """Fetch stock footage from Pexels/Pixabay."""
    try:
        await send_status("assets", "running", "Fetching stock footage")
        media_files = fetch_assets()
        await send_status("assets", "completed", f"Downloaded {len(media_files)} media files", 100.0)
        return JSONResponse({
            "success": True,
            "media_files": [str(f) for f in media_files],
            "count": len(media_files),
        })
    except Exception as e:
        await send_status("assets", "error", str(e))
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@app.post("/api/ffmpeg/assemble")
async def api_ffmpeg_assemble():
    """Assemble video with FFmpeg."""
    try:
        await send_status("assembly", "running", "Assembling video with FFmpeg")
        
        # Discover media files
        media_files = []
        for i in range(1, 100):
            media_path = config.MEDIA_DIR / f"{i:03d}.mp4"
            if media_path.exists():
                media_files.append(media_path)
            else:
                break
        
        if not media_files:
            raise FileNotFoundError("No media files found")
        
        output_path = assemble_with_ffmpeg(media_files)
        await send_status("assembly", "completed", "Video assembled successfully", 100.0)
        return JSONResponse({
            "success": True,
            "output_path": str(output_path),
        })
    except Exception as e:
        await send_status("assembly", "error", str(e))
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@app.post("/api/pipeline/full")
async def api_full_pipeline(request: GenerateScriptRequest):
    """Run the full automated pipeline."""
    try:
        # Step 1: Generate script
        await send_status("script", "running", f"Generating script for: {request.product}")
        script = generate_script(request.product)
        await send_status("script", "completed", "Script generated successfully", 12.5)
        
        # Step 2: Generate audio
        await send_status("audio", "running", "Generating voiceover with ElevenLabs")
        generate_audio(script=script)
        await send_status("audio", "completed", "Voiceover generated successfully", 25.0)
        
        # Step 3: Transcribe
        await send_status("transcription", "running", "Transcribing audio with Whisper")
        transcribe_audio()
        await send_status("transcription", "completed", "Transcription completed", 37.5)
        
        # Step 4: Fetch assets
        await send_status("assets", "running", "Fetching stock footage")
        media_files = fetch_assets(script=script)
        await send_status("assets", "completed", f"Downloaded {len(media_files)} media files", 50.0)
        
        # Step 5: Assemble
        await send_status("assembly", "running", "Assembling video with FFmpeg")
        output_path = assemble_with_ffmpeg(media_files=media_files)
        await send_status("assembly", "completed", "Video assembled successfully", 100.0)
        
        return JSONResponse({
            "success": True,
            "output_path": str(output_path),
            "segments_count": len(script.segments),
        })
    except Exception as e:
        await send_status("pipeline", "error", str(e))
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@app.get("/api/status")
async def api_status():
    """Get current status of files."""
    return JSONResponse({
        "script_exists": config.SCRIPT_PATH.exists(),
        "audio_exists": config.VOICEOVER_PATH.exists(),
        "subtitles_exist": config.SUBTITLES_PATH.exists(),
        "output_exists": config.OUTPUT_VIDEO_PATH.exists(),
        "media_files": len(list(config.MEDIA_DIR.glob("*.mp4"))),
    })


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time status updates."""
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# ---------------------------------------------------------------------------
# Run server
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
