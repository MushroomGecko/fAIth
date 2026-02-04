import pytest
import os
from unittest.mock import patch, AsyncMock
from django.test import SimpleTestCase
from django.http import HttpRequest, HttpResponse

from frontend import views
from frontend import globals as globals_module


def reset_globals(enabled_versions, default_version, default_book, default_chapter):
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

    # Set the environment variables
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


class FailingObject:
    """Create an object that raises an exception on any operation."""
    def __getattr__(self, name):
        raise RuntimeError("Something went wrong")


class TestFullView(SimpleTestCase):
    """Tests for full_view function."""
    
    # Success tests
    @pytest.mark.asyncio
    async def test_full_view_success_genesis_1(self):
        """Test that full_view succeeds with valid book, chapter, and version for Genesis 1 (very first chapter in the Bible)."""
        reset_globals('[]', 'bsb', 'Genesis', '1')
        request = HttpRequest()
        
        request_book = 'Genesis'
        request_chapter = 1
        request_version = 'bsb'
        request.path_info = f'/{request_book}-{request_chapter}-{request_version}/'
        
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
            
            # Mock async_render to return a response
            with patch('frontend.views.async_render', new_callable=AsyncMock) as mock_render:
                mock_render.return_value = HttpResponse("Genesis 1 content")
                
                # Call full_view with valid inputs
                response = await views.full_view(request, request_book, request_chapter, request_version)
                
                # Verify async_render was called
                assert mock_render.called
                # Verify we got the correct response back
                assert response is not None
                assert response.content == b"Genesis 1 content"
                
                # Verify the context passed to async_render
                call_args = mock_render.call_args
                assert call_args is not None

                # verify the request path info is passed to the context (first positional argument)
                assert call_args[0][0].path_info == f'/{request_book}-{request_chapter}-{request_version}/'

                # verify the template name is passed to the context (second positional argument)
                assert call_args[0][1] == 'index.html'
                
                # verify the context is passed to the context (third positional argument)
                context = call_args[0][2]
                
                # Verify context contains expected book/chapter/version info
                assert context['book'] == request_book
                assert context['chapter'] == request_chapter
                assert context['version'] == request_version
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
                assert context['current_url'] == f'/{request_book}-{request_chapter}-{request_version}/'

    @pytest.mark.asyncio
    async def test_full_view_success_revelation_22(self):
        """Test that full_view succeeds with valid book, chapter, and version for Revelation 22 (very last chapter in the Bible)."""
        reset_globals('[]', 'bsb', 'Genesis', '1')
        request = HttpRequest()
        
        request_book = 'Revelation'
        request_chapter = 22
        request_version = 'bsb'
        request.path_info = f'/{request_book}-{request_chapter}-{request_version}/'
        
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
            
            # Mock async_render to return a response
            with patch('frontend.views.async_render', new_callable=AsyncMock) as mock_render:
                mock_render.return_value = HttpResponse("Revelation 22 content")
                
                # Call full_view with valid inputs
                response = await views.full_view(request, request_book, request_chapter, request_version)
                
                # Verify async_render was called
                assert mock_render.called
                # Verify we got the correct response back
                assert response is not None
                assert response.content == b"Revelation 22 content"
                
                # Verify the context passed to async_render
                call_args = mock_render.call_args
                assert call_args is not None

                # verify the request path info is passed to the context (first positional argument)
                assert call_args[0][0].path_info == f'/{request_book}-{request_chapter}-{request_version}/'

                # verify the template name is passed to the context (second positional argument)
                assert call_args[0][1] == 'index.html'
                
                # verify the context is passed to the context (third positional argument)
                context = call_args[0][2]
                
                # Verify context contains expected book/chapter/version info
                assert context['book'] == request_book
                assert context['chapter'] == request_chapter
                assert context['version'] == request_version
                assert 'verses' in context
                assert context['verses'] is not None
                assert len(context['verses']) > 0

                # Verify navigation context
                assert 'previous_book' in context
                assert context['previous_book'] == 'Revelation'
                assert 'previous_chapter' in context
                assert context['previous_chapter'] == 21
                assert 'next_book' in context
                assert context['next_book'] == 'Genesis'
                assert 'next_chapter' in context
                assert context['next_chapter'] == 1

                # Verify all books, chapters, and versions information
                assert 'in_order' in context
                assert context['in_order'] == globals_module.IN_ORDER_BOOKS
                assert 'chapter_selection' in context
                assert context['chapter_selection'] == globals_module.CHAPTER_SELECTION
                assert 'version_selection' in context
                assert context['version_selection'] == globals_module.VERSION_SELECTION
                
                # Verify current URL for navigation state
                assert 'current_url' in context
                assert context['current_url'] == f'/{request_book}-{request_chapter}-{request_version}/'

    @pytest.mark.asyncio
    async def test_full_view_success_2_timothy_2(self):
        """Test that full_view succeeds with valid book, chapter, and version for 2 Timothy 2 (a multi-word chapter name while also checking a mid-chapter and not an edge chapter)."""
        reset_globals('[]', 'bsb', 'Genesis', '1')
        request = HttpRequest()
        
        request_book = '2 Timothy'
        request_chapter = 2
        request_version = 'bsb'
        request.path_info = f'/{request_book}-{request_chapter}-{request_version}/'
        
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
            
            # Mock async_render to return a response
            with patch('frontend.views.async_render', new_callable=AsyncMock) as mock_render:
                mock_render.return_value = HttpResponse("2 Timothy 2 content")
                
                # Call full_view with valid inputs
                response = await views.full_view(request, request_book, request_chapter, request_version)
                
                # Verify async_render was called
                assert mock_render.called
                # Verify we got the correct response back
                assert response is not None
                assert response.content == b"2 Timothy 2 content"
                
                # Verify the context passed to async_render
                call_args = mock_render.call_args
                assert call_args is not None

                # verify the request path info is passed to the context (first positional argument)
                assert call_args[0][0].path_info == f'/{request_book}-{request_chapter}-{request_version}/'

                # verify the template name is passed to the context (second positional argument)
                assert call_args[0][1] == 'index.html'
                
                # verify the context is passed to the context (third positional argument)
                context = call_args[0][2]
                
                # Verify context contains expected book/chapter/version info
                assert context['book'] == request_book
                assert context['chapter'] == request_chapter
                assert context['version'] == request_version
                assert 'verses' in context
                assert context['verses'] is not None
                assert len(context['verses']) > 0

                # Verify navigation context
                assert 'previous_book' in context
                assert context['previous_book'] == '2 Timothy'
                assert 'previous_chapter' in context
                assert context['previous_chapter'] == 1
                assert 'next_book' in context
                assert context['next_book'] == '2 Timothy'
                assert 'next_chapter' in context
                assert context['next_chapter'] == 3

                # Verify all books, chapters, and versions information
                assert 'in_order' in context
                assert context['in_order'] == globals_module.IN_ORDER_BOOKS
                assert 'chapter_selection' in context
                assert context['chapter_selection'] == globals_module.CHAPTER_SELECTION
                assert 'version_selection' in context
                assert context['version_selection'] == globals_module.VERSION_SELECTION
                
                # Verify current URL for navigation state
                assert 'current_url' in context
                assert context['current_url'] == f'/{request_book}-{request_chapter}-{request_version}/'

    # Error tests
    @pytest.mark.asyncio
    async def test_full_view_invalid_book(self):
        """Test that full_view redirects with invalid book."""
        reset_globals('[]', 'bsb', 'Genesis', '1')
        request = HttpRequest()

        # We want to intend Revelation 22 WEB because we need a book, chapter, and version that is not the same as the default book, chapter, and version
        request_book = 'Invalid'
        request_chapter = 22
        request_version = 'web'
        request.path_info = f'/{request_book}-{request_chapter}-{request_version}/'
        
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
            
            # Mock async_redirect to return a response
            with patch('frontend.views.async_redirect', new_callable=AsyncMock) as mock_redirect:
                mock_redirect.return_value = HttpResponse("Redirected")
                
                # Call full_view with invalid book
                response = await views.full_view(request, request_book, request_chapter, request_version)
                
                # Verify async_redirect was called (since book is invalid)
                assert mock_redirect.called
                # Verify we got a response
                assert response is not None
                assert response.content == b"Redirected"
                
                # Verify the redirect was to the default book/chapter/version
                call_args = mock_redirect.call_args
                assert call_args is not None
                
                # Verify the view name is 'full_view'
                assert call_args[0][0] == 'full_view'
                
                # Verify the redirect args are valid defaults
                redirect_args = call_args[1]['args']
                default_book, default_chapter, default_version = redirect_args
                
                # Verify the redirect goes to a valid book that exists in IN_ORDER_BOOKS
                assert default_book in globals_module.IN_ORDER_BOOKS
                assert default_book == globals_module.DEFAULT_BOOK
                
                # Verify the chapter is valid for that book
                assert default_chapter in range(1, globals_module.CHAPTER_SELECTION[default_book] + 1)
                assert default_chapter == globals_module.DEFAULT_CHAPTER
                
                # Verify the version is in VERSION_SELECTION
                assert default_version in globals_module.VERSION_SELECTION
                assert default_version == globals_module.DEFAULT_VERSION

    @pytest.mark.asyncio
    async def test_full_view_invalid_chapter(self):
        """Test that full_view redirects with invalid chapter."""
        reset_globals('[]', 'bsb', 'Genesis', '1')
        request = HttpRequest()
        
        # We want to intend Revelation 22 WEB because we need a book, chapter, and version that is not the same as the default book, chapter, and version
        request_book = 'Revelation'
        request_chapter = 999
        request_version = 'web'
        request.path_info = f'/{request_book}-{request_chapter}-{request_version}/'
        
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
            
            # Mock async_redirect to return a response
            with patch('frontend.views.async_redirect', new_callable=AsyncMock) as mock_redirect:
                mock_redirect.return_value = HttpResponse("Redirected")
                
                # Call full_view with invalid chapter
                response = await views.full_view(request, request_book, request_chapter, request_version)
                
                # Verify async_redirect was called (since chapter is invalid)
                assert mock_redirect.called
                # Verify we got a response
                assert response is not None
                assert response.content == b"Redirected"
                
                # Verify the redirect was to the default book/chapter/version
                call_args = mock_redirect.call_args
                assert call_args is not None
                
                # Verify the view name is 'full_view'
                assert call_args[0][0] == 'full_view'
                
                # Verify the redirect args are valid defaults
                redirect_args = call_args[1]['args']
                book, chapter, default_version = redirect_args
                
                # Verify the redirect goes to a valid book that exists in IN_ORDER_BOOKS
                assert book in globals_module.IN_ORDER_BOOKS
                assert book == request_book
                
                # Verify the chapter is valid for that book
                assert chapter in range(1, globals_module.CHAPTER_SELECTION[book] + 1)
                assert chapter == 1
                
                # Verify the version is in VERSION_SELECTION
                assert default_version in globals_module.VERSION_SELECTION
                assert default_version == globals_module.DEFAULT_VERSION

    @pytest.mark.asyncio
    async def test_full_view_chapter_is_string(self):
        """Test that full_view redirects with chapter is a string."""
        reset_globals('[]', 'bsb', 'Genesis', '1')
        request = HttpRequest()

        # We want to intend Revelation 22 WEB because we need a book, chapter, and version that is not the same as the default book, chapter, and version
        request_book = 'Revelation'
        request_chapter = 'Invalid'
        request_version = 'web'
        request.path_info = f'/{request_book}-{request_chapter}-{request_version}/'
        
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
            
            # Mock async_redirect to return a response
            with patch('frontend.views.async_redirect', new_callable=AsyncMock) as mock_redirect:
                mock_redirect.return_value = HttpResponse("Redirected")
                
                # Call full_view with invalid chapter
                response = await views.full_view(request, request_book, request_chapter, request_version)
                
                # Verify async_redirect was called (since chapter is invalid)
                assert mock_redirect.called
                # Verify we got a response
                assert response is not None
                assert response.content == b"Redirected"
                
                # Verify the redirect was to the default book/chapter/version
                call_args = mock_redirect.call_args
                assert call_args is not None
                
                # Verify the view name is 'full_view'
                assert call_args[0][0] == 'full_view'
                
                # Verify the redirect args are valid defaults
                redirect_args = call_args[1]['args']
                book, chapter, default_version = redirect_args
                
                # Verify the redirect goes to a valid book that exists in IN_ORDER_BOOKS
                assert book in globals_module.IN_ORDER_BOOKS
                assert book == request_book
                
                # Verify the chapter is valid for that book
                assert chapter in range(1, globals_module.CHAPTER_SELECTION[book] + 1)
                assert chapter == 1
                
                # Verify the version is in VERSION_SELECTION
                assert default_version in globals_module.VERSION_SELECTION
                assert default_version == globals_module.DEFAULT_VERSION

    @pytest.mark.asyncio
    async def test_full_view_invalid_version(self):
        """Test that full_view redirects with invalid version."""
        reset_globals('[]', 'bsb', 'Genesis', '1')
        request = HttpRequest()

        # We want to intend Revelation 22 WEB because we need a book, chapter, and version that is not the same as the default book, chapter, and version
        request_book = 'Revelation'
        request_chapter = 22
        request_version = 'Invalid'
        request.path_info = f'/{request_book}-{request_chapter}-{request_version}/'
        
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
            
            # Mock async_redirect to return a response
            with patch('frontend.views.async_redirect', new_callable=AsyncMock) as mock_redirect:
                mock_redirect.return_value = HttpResponse("Redirected")
                
                # Call full_view with invalid version
                response = await views.full_view(request, request_book, request_chapter, request_version)
                
                # Verify async_redirect was called (since version is invalid)
                assert mock_redirect.called
                # Verify we got a response
                assert response is not None
                assert response.content == b"Redirected"
                
                # Verify the redirect was to the default book/chapter/version
                call_args = mock_redirect.call_args
                assert call_args is not None
                
                # Verify the view name is 'full_view'
                assert call_args[0][0] == 'full_view'
                
                # Verify the redirect args are valid defaults
                redirect_args = call_args[1]['args']
                book, chapter, default_version = redirect_args
                
                # Verify the redirect goes to a valid book that exists in IN_ORDER_BOOKS
                assert book in globals_module.IN_ORDER_BOOKS
                assert book == request_book
                
                # Verify the chapter is valid for that book
                assert chapter in range(1, globals_module.CHAPTER_SELECTION[book] + 1)
                assert chapter == request_chapter
                
                # Verify the version is in VERSION_SELECTION
                assert default_version in globals_module.VERSION_SELECTION
                assert default_version == globals_module.DEFAULT_VERSION

    @pytest.mark.asyncio
    async def test_full_view_general_error(self):
        """Test that full_view handles a general error gracefully."""
        reset_globals('[]', 'bsb', 'Genesis', '1')
        request = HttpRequest()
        
        # We want to intend Revelation 22 WEB because we need a book, chapter, and version that is not the same as the default book, chapter, and version
        request_book = 'Revelation'
        request_chapter = 22
        request_version = 'web'
        request.path_info = f'/{request_book}-{request_chapter}-{request_version}/'
        
        # Patch the globals in views module to match what we set up
        with patch.multiple('frontend.views',
                          BIBLE_DATA_ROOT=globals_module.BIBLE_DATA_ROOT,
                          DEFAULT_VERSION=globals_module.DEFAULT_VERSION,
                          DEFAULT_BOOK=globals_module.DEFAULT_BOOK,
                          DEFAULT_CHAPTER=globals_module.DEFAULT_CHAPTER,
                          VERSION_SELECTION=globals_module.VERSION_SELECTION,
                          IN_ORDER_BOOKS=globals_module.IN_ORDER_BOOKS,
                          CHAPTER_SELECTION=globals_module.CHAPTER_SELECTION,
                          ALL_VERSES=FailingObject()):
            
            # Mock async_redirect to verify it's called
            with patch('frontend.views.async_redirect', new_callable=AsyncMock) as mock_redirect:
                mock_redirect.return_value = HttpResponse("Redirected")
                
                # Call full_view with valid parameters but ALL_VERSES will raise an exception
                response = await views.full_view(request, request_book, request_chapter, request_version)
                
                # Verify async_redirect was called (since an exception occurred)
                assert mock_redirect.called
                # Verify we got a response
                assert response is not None
                assert response.content == b"Redirected"
                
                # Verify the redirect was to the default book/chapter/version
                call_args = mock_redirect.call_args
                assert call_args is not None
                
                # Verify the view name is 'full_view'
                assert call_args[0][0] == 'full_view'
                
                # Verify the redirect args are valid defaults
                redirect_args = call_args[1]['args']
                default_book, default_chapter, default_version = redirect_args
                
                # Verify the redirect goes to a valid book that exists in IN_ORDER_BOOKS
                assert default_book in globals_module.IN_ORDER_BOOKS
                assert default_book == globals_module.DEFAULT_BOOK
                
                # Verify the chapter is valid for that book
                assert default_chapter in range(1, globals_module.CHAPTER_SELECTION[default_book] + 1)
                assert default_chapter == globals_module.DEFAULT_CHAPTER
                
                # Verify the version is in VERSION_SELECTION
                assert default_version in globals_module.VERSION_SELECTION
                assert default_version == globals_module.DEFAULT_VERSION

class TestBookChapterView(SimpleTestCase):
    """Tests for book_chapter_view function."""
    
    # Success tests
    @pytest.mark.asyncio
    async def test_book_chapter_view_success_genesis_1(self):
        """Test that book_chapter_view redirects to full_view with default version for Genesis 1 (first chapter in the Bible)."""
        reset_globals('[]', 'bsb', 'Genesis', '1')
        
        request = HttpRequest()
        request_book = 'Genesis'
        request_chapter = 1
        request.path_info = f'/{request_book}-{request_chapter}/'
        
        # Patch the globals in views module to match what we set up
        with patch.multiple('frontend.views',
                          DEFAULT_VERSION=globals_module.DEFAULT_VERSION,
                          DEFAULT_BOOK=globals_module.DEFAULT_BOOK,
                          DEFAULT_CHAPTER=globals_module.DEFAULT_CHAPTER,
                          IN_ORDER_BOOKS=globals_module.IN_ORDER_BOOKS,
                          CHAPTER_SELECTION=globals_module.CHAPTER_SELECTION):
            
            # Mock async_redirect to verify it's called
            with patch('frontend.views.async_redirect', new_callable=AsyncMock) as mock_redirect:
                mock_redirect.return_value = HttpResponse("Redirected")
                
                # Call book_chapter_view with valid book and chapter
                response = await views.book_chapter_view(request, request_book, request_chapter)
                
                # Verify async_redirect was called
                assert mock_redirect.called
                # Verify we got a response
                assert response is not None
                assert response.content == b"Redirected"
                
                # Verify the redirect was to full_view with the default version
                call_args = mock_redirect.call_args
                assert call_args is not None
                
                # Verify the view name is 'full_view'
                assert call_args[0][0] == 'full_view'
                
                # Verify the redirect args include the book, chapter, and default version
                redirect_args = call_args[1]['args']
                book, chapter, default_version = redirect_args

                # Verify the redirect goes to a valid book that exists in IN_ORDER_BOOKS
                assert book in globals_module.IN_ORDER_BOOKS
                assert book == request_book
                
                # Verify the chapter is valid for that book
                assert chapter in range(1, globals_module.CHAPTER_SELECTION[book] + 1)
                assert chapter == request_chapter

                # Verify the version is the default version
                assert default_version in globals_module.VERSION_SELECTION
                assert default_version == globals_module.DEFAULT_VERSION

    @pytest.mark.asyncio
    async def test_book_chapter_view_success_revelation_22(self):
        """Test that book_chapter_view redirects to full_view with default version for Revelation 22 (very last chapter in the Bible)."""
        reset_globals('[]', 'bsb', 'Genesis', '1')
        request = HttpRequest()

        request_book = 'Revelation'
        request_chapter = 22
        request.path_info = f'/{request_book}-{request_chapter}/'
        
        # Patch the globals in views module to match what we set up
        with patch.multiple('frontend.views',
                          DEFAULT_VERSION=globals_module.DEFAULT_VERSION,
                          DEFAULT_BOOK=globals_module.DEFAULT_BOOK,
                          DEFAULT_CHAPTER=globals_module.DEFAULT_CHAPTER,
                          IN_ORDER_BOOKS=globals_module.IN_ORDER_BOOKS,
                          CHAPTER_SELECTION=globals_module.CHAPTER_SELECTION):
            
            # Mock async_redirect to verify it's called
            with patch('frontend.views.async_redirect', new_callable=AsyncMock) as mock_redirect:
                mock_redirect.return_value = HttpResponse("Redirected")
                
                # Call book_chapter_view with valid book and chapter
                response = await views.book_chapter_view(request, request_book, request_chapter)
                
                # Verify async_redirect was called
                assert mock_redirect.called
                # Verify we got a response
                assert response is not None
                assert response.content == b"Redirected"
                
                # Verify the redirect was to full_view with the default version
                call_args = mock_redirect.call_args
                assert call_args is not None
                
                # Verify the view name is 'full_view'
                assert call_args[0][0] == 'full_view'
                
                # Verify the redirect args include the book, chapter, and default version
                redirect_args = call_args[1]['args']
                book, chapter, default_version = redirect_args

                # Verify the redirect goes to a valid book that exists in IN_ORDER_BOOKS
                assert book in globals_module.IN_ORDER_BOOKS
                assert book == request_book
                
                # Verify the chapter is valid for that book
                assert chapter in range(1, globals_module.CHAPTER_SELECTION[book] + 1)
                assert chapter == request_chapter

                # Verify the version is the default version
                assert default_version in globals_module.VERSION_SELECTION
                assert default_version == globals_module.DEFAULT_VERSION
    
    @pytest.mark.asyncio
    async def test_book_chapter_view_success_2_timothy_2(self):
        """Test that book_chapter_view redirects to full_view with default version for 2 Timothy 2 (a multi-word chapter name while also checking a mid-chapter and not an edge chapter)."""
        reset_globals('[]', 'bsb', 'Genesis', '1')
        request = HttpRequest()

        request_book = '2 Timothy'
        request_chapter = 2
        request.path_info = f'/{request_book}-{request_chapter}/'
        
        # Patch the globals in views module to match what we set up
        with patch.multiple('frontend.views',
                          DEFAULT_VERSION=globals_module.DEFAULT_VERSION,
                          DEFAULT_BOOK=globals_module.DEFAULT_BOOK,
                          DEFAULT_CHAPTER=globals_module.DEFAULT_CHAPTER,
                          IN_ORDER_BOOKS=globals_module.IN_ORDER_BOOKS,
                          CHAPTER_SELECTION=globals_module.CHAPTER_SELECTION):
            
            # Mock async_redirect to verify it's called
            with patch('frontend.views.async_redirect', new_callable=AsyncMock) as mock_redirect:
                mock_redirect.return_value = HttpResponse("Redirected")
                
                # Call book_chapter_view with valid book and chapter
                response = await views.book_chapter_view(request, request_book, request_chapter)
                
                # Verify async_redirect was called
                assert mock_redirect.called
                # Verify we got a response
                assert response is not None
                assert response.content == b"Redirected"
                
                # Verify the redirect was to full_view with the default version
                call_args = mock_redirect.call_args
                assert call_args is not None
                
                # Verify the view name is 'full_view'
                assert call_args[0][0] == 'full_view'
                
                # Verify the redirect args include the book, chapter, and default version
                redirect_args = call_args[1]['args']
                book, chapter, default_version = redirect_args

                # Verify the redirect goes to a valid book that exists in IN_ORDER_BOOKS
                assert book in globals_module.IN_ORDER_BOOKS
                assert book == request_book
                
                # Verify the chapter is valid for that book
                assert chapter in range(1, globals_module.CHAPTER_SELECTION[book] + 1)
                assert chapter == request_chapter

                # Verify the version is the default version
                assert default_version in globals_module.VERSION_SELECTION
                assert default_version == globals_module.DEFAULT_VERSION

    @pytest.mark.asyncio
    async def test_book_chapter_view_invalid_book(self):
        """Test that book_chapter_view redirects to defaults when given invalid book."""
        reset_globals('[]', 'bsb', 'Genesis', '1')
        request = HttpRequest()

        # We want to intend Revelation 22 because we need a book and chapter that is not the same as the default book and chapter
        request_book = 'Invalid'
        request_chapter = 22
        request.path_info = f'/{request_book}-{request_chapter}/'
        
        # Patch the globals in views module to match what we set up
        with patch.multiple('frontend.views',
                          DEFAULT_VERSION=globals_module.DEFAULT_VERSION,
                          DEFAULT_BOOK=globals_module.DEFAULT_BOOK,
                          DEFAULT_CHAPTER=globals_module.DEFAULT_CHAPTER,
                          IN_ORDER_BOOKS=globals_module.IN_ORDER_BOOKS,
                          CHAPTER_SELECTION=globals_module.CHAPTER_SELECTION):
            
            # Mock async_redirect to verify it's called
            with patch('frontend.views.async_redirect', new_callable=AsyncMock) as mock_redirect:
                mock_redirect.return_value = HttpResponse("Redirected")
                
                # Call book_chapter_view with invalid book
                response = await views.book_chapter_view(request, request_book, request_chapter)
                
                # Verify async_redirect was called
                assert mock_redirect.called
                # Verify we got a response
                assert response is not None
                assert response.content == b"Redirected"
                
                # Verify the redirect was to full_view with defaults
                call_args = mock_redirect.call_args
                assert call_args is not None
                
                # Verify the view name is 'full_view'
                assert call_args[0][0] == 'full_view'
                
                # Verify the redirect args are all defaults
                redirect_args = call_args[1]['args']
                default_book, default_chapter, default_version = redirect_args

                # Verify the redirect goes to the default book
                assert default_book in globals_module.IN_ORDER_BOOKS
                assert default_book == globals_module.DEFAULT_BOOK
                
                # Verify the chapter is the default chapter
                assert default_chapter in range(1, globals_module.CHAPTER_SELECTION[default_book] + 1)
                assert default_chapter == globals_module.DEFAULT_CHAPTER

                # Verify the version is the default version
                assert default_version in globals_module.VERSION_SELECTION
                assert default_version == globals_module.DEFAULT_VERSION
    
    @pytest.mark.asyncio
    async def test_book_chapter_view_invalid_chapter(self):
        """Test that book_chapter_view redirects to default chapter when given invalid chapter."""
        reset_globals('[]', 'bsb', 'Genesis', '1')
        request = HttpRequest()

        # We want to intend Revelation 22 because we need a book and chapter that is not the same as the default book and chapter
        request_book = 'Revelation'
        request_chapter = 999
        request.path_info = f'/{request_book}-{request_chapter}/'
        
        # Patch the globals in views module to match what we set up
        with patch.multiple('frontend.views',
                          DEFAULT_VERSION=globals_module.DEFAULT_VERSION,
                          DEFAULT_BOOK=globals_module.DEFAULT_BOOK,
                          DEFAULT_CHAPTER=globals_module.DEFAULT_CHAPTER,
                          IN_ORDER_BOOKS=globals_module.IN_ORDER_BOOKS,
                          CHAPTER_SELECTION=globals_module.CHAPTER_SELECTION):
            
            # Mock async_redirect to verify it's called
            with patch('frontend.views.async_redirect', new_callable=AsyncMock) as mock_redirect:
                mock_redirect.return_value = HttpResponse("Redirected")
                
                # Call book_chapter_view with invalid chapter
                response = await views.book_chapter_view(request, request_book, request_chapter)
                
                # Verify async_redirect was called
                assert mock_redirect.called
                # Verify we got a response
                assert response is not None
                assert response.content == b"Redirected"
                
                # Verify the redirect was to full_view with default chapter and version
                call_args = mock_redirect.call_args
                assert call_args is not None
                
                # Verify the view name is 'full_view'
                assert call_args[0][0] == 'full_view'
                
                # Verify the redirect args are book, default chapter, and default version
                redirect_args = call_args[1]['args']
                book, default_chapter, default_version = redirect_args

                # Verify the redirect goes to the default book
                assert book in globals_module.IN_ORDER_BOOKS    
                assert book == request_book
                
                # Verify the chapter is the default chapter
                assert default_chapter in range(1, globals_module.CHAPTER_SELECTION[book] + 1)
                assert default_chapter == 1

                # Verify the version is the default version
                assert default_version in globals_module.VERSION_SELECTION
                assert default_version == globals_module.DEFAULT_VERSION

    @pytest.mark.asyncio
    async def test_book_chapter_view_chapter_is_string(self):
        """Test that book_chapter_view redirects to default chapter when given invalid chapter."""
        reset_globals('[]', 'bsb', 'Genesis', '1')
        request = HttpRequest()
        
        # We want to intend Revelation 22 because we need a book and chapter that is not the same as the default book and chapter
        request_book = 'Revelation'
        request_chapter = 'Invalid'
        request.path_info = f'/{request_book}-{request_chapter}/'
        
        # Patch the globals in views module to match what we set up
        with patch.multiple('frontend.views',
                          DEFAULT_VERSION=globals_module.DEFAULT_VERSION,
                          DEFAULT_BOOK=globals_module.DEFAULT_BOOK,
                          DEFAULT_CHAPTER=globals_module.DEFAULT_CHAPTER,
                          IN_ORDER_BOOKS=globals_module.IN_ORDER_BOOKS,
                          CHAPTER_SELECTION=globals_module.CHAPTER_SELECTION):
            
            # Mock async_redirect to verify it's called
            with patch('frontend.views.async_redirect', new_callable=AsyncMock) as mock_redirect:
                mock_redirect.return_value = HttpResponse("Redirected")
                
                # Call book_chapter_view with invalid chapter
                response = await views.book_chapter_view(request, request_book, request_chapter)
                
                # Verify async_redirect was called
                assert mock_redirect.called
                # Verify we got a response
                assert response is not None
                assert response.content == b"Redirected"

                # Verify the redirect was to full_view with default chapter and version
                call_args = mock_redirect.call_args
                assert call_args is not None
                
                # Verify the view name is 'full_view'
                assert call_args[0][0] == 'full_view'
                
                # Verify the redirect args are book, default chapter, and default version
                redirect_args = call_args[1]['args']
                book, default_chapter, default_version = redirect_args

                # Verify the redirect goes to the default book
                assert book in globals_module.IN_ORDER_BOOKS    
                assert book == request_book
                
                # Verify the chapter is the default chapter
                assert default_chapter in range(1, globals_module.CHAPTER_SELECTION[book] + 1)
                assert default_chapter == 1

                # Verify the version is the default version
                assert default_version in globals_module.VERSION_SELECTION
                assert default_version == globals_module.DEFAULT_VERSION

    @pytest.mark.asyncio
    async def test_book_chapter_view_general_error(self):
        """Test that book_chapter_view handles errors gracefully."""
        reset_globals('[]', 'bsb', 'Genesis', '1')
        request = HttpRequest()

        # We want to intend Revelation 22 because we need a book and chapter that is not the same as the default book and chapter
        request_book = 'Revelation'
        request_chapter = 22
        request.path_info = f'/{request_book}-{request_chapter}/'
        
        # Patch the globals in views module with IN_ORDER_BOOKS that will cause an error
        with patch.multiple('frontend.views',
                          DEFAULT_VERSION=globals_module.DEFAULT_VERSION,
                          DEFAULT_BOOK=globals_module.DEFAULT_BOOK,
                          DEFAULT_CHAPTER=globals_module.DEFAULT_CHAPTER,
                          IN_ORDER_BOOKS=FailingObject(),
                          CHAPTER_SELECTION=globals_module.CHAPTER_SELECTION):
            
            # Mock async_redirect to verify it's called
            with patch('frontend.views.async_redirect', new_callable=AsyncMock) as mock_redirect:
                mock_redirect.return_value = HttpResponse("Redirected")
                
                # Call book_chapter_view - the FailingObject will cause an exception
                response = await views.book_chapter_view(request, request_book, request_chapter)
                
                # Verify async_redirect was called
                assert mock_redirect.called
                # Verify we got a response
                assert response is not None
                
                # Verify the redirect was to full_view with defaults
                call_args = mock_redirect.call_args
                assert call_args is not None
                
                # Verify the view name is 'full_view'
                assert call_args[0][0] == 'full_view'
                
                # Verify the redirect args are all defaults
                redirect_args = call_args[1]['args']
                default_book, default_chapter, default_version = redirect_args

                # Verify the redirect goes to the default book
                assert default_book in globals_module.IN_ORDER_BOOKS
                assert default_book == globals_module.DEFAULT_BOOK
                
                # Verify the chapter is the default chapter
                assert default_chapter in range(1, globals_module.CHAPTER_SELECTION[default_book] + 1)
                assert default_chapter == 1

                # Verify the version is the default version
                assert default_version in globals_module.VERSION_SELECTION
                assert default_version == globals_module.DEFAULT_VERSION


class TestBookView(SimpleTestCase):
    """Tests for book_view function."""
    
    # Success tests
    @pytest.mark.asyncio
    async def test_book_view_success_genesis(self):
        """Test that book_view redirects to full_view with chapter 1 and default version for Genesis (first book in the Bible)."""
        reset_globals('[]', 'bsb', 'Genesis', '1')
        request = HttpRequest()
        
        request_book = 'Genesis'
        request.path_info = f'/{request_book}/'
        
        # Patch the globals in views module to match what we set up
        with patch.multiple('frontend.views',
                          DEFAULT_VERSION=globals_module.DEFAULT_VERSION,
                          DEFAULT_BOOK=globals_module.DEFAULT_BOOK,
                          DEFAULT_CHAPTER=globals_module.DEFAULT_CHAPTER,
                          IN_ORDER_BOOKS=globals_module.IN_ORDER_BOOKS):
            
            # Mock async_redirect to verify it's called
            with patch('frontend.views.async_redirect', new_callable=AsyncMock) as mock_redirect:
                mock_redirect.return_value = HttpResponse("Redirected")
                
                # Call book_view with valid book
                response = await views.book_view(request, request_book)
                
                # Verify async_redirect was called
                assert mock_redirect.called
                # Verify we got a response
                assert response is not None
                assert response.content == b"Redirected"
                
                # Verify the redirect was to full_view with the specified book, chapter 1, and default version
                call_args = mock_redirect.call_args
                assert call_args is not None
                
                # Verify the view name is 'full_view'
                assert call_args[0][0] == 'full_view'
                
                # Verify the redirect args are the specified book, chapter 1, and default version
                redirect_args = call_args[1]['args']
                book, chapter, default_version = redirect_args

                # Verify the redirect goes to the specified book
                assert book in globals_module.IN_ORDER_BOOKS
                assert book == request_book
                
                # Verify the chapter is the specified chapter
                assert chapter in range(1, globals_module.CHAPTER_SELECTION[book] + 1)
                assert chapter == 1

                # Verify the version is the default version
                assert default_version in globals_module.VERSION_SELECTION
                assert default_version == globals_module.DEFAULT_VERSION
    
    @pytest.mark.asyncio
    async def test_book_view_success_revelation(self):
        """Test that book_view redirects to full_view with chapter 1 and default version for Revelation (last book in the Bible)."""
        reset_globals('[]', 'bsb', 'Genesis', '1')
        request = HttpRequest()

        request_book = 'Revelation'
        request.path_info = f'/{request_book}/'
        
        # Patch the globals in views module to match what we set up
        with patch.multiple('frontend.views',
                          DEFAULT_VERSION=globals_module.DEFAULT_VERSION,
                          DEFAULT_BOOK=globals_module.DEFAULT_BOOK,
                          DEFAULT_CHAPTER=globals_module.DEFAULT_CHAPTER,
                          IN_ORDER_BOOKS=globals_module.IN_ORDER_BOOKS):
            
            # Mock async_redirect to verify it's called
            with patch('frontend.views.async_redirect', new_callable=AsyncMock) as mock_redirect:
                mock_redirect.return_value = HttpResponse("Redirected")
                
                # Call book_view with valid book
                response = await views.book_view(request, request_book)
                
                # Verify async_redirect was called
                assert mock_redirect.called
                # Verify we got a response
                assert response is not None
                assert response.content == b"Redirected"
                
                # Verify the redirect was to full_view with the specified book, chapter 1, and default version
                call_args = mock_redirect.call_args
                assert call_args is not None
                
                # Verify the view name is 'full_view'
                assert call_args[0][0] == 'full_view'
                
                # Verify the redirect args are the specified book, chapter 1, and default version
                redirect_args = call_args[1]['args']
                book, chapter, default_version = redirect_args

                # Verify the redirect goes to the specified book
                assert book in globals_module.IN_ORDER_BOOKS
                assert book == request_book
                
                # Verify the chapter is the specified chapter
                assert chapter in range(1, globals_module.CHAPTER_SELECTION[book] + 1)
                assert chapter == 1

                # Verify the version is the default version
                assert default_version in globals_module.VERSION_SELECTION
                assert default_version == globals_module.DEFAULT_VERSION

    @pytest.mark.asyncio
    async def test_book_view_success_2_timothy(self):
        """Test that book_view redirects to full_view with chapter 1 and default version."""
        reset_globals('[]', 'bsb', 'Genesis', '1')
        request = HttpRequest()

        request_book = '2 Timothy'
        request.path_info = f'/{request_book}/'
        
        # Patch the globals in views module to match what we set up
        with patch.multiple('frontend.views',
                          DEFAULT_VERSION=globals_module.DEFAULT_VERSION,
                          DEFAULT_BOOK=globals_module.DEFAULT_BOOK,
                          DEFAULT_CHAPTER=globals_module.DEFAULT_CHAPTER,
                          IN_ORDER_BOOKS=globals_module.IN_ORDER_BOOKS):
            
            # Mock async_redirect to verify it's called
            with patch('frontend.views.async_redirect', new_callable=AsyncMock) as mock_redirect:
                mock_redirect.return_value = HttpResponse("Redirected")
                
                # Call book_view with valid book
                response = await views.book_view(request, request_book)
                
                # Verify async_redirect was called
                assert mock_redirect.called
                # Verify we got a response
                assert response is not None
                assert response.content == b"Redirected"
                
                # Verify the redirect was to full_view with the specified book, chapter 1, and default version
                call_args = mock_redirect.call_args
                assert call_args is not None
                
                # Verify the view name is 'full_view'
                assert call_args[0][0] == 'full_view'
                
                # Verify the redirect args are the specified book, chapter 1, and default version
                redirect_args = call_args[1]['args']
                book, chapter, default_version = redirect_args

                # Verify the redirect goes to the specified book
                assert book in globals_module.IN_ORDER_BOOKS
                assert book == request_book
                
                # Verify the chapter is the specified chapter
                assert chapter in range(1, globals_module.CHAPTER_SELECTION[book] + 1)
                assert chapter == 1

                # Verify the version is the default version
                assert default_version in globals_module.VERSION_SELECTION
                assert default_version == globals_module.DEFAULT_VERSION

    # Error tests
    @pytest.mark.asyncio
    async def test_book_view_invalid_book(self):
        """Test that book_view redirects to defaults when given invalid book."""
        reset_globals('[]', 'bsb', 'Genesis', '1')
        request = HttpRequest()

        # We want to intend Revelation because we need a book that is not the same as the default book
        request_book = 'Invalid'
        request.path_info = f'/{request_book}/'
        
        # Patch the globals in views module to match what we set up
        with patch.multiple('frontend.views',
                          DEFAULT_VERSION=globals_module.DEFAULT_VERSION,
                          DEFAULT_BOOK=globals_module.DEFAULT_BOOK,
                          DEFAULT_CHAPTER=globals_module.DEFAULT_CHAPTER,
                          IN_ORDER_BOOKS=globals_module.IN_ORDER_BOOKS):
            
            # Mock async_redirect to verify it's called
            with patch('frontend.views.async_redirect', new_callable=AsyncMock) as mock_redirect:
                mock_redirect.return_value = HttpResponse("Redirected")
                
                # Call book_view with invalid book
                response = await views.book_view(request, request_book)
                
                # Verify async_redirect was called
                assert mock_redirect.called
                # Verify we got a response
                assert response is not None
                assert response.content == b"Redirected"
                
                # Verify the redirect was to full_view with defaults
                call_args = mock_redirect.call_args
                assert call_args is not None
                
                # Verify the view name is 'full_view'
                assert call_args[0][0] == 'full_view'
                
                # Verify the redirect args are the default book, default chapter, and default version
                redirect_args = call_args[1]['args']
                default_book, default_chapter, default_version = redirect_args

                # Verify the redirect goes to the default book
                assert default_book in globals_module.IN_ORDER_BOOKS
                assert default_book == globals_module.DEFAULT_BOOK
                
                # Verify the chapter is the default chapter
                assert default_chapter in range(1, globals_module.CHAPTER_SELECTION[default_book] + 1)
                assert default_chapter == globals_module.DEFAULT_CHAPTER

                # Verify the version is the default version
                assert default_version in globals_module.VERSION_SELECTION
                assert default_version == globals_module.DEFAULT_VERSION

    @pytest.mark.asyncio
    async def test_book_view_general_error(self):
        """Test that book_view handles errors gracefully."""
        reset_globals('[]', 'bsb', 'Genesis', '1')
        request = HttpRequest()

        # We want to intend Revelation because we need a book that is not the same as the default book
        request_book = 'Revelation'
        request.path_info = f'/{request_book}/'
        
        # Patch the globals in views module with IN_ORDER_BOOKS that will cause an error
        with patch.multiple('frontend.views',
                          DEFAULT_VERSION=globals_module.DEFAULT_VERSION,
                          DEFAULT_BOOK=globals_module.DEFAULT_BOOK,
                          DEFAULT_CHAPTER=globals_module.DEFAULT_CHAPTER,
                          IN_ORDER_BOOKS=FailingObject()):
            
            # Mock async_redirect to verify it's called
            with patch('frontend.views.async_redirect', new_callable=AsyncMock) as mock_redirect:
                mock_redirect.return_value = HttpResponse("Redirected")
                
                # Call book_view - the FailingObject will cause an exception
                response = await views.book_view(request, request_book)
                
                # Verify async_redirect was called (due to the exception)
                assert mock_redirect.called
                # Verify we got a response
                assert response is not None
                assert response.content == b"Redirected"

                # Verify the redirect was to full_view with defaults
                call_args = mock_redirect.call_args
                assert call_args is not None
                
                # Verify the view name is 'full_view'
                assert call_args[0][0] == 'full_view'
                
                # Verify the redirect args are the default book, default chapter, and default version
                redirect_args = call_args[1]['args']
                default_book, default_chapter, default_version = redirect_args

                # Verify the redirect goes to the default book
                assert default_book in globals_module.IN_ORDER_BOOKS
                assert default_book == globals_module.DEFAULT_BOOK
                
                # Verify the chapter is the default chapter
                assert default_chapter in range(1, globals_module.CHAPTER_SELECTION[default_book] + 1)
                assert default_chapter == globals_module.DEFAULT_CHAPTER

                # Verify the version is the default version
                assert default_version in globals_module.VERSION_SELECTION
                assert default_version == globals_module.DEFAULT_VERSION

class TestDefaultView(SimpleTestCase):
    """Tests for default_view function."""
    
    # Success tests
    @pytest.mark.asyncio
    async def test_default_view_success(self):
        """Test that default_view redirects to full_view with default book, chapter, and version."""
        reset_globals('[]', 'bsb', 'Genesis', '1')
        request = HttpRequest()
        request.path_info = '/'
        
        # Patch the globals in views module to match what we set up
        with patch.multiple('frontend.views',
                          DEFAULT_VERSION=globals_module.DEFAULT_VERSION,
                          DEFAULT_BOOK=globals_module.DEFAULT_BOOK,
                          DEFAULT_CHAPTER=globals_module.DEFAULT_CHAPTER):
            
            # Mock async_redirect to verify it's called
            with patch('frontend.views.async_redirect', new_callable=AsyncMock) as mock_redirect:
                mock_redirect.return_value = HttpResponse("Redirected")
                
                # Call default_view
                response = await views.default_view(request)
                
                # Verify async_redirect was called
                assert mock_redirect.called
                # Verify we got a response
                assert response is not None
                assert response.content == b"Redirected"
                
                # Verify the redirect was to full_view with defaults
                call_args = mock_redirect.call_args
                assert call_args is not None
                
                # Verify the view name is 'full_view'
                assert call_args[0][0] == 'full_view'
                
                # Verify the redirect args are the default book, default chapter, and default version
                redirect_args = call_args[1]['args']
                default_book, default_chapter, default_version = redirect_args

                # Verify the redirect goes to the default book
                assert default_book in globals_module.IN_ORDER_BOOKS
                assert default_book == globals_module.DEFAULT_BOOK
                
                # Verify the chapter is the default chapter
                assert default_chapter in range(1, globals_module.CHAPTER_SELECTION[default_book] + 1)
                assert default_chapter == globals_module.DEFAULT_CHAPTER

                # Verify the version is the default version
                assert default_version in globals_module.VERSION_SELECTION
                assert default_version == globals_module.DEFAULT_VERSION

    # Error tests
    @pytest.mark.asyncio
    async def test_default_view_general_error(self):
        """Test that default_view handles errors gracefully."""
        reset_globals('[]', 'bsb', 'Genesis', '1')
        request = HttpRequest()
        request.path_info = '/'
        
        # Patch the globals in views module with VERSION_SELECTION that will cause an error
        with patch.multiple('frontend.views',
                          DEFAULT_VERSION=globals_module.DEFAULT_VERSION,
                          DEFAULT_BOOK=globals_module.DEFAULT_BOOK,
                          DEFAULT_CHAPTER=globals_module.DEFAULT_CHAPTER,
                          VERSION_SELECTION=FailingObject()):
            
            # Mock async_redirect to verify it's called
            with patch('frontend.views.async_redirect', new_callable=AsyncMock) as mock_redirect:
                mock_redirect.return_value = HttpResponse("Redirected")
                
                # Call default_view - the FailingObject will cause an exception
                response = await views.default_view(request)
                
                # Verify async_redirect was called
                assert mock_redirect.called
                # Verify we got a response
                assert response is not None
                assert response.content == b"Redirected"
                
                # Verify the redirect was to full_view with defaults
                call_args = mock_redirect.call_args
                assert call_args is not None
                
                # Verify the view name is 'full_view'
                assert call_args[0][0] == 'full_view'
                
                # Verify the redirect args are the default book, default chapter, and default version
                redirect_args = call_args[1]['args']
                default_book, default_chapter, default_version = redirect_args

                # Verify the redirect goes to the default book
                assert default_book in globals_module.IN_ORDER_BOOKS
                assert default_book == globals_module.DEFAULT_BOOK
                
                # Verify the chapter is the default chapter
                assert default_chapter in range(1, globals_module.CHAPTER_SELECTION[default_book] + 1)
                assert default_chapter == globals_module.DEFAULT_CHAPTER

                # Verify the version is the default version
                assert default_version in globals_module.VERSION_SELECTION
                assert default_version == globals_module.DEFAULT_VERSION