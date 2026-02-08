import os
import json
from django.conf import settings
import logging

# Set up logging
logger = logging.getLogger(__name__)

BIBLE_DATA_ROOT = None
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
        BIBLE_DATA_ROOT = settings.BASE_DIR.joinpath('frontend', 'bible_data')
    except Exception as e:
        logger.error(f"Error: {e}. 'BIBLE_DATA_ROOT' cannot be set.")
        raise ValueError(f"Error: {e}. 'BIBLE_DATA_ROOT' cannot be set.")

def set_version_selection():
    """Set the available versions."""
    global VERSION_SELECTION
    logger.info("Setting available versions.")
    try:
        # Dependency checks
        if not BIBLE_DATA_ROOT or not BIBLE_DATA_ROOT.exists():
            logger.error("'BIBLE_DATA_ROOT' is not set or does not exist. Cannot set 'VERSION_SELECTION'.")
            raise ValueError("'BIBLE_DATA_ROOT' is not set or does not exist. Cannot set 'VERSION_SELECTION'.")
        
        enabled_versions = json.loads(str(os.getenv("ENABLED_VERSIONS", "[]")).strip())
        available_versions = [item.name for item in BIBLE_DATA_ROOT.iterdir()]
        
        # Filter out versions that don't exist in the filesystem
        valid_versions = []
        for version in enabled_versions:
            if version in available_versions:
                valid_versions.append(version)
            else:
                logger.warning(f"Version {version} not found in the filesystem. Not including in the list of valid versions.")
        
        if not valid_versions:
            logger.warning("No valid versions found in `ENABLED_VERSIONS` environment variable. Including all versions in the filesystem.")
            valid_versions = available_versions
        VERSION_SELECTION = valid_versions
    except Exception as e:
        logger.error(f"Error: {e}. Global variable 'VERSION_SELECTION' cannot be set.")
        raise ValueError(f"Error: {e}. Global variable 'VERSION_SELECTION' cannot be set.")
    logger.info(f"Available versions successfully set to {VERSION_SELECTION}.")

def set_default_version():
    """Set the default version."""
    global DEFAULT_VERSION
    logger.info("Setting default version.")
    try:
        # Dependency checks
        if not VERSION_SELECTION:
            logger.error("'VERSION_SELECTION' is not set. Cannot set 'DEFAULT_VERSION'.")
            raise ValueError("'VERSION_SELECTION' is not set. Cannot set 'DEFAULT_VERSION'.")
        
        DEFAULT_VERSION = str(os.getenv("DEFAULT_VERSION", "bsb")).strip()
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
    logger.info("Bible books successfully set in order.")

def set_default_book():
    """Set the default book."""
    global DEFAULT_BOOK
    logger.info("Setting default book.")
    try:
        # Dependency checks
        if not IN_ORDER_BOOKS:
            logger.error("'IN_ORDER_BOOKS' is not set. Cannot set 'DEFAULT_BOOK'.")
            raise ValueError("'IN_ORDER_BOOKS' is not set. Cannot set 'DEFAULT_BOOK'.")
        
        DEFAULT_BOOK = str(os.getenv("DEFAULT_BOOK", "Genesis")).strip()
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
    try:
        # Dependency checks
        if not BIBLE_DATA_ROOT or not BIBLE_DATA_ROOT.exists():
            logger.error("'BIBLE_DATA_ROOT' is not set or does not exist. Cannot set 'CHAPTER_SELECTION'.")
            raise ValueError("'BIBLE_DATA_ROOT' is not set or does not exist. Cannot set 'CHAPTER_SELECTION'.")
        if not DEFAULT_VERSION:
            logger.error("'DEFAULT_VERSION' is not set. Cannot set 'CHAPTER_SELECTION'.")
            raise ValueError("'DEFAULT_VERSION' is not set. Cannot set 'CHAPTER_SELECTION'.")
        if not IN_ORDER_BOOKS:
            logger.error("'IN_ORDER_BOOKS' is not set. Cannot set 'CHAPTER_SELECTION'.")
            raise ValueError("'IN_ORDER_BOOKS' is not set. Cannot set 'CHAPTER_SELECTION'.")
        
        default_version_path = BIBLE_DATA_ROOT.joinpath(DEFAULT_VERSION)
        if not default_version_path.exists():
            logger.error(f"Default version directory not found at {default_version_path}. 'CHAPTER_SELECTION' cannot be set.")
            raise ValueError(f"Default version directory not found at {default_version_path}. 'CHAPTER_SELECTION' cannot be set.")
        
        for book_title in IN_ORDER_BOOKS:
            book_path = BIBLE_DATA_ROOT.joinpath(DEFAULT_VERSION, book_title)
            if book_path.exists() and book_path.is_dir():
                # Count JSON files (chapters) in the book directory
                json_files = [file for file in book_path.iterdir() if file.suffix == '.json' and file.stem.isdigit()]
                CHAPTER_SELECTION[book_title] = len(json_files)
            else:
                logger.error(f"Book directory not found at {book_path}. 'CHAPTER_SELECTION' cannot be set.")
                raise ValueError(f"Book directory not found at {book_path}. 'CHAPTER_SELECTION' cannot be set.")
    except ValueError:
        raise
    except Exception as e:
        logger.error(f"Error: {e}. 'CHAPTER_SELECTION' cannot be set.")
        raise ValueError(f"Error: {e}. 'CHAPTER_SELECTION' cannot be set.")
    logger.info("Number of chapters in each book successfully set.")

def set_default_chapter():
    """Set the default chapter."""
    global DEFAULT_CHAPTER
    logger.info("Setting default chapter.")
    try:
        # Dependency checks
        if not CHAPTER_SELECTION:
            logger.error("'CHAPTER_SELECTION' is not set. Cannot set 'DEFAULT_CHAPTER'.")
            raise ValueError("'CHAPTER_SELECTION' is not set. Cannot set 'DEFAULT_CHAPTER'.")
        if not DEFAULT_BOOK:
            logger.error("'DEFAULT_BOOK' is not set. Cannot set 'DEFAULT_CHAPTER'.")
            raise ValueError("'DEFAULT_BOOK' is not set. Cannot set 'DEFAULT_CHAPTER'.")
        
        DEFAULT_CHAPTER = int(str(os.getenv("DEFAULT_CHAPTER", "1")).strip())
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
    try:
        if not BIBLE_DATA_ROOT or not BIBLE_DATA_ROOT.exists():
            logger.error("'BIBLE_DATA_ROOT' is not set or does not exist. Cannot set 'ALL_VERSES'.")
            raise ValueError("'BIBLE_DATA_ROOT' is not set or does not exist. Cannot set 'ALL_VERSES'.")
        if not VERSION_SELECTION:
            logger.error("'VERSION_SELECTION' is not set. Cannot set 'ALL_VERSES'.")
            raise ValueError("'VERSION_SELECTION' is not set. Cannot set 'ALL_VERSES'.")
        if not IN_ORDER_BOOKS:
            logger.error("'IN_ORDER_BOOKS' is not set. Cannot set 'ALL_VERSES'.")
            raise ValueError("'IN_ORDER_BOOKS' is not set. Cannot set 'ALL_VERSES'.")
        if not CHAPTER_SELECTION:
            logger.error("'CHAPTER_SELECTION' is not set. Cannot set 'ALL_VERSES'.")
            raise ValueError("'CHAPTER_SELECTION' is not set. Cannot set 'ALL_VERSES'.")
        
        for version in VERSION_SELECTION:
            version = version.lower()
            ALL_VERSES[version] = {}
            for book in IN_ORDER_BOOKS:
                ALL_VERSES[version][book] = {}
                for chapter in range(1, CHAPTER_SELECTION[book] + 1):
                    ALL_VERSES[version][book][chapter] = {}
                    file_path = BIBLE_DATA_ROOT.joinpath(version, book, f"{chapter}.json")
                    if file_path.exists():
                        with file_path.open("r", encoding="utf-8") as file:
                            json_data = json.load(file)
                            for verse_num, verse_text in json_data.items():
                                # The text is already properly formatted, no parsing needed, just add the verse number and get headers
                                try:
                                    # This should fail if verse_num is not an int (i.e. header_1, header_2, etc.)
                                    ALL_VERSES[version][book][chapter][verse_num] = f'{int(verse_num)}) {verse_text}'
                                except Exception:
                                    # If the exception occurs, we assume the verse_num is a header
                                    ALL_VERSES[version][book][chapter][verse_num] = f'<span class="header">{verse_text}</span>'
                    else:
                        logger.error(f"File not found at {file_path}. 'ALL_VERSES' cannot be set for {book} {chapter} in the {version} version.")
                        raise ValueError(f"File not found at {file_path}. 'ALL_VERSES' cannot be set for {book} {chapter} in the {version} version.")
    except ValueError:
        raise
    except Exception as e:
        logger.error(f"Error: {e}. 'ALL_VERSES' cannot be set.")
        raise ValueError(f"Error: {e}. 'ALL_VERSES' cannot be set.")
    logger.info("Verses for each version, book, and chapter successfully set.")

def check_globals():
    """Check if the globals are set."""
    logger.info("Checking if the globals are set.")
    try:
        if not BIBLE_DATA_ROOT or not BIBLE_DATA_ROOT.exists():
            logger.error("'BIBLE_DATA_ROOT' is not set or does not exist. Cannot verify globals.")
            raise ValueError("'BIBLE_DATA_ROOT' is not set or does not exist. Cannot verify globals.")
        if not VERSION_SELECTION:
            logger.error("'VERSION_SELECTION' is not set. Cannot verify globals.")
            raise ValueError("'VERSION_SELECTION' is not set. Cannot verify globals.")
        if not DEFAULT_VERSION:
            logger.error("'DEFAULT_VERSION' is not set. Cannot verify globals.")
            raise ValueError("'DEFAULT_VERSION' is not set. Cannot verify globals.")
        if not IN_ORDER_BOOKS:
            logger.error("'IN_ORDER_BOOKS' is not set. Cannot verify globals.")
            raise ValueError("'IN_ORDER_BOOKS' is not set. Cannot verify globals.")
        if not DEFAULT_BOOK:
            logger.error("'DEFAULT_BOOK' is not set. Cannot verify globals.")
            raise ValueError("'DEFAULT_BOOK' is not set. Cannot verify globals.")
        if not CHAPTER_SELECTION:
            logger.error("'CHAPTER_SELECTION' is not set. Cannot verify globals.")
            raise ValueError("'CHAPTER_SELECTION' is not set. Cannot verify globals.")
        if DEFAULT_CHAPTER == '':
            logger.error("'DEFAULT_CHAPTER' is not set. Cannot verify globals.")
            raise ValueError("'DEFAULT_CHAPTER' is not set. Cannot verify globals.")
        if not ALL_VERSES:
            logger.error("'ALL_VERSES' is not set. Cannot verify globals.")
            raise ValueError("'ALL_VERSES' is not set. Cannot verify globals.")
        
        logger.info("All globals successfully verified.")
    except ValueError:
        raise
    except Exception as e:
        logger.error(f"Error: {e}. Globals cannot be verified.")
        raise ValueError(f"Error: {e}. Globals cannot be verified.")
