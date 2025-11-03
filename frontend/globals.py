from contextlib import asynccontextmanager
from django_asgi_lifespan.types import LifespanManager
import os
from pathlib import Path
import json
from django.conf import settings
import logging

# Set up logging
logger = logging.getLogger(__name__)

BIBLE_DATA_ROOT = ''
DEFAULT_VERSION = ''
DEFAULT_BOOK = ''
DEFAULT_CHAPTER = ''
VERSION_SELECTION = []
IN_ORDER_BOOKS = []
CHAPTER_SELECTION = {}
ALL_VERSES = {}

def set_bible_data_root():
    """Set the root directory for the Bible data."""
    global BIBLE_DATA_ROOT
    try:
        BIBLE_DATA_ROOT = Path(settings.BASE_DIR) / 'frontend' / 'bible_data'
    except Exception as e:
        logger.error(f"Error: {e}. 'BIBLE_DATA_ROOT' cannot be set.")
        raise ValueError(f"Error: {e}. 'BIBLE_DATA_ROOT' cannot be set.")

def set_version_selection():
    """Set the available versions."""
    global VERSION_SELECTION
    logger.info("Setting available versions.")
    try:
        VERSION_SELECTION = os.listdir(BIBLE_DATA_ROOT)
    except Exception as e:
        logger.error(f"Error: {e}. 'VERSION_SELECTION' cannot be set.")
        raise ValueError(f"Error: {e}. 'VERSION_SELECTION' cannot be set.")
    logger.info(f"Available versions successfully set to {VERSION_SELECTION}.")

def set_default_version():
    """Set the default version."""
    global DEFAULT_VERSION
    logger.info("Setting default version.")
    try:
        DEFAULT_VERSION = os.getenv("DEFAULT_VERSION", "bsb")
        if DEFAULT_VERSION not in VERSION_SELECTION:
            logger.warning(f"Default version {DEFAULT_VERSION} is not in the list of available versions. Defaulting to first version in the list.")
            DEFAULT_VERSION = VERSION_SELECTION[0]
    except Exception as e:
        logger.error(f"Error: {e}. 'DEFAULT_VERSION' cannot be set.")
        raise ValueError(f"Error: {e}. 'DEFAULT_VERSION' cannot be set.")
    logger.info(f"Default version successfully set to {DEFAULT_VERSION}.")

def set_in_order_books():
    """Set the Bible books in order."""
    global IN_ORDER_BOOKS
    logger.info("Setting Bible books in order.")
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
    logger.info(f"Bible books successfully set in order.")

def set_default_book():
    """Set the default book."""
    global DEFAULT_BOOK
    logger.info("Setting default book.")
    try:
        DEFAULT_BOOK = os.getenv("DEFAULT_BOOK", "Genesis")
        if DEFAULT_BOOK not in IN_ORDER_BOOKS:
            logger.warning(f"Default book {DEFAULT_BOOK} is not in the list of available books. Defaulting to first book in the list.")
            DEFAULT_BOOK = IN_ORDER_BOOKS[0]
    except Exception as e:
        logger.error(f"Error: {e}. 'DEFAULT_BOOK' cannot be set.")
        raise ValueError(f"Error: {e}. 'DEFAULT_BOOK' cannot be set.")
    logger.info(f"Default book successfully set to {DEFAULT_BOOK}.")

def set_chapter_selection():
    """Set the number of chapters in each book."""
    global CHAPTER_SELECTION
    logger.info("Setting number of chapters in each book.")
    if BIBLE_DATA_ROOT is not None and BIBLE_DATA_ROOT.exists() and (BIBLE_DATA_ROOT / DEFAULT_VERSION).exists():
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
                    raise ValueError(f"Error: {e}")
            else:
                logger.error(f"Book directory not found at {book_path}. 'CHAPTER_SELECTION' cannot be set.")
                raise ValueError(f"Book directory not found at {book_path}. 'CHAPTER_SELECTION' cannot be set.")
    else:
        if not BIBLE_DATA_ROOT:
            logger.error(f"BIBLE_DATA_ROOT is None. 'CHAPTER_SELECTION' cannot be set.")
            raise ValueError(f"BIBLE_DATA_ROOT is None. 'CHAPTER_SELECTION' cannot be set.")
        elif not BIBLE_DATA_ROOT.exists():
            logger.error(f"Bible data directory not found at {BIBLE_DATA_ROOT}. 'CHAPTER_SELECTION' cannot be set.")
            raise ValueError(f"Bible data directory not found at {BIBLE_DATA_ROOT}. 'CHAPTER_SELECTION' cannot be set.")
        elif not (BIBLE_DATA_ROOT / DEFAULT_VERSION).exists():
            logger.error(f"Default version directory not found at {BIBLE_DATA_ROOT / DEFAULT_VERSION}. 'CHAPTER_SELECTION' cannot be set.")
            raise ValueError(f"Default version directory not found at {BIBLE_DATA_ROOT / DEFAULT_VERSION}. 'CHAPTER_SELECTION' cannot be set.")
    logger.info("Number of chapters in each book successfully set.")

def set_default_chapter():
    """Set the default chapter."""
    global DEFAULT_CHAPTER
    logger.info("Setting default chapter.")
    try:
        DEFAULT_CHAPTER = os.getenv("DEFAULT_CHAPTER", "1")
        DEFAULT_CHAPTER = int(DEFAULT_CHAPTER)
        if DEFAULT_BOOK not in CHAPTER_SELECTION:
            logger.error(f"'DEFAULT_BOOK' {DEFAULT_BOOK} is not in the list of available books. 'DEFAULT_CHAPTER' cannot be set.")
            raise ValueError(f"'DEFAULT_BOOK' {DEFAULT_BOOK} is not in the list of available books. 'DEFAULT_CHAPTER' cannot be set.")
        if DEFAULT_CHAPTER not in range(1, CHAPTER_SELECTION[DEFAULT_BOOK] + 1):
            logger.error(f"'DEFAULT_CHAPTER' {DEFAULT_CHAPTER} is not in the range of chapters for {DEFAULT_BOOK}. 'DEFAULT_CHAPTER' cannot be set.")
            raise ValueError(f"'DEFAULT_CHAPTER' {DEFAULT_CHAPTER} is not in the range of chapters for {DEFAULT_BOOK}. 'DEFAULT_CHAPTER' cannot be set.")
    except Exception as e:
        logger.error(f"Error: {e}. 'DEFAULT_CHAPTER' cannot be set.")
        raise ValueError(f"Error: {e}. 'DEFAULT_CHAPTER' cannot be set.")
    logger.info(f"Default chapter successfully set to {DEFAULT_CHAPTER} for {DEFAULT_BOOK}.")

def set_all_verses():
    """Set the verses for each version, book, and chapter."""
    global ALL_VERSES
    logger.info("Setting verses for each version, book, and chapter.")
    necessary_globals = [VERSION_SELECTION, IN_ORDER_BOOKS, CHAPTER_SELECTION, BIBLE_DATA_ROOT]
    if all(global_var is not None for global_var in necessary_globals):
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
                    else:
                        logger.error(f"File not found at {file_path}. 'ALL_VERSES' cannot be set for {book} {chapter} in the {version} version.")
                        raise ValueError(f"File not found at {file_path}. 'ALL_VERSES' cannot be set for {book} {chapter} in the {version} version.")
    else:
        for global_var in necessary_globals:
            if global_var is None:
                logger.error(f"{global_var.__name__} is None. 'ALL_VERSES' cannot be set.")
                raise ValueError(f"{global_var.__name__} is None. 'ALL_VERSES' cannot be set.")
        logger.error("One or more globals are not set.")
        raise ValueError("One or more globals are not set.")
    logger.info("Verses for each version, book, and chapter successfully set.")

def check_globals():
    """Check if the globals are set."""
    logger.info("Checking if the globals are set.")
    necessary_globals = [BIBLE_DATA_ROOT, VERSION_SELECTION, DEFAULT_VERSION, IN_ORDER_BOOKS, DEFAULT_BOOK, CHAPTER_SELECTION, DEFAULT_CHAPTER, ALL_VERSES]
    if all(global_var is not None and global_var != '' and global_var != [] and global_var != {} for global_var in necessary_globals):
        logger.info("All globals successfully set.")
        return
    else:
        for global_var in necessary_globals:
            if global_var is None:
                logger.error(f"{global_var.__name__} is None. 'check_globals' cannot be set.")
                raise ValueError(f"{global_var.__name__} is None. 'check_globals' cannot be set.")
        logger.error("One or more globals are not set.")
        raise ValueError("One or more globals are not set.")

set_bible_data_root()
set_version_selection()
set_default_version()
set_in_order_books()
set_default_book()
set_chapter_selection()
set_default_chapter()
set_all_verses()
check_globals()