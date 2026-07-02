# VideoCreatorAI

Automated affiliate video generation pipeline with AI-powered script generation, voiceover, transcription, asset hunting, and video assembly.

## Features

- **AI Script Generation**: English scripts with dark psychology tone for USA/Global market
- **Voiceover Generation**: ElevenLabs TTS with American narrator presets
- **Whisper Transcription**: Word-level timestamps for karaoke subtitles
- **Asset Hunting**: Automatic stock footage download from Pexels/Pixabay
- **FFmpeg Assembly**: Ken Burns effect with ASS subtitle burning
- **Web Interface**: FastAPI backend with real-time WebSocket updates

## Installation

1. Clone the repository:
```bash
git clone https://github.com/carlos1279/dev.git
cd dev/VideoCreatorAI
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables:
```bash
cp .env.template .env
# Edit .env with your API keys
```

## Required API Keys

- **OpenRouter API Key**: For LLM script generation
- **ElevenLabs API Key**: For voiceover generation
- **OpenAI API Key**: For Whisper transcription
- **Pexels API Key**: For stock footage (optional, Pixabay as fallback)
- **Pixabay API Key**: For stock footage fallback (optional)

## Usage

### CLI Interface

Run the main script:
```bash
python main.py
```

Available options:
- **Option 1**: Full Pipeline (manual media)
- **Option 2**: Script Only
- **Option 3**: Audio Only
- **Option 4**: Assemble Only
- **Option 5**: Full Automated Pipeline (recommended)
- **Option 6**: Fetch Assets Only
- **Option 7**: Transcribe Only
- **Option 8**: FFmpeg Assemble Only

### Web Interface

Start the web server:
```bash
python web_server.py
```

Open your browser to: `http://127.0.0.1:8000`

## Pipeline Architecture

```
Product → Script → Audio → Whisper → Assets → FFmpeg → Output
```

1. **Script Generation**: LLM generates 5-second segments with search keywords
2. **Audio Generation**: ElevenLabs creates voiceover with American narrator
3. **Transcription**: Whisper API provides word-level timestamps
4. **Asset Hunting**: Pexels/Pixabay APIs download matching stock footage
5. **Assembly**: FFmpeg applies Ken Burns effect and burns subtitles

## Configuration

Edit `config.py` to customize:
- Video resolution (default: 1920x1080)
- Segment duration (default: 5s)
- Ken Burns zoom factor (default: 1.08)
- Subtitle styling (font, colors, size)
- API endpoints and models

## Project Structure

```
VideoCreatorAI/
├── script_generator.py    # LLM script generation
├── audio_generator.py     # ElevenLabs TTS
├── transcription.py       # Whisper API
├── asset_hunter.py        # Pexels/Pixabay integration
├── ffmpeg_assembler.py    # FFmpeg video assembly
├── web_server.py          # FastAPI backend
├── main.py                # CLI interface
├── config.py              # Configuration
├── requirements.txt       # Dependencies
├── .env.template          # Environment variables template
└── static/
    └── index.html         # Web frontend
```

## Output Files

- `script.json` - Generated script with segments
- `voiceover.mp3` - Generated audio
- `timestamps.json` - Word-level timestamps
- `subtitles.ass` - ASS subtitle file with karaoke
- `media/001.mp4, 002.mp4, ...` - Downloaded stock footage
- `output/output.mp4` - Final assembled video

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
