 Installation:
   1. install ollama + model
   2. be sure to python -m venv
   3. clone repository
   4. pip install -r requirements.txt

 Usage Examples:<br />
   python dialog_parser.py book.txt <br />
   python dialog_parser.py book.txt -m mistral -o output.json<br />

 Features:<br />
    - Automatic dialogue detection using quotation marks and dialogue patterns<br />
    - Context-aware speaker identification using surrounding text<br />
    - Confidence scoring for each identification<br />
    - Character consistency tracking<br />
    - Flexible output in JSON format<br />
    - Progress tracking for long books<br />
    - Customizable Ollama models<br />

 Tips for Better Results:<br />
    - Use better models: Try mistral, codellama, or llama2:13b for more accurate results<br />
    - Clean your text: Remove headers, footers, and formatting artifacts<br />
    - Adjust context: Modify the context window size in identify_speaker() method<br />
    - Post-process: Review and manually correct low-confidence identifications<br />

 Limitations:<br />
    - Requires Ollama to be running locally<br />
    - Processing time depends on book length and model speed<br />
    - Accuracy varies with text quality and dialogue complexity<br />
    - May struggle with books that have minimal dialogue tags<br />
