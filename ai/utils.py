import asyncio
import markdown
from pathlib import Path

async def async_read_file(file_path, encoding='utf-8'):
    """Async wrapper for reading a file."""
    try:
        def read_sync():
            with Path(file_path).open("r", encoding=encoding) as file:
                return file.read()
        return await asyncio.to_thread(read_sync)
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        return None

async def stringify_vdb_results(vdb_results):
    """Async wrapper for stringifying the vector database results."""
    if isinstance(vdb_results, list):
        try:
            result_strings = []
            for result in vdb_results:
                entity = result.get("entity", {})
                if entity:
                    text = entity.get("text", "")
                    book = entity.get("book", "")
                    chapter = entity.get("chapter", "")
                    verse = entity.get("verse", "")
                    version = entity.get("version", "")
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
    Clean LLM output by converting escaped newlines and other escape sequences
    to their actual characters. This ensures markdown processing works correctly.
    """
    cleaned_text = str(text)

    # Convert Markdown to HTML
    cleaned_text = await asyncio.to_thread(markdown.markdown, cleaned_text)

    # Remove newlines for better HTML formatting
    cleaned_text = cleaned_text.replace('\n', '')

    return cleaned_text
