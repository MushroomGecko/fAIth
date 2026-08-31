"""Print a detailed WordNet report for a word."""

import asyncio
import logging
import os

import wn
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()
if "WN_DATA_DIR" in os.environ:
    os.environ["WN_DATA_DIR"] = os.path.expanduser(os.environ["WN_DATA_DIR"])


wn.config.allow_multithreading = True
WORDNET_ENABLED = True
WORDNET_DOWNLOAD_VERSION = "oewn:2025+"
WORD = "God"
wordnet_obj = wn.Wordnet(WORDNET_DOWNLOAD_VERSION)
logger.info("Wordnet object initialized")


async def definition_query(word: str, wordnet_obj: wn.Wordnet) -> str:
    """
    Search WordNet for synsets defining a word.

    Parameters:
        word (str): The word to search for.

    Returns:
        str: Formatted definitions and related synset words.
    """

    # Initialize the Wordnet object if it is usable.
    def format_all_definitions(word: str) -> str:
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
        )
    except Exception as error:
        logger.error(f"Error searching WordNet: {error}")
        return ""


async def main() -> None:
    """Download the configured lexicon and print a detailed word report."""
    print("\nDefinition-query output:")
    print(await definition_query(WORD, wordnet_obj))


if __name__ == "__main__":
    asyncio.run(main())
