import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock
from django.test import SimpleTestCase

from ai.utils import async_read_file, stringify_vdb_results, clean_llm_output


@pytest.mark.asyncio
class TestAsyncReadFile(SimpleTestCase):
    """Tests for async_read_file function."""
    
    def setUp(self):
        """Set up temporary test files."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
    
    def tearDown(self):
        """Clean up temporary files."""
        self.temp_dir.cleanup()
    
    async def test_async_read_file_success(self):
        """Test that async_read_file successfully reads a file."""
        test_content = "This is test file content"
        test_file = self.temp_path.joinpath("test.txt")
        with open(test_file, 'w', encoding='utf-8') as file:
            file.write(test_content)
        
        result = await async_read_file(str(test_file))
        
        assert result == test_content
    
    async def test_async_read_file_with_utf8_encoding(self):
        """Test that async_read_file handles UTF-8 encoding correctly."""
        test_content = "Hello 世界 🌍"
        test_file = self.temp_path.joinpath("utf8.txt")
        with open(test_file, 'w', encoding='utf-8') as file:
            file.write(test_content)
        
        result = await async_read_file(str(test_file), encoding='utf-8')
        
        assert result == test_content
    
    async def test_async_read_file_invalid_path(self):
        """Test that async_read_file returns None for invalid file path."""
        result = await async_read_file('./nonexistent/path/file.txt')
        
        assert result is None
    
    async def test_async_read_file_with_multiline_content(self):
        """Test that async_read_file preserves multiline content."""
        test_content = "Line 1\nLine 2\nLine 3"
        test_file = self.temp_path.joinpath("multiline.txt")
        with open(test_file, 'w', encoding='utf-8') as file:
            file.write(test_content)
        
        result = await async_read_file(str(test_file))
        
        assert result == test_content
        assert result.count('\n') == 2
    
    async def test_async_read_file_with_empty_file(self):
        """Test that async_read_file handles empty files."""
        test_file = self.temp_path.joinpath("empty.txt")
        with open(test_file, 'w', encoding='utf-8') as file:
            file.write("")
        
        result = await async_read_file(str(test_file))
        
        assert result == ""
    
    async def test_async_read_file_with_large_content(self):
        """Test that async_read_file handles large files."""
        test_content = "x" * 100000  # 100k characters
        test_file = self.temp_path.joinpath("large.txt")
        with open(test_file, 'w', encoding='utf-8') as file:
            file.write(test_content)
        
        result = await async_read_file(str(test_file))
        
        assert result == test_content
        assert len(result) == 100000
    
    async def test_async_read_file_logging_on_error(self):
        """Test that async_read_file logs errors."""
        with patch('ai.utils.logger') as mock_logger:
            result = await async_read_file('/nonexistent/path.txt')
            
            assert mock_logger.error.called
            assert result is None


@pytest.mark.asyncio
class TestStringifyVdbResults(SimpleTestCase):
    """Tests for stringify_vdb_results function."""
    
    async def test_stringify_vdb_results_single_result(self):
        """Test stringifying a single vector database result."""
        vdb_results = [
            {
                "entity": {
                    "text": "In the beginning",
                    "book": "Genesis",
                    "chapter": "1",
                    "verse": "1",
                    "version": "KJV"
                }
            }
        ]
        
        result = await stringify_vdb_results(vdb_results)
        
        assert result == "In the beginning (Genesis 1:1 KJV)"
    
    async def test_stringify_vdb_results_multiple_results(self):
        """Test stringifying multiple vector database results."""
        vdb_results = [
            {
                "entity": {
                    "text": "In the beginning God created the heavens and the earth.",
                    "book": "Genesis",
                    "chapter": "1",
                    "verse": "1",
                    "version": "BSB"
                }
            },
            {
                "entity": {
                    "text": "The earth was formless and empty.",
                    "book": "Genesis",
                    "chapter": "1",
                    "verse": "2",
                    "version": "WEB"
                }
            }
        ]
        
        result = await stringify_vdb_results(vdb_results)
        
        assert "In the beginning God created the heavens and the earth. (Genesis 1:1 BSB)" in result
        assert "The earth was formless and empty. (Genesis 1:2 WEB)" in result
        assert result.count('\n') == 1  # Results separated by newline
    
    async def test_stringify_vdb_results_with_missing_fields(self):
        """Test stringifying results with missing optional fields."""
        vdb_results = [
            {
                "entity": {
                    "text": "Test verse",
                    "book": "",
                    "chapter": "",
                    "verse": "",
                    "version": ""
                }
            }
        ]
        
        result = await stringify_vdb_results(vdb_results)
        
        assert "Test verse ( : )" in result
    
    async def test_stringify_vdb_results_with_empty_entity(self):
        """Test stringifying results with empty entity."""
        vdb_results = [
            {
                "entity": {}
            }
        ]
        
        result = await stringify_vdb_results(vdb_results)
        
        # Should skip empty entities and return empty string or handle gracefully
        assert isinstance(result, str)
        assert result == ""
    
    async def test_stringify_vdb_results_invalid_type_returns_error_message(self):
        """Test that non-list results return error message."""
        vdb_results = "not a list"
        
        result = await stringify_vdb_results(vdb_results)
        
        assert result == "No results found"
    
    async def test_stringify_vdb_results_dict_returns_error_message(self):
        """Test that dict results return error message."""
        vdb_results = {"entity": {}}
        
        result = await stringify_vdb_results(vdb_results)
        
        assert result == "No results found"
    
    async def test_stringify_vdb_results_empty_list(self):
        """Test stringifying empty list of results."""
        vdb_results = []
        
        result = await stringify_vdb_results(vdb_results)
        
        assert result == ""
    
    async def test_stringify_vdb_results_with_special_characters(self):
        """Test stringifying results with special characters."""
        vdb_results = [
            {
                "entity": {
                    "text": "In the beginning, God created the heavens and the earth. The earth was formless and empty. (Genesis 1:1-2)",
                    "book": "Genesis",
                    "chapter": "1",
                    "verse": "1-2",
                    "version": "WEB"
                }
            }
        ]
        
        result = await stringify_vdb_results(vdb_results)
        
        assert "In the beginning, God created the heavens and the earth. The earth was formless and empty." in result
        assert "Genesis 1:1-2" in result
        assert result == "In the beginning, God created the heavens and the earth. The earth was formless and empty. (Genesis 1:1-2) (Genesis 1:1-2 WEB)"


@pytest.mark.asyncio
class TestCleanLLMOutput(SimpleTestCase):
    """Tests for clean_llm_output function."""
    
    async def test_clean_llm_output_basic_text(self):
        """Test cleaning basic text without markdown."""
        text = "This is plain text"
        
        result = await clean_llm_output(text)
        
        assert isinstance(result, str)
        assert "This is plain text" in result
    
    async def test_clean_llm_output_with_markdown_bold(self):
        """Test cleaning text with markdown bold formatting."""
        text = "This is **bold** text"
        
        result = await clean_llm_output(text)
        
        assert isinstance(result, str)
        assert "<strong>" in result or "bold" in result.lower()
    
    async def test_clean_llm_output_with_markdown_italic(self):
        """Test cleaning text with markdown italic formatting."""
        text = "This is *italic* text"
        
        result = await clean_llm_output(text)
        
        assert isinstance(result, str)
        assert "<em>" in result or "italic" in result.lower()
    
    async def test_clean_llm_output_removes_newlines(self):
        """Test that clean_llm_output removes newlines."""
        text = "Line 1\nLine 2\nLine 3"
        
        result = await clean_llm_output(text)
        
        assert '\n' not in result
    
    async def test_clean_llm_output_with_markdown_links(self):
        """Test cleaning text with markdown links."""
        text = "[Click here](https://example.com)"
        
        result = await clean_llm_output(text)
        
        assert isinstance(result, str)
        assert "href" in result or "example.com" in result
    
    async def test_clean_llm_output_with_markdown_headers(self):
        """Test cleaning text with markdown headers."""
        text = "# Header 1\n## Header 2\n### Header 3"
        
        result = await clean_llm_output(text)
        
        assert isinstance(result, str)
        assert "<h1>" in result or "Header 1" in result.lower()
        assert "<h2>" in result or "Header 2" in result.lower()
        assert "<h3>" in result or "Header 3" in result.lower()
        assert '\n' not in result
    
    async def test_clean_llm_output_with_markdown_lists(self):
        """Test cleaning text with markdown lists."""
        text = "- Item 1\n- Item 2\n- Item 3"
        
        result = await clean_llm_output(text)
        
        assert isinstance(result, str)
        assert "<ul>" in result or "Item 1" in result.lower()
        assert "<ul>" in result or "Item 2" in result.lower()
        assert "<ul>" in result or "Item 3" in result.lower()
        assert '\n' not in result
    
    async def test_clean_llm_output_with_code_blocks(self):
        """Test cleaning text with code blocks."""
        text = "```python\nprint('hello')\n```"
        
        result = await clean_llm_output(text)
        
        assert isinstance(result, str)
        assert "<pre>" in result or "print('hello')" in result.lower()
        assert '\n' not in result
    
    async def test_clean_llm_output_empty_string(self):
        """Test cleaning empty string."""
        text = ""
        
        result = await clean_llm_output(text)
        
        assert isinstance(result, str)
        assert result == ""
    
    async def test_clean_llm_output_with_special_characters(self):
        """Test cleaning text with special characters."""
        text = "Special chars: & < > \" '"
        
        result = await clean_llm_output(text)
        
        assert isinstance(result, str)
        assert "&" in result or "<" in result or ">" in result or '"' in result or "'" in result
    
    async def test_clean_llm_output_non_string_input(self):
        """Test cleaning non-string input (should be converted)."""
        text = 123
        
        result = await clean_llm_output(text)
        
        assert isinstance(result, str)
        assert "123" in result
    
    async def test_clean_llm_output_with_complex_markdown(self):
        """Test cleaning text with complex markdown."""
        text = "# Title\n\nThis is **bold** and *italic*.\n\n- Item 1\n- Item 2\n\n[Link](url)"
        
        result = await clean_llm_output(text)
        
        assert isinstance(result, str)
        assert "<h1>" in result or "title" in result.lower()
        assert "<strong>" in result or "bold" in result.lower()
        assert "<em>" in result or "italic" in result.lower()
        assert "<li>" in result or "item 1" in result.lower()
        assert "<li>" in result or "item 2" in result.lower()
        assert "<a" in result or "link" in result.lower()
        assert "url" in result.lower()
        assert '\n' not in result
