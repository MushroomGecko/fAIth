import asyncio
import logging

from fAIth.bible_globals import BIBLE_DATA_ROOT, DEFAULT_VERSION, DEFAULT_BOOK, DEFAULT_CHAPTER, IN_ORDER_BOOKS, CHAPTER_SELECTION, VERSION_SELECTION, ALL_VERSES
from frontend.utils import async_redirect, async_render

# Set up logging
logger = logging.getLogger(__name__)

async def full_view(request, book, chapter, version):
    """
    Render the full Bible view for the given book, chapter, and version.

    Parameters:
        request: The HTTP request object.
        book (str): The name of the Bible book.
        chapter (int): The chapter number.
        version (str): The Bible version (e.g., 'kjv', 'niv').

    Returns:
        HttpResponse: Rendered HTML response with Bible verses and navigation context.
    """
    # Try to get the verses for the book and chapter
    try:
        # Validate book
        if book is None or book not in IN_ORDER_BOOKS or book not in CHAPTER_SELECTION:
            logger.warning(f"Invalid book: {book}. Redirecting to default.")
            # Return a redirect to the default book, chapter, and version
            return await async_redirect('full_view', args=[DEFAULT_BOOK, DEFAULT_CHAPTER, DEFAULT_VERSION])

        # Validate chapter
        try:
            chapter = int(chapter)
            if chapter < 1 or chapter > CHAPTER_SELECTION[book]:
                logger.warning(f"Invalid chapter: {chapter} in book: {book}. Redirecting to first chapter.")
                # Return a redirect to the full view with the given book, chapter 1, and default version
                return await async_redirect('full_view', args=[book, 1, DEFAULT_VERSION])
        except (ValueError, TypeError):
            logger.warning(f"Invalid chapter format: {chapter} in book: {book}. Expected integer. Redirecting to first chapter.")
            # Return a redirect to the full view with the given book, chapter 1, and default version
            return await async_redirect('full_view', args=[book, 1, DEFAULT_VERSION])

        # Validate version
        processed_version = version.lower()
        if processed_version is None or processed_version not in VERSION_SELECTION:
            logger.warning(f"Invalid version: {processed_version}. Redirecting to default.")
            # Return a redirect to the full view with the given book, chapter, and default version
            return await async_redirect('full_view', args=[book, chapter, DEFAULT_VERSION])

        # Get the file path
        file_path = BIBLE_DATA_ROOT.joinpath(processed_version, book, f"{chapter}.json")

        # Check if the file exists
        file_exists = await asyncio.to_thread(file_path.exists)
        if not file_exists:
            logger.error(f"Error: Bible data file not found at {file_path}")
            # Return a redirect to the default book, chapter, and version
            return await async_redirect('full_view', args=[DEFAULT_BOOK, DEFAULT_CHAPTER, DEFAULT_VERSION])

        # Get the verses for the book and chapter
        verses = ALL_VERSES[processed_version][book][chapter]

        # Get previous chapter and book
        if chapter - 1 <= 0 and book == IN_ORDER_BOOKS[0]:
            # Wrap around to end of Bible
            previous_book = IN_ORDER_BOOKS[-1]
            previous_chapter = CHAPTER_SELECTION[previous_book]
        elif chapter - 1 <= 0:
            # Move to last chapter of previous book
            previous_book = IN_ORDER_BOOKS[IN_ORDER_BOOKS.index(book) - 1]
            previous_chapter = CHAPTER_SELECTION[previous_book]
        else:
            # Previous chapter in same book
            previous_book = book
            previous_chapter = chapter - 1
        
        # Get next chapter and book
        if chapter + 1 > CHAPTER_SELECTION[book] and book == IN_ORDER_BOOKS[-1]:
            # Wrap around to start of Bible
            next_book = IN_ORDER_BOOKS[0]
            next_chapter = 1
        elif chapter + 1 > CHAPTER_SELECTION[book]:
            # Move to first chapter of next book
            next_book = IN_ORDER_BOOKS[IN_ORDER_BOOKS.index(book) + 1]
            next_chapter = 1
        else:
            # Next chapter in same book
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
        
        # Render the full view with the given context
        return await async_render(request, 'index.html', context)
    
    except Exception as e:
        logger.error(f"Unexpected error in full_view for {book} {chapter} ({processed_version}): {e}")
        # Return a redirect to the default book, chapter, and version
        return await async_redirect('full_view', args=[DEFAULT_BOOK, DEFAULT_CHAPTER, DEFAULT_VERSION])

async def book_chapter_view(request, book, chapter):
    """
    Redirect to the full view for the given book and chapter.

    Parameters:
        request: The HTTP request object.
        book (str): The name of the Bible book.
        chapter (int): The chapter number.

    Returns:
        HttpResponseRedirect: Redirect to full_view with default version.
    """
    try:
        # Validate book exists before redirecting
        if book not in IN_ORDER_BOOKS:
            logger.warning(f"Invalid book in book_chapter_view: {book}")
            # Return a redirect to the default book, chapter, and version
            return await async_redirect('full_view', args=[DEFAULT_BOOK, DEFAULT_CHAPTER, DEFAULT_VERSION])
        
        # Validate chapter format
        try:
            chapter = int(chapter)
            if chapter < 1 or chapter > CHAPTER_SELECTION[book]:
                logger.warning(f"Invalid chapter: {chapter} in book: {book}. Redirecting to first chapter.")
                # Return a redirect to the full view with the given book, chapter 1, and default version
                return await async_redirect('full_view', args=[book, 1, DEFAULT_VERSION])
        except (ValueError, TypeError):
            logger.warning(f"Invalid chapter format: {chapter} in book: {book}. Expected integer. Redirecting to first chapter.")
            # Return a redirect to the full view with the given book, chapter 1, and default version
            return await async_redirect('full_view', args=[book, 1, DEFAULT_VERSION])

        # Return a redirect to the full view with the given book, chapter, and default version
        return await async_redirect('full_view', args=[book, chapter, DEFAULT_VERSION])
    except Exception as e:
        logger.warning(f"Unexpected error in book_chapter_view for {book} {chapter}: {e}")
        # Return a redirect to the default book, chapter, and version
        return await async_redirect('full_view', args=[DEFAULT_BOOK, DEFAULT_CHAPTER, DEFAULT_VERSION])

async def book_view(request, book):
    """
    Redirect to the full view for the given book at chapter 1.

    Parameters:
        request: The HTTP request object.
        book (str): The name of the Bible book.

    Returns:
        HttpResponseRedirect: Redirect to full_view with chapter 1 and default version.
    """
    try:
        # Validate book exists before redirecting
        if book not in IN_ORDER_BOOKS:
            logger.warning(f"Invalid book in book_view: {book}")
            # Return a redirect to the default book, chapter, and version
            return await async_redirect('full_view', args=[DEFAULT_BOOK, DEFAULT_CHAPTER, DEFAULT_VERSION])
        
        # Return a redirect to the full view with the given book, chapter 1, and default version
        return await async_redirect('full_view', args=[book, 1, DEFAULT_VERSION])
    except Exception as e:
        logger.error(f"Unexpected error in book_view for {book}: {e}")
        # Return a redirect to the default book, chapter, and version
        return await async_redirect('full_view', args=[DEFAULT_BOOK, DEFAULT_CHAPTER, DEFAULT_VERSION])

async def default_view(request):
    """
    Redirect to the default Bible view.

    Parameters:
        request: The HTTP request object.

    Returns:
        HttpResponseRedirect: Redirect to full_view with default book, chapter, and version.
    """
    # Return a redirect to the default book, chapter, and version
    return await async_redirect('full_view', args=[DEFAULT_BOOK, DEFAULT_CHAPTER, DEFAULT_VERSION])