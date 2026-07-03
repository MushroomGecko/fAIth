def derive_boolean_from_string(string):
    """
    Derive a boolean value from a string.

    Parameters:
        string (str): The string to derive a boolean value from.

    Returns:
        bool: The boolean value derived from the string.
    """
    return bool(str(string).strip().lower() in ("1", "true", "yes"))