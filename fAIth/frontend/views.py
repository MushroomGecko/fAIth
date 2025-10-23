from django.shortcuts import render
from django.shortcuts import redirect
from django.urls import reverse
from asgiref.sync import sync_to_async
from frontend.globals import BIBLE_DATA_ROOT, DEFAULT_VERSION, IN_ORDER_BOOKS, CHAPTER_SELECTION, VERSION_SELECTION, ALL_VERSES
import asyncio
from frontend.utils import async_parse_verses

# Set up logging
import logging
logger = logging.getLogger(__name__)

async def async_render(request, template, context):
    """Async wrapper for rendering a template."""
    return await sync_to_async(render, thread_sensitive=False)(request, template, context)

async def async_redirect(url, args=[]):
    """Async wrapper for redirecting to a URL."""
    return await sync_to_async(redirect, thread_sensitive=False)(reverse(url, args=args))

async def full_view(request, book, chapter, version):
    """Async view for the full Bible view for the given book, chapter, and version."""
    # Try to get the verses for the book and chapter
    try:
        # Process the version
        processed_version = version.lower()
        # Convert chapter from string to integer
        chapter = int(chapter)
        # Get the file path
        file_path = BIBLE_DATA_ROOT / processed_version / book / f"{chapter}.json"

        # Check if the file exists
        file_exists = await asyncio.to_thread(file_path.exists)
        if not file_exists:
            logger.error(f"Error: Bible data file not found at {file_path}")
            # Consider a more user-friendly error page or redirect to a known good chapter/version
            return await async_redirect('full_view', args=['Genesis', '1', DEFAULT_VERSION])

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
    except FileNotFoundError:
        logger.error(f"Error: Bible data file not found for {book} {chapter} ({processed_version}). Redirecting to default.")
        return await async_redirect('default_view')
    except Exception as e:
        logger.error(f"Error in bible_book_view for {book} {chapter} ({processed_version}): {e}")
        # A more specific error handling or logging would be good here
        return await async_redirect('default_view')

async def book_chapter_view(request, book, chapter):
    """Redirect to the given book and chapter in the default version."""
    return await async_redirect('full_view', args=[book, chapter, DEFAULT_VERSION])

async def book_view(request, book):
    """Redirect to chapter 1 of the given book in the default version."""
    return await async_redirect('full_view', args=[book, 1, DEFAULT_VERSION])

async def default_view(request):
    """Redirect to Genesis 1 in the default version."""
    return await async_redirect('full_view', args=['Genesis', '1', DEFAULT_VERSION])