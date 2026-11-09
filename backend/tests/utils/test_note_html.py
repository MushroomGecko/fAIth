from backend.utils.note_html import sanitize_note_html


class TestSanitizeNoteHtml:
    """Tests for sanitize_note_html function."""

    def test_empty_string_returns_empty_string(self):
        """Test that an empty value stays empty."""
        assert sanitize_note_html("") == ""

    def test_plain_text_is_unchanged(self):
        """Test that plain text with no markup is returned as-is."""
        assert sanitize_note_html("In the beginning") == "In the beginning"

    def test_wj_span_is_kept(self):
        """Test that the red words-of-Jesus span is kept."""
        html = '<span class="wj">“Now draw some out,”</span>'

        assert sanitize_note_html(html) == html

    def test_header_span_is_kept(self):
        """Test that the section header span is kept."""
        html = '<span class="header">Creation</span>'

        assert sanitize_note_html(html) == html

    def test_span_with_other_class_is_dropped_but_text_is_kept(self):
        """Test that a span with a class that isn't on the allow list loses its tags and keeps its text."""
        assert sanitize_note_html('<span class="evil">text</span>') == "text"

    def test_allowed_span_loses_extra_attributes(self):
        """Test that attributes such as onclick are removed from an allowed span."""
        result = sanitize_note_html('<span class="wj" onclick="alert(1)">words</span>')

        assert result == '<span class="wj">words</span>'

    def test_script_tag_is_dropped_and_its_text_is_escaped(self):
        """Test that script tags are removed, so they can't run when the note renders."""
        result = sanitize_note_html("<script>alert(1)</script>")

        assert "<script" not in result
        assert result == "alert(1)"

    def test_other_tags_are_dropped_and_text_is_kept(self):
        """Test that tags other than span and br are removed, and their text is kept."""
        assert sanitize_note_html("<b>bold</b> and <i>italic</i>") == "bold and italic"

    def test_img_tag_with_handler_is_dropped(self):
        """Test that an image tag with an event handler is removed entirely."""
        assert sanitize_note_html("<img src=x onerror=alert(1)>text") == "text"

    def test_br_is_kept(self):
        """Test that line breaks are kept, since selections across verses use them."""
        assert sanitize_note_html("first<br>second") == "first<br>second"

    def test_less_than_in_text_is_escaped(self):
        """Test that a plain '<' in text is escaped, so it can't start a tag."""
        assert sanitize_note_html("a <3 b") == "a &lt;3 b"

    def test_ampersand_in_text_is_escaped(self):
        """Test that an ampersand is escaped, so it renders as written."""
        assert sanitize_note_html("Tom & Jerry") == "Tom &amp; Jerry"

    def test_already_escaped_entities_are_not_double_escaped(self):
        """Test that an entity in the input is decoded once and then escaped once, so it shows as typed."""
        assert sanitize_note_html("&lt;b&gt;") == "&lt;b&gt;"
        assert sanitize_note_html("&amp;") == "&amp;"

    def test_quotes_are_not_escaped(self):
        """Test that quote characters are left alone in the text."""
        assert sanitize_note_html('He said "hi"') == 'He said "hi"'

    def test_nested_allowed_spans_are_kept(self):
        """Test that allowed spans nested inside each other are kept with their tags."""
        html = '<span class="wj">a<span class="header">b</span>c</span>'

        assert sanitize_note_html(html) == html

    def test_disallowed_span_inside_allowed_span_is_dropped(self):
        """Test that a disallowed span nested inside an allowed span loses its tags."""
        result = sanitize_note_html('<span class="wj"><span class="evil">a</span></span>')

        assert result == '<span class="wj">a</span>'

    def test_unclosed_allowed_span_is_closed(self):
        """Test that an allowed span left open gets its closing tag added."""
        assert sanitize_note_html('<span class="wj">open') == '<span class="wj">open</span>'

    def test_stray_closing_span_is_ignored(self):
        """Test that a closing span tag with no opening tag is dropped."""
        assert sanitize_note_html("x</span>y") == "xy"

    def test_whitespace_around_result_is_trimmed(self):
        """Test that leading and trailing whitespace is removed from the result."""
        assert sanitize_note_html("   hi   ") == "hi"

    def test_paragraph_tags_are_dropped_and_text_is_kept(self):
        """Test that paragraph tags from the verse HTML are removed and their text is kept."""
        assert sanitize_note_html("<p>one</p><p>two</p>") == "onetwo"
