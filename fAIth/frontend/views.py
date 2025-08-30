from django.shortcuts import render
import os
from pathlib import Path
from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse
import json

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
                print(f"Error: {e}")
                CHAPTER_SELECTION[book_title] = 0
        else:
            CHAPTER_SELECTION[book_title] = 0
else:
    print(f"Warning: Bible data directory not found or incomplete at {BIBLE_DATA_ROOT}. 'CHAPTER_SELECTION' may be incomplete.")
    # Initialize to prevent KeyErrors if data is missing
    for book_title in IN_ORDER_BOOKS:
        CHAPTER_SELECTION[book_title] = 0


def full_view(request, book, chapter, version):
    # Try to get the verses for the book and chapter
    try:
        # Process the version
        processed_version = version.lower()
        # Convert chapter from string to integer
        chapter = int(chapter)
        # Initialize the verses list
        verses = []
        # Get the file path
        file_path = BIBLE_DATA_ROOT / processed_version / book / f"{chapter}.json"

        # Check if the file exists
        if not file_path.exists():
            print(f"Error: Bible data file not found at {file_path}")
            # Consider a more user-friendly error page or redirect to a known good chapter/version
            return redirect(reverse('bible_book_view', args=['Genesis', '1', DEFAULT_VERSION]))

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

        # Get previous chapter and book
        if chapter - 1 <= 0 and book == IN_ORDER_BOOKS[0]:
            previous_book = IN_ORDER_BOOKS[-1]
            previous_chapter = CHAPTER_SELECTION[previous_book]
        elif chapter - 1 <= 0:
            previous_book = IN_ORDER_BOOKS[IN_ORDER_BOOKS.index(book) - 1]
            previous_chapter = CHAPTER_SELECTION[previous_book]
        else:
            previous_book = book
            previous_chapter = chapter - 1
        
        # Get next chapter and book
        if chapter + 1 > CHAPTER_SELECTION[book] and book == IN_ORDER_BOOKS[-1]:
            next_book = IN_ORDER_BOOKS[0]
            next_chapter = 1
        elif chapter + 1 > CHAPTER_SELECTION[book]:
            next_book = IN_ORDER_BOOKS[IN_ORDER_BOOKS.index(book) + 1]
            next_chapter = 1
        else:
            next_book = book
            next_chapter = chapter + 1

        # Pass the context to the template
        context = {
            # Current book, chapter, and version information
            'book': book,
            'chapter': chapter,
            'version': processed_version,
            'verses': verses,
            'current_book_chapters': range(1, CHAPTER_SELECTION[book] + 1),

            # Previous and next book and chapter information
            'previous_book': previous_book,
            'previous_chapter': previous_chapter,
            'next_book': next_book,
            'next_chapter': next_chapter,

            # All books, chapters, and versions information
            'in_order': IN_ORDER_BOOKS,
            'chapter_selection': CHAPTER_SELECTION,
            'version_selection': VERSION_SELECTION,
            
            # Current URL for navigation state
            'current_url': request.path_info,
        }
        return render(request, 'index.html', context)
    except FileNotFoundError:
        print(f"Error: Bible data file not found for {book} {chapter} ({processed_version}). Redirecting to default.")
        return redirect(reverse('default_view'))
    except Exception as e:
        print(f"Error in bible_book_view for {book} {chapter} ({processed_version}): {e}")
        # A more specific error handling or logging would be good here
        return redirect(reverse('default_view'))

def book_chapter_view(request, book, chapter):
    # Redirects to the versioned URL using the default version
    return redirect(reverse('full_view', args=[book, chapter, DEFAULT_VERSION]))

def book_view(request, book):
    # Redirect to a default Bible view, e.g., Genesis 1 in the default version
    return redirect(reverse('full_view', args=[book, 1, DEFAULT_VERSION]))

def default_view(request):
    # Redirect to a default Bible view, e.g., Genesis 1 in the default version
    return redirect(reverse('full_view', args=['Genesis', '1', DEFAULT_VERSION]))