import pytest
import os
from unittest.mock import patch, AsyncMock
from django.test import SimpleTestCase
from django.http import HttpRequest, HttpResponse

from frontend import views
from frontend import globals as globals_module


def reset_globals():
    """Reset the globals to their default values."""
    globals_module.BIBLE_DATA_ROOT = None
    globals_module.DEFAULT_VERSION = ''
    globals_module.DEFAULT_BOOK = ''
    globals_module.DEFAULT_CHAPTER = ''
    globals_module.VERSION_SELECTION = []
    globals_module.IN_ORDER_BOOKS = []
    globals_module.CHAPTER_SELECTION = {}
    globals_module.ALL_VERSES = {}


class TestFullView(SimpleTestCase):
    """Tests for full_view function."""
    
    @staticmethod
    def reset_env_and_globals(enabled_versions, default_version, default_book, default_chapter):
        """Set up environment variables and initialize globals."""
        reset_globals()
        os.environ['ENABLED_VERSIONS'] = enabled_versions
        os.environ['DEFAULT_VERSION'] = default_version
        os.environ['DEFAULT_BOOK'] = default_book
        os.environ['DEFAULT_CHAPTER'] = default_chapter
        
        # Initialize all globals
        globals_module.set_bible_data_root()
        globals_module.set_version_selection()
        globals_module.set_default_version()
        globals_module.set_in_order_books()
        globals_module.set_default_book()
        globals_module.set_chapter_selection()
        globals_module.set_default_chapter()
        globals_module.set_all_verses()
    
    @pytest.mark.asyncio
    async def test_full_view_success(self):
        """Test that full_view succeeds with valid book, chapter, and version."""
        self.reset_env_and_globals('[]', 'bsb', 'Genesis', '1')
        request = HttpRequest()
        request.path_info = '/Genesis-1-bsb/'
        
        # Mock async_render to return a response
        with patch('frontend.views.async_render', new_callable=AsyncMock) as mock_render:
            mock_render.return_value = HttpResponse("Genesis 1 content")
            
            # Patch the globals in views module to match what we set up
            with patch.multiple('frontend.views',
                              BIBLE_DATA_ROOT=globals_module.BIBLE_DATA_ROOT,
                              DEFAULT_VERSION=globals_module.DEFAULT_VERSION,
                              DEFAULT_BOOK=globals_module.DEFAULT_BOOK,
                              DEFAULT_CHAPTER=globals_module.DEFAULT_CHAPTER,
                              VERSION_SELECTION=globals_module.VERSION_SELECTION,
                              IN_ORDER_BOOKS=globals_module.IN_ORDER_BOOKS,
                              CHAPTER_SELECTION=globals_module.CHAPTER_SELECTION,
                              ALL_VERSES=globals_module.ALL_VERSES):
                
                # Call full_view with valid inputs
                response = await views.full_view(request, 'Genesis', 1, 'bsb')
                
                # Verify async_render was called
                assert mock_render.called
                # Verify we got the correct response back
                assert response.content == b"Genesis 1 content"
                
                # Verify the context passed to async_render
                call_args = mock_render.call_args
                assert call_args is not None

                # verify the request path info is passed to the context (first positional argument)
                assert call_args[0][0].path_info == '/Genesis-1-bsb/'

                # verify the template name is passed to the context (second positional argument)
                assert call_args[0][1] == 'index.html'
                
                # verify the context is passed to the context (third positional argument)
                context = call_args[0][2]
                
                # Verify context contains expected book/chapter/version info
                assert context['book'] == 'Genesis'
                assert context['chapter'] == 1
                assert context['version'] == 'bsb'
                assert 'verses' in context
                assert context['verses'] is not None
                assert len(context['verses']) > 0

                # Verify navigation context
                assert 'previous_book' in context
                assert context['previous_book'] == 'Revelation'
                assert 'previous_chapter' in context
                assert context['previous_chapter'] == 22
                assert 'next_book' in context
                assert context['next_book'] == 'Genesis'
                assert 'next_chapter' in context
                assert context['next_chapter'] == 2

                # Verify all books, chapters, and versions information
                assert 'in_order' in context
                assert context['in_order'] == globals_module.IN_ORDER_BOOKS
                assert 'chapter_selection' in context
                assert context['chapter_selection'] == globals_module.CHAPTER_SELECTION
                assert 'version_selection' in context
                assert context['version_selection'] == globals_module.VERSION_SELECTION
                
                # Verify current URL for navigation state
                assert 'current_url' in context
                assert context['current_url'] == '/Genesis-1-bsb/'