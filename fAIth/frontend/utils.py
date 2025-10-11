import json
import logging

# Set up logging
logger = logging.getLogger(__name__)

def parse_verses(file_path):
    # Read the JSON file and parse the verses of the book and chapter
    verses = []
    try:
        logger.debug(f"Parsing verses from {file_path}")
        # Read the JSON file and parse the verses of the book and chapter
        with open(file_path, "r", encoding='utf-8') as file: # Added encoding
            json_data = json.load(file)
            for verse_num, verse_text in json_data.items():
                # The text is already properly formatted, no parsing needed, just add the verse number and get headers
                try:
                    # This should fail if verse_num is not an int (i.e. header_1, header_2, etc.)
                    verses.append(f'{int(verse_num)}) {verse_text}')
                except Exception as e:
                    # If the exception occurs, we assume the verse_num is a header
                    verses.append(f'<span class="header">{verse_text}</span>')
        logger.info(f"Parsed {len(verses)} verses from {file_path}")
    except Exception as e:
        logger.error(f"Error parsing verses: {e}")
        return []
    return verses
