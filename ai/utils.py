import asyncio
import json
import logging
from pathlib import Path
from typing import Any
from django.http import HttpRequest
import httpx
import markdown
import wn
from fAIth.bible_globals import BIBLE_DATA_ROOT
from fAIth.settings import WORDNET_ENABLED, WORDNET_DOWNLOAD_VERSION
# Set up logging
logger = logging.getLogger(__name__)


def remove_newlines_whitespace(text: str) -> str:
    """
    Collapse blank/whitespace-only lines in text, preserving intentional newlines.

    Parameters:
        text (str): Text that may contain blank or whitespace-only lines.

    Returns:
        str: Text with blank/whitespace-only lines removed, newlines preserved between
            remaining lines.
    """
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())


async def async_read_file(file_path: str | Path, encoding: str = "utf-8") -> str | None:
    """
    Asynchronously read a file without blocking the event loop.

    Parameters:
        file_path (str | Path): Path to the file to read.
        encoding (str): File encoding (default: 'utf-8').

    Returns:
        str | None: File contents, or None if an error occurs.
    """
    try:

        def read_sync():
            with Path(file_path).open("r", encoding=encoding) as file:
                return file.read()

        return await asyncio.to_thread(read_sync)
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        return None


async def ripgrep_bible(query: str, collection_name: str) -> list[dict[str, Any]]:
    """
    Search the Bible using ripgrep.

    Parameters:
        query (str): The search query.
        collection_name (str): The name of the collection to search.

    Returns:
        list[dict[str, Any]]: Ripgrep's matching output, or an empty list if no matches/error.
    """
    try:
        # Restrict the search to the selected Bible translation directory.
        search_path = BIBLE_DATA_ROOT / collection_name

        # Run ripgrep asynchronously so the search does not block the event loop.
        process = await asyncio.create_subprocess_exec(
            "rg",
            "--no-heading",
            "--line-number",
            "--smart-case",
            "--fixed-strings",
            "--json",
            "--",
            query,
            str(search_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        # Wait for ripgrep to finish and collect both output streams.
        stdout, stderr = await process.communicate()

        # ripgrep returns 1 when no matches are found and 2 for an error.
        if process.returncode not in (0, 1):
            logger.error("ripgrep failed: %s", stderr.decode().strip())
            return []

        # Each line in ripgrep's JSON output represents an event or a match.
        response = stdout.decode().splitlines()
        results = []
        for line in response:
            record = json.loads(line)

            # Ignore summaries and other non-match events from ripgrep.
            if record.get("type") != "match":
                continue

            data = record["data"]
            path = Path(data["path"]["text"])
            content = data["lines"]["text"].strip().rstrip(",")

            # Convert: '"15": "Verse text"' into a one-item dictionary
            verse_data = json.loads("{" + content + "}")
            verse, text = next(iter(verse_data.items()))

            # Skip non-verse JSON entries, such as chapter headings.
            try:
                results.append(
                    {
                        "book": path.parent.name,
                        "chapter": int(path.stem),
                        "verse": int(verse),
                        "text": text,
                    }
                )
            except ValueError:
                continue

        return results
    except Exception as e:
        logger.error(f"Error searching Bible: {e}")
        return []

async def definition_query(word: str, request: HttpRequest) -> str:
    """
    Search WordNet for synsets defining a word.

    Parameters:
        word (str): The word to search for.
        request (HttpRequest): The HTTP request object.
    Returns:
        str: Formatted definitions and related synset words.
    """
    
    # Get the Wordnet object from the request state.
    wordnet_obj = request.state["wordnet_obj"]
    if not wordnet_obj:
        logger.warning("Wordnet object not initialized: WORDNET_ENABLED is False")
        return ""

    def format_all_definitions(word: str, wordnet_obj: wn.Wordnet) -> str:
        """
        Look up and format all WordNet definitions for a word.

        Parameters:
            word (str): The word to search for.

        Returns:
            str: Formatted definitions and related synset words.
        """

        def format_output(word: str, synset: wn.Synset) -> str:
            """
            Format the definition and relationships for a WordNet synset.

            Parameters:
                word (str): The word associated with the synset.
                synset (wn.Synset): The WordNet synset to format.

            Returns:
                str: Formatted synset information.
            """

            def format_examples(examples: list[str]) -> str:
                """
                Format a list of WordNet example sentences.

                Parameters:
                    examples (list[str]): Example sentences for a synset.

                Returns:
                    str: Formatted example sentences, or "(none)".
                """
                if not examples:
                    return "(none)"

                result_string = ""
                for example in examples:
                    result_string += f" - {example}\n"
                return "\n" + result_string.rstrip()

            def format_synset_words(synsets: list[wn.Synset]) -> str:
                """
                Format the lemma words for related WordNet synsets.

                Parameters:
                    synsets (list[wn.Synset]): Related synsets to format.

                Returns:
                    str: Comma-separated lemma words, or "(none)".
                """
                if not synsets:
                    return "(none)"

                result_string = ""
                for synset in synsets:
                    if not synset.lemmas():
                        result_string += "(unnamed)"
                    else:
                        result_string += ", ".join(synset.lemmas()) + " "

                return result_string.strip()

            return (
                f"Word: {word}\n"
                f"Part of speech: {synset.pos} ({synset.lexfile()})\n"
                f"Definition: {synset.definition()}\n"
                f"Examples: {format_examples(synset.examples())}\n"
                f"Lemmas: {', '.join(synset.lemmas()) or '(none)'}\n"
                f"Hypernyms: {format_synset_words(synset.hypernyms())}\n"
                f"Hyponyms: {format_synset_words(synset.hyponyms())}\n"
                f"Meronyms: {format_synset_words(synset.meronyms())}\n"
                f"Holonyms: {format_synset_words(synset.holonyms())}\n\n"
            )

        result_string = ""
        word_entries = wordnet_obj.words(word)
        if word_entries:
            for word_entry in word_entries:
                synsets = word_entry.synsets()
                if synsets:
                    for synset in synsets:
                        result_string += format_output(word, synset)
                else:
                    logger.warning(f"No synsets found for word: {word}")
                    return ""
        else:
            logger.warning(f"No synsets found for word: {word}")
            return ""
        return result_string

    try:
        return await asyncio.to_thread(
            format_all_definitions,
            word,
            wordnet_obj,
        )
    except Exception as error:
        logger.error(f"Error searching WordNet: {error}")
        return ""


async def unify_vdb_results(vdb_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Unify vector database search results by deduplicating entries with identical text content.

    Removes duplicate results that contain the same text, preserving the first occurrence
    of each unique text. This is useful when combining results from multiple searches
    where the same passage may be retrieved multiple times.

    Parameters:
        vdb_results (list[dict[str, Any]]): Search results from Milvus vector database.
            Expected format: [{"entity": {"text": "...", "book": "...", ...}}, ...]

    Returns:
        list[dict[str, Any]]: Unified search results with duplicates removed, or empty list if invalid or error occurs.
    """

    if isinstance(vdb_results, list):
        try:
            seen_texts = set()
            unified_results = []
            for result in vdb_results:
                entity = result.get("entity", {})
                if entity:
                    text = entity.get("text", "")
                    # Only add results with unique text content
                    if text and text not in seen_texts:
                        seen_texts.add(text)
                        unified_results.append(result)
            return unified_results
        except Exception as e:
            logger.error(f"Error unifying vector database results: {e}")
            return []
    else:
        logger.error(f"Invalid vector database results: {vdb_results}")
        return []


async def stringify_vdb_results(vdb_results: list[dict[str, Any]]) -> str:
    """
    Format vector database search results into a human-readable string.

    Extracts text and metadata from each result and formats them as:
    "{text} ({book} {chapter}:{verse} {version})"

    Each result is joined with newlines for readability.

    Parameters:
        vdb_results (list[dict[str, Any]]): Search results from Milvus vector database.
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
    cleaned_text = cleaned_text.replace("\n", "")

    return cleaned_text


async def search_for_images(selected_text: str, searxng_image_limit: int = 10) -> list[str]:
    """
    Search for images via the local SearXNG instance.

    Queries SearXNG's JSON API over the internal Docker network.
    Not accessible from outside the container network. Results are deduplicated
    and ranked by SearXNG across multiple image engines (Bing, DuckDuckGo,
    Google Images, etc.).

    Parameters:
        selected_text (str): The search query to find images for.
        searxng_image_limit (int): The maximum number of images to return.

    Returns:
        list[str]: Direct image URLs (img_src) from the search results.
            Empty strings are included where a result had no img_src.
    """
    # SearXNG is only reachable via Docker service name — not localhost
    url = "http://search-engine-core:8080/search"
    params = {
        "q": selected_text,
        "categories": "images",
        "format": "json",
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()

    # Extract direct image URLs from each result
    image_results = data.get("results", [])
    image_urls = []
    for result in image_results:
        img_src = result.get("img_src", "")
        if img_src:
            image_urls.append(img_src)

    return image_urls[:searxng_image_limit]
