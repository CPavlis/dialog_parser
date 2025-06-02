{
  "characters": {
    "ALICE": {
      "voice": "nova",
      "modifiers": {
        "tone": "cheerful",
        "speed": 1.1
      }
    },
    "BOB": {
      "voice": "onyx",
      "modifiers": {
        "tone": "serious",
        "speed": 0.95
      }
    },
    "NARRATOR": {
      "voice": "echo",
      "modifiers": {
        "tone": "neutral"
      }
    }
  }
}import json
import requests
import os
import re
import time
import argparse
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
from tqdm import tqdm
import hashlib

@dataclass
class TTSConfig:
    voice: str
    prompt: str
    speed: float = 1.0

@dataclass
class AudioFile:
    file_path: str
    speaker: str
    line_number: int
    text: str
    duration: Optional[float] = None

class OpenAIFMTTSGenerator:
    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1"):
        self.api_key = api_key
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        })

    def chunk_text(self, text: str, max_length: int = 4000) -> List[str]:
        """Split text into chunks that respect sentence boundaries."""
        if len(text) <= max_length:
            return [text]

        # Split by sentences
        sentences = re.split(r'(?<=[.!?])\s+', text)
        chunks = []
        current_chunk = ""

        for sentence in sentences:
            if len(current_chunk) + len(sentence) + 1 <= max_length:
                current_chunk += sentence + " "
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + " "

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    def clean_text_for_tts(self, text: str) -> str:
        """Clean text for TTS processing."""
        # Remove quotation marks and dialogue tags
        text = re.sub(r'^["\']|["\']$', '', text.strip())
        text = re.sub(r'\s*he said\s*|\s*she said\s*|\s*they said\s*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\s*said [A-Za-z]+\s*', '', text, flags=re.IGNORECASE)

        # Clean up extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    def generate_audio(self, text: str, voice: str, prompt: str = "", speed: float = 1.0) -> Optional[bytes]:
        """Generate audio using OpenAI TTS API."""
        try:
            # Prepare the request payload
            payload = {
                "model": "tts-1-hd",  # Use high-quality model
                "input": text,
                "voice": voice.lower(),
                "speed": speed
            }

            # Add prompt if provided (this might need adjustment based on actual API)
            if prompt:
                payload["prompt"] = prompt

            response = self.session.post(
                f"{self.base_url}/audio/speech",
                json=payload,
                timeout=60
            )

            if response.status_code == 200:
                return response.content
            else:
                print(f"TTS API error: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            print(f"Error generating audio: {e}")
            return None

    def save_audio(self, audio_data: bytes, file_path: str) -> bool:
        """Save audio data to file."""
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'wb') as f:
                f.write(audio_data)
            return True
        except Exception as e:
            print(f"Error saving audio to {file_path}: {e}")
            return False

class BookTTSProcessor:
    def __init__(self, api_key: str, config_file: str, output_dir: str = "audiobook_output"):
        self.tts_generator = OpenAIFMTTSGenerator(api_key)
        self.output_dir = Path(output_dir)
        self.config = self.load_config(config_file)
        self.generated_files = []

    def load_config(self, config_file: str) -> Dict[str, TTSConfig]:
        """Load character voice configuration."""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)

            character_configs = {}

            # Load character configurations
            for char_config in config_data.get("character_voices", []):
                character_configs[char_config["character"].upper()] = TTSConfig(
                    voice=char_config["voice"],
                    prompt=char_config.get("prompt", ""),
                    speed=char_config.get("speed", 1.0)
                )

            # Add default configurations
            if "default" in config_data:
                default_config = config_data["default"]
                character_configs["DEFAULT"] = TTSConfig(
                    voice=default_config["voice"],
                    prompt=default_config.get("prompt", ""),
                    speed=default_config.get("speed", 1.0)
                )

            return character_configs

        except Exception as e:
            print(f"Error loading config: {e}")
            return {}

    def get_character_config(self, speaker: str) -> TTSConfig:
        """Get TTS configuration for a character."""
        speaker = speaker.upper()

        if speaker in self.config:
            return self.config[speaker]
        elif "DEFAULT" in self.config:
            return self.config["DEFAULT"]
        else:
            # Fallback default
            return TTSConfig(voice="alloy", prompt="", speed=1.0)

    def generate_filename(self, speaker: str, line_number: int, chunk_index: int = 0) -> str:
        """Generate a filename for the audio file."""
        safe_speaker = re.sub(r'[^\w\-_]', '_', speaker)
        if chunk_index > 0:
            return f"{line_number:04d}_{safe_speaker}_chunk_{chunk_index:02d}.mp3"
        else:
            return f"{line_number:04d}_{safe_speaker}.mp3"

    def process_dialogue_file(self, dialogue_file: str) -> List[AudioFile]:
        """Process the dialogue JSON file and generate audio."""
        try:
            with open(dialogue_file, 'r', encoding='utf-8') as f:
                dialogue_data = json.load(f)
        except Exception as e:
            print(f"Error loading dialogue file: {e}")
            return []

        dialogue_lines = dialogue_data.get("dialogue", [])
        print(f"Processing {len(dialogue_lines)} dialogue lines...")

        # Create output directory structure
        self.output_dir.mkdir(parents=True, exist_ok=True)

        generated_files = []

        # Process each dialogue line
        for dialogue in tqdm(dialogue_lines, desc="Generating audio"):
            speaker = dialogue["speaker"]
            line_number = dialogue["line_number"]
            text = dialogue["text"]

            # Clean text for TTS
            clean_text = self.tts_generator.clean_text_for_tts(text)

            if not clean_text.strip():
                continue

            # Get character configuration
            char_config = self.get_character_config(speaker)

            # Chunk text if necessary
            text_chunks = self.tts_generator.chunk_text(clean_text)

            for chunk_index, chunk_text in enumerate(text_chunks):
                # Generate filename
                filename = self.generate_filename(speaker, line_number, chunk_index)
                file_path = self.output_dir / filename

                # Skip if file already exists
                if file_path.exists():
                    print(f"Skipping existing file: {filename}")
                    generated_files.append(AudioFile(
                        file_path=str(file_path),
                        speaker=speaker,
                        line_number=line_number,
                        text=chunk_text
                    ))
                    continue

                # Generate audio
                audio_data = self.tts_generator.generate_audio(
                    text=chunk_text,
                    voice=char_config.voice,
                    prompt=char_config.prompt,
                    speed=char_config.speed
                )

                if audio_data:
                    if self.tts_generator.save_audio(audio_data, str(file_path)):
                        generated_files.append(AudioFile(
                            file_path=str(file_path),
                            speaker=speaker,
                            line_number=line_number,
                            text=chunk_text
                        ))
                        print(f"Generated: {filename}")
                    else:
                        print(f"Failed to save: {filename}")
                else:
                    print(f"Failed to generate audio for line {line_number}")

                # Rate limiting - small delay between requests
                time.sleep(0.1)

        return generated_files

    def create_playlist(self, audio_files: List[AudioFile], playlist_file: str = "playlist.m3u"):
        """Create a playlist file for the generated audio."""
        playlist_path = self.output_dir / playlist_file

        # Sort files by line number
        sorted_files = sorted(audio_files, key=lambda x: x.line_number)

        with open(playlist_path, 'w', encoding='utf-8') as f:
            f.write("#EXTM3U\n")
            for audio_file in sorted_files:
                f.write(f"#EXTINF:-1,{audio_file.speaker} - Line {audio_file.line_number}\n")
                f.write(f"{os.path.basename(audio_file.file_path)}\n")

        print(f"Playlist created: {playlist_path}")

    def generate_summary(self, audio_files: List[AudioFile]) -> Dict:
        """Generate a summary of the TTS generation process."""
        summary = {
            "total_files": len(audio_files),
            "speakers": {},
            "output_directory": str(self.output_dir),
            "files": []
        }

        for audio_file in audio_files:
            speaker = audio_file.speaker
            if speaker not in summary["speakers"]:
                summary["speakers"][speaker] = 0
            summary["speakers"][speaker] += 1

            summary["files"].append({
                "filename": os.path.basename(audio_file.file_path),
                "speaker": speaker,
                "line_number": audio_file.line_number,
                "text_preview": audio_file.text[:100] + "..." if len(audio_file.text) > 100 else audio_file.text
            })

        # Save summary
        summary_path = self.output_dir / "generation_summary.json"
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        return summary

def main():
    parser = argparse.ArgumentParser(description="Generate TTS audio from parsed dialogue")
    parser.add_argument("dialogue_file", help="Path to the dialogue JSON file")
    parser.add_argument("config_file", help="Path to the character voice configuration file")
    parser.add_argument("-k", "--api-key", required=True, help="OpenAI API key")
    parser.add_argument("-o", "--output", default="audiobook_output",
                       help="Output directory (default: audiobook_output)")

    args = parser.parse_args()

    # Initialize processor
    processor = BookTTSProcessor(
        api_key=args.api_key,
        config_file=args.config_file,
        output_dir=args.output
    )

    # Process dialogue file
    audio_files = processor.process_dialogue_file(args.dialogue_file)

    if audio_files:
        # Create playlist
        processor.create_playlist(audio_files)

        # Generate summary
        summary = processor.generate_summary(audio_files)

        print(f"\n{'='*50}")
        print("TTS GENERATION COMPLETE")
        print(f"{'='*50}")
        print(f"Total files generated: {summary['total_files']}")
        print(f"Output directory: {summary['output_directory']}")
        print(f"Speakers processed: {len(summary['speakers'])}")

        for speaker, count in summary['speakers'].items():
            print(f"  - {speaker}: {count} files")

        print(f"\nCheck {args.output}/ for all generated audio files and playlist.")
    else:
        print("No audio files were generated.")

if __name__ == "__main__":
    main()
