import pytest
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
from django.conf import settings
from django.test import SimpleTestCase

# Import the global functions
from frontend import globals as globals_module

def reset_globals():
    """Reset the globals to their default values."""

    # Reset the globals to their default values
    globals_module.BIBLE_DATA_ROOT = None
    globals_module.DEFAULT_VERSION = ''
    globals_module.DEFAULT_BOOK = ''
    globals_module.DEFAULT_CHAPTER = ''
    globals_module.VERSION_SELECTION = []
    globals_module.IN_ORDER_BOOKS = []
    globals_module.CHAPTER_SELECTION = {}
    globals_module.ALL_VERSES = {}


class FailingObject:
    """Create an object that raises an exception on any operation."""
    def __getattr__(self, name):
        raise RuntimeError("Something went wrong")


class TestSetBibleDataRoot(SimpleTestCase):
    """Tests for set_bible_data_root function."""
    ROOT_DIR = Path(__file__).resolve().parents[2]

    # Success tests
    def test_set_bible_data_success(self):
        reset_globals()
        globals_module.set_bible_data_root()
        EXPECTED_PATH = self.ROOT_DIR.joinpath('frontend', 'bible_data')
        # Should set the global variable to the expected path
        assert globals_module.BIBLE_DATA_ROOT == EXPECTED_PATH

    def test_set_bible_data_wrong_endpoint(self):
        reset_globals()
        globals_module.set_bible_data_root()
        wrong_path = self.ROOT_DIR.joinpath('frontend', 'this_is_wrong')
        # Should not set the global variable to the wrong endpoint
        assert globals_module.BIBLE_DATA_ROOT != wrong_path

    # Error tests
    def test_set_bible_data_no_endpoint(self):
        reset_globals()
        # Should raise an error if there is no endpoint
        with patch.object(settings, 'BASE_DIR', self.ROOT_DIR):
            with patch.object(Path, 'joinpath', side_effect=Exception("Invalid endpoint")):
                with pytest.raises(ValueError):
                    globals_module.set_bible_data_root()

    def test_set_bible_data_wrong_root_dir(self):
        reset_globals()
        # Should raise an error if the root directory is wrong
        with patch.object(settings, 'BASE_DIR', "this_is_wrong"):
            with pytest.raises(ValueError):
                globals_module.set_bible_data_root()

    def test_set_bible_data_no_root_dir(self):
        reset_globals()
        # Should raise an error if the root directory is not set
        with patch.object(settings, 'BASE_DIR', None):
            with pytest.raises(ValueError):
                globals_module.set_bible_data_root()


class TestSetVersionSelection(SimpleTestCase):
    """Tests for set_version_selection function."""

    @staticmethod
    def create_mock_version(version_name):
        """Create a mock version object with proper name attribute."""
        mock = MagicMock()
        mock.name = version_name
        return mock

    # Success tests
    @patch.dict(os.environ, {"ENABLED_VERSIONS": '["bsb", "web"]'})
    def test_set_version_selection_all_versions_found(self):
        reset_globals()
        mock_versions = [self.create_mock_version('bsb'), self.create_mock_version('web')]
        with patch.object(globals_module, 'BIBLE_DATA_ROOT') as mock_root:
            mock_root.iterdir.return_value = mock_versions
            globals_module.set_version_selection()
            # Should include all versions
            assert len(globals_module.VERSION_SELECTION) == 2
            assert 'bsb' in globals_module.VERSION_SELECTION
            assert 'web' in globals_module.VERSION_SELECTION

    @patch.dict(os.environ, {"ENABLED_VERSIONS": '["bsb"]'})
    def test_set_version_selection_one_version_only(self):
        reset_globals()
        mock_versions = [self.create_mock_version('bsb'), self.create_mock_version('web')]
        with patch.object(globals_module, 'BIBLE_DATA_ROOT') as mock_root:
            mock_root.iterdir.return_value = mock_versions
            globals_module.set_version_selection()
            # Should include only the version that is found
            assert len(globals_module.VERSION_SELECTION) == 1
            assert globals_module.VERSION_SELECTION == ['bsb']
            assert 'web' not in globals_module.VERSION_SELECTION

    @patch.dict(os.environ, {"ENABLED_VERSIONS": '["bsb", "not_a_version"]'})
    def test_set_version_selection_one_version_not_found(self):
        reset_globals()
        mock_versions = [self.create_mock_version('bsb'), self.create_mock_version('web')]
        with patch.object(globals_module, 'BIBLE_DATA_ROOT') as mock_root:
            mock_root.iterdir.return_value = mock_versions
            globals_module.set_version_selection()
            # Should include only the version that is found
            assert len(globals_module.VERSION_SELECTION) == 1
            assert 'bsb' in globals_module.VERSION_SELECTION
            assert 'not_a_version' not in globals_module.VERSION_SELECTION

    @patch.dict(os.environ, {"ENABLED_VERSIONS": '["not_a_version_1", "not_a_version_2"]'})
    def test_set_version_selection_no_versions_found(self):
        reset_globals()
        mock_versions = [self.create_mock_version('bsb'), self.create_mock_version('web')]
        with patch.object(globals_module, 'BIBLE_DATA_ROOT') as mock_root:
            mock_root.iterdir.return_value = mock_versions
            globals_module.set_version_selection()
            # Should fallback to all available versions
            assert len(globals_module.VERSION_SELECTION) == 2
            assert 'bsb' in globals_module.VERSION_SELECTION
            assert 'web' in globals_module.VERSION_SELECTION

    @patch.dict(os.environ, {"ENABLED_VERSIONS": '[]'})
    def test_set_version_selection_no_selected_versions(self):
        reset_globals()
        mock_versions = [self.create_mock_version('bsb'), self.create_mock_version('web')]
        with patch.object(globals_module, 'BIBLE_DATA_ROOT') as mock_root:
            mock_root.iterdir.return_value = mock_versions
            globals_module.set_version_selection()
            # Should include all available versions
            assert len(globals_module.VERSION_SELECTION) == 2
            assert 'bsb' in globals_module.VERSION_SELECTION
            assert 'web' in globals_module.VERSION_SELECTION

    # Error tests
    def test_set_version_selection_error_thrown(self):
        """Test that set_version_selection raises ValueError when an error occurs."""
        reset_globals()
        globals_module.BIBLE_DATA_ROOT = FailingObject()
        # Should catch and throw an error
        with pytest.raises(ValueError):
            globals_module.set_version_selection()
    
    def test_set_version_selection_dependency_bible_data_root_not_set(self):
        """Test that set_version_selection fails when BIBLE_DATA_ROOT is not set."""
        reset_globals()
        # BIBLE_DATA_ROOT is empty by default after reset_globals()
        with pytest.raises(ValueError):
            globals_module.set_version_selection()

class TestSetDefaultVersion(SimpleTestCase):
    """Tests for set_default_version function."""

    # Success tests
    @patch.dict(os.environ, {"DEFAULT_VERSION": "web"})
    def test_set_default_version_in_selection(self):
        """Test that set_default_version sets the global variable to the default version."""
        reset_globals()
        globals_module.VERSION_SELECTION = ['bsb', 'web']
        globals_module.set_default_version()
        # Should set DEFAULT_VERSION to the global variable
        assert globals_module.DEFAULT_VERSION == 'web'

    @patch.dict(os.environ, {"DEFAULT_VERSION": "not_a_version"})
    def test_set_default_version_not_in_selection(self):
        """Test that set_default_version throws an error when the default version is not in the selection."""
        reset_globals()
        globals_module.VERSION_SELECTION = ['bsb', 'web']
        globals_module.set_default_version()
        # Should set DEFAULT_VERSION to the first version in the selection
        assert globals_module.DEFAULT_VERSION == 'bsb'

    # Error tests
    def test_set_default_version_error_thrown(self):
        """Test that set_default_version raises ValueError when an error occurs."""
        reset_globals()
        globals_module.VERSION_SELECTION = FailingObject()
        # Should catch and throw an error
        with pytest.raises(ValueError):
            globals_module.set_default_version()
    
    def test_set_default_version_dependency_version_selection_not_set(self):
        """Test that set_default_version fails when VERSION_SELECTION is empty."""
        reset_globals()
        # VERSION_SELECTION is empty by default after reset_globals()
        with pytest.raises(ValueError):
            globals_module.set_default_version()


class TestSetInOrderBooks(SimpleTestCase):
    """Tests for set_in_order_books function."""
    in_order_books = [
        "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy", "Joshua",
        "Judges", "Ruth", "1 Samuel", "2 Samuel", "1 Kings", "2 Kings",
        "1 Chronicles", "2 Chronicles", "Ezra", "Nehemiah", "Esther", "Job",
        "Psalms", "Proverbs", "Ecclesiastes", "Song of Solomon", "Isaiah",
        "Jeremiah", "Lamentations", "Ezekiel", "Daniel", "Hosea", "Joel",
        "Amos", "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk", "Zephaniah",
        "Haggai", "Zechariah", "Malachi", "Matthew", "Mark", "Luke", "John",
        "Acts", "Romans", "1 Corinthians", "2 Corinthians", "Galatians",
        "Ephesians", "Philippians", "Colossians", "1 Thessalonians",
        "2 Thessalonians", "1 Timothy", "2 Timothy", "Titus", "Philemon",
        "Hebrews", "James", "1 Peter", "2 Peter", "1 John", "2 John",
        "3 John", "Jude", "Revelation"
    ]

    # Success tests
    def test_set_in_order_books_in_order(self):
        """Test that set_in_order_books sets the global variable to the in order books."""
        reset_globals()
        globals_module.set_in_order_books()
        # Should succeed because books are in order
        assert globals_module.IN_ORDER_BOOKS == self.in_order_books

    def test_set_in_order_books_all_66_books(self):
        """Test that set_in_order_books succeeds if there are 66 books."""
        reset_globals()
        globals_module.set_in_order_books()
        # Should succeed because there are 66 books
        assert len(globals_module.IN_ORDER_BOOKS) == 66

    def test_set_in_order_books_not_in_order(self):
        """Test that set_in_order_books fails if books are not in order."""
        reset_globals()
        reversed_books = self.in_order_books.copy().reverse()
        globals_module.set_in_order_books()
        # Should fail because books are reversed
        assert globals_module.IN_ORDER_BOOKS != reversed_books

    def test_set_in_order_books_missing_book(self):
        """Test that set_in_order_books fails if a book is missing."""
        reset_globals()
        missing_book = self.in_order_books.copy().remove('Genesis')
        globals_module.set_in_order_books()
        # Should fail because Genesis is missing
        assert globals_module.IN_ORDER_BOOKS != missing_book

    def test_set_in_order_books_empty(self):
        """Test that set_in_order_books fails if there are no books."""
        reset_globals()
        empty_books = []
        globals_module.set_in_order_books()
        # Should fail because there are no books
        assert globals_module.IN_ORDER_BOOKS != empty_books

class TestSetDefaultBook(SimpleTestCase):
    """Tests for set_default_book function."""

    # Success tests
    @patch.dict(os.environ, {"DEFAULT_BOOK": "Genesis"})
    def test_set_default_book_in_selection(self):
        """Test that set_default_book sets the global variable to the default book."""
        reset_globals()
        globals_module.set_in_order_books()
        globals_module.set_default_book()
        # Should set DEFAULT_BOOK to the global variable
        assert globals_module.DEFAULT_BOOK == 'Genesis'

    @patch.dict(os.environ, {"DEFAULT_BOOK": "not_a_book"})
    def test_set_default_book_not_in_selection(self):
        """Test that set_default_book throws an error when the default book is not in the selection."""
        reset_globals()
        globals_module.set_in_order_books()
        globals_module.set_default_book()
        # Should set DEFAULT_BOOK to the first book in the selection
        assert globals_module.DEFAULT_BOOK == 'Genesis'

    # Error tests
    def test_set_default_book_error_thrown(self):
        """Test that set_default_book raises ValueError when an error occurs."""
        reset_globals()
        globals_module.IN_ORDER_BOOKS = FailingObject()
        # Should catch and throw an error
        with pytest.raises(ValueError):
            globals_module.set_default_book()
    
    def test_set_default_book_dependency_in_order_books_not_set(self):
        """Test that set_default_book fails when IN_ORDER_BOOKS is empty."""
        reset_globals()
        # IN_ORDER_BOOKS is empty by default after reset_globals()
        with pytest.raises(ValueError):
            globals_module.set_default_book()


class TestSetChapterSelection(SimpleTestCase):
    """Tests for set_chapter_selection function."""
    books_with_chapters = {
        "Genesis": 50,
        "Exodus": 40,
        "Leviticus": 27,
        "Numbers": 36,
        "Deuteronomy": 34,
        "Joshua": 24,
        "Judges": 21,
        "Ruth": 4,
        "1 Samuel": 31,
        "2 Samuel": 24,
        "1 Kings": 22,
        "2 Kings": 25,
        "1 Chronicles": 29,
        "2 Chronicles": 36,
        "Ezra": 10,
        "Nehemiah": 13,
        "Esther": 10,
        "Job": 42,
        "Psalms": 150,
        "Proverbs": 31,
        "Ecclesiastes": 12,
        "Song of Solomon": 8,
        "Isaiah": 66,
        "Jeremiah": 52,
        "Lamentations": 5,
        "Ezekiel": 48,
        "Daniel": 12,
        "Hosea": 14,
        "Joel": 3,
        "Amos": 9,
        "Obadiah": 1,
        "Jonah": 4,
        "Micah": 7,
        "Nahum": 3,
        "Habakkuk": 3,
        "Zephaniah": 3,
        "Haggai": 2,
        "Zechariah": 14,
        "Malachi": 4,
        "Matthew": 28,
        "Mark": 16,
        "Luke": 24,
        "John": 21,
        "Acts": 28,
        "Romans": 16,
        "1 Corinthians": 16,
        "2 Corinthians": 13,
        "Galatians": 6,
        "Ephesians": 6,
        "Philippians": 4,
        "Colossians": 4,
        "1 Thessalonians": 5,
        "2 Thessalonians": 3,
        "1 Timothy": 6,
        "2 Timothy": 4,
        "Titus": 3,
        "Philemon": 1,
        "Hebrews": 13,
        "James": 5,
        "1 Peter": 5,
        "2 Peter": 3,
        "1 John": 5,
        "2 John": 1,
        "3 John": 1,
        "Jude": 1,
        "Revelation": 22,
    }

    # BSB tests
    def test_set_chapter_selection_bsb_success(self):
        """Test that set_chapter_selection sets the global variable to the chapter selection."""
        reset_globals()
        globals_module.set_bible_data_root()
        globals_module.set_version_selection()
        globals_module.set_default_version()
        globals_module.set_in_order_books()
        globals_module.set_chapter_selection()
        # Should succeed because bsb should have all the designated chapters per book
        for book in self.books_with_chapters:
            assert globals_module.CHAPTER_SELECTION[book] == self.books_with_chapters[book]

    def test_set_chapter_selection_bsb_chapters_off_by_one(self):
        """Test that set_chapter_selection fails if the chapters are off by one."""
        reset_globals()
        globals_module.set_bible_data_root()
        globals_module.set_version_selection()
        globals_module.set_default_version()
        globals_module.set_in_order_books()
        globals_module.set_chapter_selection()
        # Should fail because the chapters are off by one
        for book in self.books_with_chapters:
            assert globals_module.CHAPTER_SELECTION[book] != self.books_with_chapters[book] - 1

    # WEB tests
    def test_set_chapter_selection_web_success(self):
        """Test that set_chapter_selection sets the global variable to the chapter selection."""
        reset_globals()
        globals_module.set_bible_data_root()
        globals_module.set_version_selection()
        globals_module.set_default_version()
        globals_module.set_in_order_books()
        # Change DEFAULT_VERSION to 'web' for this test
        globals_module.DEFAULT_VERSION = 'web'
        globals_module.set_chapter_selection()
        # Should succeed because web should have all the designated chapters per book
        for book in self.books_with_chapters:
            assert globals_module.CHAPTER_SELECTION[book] == self.books_with_chapters[book]

    def test_set_chapter_selection_web_chapters_off_by_one(self):
        """Test that set_chapter_selection fails if the chapters are off by one."""
        reset_globals()
        globals_module.set_bible_data_root()
        globals_module.set_version_selection()
        globals_module.set_default_version()
        globals_module.set_in_order_books()
        # Change DEFAULT_VERSION to 'web' for this test
        globals_module.DEFAULT_VERSION = 'web'
        globals_module.set_chapter_selection()
        # Should fail because the chapters are off by one
        for book in self.books_with_chapters:
            assert globals_module.CHAPTER_SELECTION[book] != self.books_with_chapters[book] - 1
    
    # Dependency tests
    def test_set_chapter_selection_dependency_bible_data_root_not_set(self):
        """Test that set_chapter_selection fails when BIBLE_DATA_ROOT is not set."""
        reset_globals()
        # BIBLE_DATA_ROOT is empty by default after reset_globals()
        with pytest.raises(ValueError):
            globals_module.set_chapter_selection()
    
    def test_set_chapter_selection_dependency_default_version_not_set(self):
        """Test that set_chapter_selection fails when DEFAULT_VERSION is not set."""
        reset_globals()
        globals_module.set_bible_data_root()
        # DEFAULT_VERSION is empty by default after reset_globals()
        with pytest.raises(ValueError):
            globals_module.set_chapter_selection()
    
    def test_set_chapter_selection_dependency_in_order_books_not_set(self):
        """Test that set_chapter_selection fails when IN_ORDER_BOOKS is not set."""
        reset_globals()
        globals_module.set_bible_data_root()
        globals_module.set_version_selection()
        globals_module.set_default_version()
        # IN_ORDER_BOOKS is empty by default after reset_globals()
        with pytest.raises(ValueError):
            globals_module.set_chapter_selection()
    
    # Error tests
    def test_set_chapter_selection_error_thrown(self):
        """Test that set_chapter_selection throws an error when an error occurs."""
        reset_globals()
        globals_module.set_bible_data_root()
        globals_module.set_version_selection()
        globals_module.set_default_version()
        globals_module.set_in_order_books()
        # Make BIBLE_DATA_ROOT raise an error when accessed
        globals_module.BIBLE_DATA_ROOT = FailingObject()
        with pytest.raises(ValueError):
            globals_module.set_chapter_selection()

    def test_set_chapter_selection_dependency_version_not_found(self):
        """Test that set_chapter_selection fails when the version directory doesn't exist."""
        reset_globals()
        globals_module.set_bible_data_root()
        globals_module.set_version_selection()
        globals_module.set_default_version()
        globals_module.set_in_order_books()
        # Manually set DEFAULT_VERSION to a non-existent version
        globals_module.DEFAULT_VERSION = 'not_a_real_version'
        with pytest.raises(ValueError):
            globals_module.set_chapter_selection()

class TestSetDefaultChapter(SimpleTestCase):
    """Tests for set_default_chapter function."""
    books_with_chapters = {
        "Genesis": 50,
        "Exodus": 40,
        "Leviticus": 27,
        "Numbers": 36,
        "Deuteronomy": 34,
        "Joshua": 24,
        "Judges": 21,
        "Ruth": 4,
        "1 Samuel": 31,
        "2 Samuel": 24,
        "1 Kings": 22,
        "2 Kings": 25,
        "1 Chronicles": 29,
        "2 Chronicles": 36,
        "Ezra": 10,
        "Nehemiah": 13,
        "Esther": 10,
        "Job": 42,
        "Psalms": 150,
        "Proverbs": 31,
        "Ecclesiastes": 12,
        "Song of Solomon": 8,
        "Isaiah": 66,
        "Jeremiah": 52,
        "Lamentations": 5,
        "Ezekiel": 48,
        "Daniel": 12,
        "Hosea": 14,
        "Joel": 3,
        "Amos": 9,
        "Obadiah": 1,
        "Jonah": 4,
        "Micah": 7,
        "Nahum": 3,
        "Habakkuk": 3,
        "Zephaniah": 3,
        "Haggai": 2,
        "Zechariah": 14,
        "Malachi": 4,
        "Matthew": 28,
        "Mark": 16,
        "Luke": 24,
        "John": 21,
        "Acts": 28,
        "Romans": 16,
        "1 Corinthians": 16,
        "2 Corinthians": 13,
        "Galatians": 6,
        "Ephesians": 6,
        "Philippians": 4,
        "Colossians": 4,
        "1 Thessalonians": 5,
        "2 Thessalonians": 3,
        "1 Timothy": 6,
        "2 Timothy": 4,
        "Titus": 3,
        "Philemon": 1,
        "Hebrews": 13,
        "James": 5,
        "1 Peter": 5,
        "2 Peter": 3,
        "1 John": 5,
        "2 John": 1,
        "3 John": 1,
        "Jude": 1,
        "Revelation": 22,
    }

    # BSB tests
    @patch.dict(os.environ, {"DEFAULT_CHAPTER": "1"})
    def test_set_default_chapter_bsb_first_chapter_success(self):
        """Test that set_default_chapter sets the global variable to the first chapter."""
        reset_globals()
        globals_module.set_bible_data_root()
        globals_module.set_version_selection()
        globals_module.DEFAULT_VERSION = 'bsb'
        globals_module.set_in_order_books()
        globals_module.set_chapter_selection()
        for book in self.books_with_chapters:
            globals_module.DEFAULT_BOOK = book
            globals_module.set_default_chapter()
            assert globals_module.DEFAULT_CHAPTER == 1

    def test_set_default_chapter_bsb_last_chapter_success(self):
        """Test that set_default_chapter sets the global variable to the last chapter."""
        reset_globals()
        globals_module.set_bible_data_root()
        globals_module.set_version_selection()
        globals_module.DEFAULT_VERSION = 'bsb'
        globals_module.set_in_order_books()
        globals_module.set_chapter_selection()
        for book in self.books_with_chapters:
            globals_module.DEFAULT_BOOK = book
            with patch.dict(os.environ, {"DEFAULT_CHAPTER": str(self.books_with_chapters[book])}):
                globals_module.set_default_chapter()
                assert globals_module.DEFAULT_CHAPTER == self.books_with_chapters[book]

    @patch.dict(os.environ, {"DEFAULT_CHAPTER": "999"})
    def test_set_default_chapter_bsb_chapter_not_in_range(self):
        """Test that set_default_chapter fails if the chapter is not in the range."""
        reset_globals()
        globals_module.set_bible_data_root()
        globals_module.set_version_selection()
        globals_module.DEFAULT_VERSION = 'bsb'
        globals_module.set_in_order_books()
        globals_module.set_chapter_selection()
        for book in self.books_with_chapters:
            globals_module.DEFAULT_BOOK = book
            with pytest.raises(ValueError):
                globals_module.set_default_chapter()

    # WEB tests
    @patch.dict(os.environ, {"DEFAULT_CHAPTER": "1"})
    def test_set_default_chapter_web_first_chapter_success(self):
        """Test that set_default_chapter sets the global variable to the first chapter."""
        reset_globals()
        globals_module.set_bible_data_root()
        globals_module.set_version_selection()
        globals_module.DEFAULT_VERSION = 'web'
        globals_module.set_in_order_books()
        globals_module.set_chapter_selection()
        for book in self.books_with_chapters:
            globals_module.DEFAULT_BOOK = book
            globals_module.set_default_chapter()
            assert globals_module.DEFAULT_CHAPTER == 1

    def test_set_default_chapter_web_last_chapter_success(self):
        """Test that set_default_chapter sets the global variable to the last chapter."""
        reset_globals()
        globals_module.set_bible_data_root()
        globals_module.set_version_selection()
        globals_module.DEFAULT_VERSION = 'web'
        globals_module.set_in_order_books()
        globals_module.set_chapter_selection()
        for book in self.books_with_chapters:
            globals_module.DEFAULT_BOOK = book
            with patch.dict(os.environ, {"DEFAULT_CHAPTER": str(self.books_with_chapters[book])}):
                globals_module.set_default_chapter()
                assert globals_module.DEFAULT_CHAPTER == self.books_with_chapters[book]

    @patch.dict(os.environ, {"DEFAULT_CHAPTER": "999"})
    def test_set_default_chapter_web_chapter_not_in_range(self):
        """Test that set_default_chapter fails if the chapter is not in the range."""
        reset_globals()
        globals_module.set_bible_data_root()
        globals_module.set_version_selection()
        globals_module.DEFAULT_VERSION = 'web'
        globals_module.set_in_order_books()
        globals_module.set_chapter_selection()
        for book in self.books_with_chapters:
            globals_module.DEFAULT_BOOK = book
            with pytest.raises(ValueError):
                globals_module.set_default_chapter()

    # Error tests
    @patch.dict(os.environ, {"DEFAULT_CHAPTER": "1"})
    def test_set_default_chapter_book_error_thrown(self):
        """Test that set_default_chapter throws an error when an error occurs."""
        reset_globals()
        globals_module.set_bible_data_root()
        globals_module.set_version_selection()
        globals_module.set_default_version()
        globals_module.set_in_order_books()
        globals_module.set_chapter_selection()
        globals_module.DEFAULT_BOOK = 'Genesis'
        # Make CHAPTER_SELECTION raise an error when accessed
        globals_module.CHAPTER_SELECTION = FailingObject()
        with pytest.raises(ValueError):
            globals_module.set_default_chapter()

    @patch.dict(os.environ, {"DEFAULT_CHAPTER": "1"})
    def test_set_default_chapter_book_not_in_selection(self):
        """Test that set_default_chapter fails if the book is not in CHAPTER_SELECTION."""
        reset_globals()
        globals_module.set_bible_data_root()
        globals_module.set_version_selection()
        globals_module.DEFAULT_VERSION = 'bsb'
        globals_module.set_in_order_books()
        globals_module.set_chapter_selection()
        # Set DEFAULT_BOOK to something not in CHAPTER_SELECTION
        globals_module.DEFAULT_BOOK = "not_a_book"
        with pytest.raises(ValueError):
            globals_module.set_default_chapter()


class TestSetAllVerses(SimpleTestCase):
    """Tests for set_all_verses function."""
    
    # Success tests
    def test_set_all_verses_success(self):
        """Test that set_all_verses loads all verses correctly."""
        reset_globals()
        globals_module.set_bible_data_root()
        globals_module.set_version_selection()
        globals_module.set_default_version()
        globals_module.set_in_order_books()
        globals_module.set_chapter_selection()
        globals_module.set_all_verses()
        
        # Verify structure is populated, not just empty dicts
        assert len(globals_module.ALL_VERSES) > 0
        for version in globals_module.ALL_VERSES:
            assert len(globals_module.ALL_VERSES[version]) > 0, f"No books found for version {version}"
            for book in globals_module.ALL_VERSES[version]:
                assert len(globals_module.ALL_VERSES[version][book]) > 0, f"No chapters found for {version}/{book}"
                for chapter in globals_module.ALL_VERSES[version][book]:
                    assert len(globals_module.ALL_VERSES[version][book][chapter]) > 0, f"No verses found for {version}/{book}/{chapter}"
                    assert isinstance(globals_module.ALL_VERSES[version][book][chapter], dict)

    # Error tests
    def test_set_all_verses_error_thrown(self):
        """Test that set_all_verses raises ValueError when an error occurs."""
        reset_globals()
        globals_module.set_bible_data_root()
        globals_module.set_version_selection()
        globals_module.set_default_version()
        globals_module.set_in_order_books()
        globals_module.set_chapter_selection()
        # Make BIBLE_DATA_ROOT raise an error when accessed
        globals_module.BIBLE_DATA_ROOT = FailingObject()
        with pytest.raises(ValueError):
            globals_module.set_all_verses()

    def test_set_all_verses_dependency_bible_data_root_not_set(self):
        """Test that set_all_verses fails when BIBLE_DATA_ROOT is not set."""
        reset_globals()
        globals_module.VERSION_SELECTION = ['bsb', 'web']
        globals_module.set_in_order_books()
        globals_module.CHAPTER_SELECTION = {'Genesis': 50}
        # BIBLE_DATA_ROOT is empty by default after reset_globals()
        with pytest.raises(ValueError):
            globals_module.set_all_verses()

    def test_set_all_verses_dependency_version_selection_not_set(self):
        """Test that set_all_verses fails when VERSION_SELECTION is not set."""
        reset_globals()
        globals_module.set_bible_data_root()
        globals_module.set_in_order_books()
        globals_module.CHAPTER_SELECTION = {'Genesis': 50}
        # VERSION_SELECTION is empty by default after reset_globals()
        with pytest.raises(ValueError):
            globals_module.set_all_verses()
    
    def test_set_all_verses_dependency_in_order_books_not_set(self):
        """Test that set_all_verses fails when IN_ORDER_BOOKS is not set."""
        reset_globals()
        globals_module.set_bible_data_root()
        globals_module.VERSION_SELECTION = ['bsb', 'web']
        globals_module.CHAPTER_SELECTION = {'Genesis': 50}
        # IN_ORDER_BOOKS is empty by default after reset_globals()
        with pytest.raises(ValueError):
            globals_module.set_all_verses()

    def test_set_all_verses_dependency_chapter_selection_not_set(self):
        """Test that set_all_verses fails when CHAPTER_SELECTION is not set."""
        reset_globals()
        globals_module.set_bible_data_root()
        globals_module.VERSION_SELECTION = ['bsb', 'web']
        globals_module.set_in_order_books()
        # CHAPTER_SELECTION is empty by default after reset_globals()
        with pytest.raises(ValueError):
            globals_module.set_all_verses()


class TestCheckGlobals(SimpleTestCase):
    """Tests for check_globals function."""
    
    # Success tests
    def test_check_globals_success(self):
        """Test that check_globals succeeds when all globals are set."""
        reset_globals()
        globals_module.set_bible_data_root()
        globals_module.set_version_selection()
        globals_module.set_default_version()
        globals_module.set_in_order_books()
        globals_module.set_default_book()
        globals_module.set_chapter_selection()
        globals_module.set_default_chapter()
        globals_module.set_all_verses()
        globals_module.check_globals()
    
    # Error tests
    def test_check_globals_error_thrown(self):
        """Test that check_globals raises ValueError when an error occurs."""
        reset_globals()
        globals_module.set_bible_data_root()
        globals_module.set_version_selection()
        globals_module.set_default_version()
        globals_module.set_in_order_books()
        globals_module.set_default_book()
        globals_module.set_chapter_selection()
        globals_module.set_default_chapter()
        globals_module.set_all_verses()
        # Make BIBLE_DATA_ROOT raise an error when accessed
        globals_module.BIBLE_DATA_ROOT = FailingObject()
        with pytest.raises(ValueError):
            globals_module.check_globals()
    
    def test_check_globals_dependency_bible_data_root_not_set(self):
        """Test that check_globals fails when BIBLE_DATA_ROOT is not set."""
        reset_globals()
        # BIBLE_DATA_ROOT is empty by default after reset_globals()
        with pytest.raises(ValueError):
            globals_module.check_globals()
    
    def test_check_globals_dependency_version_selection_not_set(self):
        """Test that check_globals fails when VERSION_SELECTION is not set."""
        reset_globals()
        globals_module.set_bible_data_root()
        # VERSION_SELECTION is empty by default after reset_globals()
        with pytest.raises(ValueError):
            globals_module.check_globals()
    
    def test_check_globals_dependency_default_version_not_set(self):
        """Test that check_globals fails when DEFAULT_VERSION is not set."""
        reset_globals()
        globals_module.set_bible_data_root()
        globals_module.VERSION_SELECTION = ['bsb', 'web']
        # DEFAULT_VERSION is empty by default after reset_globals()
        with pytest.raises(ValueError):
            globals_module.check_globals()
    
    def test_check_globals_dependency_in_order_books_not_set(self):
        """Test that check_globals fails when IN_ORDER_BOOKS is not set."""
        reset_globals()
        globals_module.set_bible_data_root()
        globals_module.VERSION_SELECTION = ['bsb', 'web']
        globals_module.DEFAULT_VERSION = 'bsb'
        # IN_ORDER_BOOKS is empty by default after reset_globals()
        with pytest.raises(ValueError):
            globals_module.check_globals()
    
    def test_check_globals_dependency_default_book_not_set(self):
        """Test that check_globals fails when DEFAULT_BOOK is not set."""
        reset_globals()
        globals_module.set_bible_data_root()
        globals_module.VERSION_SELECTION = ['bsb', 'web']
        globals_module.DEFAULT_VERSION = 'bsb'
        globals_module.set_in_order_books()
        # DEFAULT_BOOK is empty by default after reset_globals()
        with pytest.raises(ValueError):
            globals_module.check_globals()
    
    def test_check_globals_dependency_chapter_selection_not_set(self):
        """Test that check_globals fails when CHAPTER_SELECTION is not set."""
        reset_globals()
        globals_module.set_bible_data_root()
        globals_module.VERSION_SELECTION = ['bsb', 'web']
        globals_module.DEFAULT_VERSION = 'bsb'
        globals_module.set_in_order_books()
        globals_module.DEFAULT_BOOK = 'Genesis'
        # CHAPTER_SELECTION is empty by default after reset_globals()
        with pytest.raises(ValueError):
            globals_module.check_globals()
    
    def test_check_globals_dependency_default_chapter_not_set(self):
        """Test that check_globals fails when DEFAULT_CHAPTER is not set."""
        reset_globals()
        globals_module.set_bible_data_root()
        globals_module.VERSION_SELECTION = ['bsb', 'web']
        globals_module.DEFAULT_VERSION = 'bsb'
        globals_module.set_in_order_books()
        globals_module.DEFAULT_BOOK = 'Genesis'
        globals_module.CHAPTER_SELECTION = {'Genesis': 50}
        # DEFAULT_CHAPTER is empty by default after reset_globals()
        with pytest.raises(ValueError):
            globals_module.check_globals()
    
    def test_check_globals_dependency_all_verses_not_set(self):
        """Test that check_globals fails when ALL_VERSES is not set."""
        reset_globals()
        globals_module.set_bible_data_root()
        globals_module.VERSION_SELECTION = ['bsb', 'web']
        globals_module.DEFAULT_VERSION = 'bsb'
        globals_module.set_in_order_books()
        globals_module.DEFAULT_BOOK = 'Genesis'
        globals_module.CHAPTER_SELECTION = {'Genesis': 50}
        globals_module.DEFAULT_CHAPTER = 1
        # ALL_VERSES is empty by default after reset_globals()
        with pytest.raises(ValueError):
            globals_module.check_globals()
    
    def test_check_globals_dependency_all_required(self):
        """Test that check_globals succeeds when all dependencies are met."""
        reset_globals()
        globals_module.set_bible_data_root()
        globals_module.set_version_selection()
        globals_module.set_default_version()
        globals_module.set_in_order_books()
        globals_module.set_default_book()
        globals_module.set_chapter_selection()
        globals_module.set_default_chapter()
        globals_module.set_all_verses()
        # Should succeed with all dependencies set
        globals_module.check_globals()