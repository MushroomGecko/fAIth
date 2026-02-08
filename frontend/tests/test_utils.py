import pytest
import json
import tempfile
from unittest.mock import patch
from django.test import SimpleTestCase, RequestFactory
from django.http import HttpResponse, HttpResponseRedirect
from pathlib import Path

from frontend import utils


class TestSyncParseVerses(SimpleTestCase):
    """Tests for sync_parse_verses function."""
    
    def setUp(self):
        """Set up temporary test files."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
    
    def tearDown(self):
        """Clean up temporary files."""
        self.temp_dir.cleanup()
    
    # Success tests
    def test_sync_parse_verses_success(self):
        """Test that sync_parse_verses succeeds when given a valid file path."""
        test_data = {
            "1": "First verse",
            "2": "Second verse"
        }
        test_file = self.temp_path.joinpath("test_verses.json")
        with open(test_file, 'w', encoding='utf-8') as file:
            json.dump(test_data, file)
        
        verses = utils.sync_parse_verses(str(test_file))

        assert isinstance(verses, list)
        assert len(verses) == 2
        assert verses[0] == '1) First verse'
        assert verses[-1] == '2) Second verse'
    
    def test_sync_parse_verses_with_headers(self):
        """Test that sync_parse_verses correctly parses verses with headers."""
        test_data = {
            "1": "First verse",
            "header_1": "Chapter Header",
            "2": "Second verse"
        }
        test_file = self.temp_path.joinpath("test_verses.json")
        with open(test_file, 'w', encoding='utf-8') as file:
            json.dump(test_data, file)
        
        verses = utils.sync_parse_verses(str(test_file))

        assert isinstance(verses, list)
        assert len(verses) == 3
        assert verses[0] == '1) First verse'
        assert '<span class="header">Chapter Header</span>' in verses[1]
        assert verses[2] == '2) Second verse'
    
    def test_sync_parse_verses_empty_file(self):
        """Test that sync_parse_verses returns empty list for empty file."""
        test_file = self.temp_path.joinpath("empty.json")
        with open(test_file, 'w', encoding='utf-8') as file:
            json.dump({}, file)
        
        verses = utils.sync_parse_verses(str(test_file))
        
        assert isinstance(verses, list)
        assert len(verses) == 0
        assert verses == []
    
    def test_sync_parse_verses_malformed_json(self):
        """Test that sync_parse_verses handles malformed JSON gracefully."""
        test_data = "{ invalid json"
        test_file = self.temp_path.joinpath("malformed.json")
        with open(test_file, 'w', encoding='utf-8') as file:
            file.write(test_data)
        
        verses = utils.sync_parse_verses(str(test_file))

        assert isinstance(verses, list)
        assert len(verses) == 0
        assert verses == []
    
    # Error tests
    def test_sync_parse_verses_invalid_file_path(self):
        """Test that sync_parse_verses returns empty list for invalid file path."""
        verses = utils.sync_parse_verses('./nonexistent/path/that/cannot/exist/file.json')

        assert isinstance(verses, list)
        assert len(verses) == 0
        assert verses == []


class TestAsyncParseVerses(SimpleTestCase):
    """Tests for async_parse_verses function."""
    
    def setUp(self):
        """Set up temporary test files."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
    
    def tearDown(self):
        """Clean up temporary files."""
        self.temp_dir.cleanup()
    
    # Success tests
    async def test_async_parse_verses_success(self):
        """Test that sync_parse_verses succeeds when given a valid file path."""
        test_data = {
            "1": "First verse",
            "2": "Second verse"
        }
        test_file = self.temp_path.joinpath("test_verses.json")
        with open(test_file, 'w', encoding='utf-8') as file:
            json.dump(test_data, file)
        
        verses = await utils.async_parse_verses(str(test_file))

        assert isinstance(verses, list)
        assert len(verses) == 2
        assert verses[0] == '1) First verse'
        assert verses[-1] == '2) Second verse'
    
    async def test_async_parse_verses_with_headers(self):
        """Test that sync_parse_verses correctly parses verses with headers."""
        test_data = {
            "1": "First verse",
            "header_1": "Chapter Header",
            "2": "Second verse"
        }
        test_file = self.temp_path.joinpath("test_verses.json")
        with open(test_file, 'w', encoding='utf-8') as file:
            json.dump(test_data, file)
        
        verses = await utils.async_parse_verses(str(test_file))

        assert isinstance(verses, list)
        assert len(verses) == 3
        assert verses[0] == '1) First verse'
        assert '<span class="header">Chapter Header</span>' in verses[1]
        assert verses[2] == '2) Second verse'
    
    async def test_async_parse_verses_empty_file(self):
        """Test that sync_parse_verses returns empty list for empty file."""
        test_file = self.temp_path.joinpath("empty.json")
        with open(test_file, 'w', encoding='utf-8') as file:
            json.dump({}, file)
        
        verses = await utils.async_parse_verses(str(test_file))
        
        assert isinstance(verses, list)
        assert len(verses) == 0
        assert verses == []
    
    async def test_async_parse_verses_malformed_json(self):
        """Test that sync_parse_verses handles malformed JSON gracefully."""
        test_data = "{ invalid json"
        test_file = self.temp_path.joinpath("malformed.json")
        with open(test_file, 'w', encoding='utf-8') as file:
            file.write(test_data)
        
        verses = await utils.async_parse_verses(str(test_file))

        assert isinstance(verses, list)
        assert len(verses) == 0
        assert verses == []
    
    # Error tests
    async def test_async_parse_verses_invalid_file_path(self):
        """Test that async_parse_verses returns empty list for invalid file path."""
        verses = await utils.async_parse_verses('./nonexistent/path/that/cannot/exist/file.json')
        
        assert isinstance(verses, list)
        assert len(verses) == 0
        assert verses == []

@pytest.mark.asyncio
class TestAsyncRender(SimpleTestCase):
    """Tests for async_render function."""
    
    async def test_async_render_success_basic(self):
        """Test that async_render successfully renders a template with basic request and context."""
        factory = RequestFactory()
        request = factory.get('/')
        
        with patch('frontend.utils.render') as mock_render:
            mock_render.return_value = HttpResponse('Rendered')
            result = await utils.async_render(request, 'test.html', {})
            
            # Verify render was called
            assert mock_render.called
            # Verify we got an HttpResponse back
            assert isinstance(result, HttpResponse)
            assert result.content == b'Rendered'
            
            # Verify render was called with correct arguments
            call_args = mock_render.call_args
            assert call_args[0][0] == request
            assert call_args[0][1] == 'test.html'
            assert call_args[0][2] == {}
    
    async def test_async_render_with_context_data(self):
        """Test that async_render passes context data correctly to render."""
        factory = RequestFactory()
        request = factory.get('/')
        context = {'book': 'Genesis', 'chapter': 1, 'verses': ['verse1', 'verse2']}
        
        with patch('frontend.utils.render') as mock_render:
            mock_render.return_value = HttpResponse('Rendered')
            result = await utils.async_render(request, 'test.html', context)

            # Verify render was called
            assert mock_render.called
            # Verify we got an HttpResponse back
            assert isinstance(result, HttpResponse)
            assert result.content == b'Rendered'
            
            # Verify render was called with context
            call_args = mock_render.call_args
            
            assert call_args is not None
            assert call_args[0][2] == context
            assert 'book' in call_args[0][2]
            assert call_args[0][2]['book'] == 'Genesis'
            assert 'chapter' in call_args[0][2]
            assert call_args[0][2]['chapter'] == 1
            assert 'verses' in call_args[0][2]
            assert call_args[0][2]['verses'] == ['verse1', 'verse2']

    async def test_async_render_empty_context(self):
        """Test that async_render handles empty context correctly."""
        factory = RequestFactory()
        request = factory.get('/')
        
        with patch('frontend.utils.render') as mock_render:
            mock_render.return_value = HttpResponse('Rendered')
            result = await utils.async_render(request, 'simple.html', {})
            
            # Verify render was called
            assert mock_render.called
            # Verify we got an HttpResponse back
            assert isinstance(result, HttpResponse)
            assert result.content == b'Rendered'
            
            # Verify render was called with correct arguments
            call_args = mock_render.call_args
            
            assert call_args is not None
            assert call_args[0][0] == request
            assert call_args[0][1] == 'simple.html'
            assert call_args[0][2] == {}

    async def test_async_render_different_templates(self):
        """Test that async_render works with different template names."""
        factory = RequestFactory()
        request = factory.get('/')
        
        templates = ['home.html', 'about.html', 'contact.html', 'index.html']
        for template in templates:
            with patch('frontend.utils.render') as mock_render:
                mock_render.return_value = HttpResponse(f'Rendered from {template}')
                result = await utils.async_render(request, template, {"1": template})
                
                # Verify render was called
                assert mock_render.called
                # Verify we got an HttpResponse back
                assert isinstance(result, HttpResponse)
                expected_content = f'Rendered from {template}'.encode('utf-8')
                assert result.content == expected_content
                
                # Verify correct template was used
                call_args = mock_render.call_args
                
                assert call_args is not None
                assert call_args[0][0] == request
                assert call_args[0][1] == template
                assert call_args[0][2] == {"1": template}
    

    
    async def test_async_render_complex_context(self):
        """Test that async_render handles complex nested context data."""
        factory = RequestFactory()
        request = factory.get('/')
        context = {
            'book': 'Psalms',
            'chapters': [1, 2, 3, 4, 5],
            'metadata': {
                'author': 'David',
                'books': {
                    'torah': ['Genesis', 'Exodus'],
                    'history': ['Joshua', 'Judges']
                }
            },
            'verses_count': 150
        }
        
        with patch('frontend.utils.render') as mock_render:
            mock_render.return_value = HttpResponse('Rendered')
            result = await utils.async_render(request, 'psalms.html', context)
            
            # Verify render was called
            assert mock_render.called
            # Verify we got an HttpResponse back
            assert isinstance(result, HttpResponse)
            assert result.content == b'Rendered'
            
            # Verify render was called with correct arguments
            call_args = mock_render.call_args
            assert call_args is not None
            assert call_args[0][0] == request
            assert call_args[0][1] == 'psalms.html'
            assert call_args[0][2] == context
            assert call_args[0][2]['book'] == 'Psalms'
            assert call_args[0][2]['chapters'] == [1, 2, 3, 4, 5]
            assert call_args[0][2]['metadata'] == {
                'author': 'David',
                'books': {
                    'torah': ['Genesis', 'Exodus'],
                    'history': ['Joshua', 'Judges']
                }
            }
            assert call_args[0][2]['metadata']['books']['torah'] == ['Genesis', 'Exodus']
            assert call_args[0][2]['metadata']['books']['history'] == ['Joshua', 'Judges']
            assert call_args[0][2]['verses_count'] == 150
    
    async def test_async_render_request_methods(self):
        """Test that async_render works with different HTTP request methods."""
        methods = ['GET', 'POST']
        
        for method in methods:
            factory = RequestFactory()
            if method == 'GET':
                request = factory.get('/test')
            else:
                request = factory.post('/test', {'data': 'value'})
            
            with patch('frontend.utils.render') as mock_render:
                mock_render.return_value = HttpResponse(f'{method} response')
                result = await utils.async_render(request, 'form.html', {})

                # Verify render was called
                assert mock_render.called
                # Verify we got an HttpResponse back
                assert isinstance(result, HttpResponse)
                expected_content = f'{method} response'.encode('utf-8')
                assert result.content == expected_content
                
                call_args = mock_render.call_args
                assert call_args is not None
                assert call_args[0][0] == request
                assert call_args[0][1] == 'form.html'
                assert call_args[0][2] == {}
                assert call_args[0][0].method == method
    
    async def test_async_render_returns_response_object(self):
        """Test that async_render always returns an HttpResponse object."""
        factory = RequestFactory()
        request = factory.get('/')
        
        with patch('frontend.utils.render') as mock_render:
            mock_render.return_value = HttpResponse('Rendered')
            result = await utils.async_render(request, 'test.html', {})
            
            assert isinstance(result, HttpResponse)
            assert hasattr(result, 'content')
            assert hasattr(result, 'status_code')
    
    async def test_async_render_with_status_code(self):
        """Test that async_render preserves HTTP status codes."""
        factory = RequestFactory()
        request = factory.get('/')
        
        # Test with 404 status code
        with patch('frontend.utils.render') as mock_render:
            response = HttpResponse('Not found', status=404)
            mock_render.return_value = response
            result = await utils.async_render(request, 'error.html', {})
            
            assert result.status_code == 404
    
    async def test_async_render_thread_safe_execution(self):
        """Test that async_render executes in a thread-safe manner."""
        factory = RequestFactory()
        request1 = factory.get('/path1')
        request2 = factory.get('/path2')
        
        with patch('frontend.utils.render') as mock_render:
            mock_render.return_value = HttpResponse('Rendered')
            
            # Simulate concurrent calls
            result1 = await utils.async_render(request1, 'template1.html', {'data': 1})
            result2 = await utils.async_render(request2, 'template2.html', {'data': 2})
            
            # Both should succeed without interference
            assert mock_render.call_count == 2
            assert result1 is not None
            assert result2 is not None
            assert result1.content == b'Rendered'
            assert result2.content == b'Rendered'

            # Verify both calls using call_args_list
            assert len(mock_render.call_args_list) == 2
            
            # Verify first call with request1
            first_call_args = mock_render.call_args_list[0][0]
            assert first_call_args[0] == request1
            assert first_call_args[1] == 'template1.html'
            assert first_call_args[2] == {'data': 1}
            
            # Verify second call with request2
            second_call_args = mock_render.call_args_list[1][0]
            assert second_call_args[0] == request2
            assert second_call_args[1] == 'template2.html'
            assert second_call_args[2] == {'data': 2}


@pytest.mark.asyncio
class TestAsyncRedirect(SimpleTestCase):
    """Tests for async_redirect function."""
    
    async def test_async_redirect_simple_url(self):
        """Test that async_redirect successfully redirects to a simple URL."""
        with patch('frontend.utils.reverse') as mock_reverse, \
             patch('frontend.utils.redirect') as mock_redirect:
            mock_reverse.return_value = '/expected/path/'
            mock_redirect.return_value = HttpResponseRedirect('/expected/path/')
            
            result = await utils.async_redirect('home')
            
            # Verify reverse was called with correct arguments
            mock_reverse.assert_called_once_with('home', args=[])
            # Verify redirect was called with the result of reverse
            mock_redirect.assert_called_once_with('/expected/path/')
            # Verify we got an HttpResponseRedirect back
            assert isinstance(result, HttpResponseRedirect)
    
    async def test_async_redirect_with_single_arg(self):
        """Test that async_redirect passes a single argument correctly."""
        with patch('frontend.utils.reverse') as mock_reverse, \
             patch('frontend.utils.redirect') as mock_redirect:
            mock_reverse.return_value = '/book/genesis/'
            mock_redirect.return_value = HttpResponseRedirect('/book/genesis/')
            
            result = await utils.async_redirect('book-detail', args=['genesis'])
            
            # Verify reverse was called with correct arguments
            mock_reverse.assert_called_once_with('book-detail', args=['genesis'])
            # Verify redirect was called
            mock_redirect.assert_called_once()
            assert isinstance(result, HttpResponseRedirect)
    
    async def test_async_redirect_with_multiple_args(self):
        """Test that async_redirect handles multiple arguments."""
        with patch('frontend.utils.reverse') as mock_reverse, patch('frontend.utils.redirect') as mock_redirect:
            mock_reverse.return_value = '/book/genesis/1/verse/1/'
            mock_redirect.return_value = HttpResponseRedirect('/book/genesis/1/verse/1/')
            
            args = ['genesis', 1, 'verse', 1]
            result = await utils.async_redirect('verse-detail', args=args)
            
            # Verify reverse was called with correct arguments
            mock_reverse.assert_called_once_with('verse-detail', args=args)
            # Verify redirect was called
            mock_redirect.assert_called_once()
            assert isinstance(result, HttpResponseRedirect)
    
    async def test_async_redirect_default_empty_args(self):
        """Test that async_redirect uses empty list as default for args."""
        with patch('frontend.utils.reverse') as mock_reverse, patch('frontend.utils.redirect') as mock_redirect:
            mock_reverse.return_value = '/home/'
            mock_redirect.return_value = HttpResponseRedirect('/home/')
            
            result = await utils.async_redirect('home')
            assert isinstance(result, HttpResponseRedirect)
            
            # Verify reverse was called with empty args list by default
            call_kwargs = mock_reverse.call_args[1]
            assert call_kwargs['args'] == []
    
    async def test_async_redirect_returns_redirect_response(self):
        """Test that async_redirect returns an HttpResponseRedirect object."""
        with patch('frontend.utils.reverse') as mock_reverse, patch('frontend.utils.redirect') as mock_redirect:
            mock_reverse.return_value = '/target/'
            response = HttpResponseRedirect('/target/')
            mock_redirect.return_value = response
            
            result = await utils.async_redirect('target')
            assert isinstance(result, HttpResponseRedirect)
            
            assert result is response
    
    async def test_async_redirect_status_code(self):
        """Test that async_redirect returns correct HTTP status code."""
        with patch('frontend.utils.reverse') as mock_reverse, patch('frontend.utils.redirect') as mock_redirect:
            mock_reverse.return_value = '/redirect-to/'
            # HttpResponseRedirect defaults to 302
            response = HttpResponseRedirect('/redirect-to/')
            mock_redirect.return_value = response
            
            result = await utils.async_redirect('redirect')
            assert isinstance(result, HttpResponseRedirect)

            assert result.status_code == 302
    
    async def test_async_redirect_with_string_arg(self):
        """Test that async_redirect works with string arguments."""
        with patch('frontend.utils.reverse') as mock_reverse, patch('frontend.utils.redirect') as mock_redirect:
            mock_reverse.return_value = '/book/genesis/'
            mock_redirect.return_value = HttpResponseRedirect('/book/genesis/')
            
            result = await utils.async_redirect('book-detail', args=['genesis'])
            assert isinstance(result, HttpResponseRedirect)

            # Verify the string argument was passed correctly
            call_args = mock_reverse.call_args[1]['args']
            assert call_args == ['genesis']
    
    async def test_async_redirect_with_numeric_args(self):
        """Test that async_redirect works with numeric arguments."""
        with patch('frontend.utils.reverse') as mock_reverse, patch('frontend.utils.redirect') as mock_redirect:
            mock_reverse.return_value = '/chapter/1/verse/1/'
            mock_redirect.return_value = HttpResponseRedirect('/chapter/1/verse/1/')
            
            result = await utils.async_redirect('chapter-verse', args=[1, 1])
            assert isinstance(result, HttpResponseRedirect)

            # Verify numeric arguments were passed correctly
            call_args = mock_reverse.call_args[1]['args']
            assert call_args == [1, 1]
    
    async def test_async_redirect_mixed_arg_types(self):
        """Test that async_redirect handles mixed string and numeric arguments."""
        with patch('frontend.utils.reverse') as mock_reverse, patch('frontend.utils.redirect') as mock_redirect:
            mock_reverse.return_value = '/book/genesis/chapter/1/'
            mock_redirect.return_value = HttpResponseRedirect('/book/genesis/chapter/1/')
            
            result = await utils.async_redirect('book-chapter', args=['genesis', 1])
            assert isinstance(result, HttpResponseRedirect)

            # Verify mixed arguments were passed correctly
            call_args = mock_reverse.call_args[1]['args']
            assert call_args == ['genesis', 1]
    
    async def test_async_redirect_reverse_called_before_redirect(self):
        """Test that reverse is called before redirect."""
        call_order = []
        
        def mock_reverse_func(url, args=[]):
            call_order.append('reverse')
            return f'/path/{url}/'
        
        def mock_redirect_func(path):
            call_order.append('redirect')
            return HttpResponseRedirect(path)
        
        with patch('frontend.utils.reverse', side_effect=mock_reverse_func), patch('frontend.utils.redirect', side_effect=mock_redirect_func):
            
            result = await utils.async_redirect('test')
            assert isinstance(result, HttpResponseRedirect)

            # Verify reverse was called before redirect
            assert call_order == ['reverse', 'redirect']
    
    async def test_async_redirect_multiple_sequential_calls(self):
        """Test that multiple sequential async_redirect calls work correctly."""
        with patch('frontend.utils.reverse') as mock_reverse, patch('frontend.utils.redirect') as mock_redirect:
            mock_reverse.side_effect = ['/home/', '/about/', '/contact/']
            mock_redirect.side_effect = [
                HttpResponseRedirect('/home/'),
                HttpResponseRedirect('/about/'),
                HttpResponseRedirect('/contact/')
            ]
            
            result1 = await utils.async_redirect('home')
            result2 = await utils.async_redirect('about')
            result3 = await utils.async_redirect('contact')
            assert isinstance(result1, HttpResponseRedirect)
            assert isinstance(result2, HttpResponseRedirect)
            assert isinstance(result3, HttpResponseRedirect)
            
            # Verify all calls succeeded
            assert mock_reverse.call_count == 3
            assert mock_redirect.call_count == 3
