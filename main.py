import re
import json
import requests
import argparse
from typing import List, Dict, Tuple
from dataclasses import dataclass

@dataclass
class DialogueLine:
    text: str
    speaker: str
    line_number: int
    confidence: float = 0.0

class BookDialogParser:
    def __init__(self, ollama_model="llama2", ollama_url="http://localhost:11434"):
        self.ollama_model = ollama_model
        self.ollama_url = ollama_url
        self.characters = set()

    def extract_potential_dialogue(self, text: str) -> List[Tuple[str, int]]:
        """Extract lines that might contain dialogue based on quotation marks."""
        lines = text.split('\n')
        dialogue_lines = []

        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            # Look for various quotation patterns
            if ('"' in line or "'" in line or
                line.startswith('"') or line.startswith("'") or
                '—' in line or '–' in line):
                dialogue_lines.append((line, i + 1))

        return dialogue_lines

    def query_ollama(self, prompt: str) -> str:
        """Send a query to Ollama and get response."""
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "top_p": 0.9
                    }
                },
                timeout=30
            )

            if response.status_code == 200:
                return response.json().get("response", "").strip()
            else:
                print(f"Ollama error: {response.status_code}")
                return ""

        except Exception as e:
            print(f"Error querying Ollama: {e}")
            return ""

    def identify_speaker(self, dialogue_line: str, context_lines: List[str]) -> Tuple[str, float]:
        """Use Ollama to identify who is speaking in a dialogue line."""

        # Create context from surrounding lines
        context = "\n".join(context_lines[-3:] + [dialogue_line] + context_lines[:2])

        prompt = f"""
Analyze this text excerpt and identify who is speaking the dialogue in quotes.

Text:
{context}

Instructions:
- Look for the dialogue in quotation marks
- Identify the speaker based on context clues (dialogue tags, narrative descriptions)
- If no clear speaker is identified, respond with "NARRATOR" for narrative text or "UNKNOWN" for unclear dialogue
- Respond with ONLY the character name or NARRATOR/UNKNOWN
- Use consistent character names (e.g., always "John" not "John Smith" then "John")

Speaker:"""

        response = self.query_ollama(prompt)

        # Clean up the response
        speaker = response.strip().upper()

        # Basic confidence scoring
        confidence = 0.8 if speaker not in ["UNKNOWN", "NARRATOR"] else 0.3

        # Add to character set if it's a named character
        if speaker not in ["UNKNOWN", "NARRATOR", ""]:
            self.characters.add(speaker)

        return speaker, confidence

    def parse_book(self, file_path: str) -> List[DialogueLine]:
        """Parse the entire book and identify all dialogue with speakers."""

        print(f"Reading book from {file_path}...")

        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                text = file.read()
        except Exception as e:
            print(f"Error reading file: {e}")
            return []

        # Extract potential dialogue lines
        dialogue_candidates = self.extract_potential_dialogue(text)
        print(f"Found {len(dialogue_candidates)} potential dialogue lines")

        # Split text into lines for context
        all_lines = text.split('\n')

        dialogue_results = []

        for i, (dialogue_line, line_number) in enumerate(dialogue_candidates):
            print(f"Processing line {i+1}/{len(dialogue_candidates)}: {line_number}")

            # Get context lines around the dialogue
            start_idx = max(0, line_number - 4)
            end_idx = min(len(all_lines), line_number + 3)
            context_lines = [line.strip() for line in all_lines[start_idx:end_idx]
                           if line.strip()]

            # Identify speaker
            speaker, confidence = self.identify_speaker(dialogue_line, context_lines)

            dialogue_results.append(DialogueLine(
                text=dialogue_line,
                speaker=speaker,
                line_number=line_number,
                confidence=confidence
            ))

        return dialogue_results

    def save_results(self, dialogue_lines: List[DialogueLine], output_file: str):
        """Save parsed dialogue to a JSON file."""

        results = {
            "characters": list(self.characters),
            "total_dialogue_lines": len(dialogue_lines),
            "dialogue": [
                {
                    "line_number": dl.line_number,
                    "speaker": dl.speaker,
                    "text": dl.text,
                    "confidence": dl.confidence
                }
                for dl in dialogue_lines
            ]
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print(f"Results saved to {output_file}")

    def print_summary(self, dialogue_lines: List[DialogueLine]):
        """Print a summary of the parsing results."""

        print("\n" + "="*50)
        print("PARSING SUMMARY")
        print("="*50)

        print(f"Total dialogue lines processed: {len(dialogue_lines)}")
        print(f"Characters identified: {len(self.characters)}")

        if self.characters:
            print("\nCharacters found:")
            for char in sorted(self.characters):
                count = sum(1 for dl in dialogue_lines if dl.speaker == char)
                print(f"  - {char}: {count} lines")

        # Show confidence distribution
        high_conf = sum(1 for dl in dialogue_lines if dl.confidence > 0.7)
        med_conf = sum(1 for dl in dialogue_lines if 0.3 < dl.confidence <= 0.7)
        low_conf = sum(1 for dl in dialogue_lines if dl.confidence <= 0.3)

        print(f"\nConfidence distribution:")
        print(f"  - High confidence (>0.7): {high_conf}")
        print(f"  - Medium confidence (0.3-0.7): {med_conf}")
        print(f"  - Low confidence (≤0.3): {low_conf}")

def main():
    parser = argparse.ArgumentParser(description="Parse book dialogue using Ollama")
    parser.add_argument("input_file", help="Path to the input text file")
    parser.add_argument("-o", "--output", default="dialogue_output.json",
                       help="Output JSON file (default: dialogue_output.json)")
    parser.add_argument("-m", "--model", default="llama2",
                       help="Ollama model to use (default: llama2)")
    parser.add_argument("--url", default="http://localhost:11434",
                       help="Ollama server URL (default: http://localhost:11434)")

    args = parser.parse_args()

    # Initialize parser
    book_parser = BookDialogParser(
        ollama_model=args.model,
        ollama_url=args.url
    )

    # Parse the book
    dialogue_lines = book_parser.parse_book(args.input_file)

    if dialogue_lines:
        # Save results
        book_parser.save_results(dialogue_lines, args.output)

        # Print summary
        book_parser.print_summary(dialogue_lines)

        print(f"\nDone! Check {args.output} for detailed results.")
    else:
        print("No dialogue found or processing failed.")

if __name__ == "__main__":
    main()
