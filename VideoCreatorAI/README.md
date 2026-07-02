# VideoCreatorAI 🎬

Automate long-form affiliate marketing video creation from a simple product name or link.

---

## Features

- **AI Script Generation** — NVIDIA NIM (Nemotron) generates a structured JSON script with 5-second video blocks and detailed visual prompts
- **Voice Synthesis** — ElevenLabs converts the script to a professional voiceover
- **Video Assembly** — MoviePy assembles media files into a polished `output.mp4` with synced audio
- **Interactive CLI** — Rich-powered menu to run the full pipeline or individual steps

---

## Quick Start

### 1. Clone / copy the project
```
cd VideoCreatorAI
```

### 2. Create and activate a virtual environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure API keys
```bash
cp .env.template .env
# Edit .env and fill in your NVIDIA_API_KEY and ELEVENLABS_API_KEY
```

### 5. Run
```bash
python main.py
```

---

## Expected Workflow

1. Run `python main.py` → **Option 1: Full Pipeline** or **Option 2: Script Only**
2. Enter your product name or URL when prompted
3. The app generates `script.json` and `visual_prompts.txt`
4. Take the visual prompts to **Runway / Kling / Flux** and generate media clips
5. Save media files in the `./media/` folder with sequential names:
   - `001.jpg`, `002.mp4`, `003.jpg`, `004.mp4` …
   - Each file = one 5-second block of the video
6. Run the app again → **Option 3: Audio Only** then **Option 4: Assemble Only**
7. Find your finished video at `./output/output.mp4` 🎉

---

## Media File Naming Convention

| Segment # | Expected filename |
|-----------|-------------------|
| 1 | `001.jpg` or `001.mp4` |
| 2 | `002.jpg` or `002.mp4` |
| … | … |

Supported formats: `.jpg`, `.jpeg`, `.png`, `.mp4`, `.mov`, `.webm`

---

## Configuration (`.env`)

| Variable | Required | Description |
|---|---|---|
| `NVIDIA_API_KEY` | ✅ | NVIDIA NIM API key |
| `ELEVENLABS_API_KEY` | ✅ | ElevenLabs API key |
| `ELEVENLABS_VOICE_ID` | ❌ | Default voice (prompted if blank) |
| `OUTPUT_DIR` | ❌ | Output folder (default: `./output`) |
| `MEDIA_DIR` | ❌ | Media input folder (default: `./media`) |

---

## Project Structure

```
VideoCreatorAI/
├── config.py            # API keys, paths, constants
├── script_generator.py  # NVIDIA NIM → JSON script
├── audio_generator.py   # ElevenLabs → voiceover.mp3
├── video_assembler.py   # MoviePy → output.mp4
├── main.py              # CLI orchestrator
├── media/               # ← Drop your generated media here
├── output/              # ← Final video appears here
├── .env.template        # Copy to .env and fill in keys
└── requirements.txt
```

---

## Security Notes

- **Never commit `.env`** — it contains your private API keys
- A `.gitignore` entry for `.env` is strongly recommended

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `NVIDIA_API_KEY not set` | Copy `.env.template` → `.env` and add your key |
| `No media files found` | Check that files are in `./media/` with names like `001.jpg` |
| `Audio sync off` | Ensure the number of media files matches the number of script segments |
| `moviepy error` | Make sure ffmpeg is installed: `pip install imageio[ffmpeg]` |
