import re

# Splits verse HTML into tags, entities, and single characters.
TOKEN_PATTERN = re.compile(r"(?P<tag><[^>]*>)|(?P<entity>&[#\w]+;)|(?P<char>.)", re.DOTALL)


def _open_mark(color):
    return f'<mark class="highlight" style="background-color: {color};">'


def apply_highlights(verse_html, highlights):
    """
    Wrap highlighted characters of a verse's HTML in <mark> tags.

    Each highlight gets its own <mark>. Where highlights overlap, the marks nest, and the later highlight
    is the inner mark, so it shows on top of the earlier one.

    Offsets count visible characters only, not HTML tags, and an HTML entity (e.g. &amp;) counts as one character.
    This matches the browser's textContent for the verse, which is what text_selection.js measures.

    Parameters:
        verse_html (str): The verse HTML, e.g. '1) In the <span class="header">...</span> beginning'.
        highlights (list[tuple[int, int, str]]): (beginning, end, hex color), oldest first.

    Returns:
        str: The verse HTML with <mark> tags around the highlighted text. Tags are never placed inside a <mark>.
    """
    if not highlights:
        return verse_html

    # For each visible character index, the highlights covering it, oldest first (outermost mark first)
    covering = {}
    for highlight_id, (beginning, end, _color) in enumerate(highlights):
        for index in range(beginning, end):
            covering.setdefault(index, []).append(highlight_id)

    output = []
    open_marks = []  # Highlight ids of the <mark> tags that are open now, outermost first
    visible_index = 0

    for match in TOKEN_PATTERN.finditer(verse_html):
        if match.lastgroup == "tag":
            # Close every mark before a tag, so no tag is inside a <mark>
            output.append("</mark>" * len(open_marks))
            open_marks = []
            output.append(match.group())
            continue

        wanted = covering.get(visible_index, [])

        # Keep the marks that still apply to this character, and close the rest
        keep = 0
        while keep < min(len(open_marks), len(wanted)) and open_marks[keep] == wanted[keep]:
            keep += 1
        output.append("</mark>" * (len(open_marks) - keep))
        open_marks = open_marks[:keep]

        # Open the marks this character needs, outermost first
        for highlight_id in wanted[keep:]:
            output.append(_open_mark(highlights[highlight_id][2]))
            open_marks.append(highlight_id)

        output.append(match.group())
        visible_index += 1

    output.append("</mark>" * len(open_marks))
    return "".join(output)
