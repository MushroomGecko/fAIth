"""
Global configuration module for the Bible data application.

This module initializes and manages global variables that store Bible metadata and content.
All global variables must be initialized in the correct order, as they have dependencies.

Global Variables:
    BIBLE_DATA_ROOT (Path): Root directory containing Bible data files.
    DEFAULT_VERSION (str): Default Bible version to display.
    DEFAULT_BOOK (str): Default book to display.
    DEFAULT_CHAPTER (int): Default chapter to display.
    VERSION_SELECTION (list): Available Bible versions.
    IN_ORDER_BOOKS (list): All 66 Bible books in canonical order.
    CHAPTER_SELECTION (dict): Maps book names to chapter counts.
    ALL_VERSES (dict): Complete nested dict of all verses: {version: {book: {chapter: {verse_num: verse_text}}}}.
"""

import json
import logging
import os

from django.conf import settings

# Set up logging
logger = logging.getLogger(__name__)

# Global configuration variables - must be initialized in order
BIBLE_DATA_ROOT = None
DEFAULT_VERSION = ''
DEFAULT_BOOK = ''
DEFAULT_CHAPTER = ''
VERSION_SELECTION = []
IN_ORDER_BOOKS = []
CHAPTER_SELECTION = {}
ALL_VERSES = {}

def set_bible_data_root():
    """
    Set the root directory for Bible data files.

    This is the first function that must be called during initialization.
    It sets BIBLE_DATA_ROOT to {Django BASE_DIR}/fAIth/bible_data.

    Raises:
        ValueError: If the directory cannot be set.
    """
    global BIBLE_DATA_ROOT
    try:
        BIBLE_DATA_ROOT = settings.BASE_DIR.joinpath('fAIth', 'bible_data')
    except Exception as e:
        logger.error(f"Error: {e}. 'BIBLE_DATA_ROOT' cannot be set.")
        raise ValueError(f"Error: {e}. 'BIBLE_DATA_ROOT' cannot be set.")

def set_version_selection():
    """
    Set available Bible versions from the filesystem and ENABLED_VERSIONS env var.

    Reads the ENABLED_VERSIONS environment variable (JSON array) and filters it
    against actual directories in BIBLE_DATA_ROOT. If ENABLED_VERSIONS is empty or
    contains invalid versions, all versions in the filesystem are used.

    Dependencies:
        BIBLE_DATA_ROOT must be set first.

    Raises:
        ValueError: If dependencies are not met or no versions are available.
    """
    global VERSION_SELECTION
    logger.info("Setting available versions.")
    try:
        # Check that BIBLE_DATA_ROOT was initialized
        if not BIBLE_DATA_ROOT or not BIBLE_DATA_ROOT.exists():
            logger.error("'BIBLE_DATA_ROOT' is not set or does not exist. Cannot set 'VERSION_SELECTION'.")
            raise ValueError("'BIBLE_DATA_ROOT' is not set or does not exist. Cannot set 'VERSION_SELECTION'.")
        
        # Get enabled versions from environment or use empty list
        enabled_versions = json.loads(str(os.getenv("ENABLED_VERSIONS", "[]")).strip())
        available_versions = [item.name for item in BIBLE_DATA_ROOT.iterdir()]
        
        # Filter to only versions that exist in filesystem
        valid_versions = []
        for version in enabled_versions:
            if version in available_versions:
                valid_versions.append(version)
            else:
                logger.warning(f"Version {version} not found in the filesystem. Not including in the list of valid versions.")
        
        # If no enabled versions are valid, use all available versions
        if not valid_versions:
            logger.warning("No valid versions found in `ENABLED_VERSIONS` environment variable. Including all versions in the filesystem.")
            valid_versions = available_versions
        VERSION_SELECTION = valid_versions
    except Exception as e:
        logger.error(f"Error: {e}. Global variable 'VERSION_SELECTION' cannot be set.")
        raise ValueError(f"Error: {e}. Global variable 'VERSION_SELECTION' cannot be set.")
    logger.info(f"Available versions successfully set to {VERSION_SELECTION}.")

def set_default_version():
    """
    Set the default Bible version from the DEFAULT_VERSION env var.

    Validates that the configured default version exists in VERSION_SELECTION.
    If the configured version doesn't exist, defaults to the first available version.

    Dependencies:
        VERSION_SELECTION must be set first.

    Raises:
        ValueError: If dependencies are not met.
    """
    global DEFAULT_VERSION
    logger.info("Setting default version.")
    try:
        # Ensure VERSION_SELECTION has been initialized
        if not VERSION_SELECTION:
            logger.error("'VERSION_SELECTION' is not set. Cannot set 'DEFAULT_VERSION'.")
            raise ValueError("'VERSION_SELECTION' is not set. Cannot set 'DEFAULT_VERSION'.")
        
        # Get default version from environment or use 'bsb' as fallback
        DEFAULT_VERSION = str(os.getenv("DEFAULT_VERSION", "bsb")).strip()
        if DEFAULT_VERSION not in VERSION_SELECTION:
            logger.warning(f"Default version {DEFAULT_VERSION} is not in the list of available versions. Defaulting to first version in the list.")
            DEFAULT_VERSION = VERSION_SELECTION[0]
    except Exception as e:
        logger.error(f"Error: {e}. 'DEFAULT_VERSION' cannot be set.")
        raise ValueError(f"Error: {e}. 'DEFAULT_VERSION' cannot be set.")
    logger.info(f"Default version successfully set to {DEFAULT_VERSION}.")

def set_in_order_books():
    """
    Set the canonical list of 66 Bible books in order.

    This is a static list hardcoded in order: Old Testament (39 books) followed
    by New Testament (27 books). This list is used as the source of truth for
    book order throughout the application.

    Raises:
        None: This function always succeeds.
    """
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
    """
    Set the default book from the DEFAULT_BOOK env var.

    Validates that the configured default book exists in IN_ORDER_BOOKS.
    If the configured book doesn't exist, defaults to the first book (Genesis).

    Dependencies:
        IN_ORDER_BOOKS must be set first.

    Raises:
        ValueError: If dependencies are not met.
    """
    global DEFAULT_BOOK
    logger.info("Setting default book.")
    try:
        # Ensure IN_ORDER_BOOKS has been initialized
        if not IN_ORDER_BOOKS:
            logger.error("'IN_ORDER_BOOKS' is not set. Cannot set 'DEFAULT_BOOK'.")
            raise ValueError("'IN_ORDER_BOOKS' is not set. Cannot set 'DEFAULT_BOOK'.")
        
        # Get default book from environment or use 'Genesis' as fallback
        DEFAULT_BOOK = str(os.getenv("DEFAULT_BOOK", "Genesis")).strip()
        if DEFAULT_BOOK not in IN_ORDER_BOOKS:
            logger.warning(f"Default book {DEFAULT_BOOK} is not in the list of available books. Defaulting to first book in the list.")
            DEFAULT_BOOK = IN_ORDER_BOOKS[0]
    except Exception as e:
        logger.error(f"Error: {e}. 'DEFAULT_BOOK' cannot be set.")
        raise ValueError(f"Error: {e}. 'DEFAULT_BOOK' cannot be set.")
    logger.info(f"Default book successfully set to {DEFAULT_BOOK}.")

def set_chapter_selection():
    """
    Build a mapping of book names to chapter counts by scanning the filesystem.

    Iterates through each book in IN_ORDER_BOOKS and counts the JSON chapter files
    in the DEFAULT_VERSION directory. Only numeric filenames (e.g., "1.json", "2.json")
    are counted as valid chapters.

    Dependencies:
        BIBLE_DATA_ROOT, DEFAULT_VERSION, and IN_ORDER_BOOKS must be set first.

    Raises:
        ValueError: If dependencies are not met or files are missing.
    """
    global CHAPTER_SELECTION
    logger.info("Setting number of chapters in each book.")
    try:
        # Verify all dependencies are initialized
        if not BIBLE_DATA_ROOT or not BIBLE_DATA_ROOT.exists():
            logger.error("'BIBLE_DATA_ROOT' is not set or does not exist. Cannot set 'CHAPTER_SELECTION'.")
            raise ValueError("'BIBLE_DATA_ROOT' is not set or does not exist. Cannot set 'CHAPTER_SELECTION'.")
        if not DEFAULT_VERSION:
            logger.error("'DEFAULT_VERSION' is not set. Cannot set 'CHAPTER_SELECTION'.")
            raise ValueError("'DEFAULT_VERSION' is not set. Cannot set 'CHAPTER_SELECTION'.")
        if not IN_ORDER_BOOKS:
            logger.error("'IN_ORDER_BOOKS' is not set. Cannot set 'CHAPTER_SELECTION'.")
            raise ValueError("'IN_ORDER_BOOKS' is not set. Cannot set 'CHAPTER_SELECTION'.")
        
        # Verify the default version directory exists
        default_version_path = BIBLE_DATA_ROOT.joinpath(DEFAULT_VERSION)
        if not default_version_path.exists():
            logger.error(f"Default version directory not found at {default_version_path}. 'CHAPTER_SELECTION' cannot be set.")
            raise ValueError(f"Default version directory not found at {default_version_path}. 'CHAPTER_SELECTION' cannot be set.")
        
        # Scan each book directory and count chapters
        for book_title in IN_ORDER_BOOKS:
            book_path = BIBLE_DATA_ROOT.joinpath(DEFAULT_VERSION, book_title)
            if book_path.exists() and book_path.is_dir():
                # Count JSON files with numeric names (chapters)
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
    """
    Set the default chapter from the DEFAULT_CHAPTER env var.

    Validates that the configured default chapter is within the valid chapter range
    for DEFAULT_BOOK. If the configured chapter is invalid, an error is raised
    (no automatic fallback for chapter).

    Dependencies:
        CHAPTER_SELECTION and DEFAULT_BOOK must be set first.

    Raises:
        ValueError: If dependencies are not met or chapter is out of range.
    """
    global DEFAULT_CHAPTER
    logger.info("Setting default chapter.")
    try:
        # Ensure dependencies have been initialized
        if not CHAPTER_SELECTION:
            logger.error("'CHAPTER_SELECTION' is not set. Cannot set 'DEFAULT_CHAPTER'.")
            raise ValueError("'CHAPTER_SELECTION' is not set. Cannot set 'DEFAULT_CHAPTER'.")
        if not DEFAULT_BOOK:
            logger.error("'DEFAULT_BOOK' is not set. Cannot set 'DEFAULT_CHAPTER'.")
            raise ValueError("'DEFAULT_BOOK' is not set. Cannot set 'DEFAULT_CHAPTER'.")
        
        # Get default chapter from environment or use 1 as fallback
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
    """
    Load all Bible verses from JSON files into memory.

    Builds a nested dictionary structure: ALL_VERSES[version][book][chapter][verse_num] = verse_text
    For each chapter file, numeric keys are formatted as verse numbers ("1) text"),
    while non-numeric keys (headers) are wrapped in HTML span tags.

    Dependencies:
        BIBLE_DATA_ROOT, VERSION_SELECTION, IN_ORDER_BOOKS, and CHAPTER_SELECTION must be set first.

    Raises:
        ValueError: If dependencies are not met or files are missing.
    """
    global ALL_VERSES
    logger.info("Setting verses for each version, book, and chapter.")
    try:
        # Verify all dependencies are initialized
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
        
        # Load verses for each version, book, and chapter
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
                                try:
                                    # Numeric keys are verse numbers; format as "1) text"
                                    ALL_VERSES[version][book][chapter][verse_num] = f'{int(verse_num)}) {verse_text}'
                                except Exception:
                                    # Non-numeric keys (e.g., header_1, header_2) are section headers
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
    """
    Verify all global variables have been properly initialized.

    Checks that all 8 critical globals are set:
    BIBLE_DATA_ROOT, VERSION_SELECTION, DEFAULT_VERSION, IN_ORDER_BOOKS,
    DEFAULT_BOOK, CHAPTER_SELECTION, DEFAULT_CHAPTER, and ALL_VERSES.

    Raises:
        ValueError: If any global is not initialized or is invalid.
    """
    logger.info("Checking if the globals are set.")
    try:
        # Verify each global variable
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
