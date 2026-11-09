from html import escape
from html.parser import HTMLParser

# Span classes that the verse HTML uses for formatting (e.g. red words of Jesus, section headers)
ALLOWED_SPAN_CLASSES = {"wj", "header"}


class _NoteHTMLSanitizer(HTMLParser):
    """
    Keeps only allowed spans and <br> tags. Every other tag is dropped, and all text is escaped.

    Each open <span> is recorded, so an end tag is only written if its start tag was written.
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.open_spans = []  # One entry per open span: True if it was written to the output

    def handle_starttag(self, tag, attrs):
        if tag == "span":
            span_class = dict(attrs).get("class")
            allowed = span_class in ALLOWED_SPAN_CLASSES
            if allowed:
                self.parts.append(f'<span class="{span_class}">')
            self.open_spans.append(allowed)
        elif tag == "br":
            self.parts.append("<br>")

    def handle_endtag(self, tag):
        if tag == "span" and self.open_spans:
            if self.open_spans.pop():
                self.parts.append("</span>")

    def handle_data(self, data):
        self.parts.append(escape(data, quote=False))

    def result(self):
        # Close any spans left open, innermost first
        closing = "".join("</span>" for allowed in reversed(self.open_spans) if allowed)
        return ("".join(self.parts) + closing).strip()


def sanitize_note_html(value):
    """
    Make HTML saved with a note safe to render with |safe.

    Parameters:
        value (str): HTML from the browser.

    Returns:
        str: HTML containing only allowed spans, <br> tags, and escaped text.
    """
    sanitizer = _NoteHTMLSanitizer()
    sanitizer.feed(value)
    sanitizer.close()
    return sanitizer.result()
