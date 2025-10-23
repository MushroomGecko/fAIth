import os
from pathlib import Path
import json
from django.conf import settings
import logging

# Set up logging
logger = logging.getLogger(__name__)

# Default version is the BSB version
DEFAULT_VERSION = 'bsb'

# Get the books in order
IN_ORDER_BOOKS = [
    "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy", "Joshua",
    "Judges", "Ruth", "1 Samuel", "2 Samuel", "1 Kings", "2 Kings",
    "1 Chronicles", "2 Chronicles", "Ezra", "Nehemiah", "Esther", "Job",
    "Psalms", "Proverbs", "Ecclesiastes", "Song of Solomon", "Isaiah",
    "Jeremiah", "Lamentations", "Ezekiel", "Daniel", "Hosea", "Joel",
    "Amos", "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk", "Zephaniah",
    "Haggai", "Zechariah", "Malachi", "Matthew", "Mark", "Luke", "John",
    "Acts", "Romans", "1 Corinthians", "2 Corinthians", "Galatians",
    "Ephesians", "Philippians", "Colossians", "1 Thessalonians",
    "2 Thessalonians", "1 Timothy", "2 Timothy", "Titus", "Philemon",
    "Hebrews", "James", "1 Peter", "2 Peter", "1 John", "2 John",
    "3 John", "Jude", "Revelation"
]

# bible_data is in the frontend directory and holds the JSON files for each Bible version
BIBLE_DATA_ROOT = Path(settings.BASE_DIR) / 'frontend' / 'bible_data'

# Get the available versions
VERSION_SELECTION = os.listdir(BIBLE_DATA_ROOT)

# Get the number of chapters in each book
CHAPTER_SELECTION = {}
if BIBLE_DATA_ROOT.exists() and (BIBLE_DATA_ROOT / DEFAULT_VERSION).exists():
    for book_title in IN_ORDER_BOOKS:
        book_path = BIBLE_DATA_ROOT / DEFAULT_VERSION / book_title
        if book_path.exists() and book_path.is_dir():
            try:
                # Count JSON files (chapters) in the book directory
                json_files = [file for file in os.listdir(book_path) if file.endswith('.json') and file.split('.')[0].isdigit()]
                CHAPTER_SELECTION[book_title] = len(json_files)
            # Catch potential errors during listdir
            except Exception as e:
                logger.error(f"Error: {e}")
                CHAPTER_SELECTION[book_title] = 0
        else:
            CHAPTER_SELECTION[book_title] = 0
else:
    logger.warning(f"Bible data directory not found or incomplete at {BIBLE_DATA_ROOT}. 'CHAPTER_SELECTION' may be incomplete.")
    # Initialize to prevent KeyErrors if data is missing
    for book_title in IN_ORDER_BOOKS:
        CHAPTER_SELECTION[book_title] = 0

ALL_VERSES = {}
for version in VERSION_SELECTION:
    version = version.lower()
    ALL_VERSES[version] = {}
    for book in IN_ORDER_BOOKS:
        ALL_VERSES[version][book] = {}
        for chapter in range(1, CHAPTER_SELECTION[book] + 1):
            ALL_VERSES[version][book][chapter] = {}
            file_path = BIBLE_DATA_ROOT / version / book / f"{chapter}.json"
            if file_path.exists():
                with open(file_path, "r", encoding="utf-8") as file:
                    json_data = json.load(file)
                    for verse_num, verse_text in json_data.items():
                        # The text is already properly formatted, no parsing needed, just add the verse number and get headers
                        try:
                            # This should fail if verse_num is not an int (i.e. header_1, header_2, etc.)
                            ALL_VERSES[version][book][chapter][verse_num] = f'{int(verse_num)}) {verse_text}'
                        except Exception as e:
                            # If the exception occurs, we assume the verse_num is a header
                            ALL_VERSES[version][book][chapter][verse_num] = f'<span class="header">{verse_text}</span>'