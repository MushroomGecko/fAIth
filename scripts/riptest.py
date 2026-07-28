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
        search_path = BIBLE_DATA_ROOT / collection_name
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
        stdout, stderr = await process.communicate()

        # ripgrep returns 1 when no matches are found and 2 for an error.
        if process.returncode not in (0, 1):
            logger.error("ripgrep failed: %s", stderr.decode().strip())
            return []

        response = stdout.decode().splitlines()
        results = []
        for line in response:
            record = json.loads(line)
            if record.get("type") != "match":
                continue
            data = record["data"]
            path = Path(data["path"]["text"])
            content = data["lines"]["text"].strip().rstrip(",")
            # Convert: '"15": "Verse text"' into a one-item dictionary
            verse_data = json.loads("{" + content + "}")
            verse, text = next(iter(verse_data.items()))

            # An error usually means that the verse is a heading, so we skip it.
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
