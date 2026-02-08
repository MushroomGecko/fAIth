import pytest
import os
from unittest.mock import patch, AsyncMock, MagicMock
from django.test import SimpleTestCase

from ai.llm.completions import Completions


@pytest.mark.asyncio
class TestCompletionsInit(SimpleTestCase):
    """Tests for Completions initialization."""
    
    def test_completions_init_with_env_variables(self):
        """Test that Completions initializes with environment variables."""
        with patch.dict(os.environ, {
            "LLM_MODEL_ID": "test-model",
            "LLM_URL": "http://test-url",
            "LLM_PORT": "11436",
            "OPENAI_API_KEY": "test-key"
        }):
            with patch('ai.llm.completions.AsyncOpenAI') as mock_client:
                completions = Completions()
                
                assert completions.model_name == "test-model"
                mock_client.assert_called_once()
    
    def test_completions_init_with_default_model(self):
        """Test that Completions uses default model when not specified."""
        with patch.dict(os.environ, {}, clear=True):
            with patch('ai.llm.completions.AsyncOpenAI'):
                completions = Completions()
                
                assert completions.model_name == "unsloth/Qwen3-4B-Instruct-2507-GGUF:Q4_K_M"
    
    def test_completions_init_with_default_arguments(self):
        """Test that Completions uses default arguments."""
        with patch.dict(os.environ, {"LLM_MODEL_ID": "test-model"}, clear=True):
            with patch('ai.llm.completions.AsyncOpenAI') as mock_client:
                Completions()
                
                # Verify AsyncOpenAI was called with correct arguments
                call_args = mock_client.call_args
                assert call_args.kwargs['base_url'] == "http://localhost:11436/v1"
                assert call_args.kwargs['api_key'] == "sk-noauth"
    
    def test_completions_init_without_model_raises_error(self):
        """Test that Completions raises error when model ID is not set."""
        with patch.dict(os.environ, {"LLM_MODEL_ID": ""}, clear=True):
            with patch('ai.llm.completions.logger') as mock_logger:
                with pytest.raises(ValueError):
                    Completions()
                
                mock_logger.error.assert_called()
    
    def test_completions_init_creates_async_client(self):
        """Test that Completions creates an AsyncOpenAI client."""
        with patch('ai.llm.completions.AsyncOpenAI') as mock_client_class:
            completions = Completions()
            
            assert mock_client_class.called
            assert hasattr(completions, 'client')


@pytest.mark.asyncio
class TestCompletionsMethod(SimpleTestCase):
    """Tests for Completions.completions() method."""
    
    async def test_completions_success(self):
        """Test that completions method successfully generates a response."""
        with patch.dict(os.environ, {"LLM_MODEL_ID": "test-model"}):
            with patch('ai.llm.completions.AsyncOpenAI') as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value = mock_client
                
                # Mock the response
                mock_response = MagicMock()
                mock_response.choices = [MagicMock()]
                mock_response.choices[0].message.content = "The Son of God!"
                mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
                
                completions = Completions()
                result = await completions.completions(
                    system_prompt="You are helpful",
                    user_prompt="Answer this: {query}",
                    query="Who is Jesus Christ?"
                )
                
                assert result == "The Son of God!"
    
    async def test_completions_message_formatting(self):
        """Test that completions correctly formats messages."""
        with patch.dict(os.environ, {"LLM_MODEL_ID": "test-model"}):
            with patch('ai.llm.completions.AsyncOpenAI') as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value = mock_client
                
                mock_response = MagicMock()
                mock_response.choices = [MagicMock()]
                mock_response.choices[0].message.content = "The Son of God!"
                mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
                
                completions = Completions()
                await completions.completions(
                    system_prompt="You are helpful",
                    user_prompt="Answer this: {query}",
                    query="Who is Jesus Christ?"
                )
                
                # Verify the messages were formatted correctly
                call_args = mock_client.chat.completions.create.call_args
                messages = call_args.kwargs['messages']
                
                assert len(messages) == 2
                assert messages[0]['role'] == 'system'
                assert messages[0]['content'] == "You are helpful"
                assert messages[1]['role'] == 'user'
                assert messages[1]['content'] == "Answer this: Who is Jesus Christ?"
    
    async def test_completions_uses_correct_model(self):
        """Test that completions uses the correct model."""
        with patch.dict(os.environ, {"LLM_MODEL_ID": "test-model"}):
            with patch('ai.llm.completions.AsyncOpenAI') as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value = mock_client
                
                mock_response = MagicMock()
                mock_response.choices = [MagicMock()]
                mock_response.choices[0].message.content = "The Son of God!"
                mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
                
                completions = Completions()
                await completions.completions(
                    system_prompt="System",
                    user_prompt="Answer this: {query}",
                    query="Who is Jesus Christ?"
                )
                
                # Verify correct model was used
                call_args = mock_client.chat.completions.create.call_args
                assert call_args.kwargs['model'] == "test-model"


@pytest.mark.asyncio
class TestCompletionsClose(SimpleTestCase):
    """Tests for Completions.close() method."""
    
    async def test_close_success(self):
        """Test that close successfully closes the client."""
        with patch.dict(os.environ, {"LLM_MODEL_ID": "test-model"}):
            with patch('ai.llm.completions.AsyncOpenAI') as mock_client_class:
                mock_client = AsyncMock()
                mock_client.close = AsyncMock()
                mock_client_class.return_value = mock_client
                
                completions = Completions()
                await completions.close()
                
                mock_client.close.assert_called_once()
    
    async def test_close_handles_error(self):
        """Test that close handles errors gracefully."""
        with patch.dict(os.environ, {"LLM_MODEL_ID": "test-model"}):
            with patch('ai.llm.completions.AsyncOpenAI') as mock_client_class:
                mock_client = AsyncMock()
                mock_client.close = AsyncMock(side_effect=Exception("Close failed"))
                mock_client_class.return_value = mock_client
                
                with patch('ai.llm.completions.logger') as mock_logger:
                    completions = Completions()
                    await completions.close()
                    
                    # Should not raise, but should log error
                    mock_logger.error.assert_called()
    
    async def test_close_logging(self):
        """Test that close logs when closing."""
        with patch.dict(os.environ, {"LLM_MODEL_ID": "test-model"}):
            with patch('ai.llm.completions.AsyncOpenAI') as mock_client_class:
                mock_client = AsyncMock()
                mock_client.close = AsyncMock()
                mock_client_class.return_value = mock_client
                
                with patch('ai.llm.completions.logger') as mock_logger:
                    completions = Completions()
                    await completions.close()
                    
                    # Verify logging was called
                    assert mock_logger.info.called


@pytest.mark.asyncio
class TestCompletionsIntegration(SimpleTestCase):
    """Integration tests for Completions."""
    
    async def test_completions_lifecycle(self):
        """Test the full lifecycle of Completions object."""
        with patch.dict(os.environ, {"LLM_MODEL_ID": "test-model"}):
            with patch('ai.llm.completions.AsyncOpenAI') as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value = mock_client
                
                # Mock response
                mock_response = MagicMock()
                mock_response.choices = [MagicMock()]
                mock_response.choices[0].message.content = "The Son of God!"
                mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
                mock_client.close = AsyncMock()
                
                # Initialize
                completions = Completions()
                
                # Use completions
                result = await completions.completions(
                    system_prompt="You are helpful",
                    user_prompt="Answer this: {query}",
                    query="Who is Jesus Christ?"
                )
                assert result == "The Son of God!"
                
                # Close
                await completions.close()
                mock_client.close.assert_called_once()
    
    async def test_multiple_completions_calls(self):
        """Test multiple consecutive completions calls."""
        with patch.dict(os.environ, {"LLM_MODEL_ID": "test-model"}):
            with patch('ai.llm.completions.AsyncOpenAI') as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value = mock_client
                
                # Create responses for multiple calls
                responses = [
                    MagicMock(choices=[MagicMock(message=MagicMock(content="Answer 1"))]),
                    MagicMock(choices=[MagicMock(message=MagicMock(content="Answer 2"))]),
                    MagicMock(choices=[MagicMock(message=MagicMock(content="Answer 3"))])
                ]
                mock_client.chat.completions.create = AsyncMock(side_effect=responses)
                
                completions = Completions()
                
                result1 = await completions.completions("sys", "user {query}", "q1")
                result2 = await completions.completions("sys", "user {query}", "q2")
                result3 = await completions.completions("sys", "user {query}", "q3")
                
                assert result1 == "Answer 1"
                assert result2 == "Answer 2"
                assert result3 == "Answer 3"
                assert mock_client.chat.completions.create.call_count == 3
