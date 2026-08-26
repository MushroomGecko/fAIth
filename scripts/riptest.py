import asyncio
import json
import logging
from pathlib import Path
from typing import Any

BIBLE_DATA_ROOT = Path("fAIth") / "bible_data"

logger = logging.getLogger(__name__)


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


if __name__ == "__main__":
    results = asyncio.run(ripgrep_bible("Joshua", "bsb"))
    print(json.dumps(results, indent=4))
