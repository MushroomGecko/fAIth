def derive_boolean_from_string(string):
    """
    Derive a boolean value from a string.

    Parameters:
        string (str): The string to derive a boolean value from.

    Returns:
        bool: The boolean value derived from the string.
    """
    return bool(str(string).strip().lower() in ("1", "true", "yes"))


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
