import asyncio
import logging
from pathlib import Path

import markdown

# Set up logging
logger = logging.getLogger(__name__)


async def async_read_file(file_path, encoding='utf-8'):
    """
    Asynchronously read a file without blocking the event loop.

    Parameters:
        file_path (str or Path): Path to the file to read.
        encoding (str): File encoding (default: 'utf-8').

    Returns:
        str: File contents, or None if an error occurs.
    """
    try:
        def read_sync():
            with Path(file_path).open("r", encoding=encoding) as file:
                return file.read()
        return await asyncio.to_thread(read_sync)
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        return None


async def stringify_vdb_results(vdb_results):
    """
    Format vector database search results into a human-readable string.

    Extracts text and metadata from each result and formats them as:
    "{text} ({book} {chapter}:{verse} {version})"

    Each result is joined with newlines for readability.

    Parameters:
        vdb_results (list): Search results from Milvus vector database.
            Expected format: [{"entity": {"text": "...", "book": "...", ...}}, ...]

    Returns:
        str: Formatted result string, or "No results found" if invalid or empty.
    """
    if isinstance(vdb_results, list):
        try:
            result_strings = []
            for result in vdb_results:
                entity = result.get("entity", {})
                if entity:
                    # Extract metadata from result
                    text = entity.get("text", "")
                    book = entity.get("book", "")
                    chapter = entity.get("chapter", "")
                    verse = entity.get("verse", "")
                    version = entity.get("version", "")
                    # Format as "text (book chapter:verse version)"
                    result_string = f"{text} ({book} {chapter}:{verse} {version})"
                    result_strings.append(result_string)
            return "\n".join(result_strings)
        except Exception as e:
            logger.error(f"Error stringifying vector database results: {e}")
            return "No results found"
    else:
        logger.error(f"Invalid vector database results: {vdb_results}")
        return "No results found"


async def clean_llm_output(text: str) -> str:
    """
    Clean and format LLM output for HTML display.

    Processes the text by:
    1. Converting markdown syntax to HTML
    2. Removing newlines for cleaner HTML rendering

    Parameters:
        text (str): Raw LLM output text (may contain markdown).

    Returns:
        str: HTML-formatted string ready for display.
    """
    cleaned_text = str(text)

    # Convert markdown syntax to HTML
    cleaned_text = await asyncio.to_thread(markdown.markdown, cleaned_text)

    # Remove newlines for better HTML rendering (newlines don't matter in HTML)
    cleaned_text = cleaned_text.replace('\n', '')

    return cleaned_text
