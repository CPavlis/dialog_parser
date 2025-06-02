 Installation:
   1. be sure to python -m venv
   2. clone repository
   3. pip install -r requirements.txt

 Usage Examples:
   python dialog_parser.py book.txt
   python dialog_parser.py book.txt -m mistral -o output.json

 Features
    Automatic dialogue detection using quotation marks and dialogue patterns
    Context-aware speaker identification using surrounding text
    Confidence scoring for each identification
    Character consistency tracking
    Flexible output in JSON format
    Progress tracking for long books
    Customizable Ollama models

 Tips for Better Results
    Use better models: Try mistral, codellama, or llama2:13b for more accurate results
    Clean your text: Remove headers, footers, and formatting artifacts
    Adjust context: Modify the context window size in identify_speaker() method
    Post-process: Review and manually correct low-confidence identifications

 Limitations
    Requires Ollama to be running locally
    Processing time depends on book length and model speed
    Accuracy varies with text quality and dialogue complexity
    May struggle with books that have minimal dialogue tags
