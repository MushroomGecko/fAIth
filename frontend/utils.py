import json
import logging
import asyncio
from asgiref.sync import sync_to_async
from django.shortcuts import render, redirect
from django.urls import reverse

# Set up logging
logger = logging.getLogger(__name__)

def sync_parse_verses(file_path):
    """Synchronous wrapper for parsing verses without blocking the event loop."""
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
        if len(verses) == 0:
            logger.warning(f"No verses found in {file_path}")
        else:
            logger.info(f"Parsed {len(verses)} verses from {file_path} synchronously")
            logger.debug(f"First verse: {verses[0]}")
            logger.debug(f"Last verse: {verses[-1]}")
        return verses
    except Exception as e:
        logger.error(f"Error parsing verses: {e} in file {file_path} synchronously. Returning empty list.")
        return []

async def async_parse_verses(file_path):
    """Async wrapper for parsing verses without blocking the event loop."""
    try:
        verses = await asyncio.to_thread(sync_parse_verses, file_path)
        return verses
    except Exception as e:
        logger.error(f"Error: {e} asynchronously. Returning empty list.")
        return []

async def async_render(request, template, context):
    """Async wrapper for rendering a template."""
    return await sync_to_async(render, thread_sensitive=False)(request, template, context)

async def async_redirect(url, args=[]):
    """Async wrapper for redirecting to a URL."""
    return await sync_to_async(redirect, thread_sensitive=False)(reverse(url, args=args))