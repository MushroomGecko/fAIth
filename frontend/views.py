import os
from frontend.globals import BIBLE_DATA_ROOT, DEFAULT_VERSION, DEFAULT_BOOK, DEFAULT_CHAPTER, IN_ORDER_BOOKS, CHAPTER_SELECTION, VERSION_SELECTION, ALL_VERSES
import asyncio
from frontend.utils import async_parse_verses, async_redirect, async_render

# Set up logging
import logging
logger = logging.getLogger(__name__)

async def full_view(request, book, chapter, version):
    """Async view for the full Bible view for the given book, chapter, and version."""
    # Try to get the verses for the book and chapter
    try:
        # Validate book
        if book is None or book not in IN_ORDER_BOOKS or book not in CHAPTER_SELECTION:
            logger.warning(f"Invalid book: {book}. Redirecting to default.")
            return await async_redirect('full_view', args=[DEFAULT_BOOK, DEFAULT_CHAPTER, DEFAULT_VERSION])

        # Validate chapter
        try:
            chapter = int(chapter)
            if chapter < 1 or chapter > CHAPTER_SELECTION[book]:
                logger.warning(f"Invalid chapter: {chapter}. Redirecting to first chapter.")
                return await async_redirect('full_view', args=[book, 1, DEFAULT_VERSION])
        except (ValueError, TypeError):
            logger.warning(f"Invalid chapter format: {chapter}. Expected integer. Redirecting to first chapter.")
            return await async_redirect('full_view', args=[book, 1, DEFAULT_VERSION])

        # Validate version
        processed_version = version.lower()
        if processed_version is None or processed_version not in VERSION_SELECTION:
            logger.warning(f"Invalid version: {processed_version}. Redirecting to default.")
            return await async_redirect('full_view', args=[book, chapter, DEFAULT_VERSION])

        # Get the file path
        file_path = os.path.join(BIBLE_DATA_ROOT, processed_version, book, f"{chapter}.json")

        # Check if the file exists
        file_exists = await asyncio.to_thread(os.path.exists, file_path)
        if not file_exists:
            logger.error(f"Error: Bible data file not found at {file_path}")
            return await async_redirect('full_view', args=[DEFAULT_BOOK, DEFAULT_CHAPTER, DEFAULT_VERSION])

        verses = ALL_VERSES[processed_version][book][chapter]

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
        
        return await async_render(request, 'index.html', context)
    
    except Exception as e:
        logger.error(f"Unexpected error in full_view for {book} {chapter} ({processed_version}): {e}")
        return await async_redirect('full_view', args=[DEFAULT_BOOK, DEFAULT_CHAPTER, DEFAULT_VERSION])

async def book_chapter_view(request, book, chapter):
    """Async view for the book and chapter view for the given book and chapter."""
    # Validate book exists before redirecting
    if book not in IN_ORDER_BOOKS:
        logger.warning(f"Invalid book in book_chapter_view: {book}")
        return await async_redirect('full_view', args=[DEFAULT_BOOK, DEFAULT_CHAPTER, DEFAULT_VERSION])
    
    # Validate chapter format
    try:
        chapter = int(chapter)
        if chapter < 1 or chapter > CHAPTER_SELECTION[book]:
            logger.warning(f"Invalid chapter in book_chapter_view: {chapter} for book: {book}")
            return await async_redirect('full_view', args=[book, DEFAULT_CHAPTER, DEFAULT_VERSION])
    except Exception as e:
        logger.warning(f"Invalid chapter format in book_chapter_view: {chapter} for book: {book}")
        return await async_redirect('full_view', args=[book, DEFAULT_CHAPTER, DEFAULT_VERSION])
    
    # Redirects to the versioned URL using the default version
    return await async_redirect('full_view', args=[book, chapter, DEFAULT_VERSION])

async def book_view(request, book):
    """Async view for the book view for the given book."""
    # Validate book exists before redirecting
    if book not in IN_ORDER_BOOKS:
        logger.warning(f"Invalid book in book_view: {book}")
        return await async_redirect('full_view', args=[DEFAULT_BOOK, DEFAULT_CHAPTER, DEFAULT_VERSION])
    
    # Redirect to a default Bible view
    return await async_redirect('full_view', args=[book, 1, DEFAULT_VERSION])

async def default_view(request):
    """Async view for the default view for the Bible."""
    # Redirect to the default Bible view
    return await async_redirect('full_view', args=[DEFAULT_BOOK, DEFAULT_CHAPTER, DEFAULT_VERSION])