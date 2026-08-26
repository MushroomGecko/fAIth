"""Print a detailed WordNet report for a word."""

import os

from dotenv import load_dotenv

load_dotenv()
if "WN_DATA_DIR" in os.environ:
    os.environ["WN_DATA_DIR"] = os.path.expanduser(os.environ["WN_DATA_DIR"])

import wn


LEXICON = "oewn:2025+"
WORD = "Jesus"


def synset_report(synset: wn.Synset) -> None:
    """Print definitions, examples, and relationships for one synset."""
    print(f"\n[{synset.id}] {synset.pos} - {synset.lexfile()}")
    print(f"Definition: {synset.definition()}")

    examples = synset.examples()
    print(f"Examples: {examples or '(none recorded)'}")
    print(f"Lemmas: {', '.join(synset.lemmas()) or '(none)'}")

    relations = {
        "Hypernyms": synset.hypernyms(),
        "Hyponyms": synset.hyponyms(),
        "Meronyms": synset.meronyms(),
        "Holonyms": synset.holonyms(),
    }
    for name, related_synsets in relations.items():
        if related_synsets:
            print(f"{name}:")
            for related in related_synsets:
                print(f"  - {related.id}: {related.definition()}")
        else:
            print(f"{name}: (none)")


def main() -> None:
    """Download the configured lexicon and print a detailed word report."""
    wn.download(LEXICON)
    wordnet = wn.Wordnet(LEXICON)
    word_entries = wordnet.words(WORD)
    synsets = wordnet.synsets(WORD)

    print(f"Word: {WORD}")
    print(f"Lexicon: {LEXICON}")
    print(f"Word entries found: {len(word_entries)}")
    print(f"Synsets found: {len(synsets)}")

    if not word_entries:
        print("\nNo matching word entries were found.")
        return

    print("\nWord-entry details:")
    for entry in word_entries:
        print(f"- Lemma: {entry.lemma()}")
        print(f"  Part of speech: {entry.pos}")
        print(f"  Forms: {', '.join(entry.forms()) or '(none)'}")
        print(f"  Synset IDs: {', '.join(s.id for s in entry.synsets())}")

    print("\nSynset details:")
    for synset in synsets:
        synset_report(synset)


if __name__ == "__main__":
    main()