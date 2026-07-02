# Plan for VideoCreatorAI Application

## Goal
Create a local Python application called "VideoCreatorAI" that automates the creation of long-form videos and affiliate marketing clips from a simple product name or link.

## Video Structure (High Retention)
1. **HOOK (0-5 seconds)**: Immediately and shockingly answers the question/curiosity present on the thumbnail.
2. **VIDEO BODY**: Introduces 3-4 secondary questions based on common user problems and answers by showing product benefits.
3. **VISUAL RHYTHM**: Final video alternates images and video clips every exactly 5 seconds to keep viewer's brain active.

## File Structure
1. `config.py`: Manages API keys (NVIDIA NIM for text, ElevenLabs for voice).
2. `script_generator.py`: Takes product name and generates:
   - Video script text (divided into 5-second blocks).
   - Visual prompts for each block (for Runway/Kling or Flux images).
   - Exact thumbnail question text.
3. `audio_generator.py`: Sends text script to ElevenLabs API and downloads `voiceover.mp3`.
4. `video_assembler.py`: Uses `moviepy` to take locally saved images/video, cut/alternate every exactly 5 seconds, and mount with `voiceover.mp3` to generate final `output.mp4`.
5. `main.py`: Coordinates everything via an interactive CLI.

## Instructions for Visual Script Prompt (for Nemotron system prompt)
"You are an expert in video automation. When analyzing the product, write the script structured as a JSON array. Each array element represents 5 seconds of video and must contain:
- 'text': The phrase the narrator voice must speak.
- 'visual_prompt': Detailed cinematic prompt to give to a generative AI (Runway/Kling) for creating that specific scene's clip (e.g., 'Cinematic 3D animation of... hyper-realistic, 4k')."

## Implementation Steps

### Phase 1: Environment Setup & Dependencies
- Create Python virtual environment.
- Install required packages: `moviepy`, `requests`, `pydantic`, `elevenlabs`.
- Verify installations.

### Phase 2: Configuration File (`config.py`)
- Define constants for API keys (to be loaded from environment variables for security).
- Provide template for users to fill in their NVIDIA NIM and ElevenLabs keys.
- Include validation for missing keys.

### Phase 3: Script Generator (`script_generator.py`)
- Accept product name or link as input.
- Use NVIDIA NIM API to generate structured JSON script:
  - Array of 5-second segments with `text` and `visual_prompt`.
  - Generate thumbnail question text separately.
- Output to JSON file (e.g., `script.json`) and thumbnail text file.
- Include error handling for API failures.

### Phase 4: Audio Generator (`audio_generator.py`)
- Read script text from JSON or text file.
- Send to ElevenLabs API for text-to-speech conversion.
- Save output as `voiceover.mp3` in local directory.
- Handle different voice models and stability settings.

### Phase 5: Video Assembler (`video_assembler.py`)
- Locate media files in local directory (e.g., `./media/`).
- Expect media files named sequentially (e.g., `001.jpg`, `002.mp4`, etc.) matching script order.
- Use `moviepy` to:
  - Load each media file for exactly 5 seconds.
  - Alternate between image and video clips (if mixed media).
  - Concatenate all clips.
  - Add audio track (`voiceover.mp3`).
  - Export final video as `output.mp4`.
- Include fallback for missing media (generate placeholder or skip).

### Phase 6: Main Coordinator (`main.py`)
- Interactive CLI:
  - Prompt for product name or link.
  - Option to specify output directory.
  - Option to skip certain steps (if media already generated).
  - Progress indicators for each stage.
  - Final output location notification.
- Orchestrate workflow:
  1. Run script generator.
  2. (User generates media using visual prompts via external tools OR future integration).
  3. Run audio generator.
  4. Run video assembler.
  5. Clean up temporary files if desired.

### Phase 7: Optional Enhancements
- Automatic media generation via Runway/Kling/Flux APIs (future extension).
- Batch processing for multiple products.
- UI version with Gradio or Streamlit.
- Logging and error reporting.

## Dependencies
- Python 3.8+
- moviepy
- requests
- pydantic
- elevenlabs
- (Optional) python-dotenv for environment variable management

## Security Notes
- API keys should never be hardcoded; use environment variables or `.env` file.
- `.env` template to be provided in README.

## Expected User Workflow
1. User runs `python main.py`.
2. Enters product name or link.
3. Application generates script and visual prompts, saves them.
4. User takes visual prompts to Runway/Kling/Flux to generate media files, saves them in `./media/` with sequential names.
5. User runs application again (or continues) to generate audio and assemble video.
6. Final video `output.mp4` is produced.

## Error Handling
- Each module should validate inputs and outputs.
- Network API calls should have retries and timeout handling.
- Missing media files should trigger clear instructions for user.
- Graceful degradation where possible.

## Testing Strategy
- Unit test each module with mock API responses.
- Integration test with dummy product.
- Verify output video duration matches script length.
- Check visual rhythm alternation.

## Timeline Estimate
- Environment setup: 15 minutes
- Config and script generator: 1 hour
- Audio generator: 45 minutes
- Video assembler: 1 hour
- Main CLI: 30 minutes
- Testing and refinement: 1 hour