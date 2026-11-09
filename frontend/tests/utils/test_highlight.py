from frontend.utils.highlight import apply_highlights

YELLOW = "#FFFF00"
PINK = "#FF69B4"
BLUE = "#00BFFF"


def mark(color):
    """Return the opening <mark> tag that apply_highlights writes for a color."""
    return f'<mark class="highlight" style="background-color: {color};">'


CLOSE = "</mark>"


class TestApplyHighlights:
    """Tests for apply_highlights function."""

    def test_no_highlights_returns_verse_unchanged(self):
        """Test that a verse with no highlights is returned as-is."""
        assert apply_highlights("1) In the beginning", []) == "1) In the beginning"

    def test_single_highlight_wraps_plain_text(self):
        """Test that offsets select the matching visible characters."""
        result = apply_highlights("1) In the beginning", [(3, 6, YELLOW)])

        assert result == f"1) {mark(YELLOW)}In {CLOSE}the beginning"

    def test_offsets_skip_html_tags(self):
        """Test that tags don't count toward offsets, so header spans don't shift the highlight."""
        verse = '1) <span class="header">Hi</span> there'

        result = apply_highlights(verse, [(0, 6, YELLOW)])

        # The visible text is "1) Hi there", so offsets 0-6 cover "1) Hi "
        assert result == (
            f'{mark(YELLOW)}1) {CLOSE}<span class="header">{mark(YELLOW)}Hi{CLOSE}</span>{mark(YELLOW)} {CLOSE}there'
        )

    def test_highlight_never_wraps_a_tag(self):
        """Test that no <mark> is opened or closed inside a tag, so the HTML stays well-formed."""
        verse = '1) <span class="header">Hi</span> there'

        result = apply_highlights(verse, [(0, 12, YELLOW)])

        # The mark closes before each tag and reopens after it, so no tag is inside a <mark>
        assert result == (
            f'{mark(YELLOW)}1) {CLOSE}<span class="header">{mark(YELLOW)}Hi{CLOSE}</span>{mark(YELLOW)} there{CLOSE}'
        )

    def test_html_entity_counts_as_one_character(self):
        """Test that an entity such as &amp; is one visible character for offsets."""
        result = apply_highlights("&amp;x", [(1, 2, YELLOW)])

        assert result == f"&amp;{mark(YELLOW)}x{CLOSE}"

    def test_entity_inside_highlight_is_kept_whole(self):
        """Test that an entity inside a highlight is not split across marks."""
        result = apply_highlights("1) A &amp; B", [(3, 8, BLUE)])

        assert result == f"1) {mark(BLUE)}A &amp; B{CLOSE}"

    def test_overlapping_highlights_last_one_wins(self):
        """Test that where highlights overlap, the last highlight in the list sets the color."""
        result = apply_highlights("1) abcdef", [(3, 6, PINK), (2, 4, YELLOW)])

        # Pink covers indexes 3-5, yellow covers 2-3. Yellow is the later highlight, so at index 3 it is nested
        # inside pink. Index 2 has only yellow, and index 4-5 have only pink.
        assert result == f"1){mark(YELLOW)} {CLOSE}{mark(PINK)}{mark(YELLOW)}a{CLOSE}bc{CLOSE}def"

    def test_newer_highlight_inside_older_one_shows_its_color(self):
        """Test that a highlight inside an older highlight shows the newer color."""
        result = apply_highlights("1) abcdefghij", [(0, 10, YELLOW), (3, 6, PINK)])

        # The pink highlight is nested inside the yellow one
        assert result == f"{mark(YELLOW)}1) {mark(PINK)}abc{CLOSE}defg{CLOSE}hij"

    def test_adjacent_highlights_with_different_colors_get_separate_marks(self):
        """Test that two touching highlights with different colors produce two marks."""
        result = apply_highlights("abcd", [(0, 2, YELLOW), (2, 4, PINK)])

        assert result == f"{mark(YELLOW)}ab{CLOSE}{mark(PINK)}cd{CLOSE}"

    def test_empty_range_adds_no_mark(self):
        """Test that a highlight with beginning equal to end adds no mark."""
        assert apply_highlights("abc", [(1, 1, YELLOW)]) == "abc"

    def test_range_past_end_of_verse_is_clipped(self):
        """Test that an end offset past the verse length wraps only the characters that exist."""
        result = apply_highlights("abc", [(1, 10, YELLOW)])

        assert result == f"a{mark(YELLOW)}bc{CLOSE}"

    def test_highlight_covering_whole_verse(self):
        """Test that a highlight covering the full verse wraps all of its text."""
        result = apply_highlights("abc", [(0, 3, YELLOW)])

        assert result == f"{mark(YELLOW)}abc{CLOSE}"

    def test_entities_outside_highlight_are_unchanged(self):
        """Test that already-escaped HTML in the verse is output unchanged apart from the marks."""
        result = apply_highlights("a &lt;b&gt;", [(0, 3, YELLOW)])

        assert result == f"{mark(YELLOW)}a &lt;{CLOSE}b&gt;"
