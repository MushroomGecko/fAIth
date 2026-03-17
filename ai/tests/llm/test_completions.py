import pytest
import os
from unittest.mock import patch, AsyncMock, MagicMock
from django.test import SimpleTestCase
import json
from ai.llm.completions import Completions


@pytest.mark.asyncio
class TestCompletionsInit(SimpleTestCase):
    """Tests for Completions initialization."""
    
    def test_completions_init_with_env_variables_local_mode(self):
        """Test that Completions initializes correctly in local mode (LLM_PORT set)."""
        with patch.dict(os.environ, {
            "LLM_MODEL_ID": "test-model",
            "BASE_LLM_URL": "http://llm:11436/v1",
            "LLM_API_KEY": "test-key"
        }, clear=True):
            with patch('ai.llm.completions.AsyncOpenAI') as mock_client:
                completions = Completions()

                assert completions.model_name == "test-model"
                call_args = mock_client.call_args
                assert call_args.kwargs['base_url'] == "http://llm:11436/v1"
                assert call_args.kwargs['api_key'] == "test-key"

    def test_completions_init_with_env_variables_api_mode(self):
        """Test that Completions initializes correctly in API mode (BASE_LLM_URL set)."""
        with patch.dict(os.environ, {
            "LLM_MODEL_ID": "test-model",
            "BASE_LLM_URL": "https://openrouter.ai/api/v1",
            "LLM_API_KEY": "sk-or-key"
        }, clear=True):
            with patch('ai.llm.completions.AsyncOpenAI') as mock_client:
                completions = Completions()

                assert completions.model_name == "test-model"
                call_args = mock_client.call_args
                assert call_args.kwargs['base_url'] == "https://openrouter.ai/api/v1"
                assert call_args.kwargs['api_key'] == "sk-or-key"
    
    def test_completions_init_with_default_model_local_mode(self):
        """Test that Completions uses default model when not specified in local mode."""
        with patch.dict(os.environ, {"BASE_LLM_URL": "http://llm:11436/v1"}, clear=True):
            with patch('ai.llm.completions.AsyncOpenAI'):
                completions = Completions()

                assert completions.model_name == "unsloth/Qwen3.5-4B-GGUF:Q4_K_M"

    def test_completions_init_with_default_model_api_mode(self):
        """Test that Completions uses default model when not specified in API mode."""
        with patch.dict(os.environ, {"BASE_LLM_URL": "https://openrouter.ai/api/v1"}, clear=True):
            with patch('ai.llm.completions.AsyncOpenAI'):
                completions = Completions()

                assert completions.model_name == "unsloth/Qwen3.5-4B-GGUF:Q4_K_M"

    def test_completions_init_with_url_local_mode(self):
        """Test that Completions constructs correct URL in local mode (LLM_PORT set)."""
        with patch.dict(os.environ, {"LLM_MODEL_ID": "test-model", "BASE_LLM_URL": "http://llm:11436/v1"}, clear=True):
            with patch('ai.llm.completions.AsyncOpenAI') as mock_client:
                Completions()

                call_args = mock_client.call_args
                assert call_args.kwargs['base_url'] == "http://llm:11436/v1"
                assert call_args.kwargs['api_key'] == ""

    def test_completions_init_with_url_api_mode(self):
        """Test that Completions uses BASE_LLM_URL when LLM_PORT is not set (API mode)."""
        with patch.dict(os.environ, {
            "LLM_MODEL_ID": "test-model",
            "BASE_LLM_URL": "https://openrouter.ai/api/v1",
            "LLM_API_KEY": "sk-or-key"
        }, clear=True):
            with patch('ai.llm.completions.AsyncOpenAI') as mock_client:
                Completions()

                call_args = mock_client.call_args
                assert call_args.kwargs['base_url'] == "https://openrouter.ai/api/v1"
                assert call_args.kwargs['api_key'] == "sk-or-key"
    
    def test_completions_init_without_model_raises_error(self):
        """Test that Completions raises error when model ID is not set."""
        with patch.dict(os.environ, {"LLM_MODEL_ID": ""}, clear=True):
            with patch('ai.llm.completions.logger') as mock_logger:
                with pytest.raises(ValueError):
                    Completions()
                
                mock_logger.error.assert_called()

    def test_completions_init_without_url_raises_error(self):
        """Test that Completions raises error when neither LLM_PORT nor BASE_LLM_URL is set."""
        with patch.dict(os.environ, {"LLM_MODEL_ID": "test-model"}, clear=True):
            with patch('ai.llm.completions.logger') as mock_logger:
                with pytest.raises(ValueError, match="Base LLM URL is not set"):
                    Completions()

                mock_logger.error.assert_called_with("Base LLM URL is not set")

    def test_completions_init_creates_async_client_local_mode(self):
        """Test that Completions creates an AsyncOpenAI client in local mode."""
        with patch.dict(os.environ, {"LLM_MODEL_ID": "test-model", "BASE_LLM_URL": "http://llm:11436/v1"}, clear=True):
            with patch('ai.llm.completions.AsyncOpenAI') as mock_client_class:
                completions = Completions()

                assert mock_client_class.called
                assert hasattr(completions, 'client')

    def test_completions_init_creates_async_client_api_mode(self):
        """Test that Completions creates an AsyncOpenAI client in API mode."""
        with patch.dict(os.environ, {
            "LLM_MODEL_ID": "test-model",
            "BASE_LLM_URL": "https://openrouter.ai/api/v1",
        }, clear=True):
            with patch('ai.llm.completions.AsyncOpenAI') as mock_client_class:
                completions = Completions()

                assert mock_client_class.called
                assert hasattr(completions, 'client')


@pytest.mark.asyncio
class TestCompletionsMethod(SimpleTestCase):
    """Tests for Completions.completions() method."""

    async def test_completions_success_local_mode(self):
        """Test that completions method successfully generates a response in local mode."""
        with patch.dict(os.environ, {"LLM_MODEL_ID": "test-model", "BASE_LLM_URL": "http://llm:11436/v1"}, clear=True):
            with patch('ai.llm.completions.AsyncOpenAI') as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value = mock_client

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

    async def test_completions_success_api_mode(self):
        """Test that completions method successfully generates a response in API mode."""
        with patch.dict(os.environ, {
            "LLM_MODEL_ID": "test-model",
            "BASE_LLM_URL": "https://openrouter.ai/api/v1",
            "LLM_API_KEY": "sk-or-key"
        }, clear=True):
            with patch('ai.llm.completions.AsyncOpenAI') as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value = mock_client

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

    async def test_completions_message_formatting_local_mode(self):
        """Test that completions correctly formats messages in local mode."""
        with patch.dict(os.environ, {"LLM_MODEL_ID": "test-model", "BASE_LLM_URL": "http://llm:11436/v1"}, clear=True):
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

    async def test_completions_message_formatting_api_mode(self):
        """Test that completions correctly formats messages in API mode."""
        with patch.dict(os.environ, {
            "LLM_MODEL_ID": "test-model",
            "BASE_LLM_URL": "https://openrouter.ai/api/v1",
            "LLM_API_KEY": "sk-or-key"
        }, clear=True):
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

    async def test_completions_uses_correct_model_local_mode(self):
        """Test that completions uses the correct model in local mode."""
        with patch.dict(os.environ, {"LLM_MODEL_ID": "test-model", "BASE_LLM_URL": "http://llm:11436/v1"}, clear=True):
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

    async def test_completions_uses_correct_model_api_mode(self):
        """Test that completions uses the correct model in API mode."""
        with patch.dict(os.environ, {
            "LLM_MODEL_ID": "test-model",
            "BASE_LLM_URL": "https://openrouter.ai/api/v1",
            "LLM_API_KEY": "sk-or-key"
        }, clear=True):
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

    async def test_completions_with_blank_extra_body_local_mode(self):
        """Test that completions handles blank extra_body (empty dict) correctly in local mode."""
        with patch.dict(os.environ, {
            "LLM_MODEL_ID": "test-model",
            "BASE_LLM_URL": "http://llm:11436/v1",
            "LLM_MODEL_ARGUMENTS": "{}"
        }, clear=True):
            with patch('ai.llm.completions.AsyncOpenAI') as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value = mock_client

                mock_response = MagicMock()
                mock_response.choices = [MagicMock()]
                mock_response.choices[0].message.content = "Response"
                mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

                completions = Completions()
                result = await completions.completions(
                    system_prompt="System",
                    user_prompt="Prompt: {query}",
                    query="test"
                )

                # Verify extra_body is passed as empty dict when no arguments are set
                call_args = mock_client.chat.completions.create.call_args
                assert 'extra_body' in call_args.kwargs
                assert call_args.kwargs['extra_body'] == {}
                assert result == "Response"

    async def test_completions_with_blank_extra_body_api_mode(self):
        """Test that completions handles blank extra_body (empty dict) correctly in API mode."""
        with patch.dict(os.environ, {
            "LLM_MODEL_ID": "test-model",
            "BASE_LLM_URL": "https://openrouter.ai/api/v1",
            "LLM_API_KEY": "sk-or-key",
            "LLM_MODEL_ARGUMENTS": "{}"
        }, clear=True):
            with patch('ai.llm.completions.AsyncOpenAI') as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value = mock_client

                mock_response = MagicMock()
                mock_response.choices = [MagicMock()]
                mock_response.choices[0].message.content = "Response"
                mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

                completions = Completions()
                result = await completions.completions(
                    system_prompt="System",
                    user_prompt="Prompt: {query}",
                    query="test"
                )

                # Verify extra_body is passed as empty dict when no arguments are set
                call_args = mock_client.chat.completions.create.call_args
                assert 'extra_body' in call_args.kwargs
                assert call_args.kwargs['extra_body'] == {}
                assert result == "Response"

    async def test_completions_with_filled_extra_body_local_mode(self):
        """Test that completions correctly passes filled extra_body with model arguments in local mode."""
        model_args = {"chat_template_kwargs": {"temperature": 0.7, "max_tokens": 512}}
        with patch.dict(os.environ, {
            "LLM_MODEL_ID": "test-model",
            "BASE_LLM_URL": "http://llm:11436/v1",
            "LLM_MODEL_ARGUMENTS": json.dumps(model_args)
        }, clear=True):
            with patch('ai.llm.completions.AsyncOpenAI') as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value = mock_client

                mock_response = MagicMock()
                mock_response.choices = [MagicMock()]
                mock_response.choices[0].message.content = "Response with args"
                mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

                completions = Completions()
                result = await completions.completions(
                    system_prompt="System",
                    user_prompt="Prompt: {query}",
                    query="test"
                )

                # Verify extra_body is passed with model arguments
                call_args = mock_client.chat.completions.create.call_args
                assert 'extra_body' in call_args.kwargs
                assert call_args.kwargs['extra_body'] == model_args
                assert result == "Response with args"

    async def test_completions_with_filled_extra_body_api_mode(self):
        """Test that completions correctly passes filled extra_body with model arguments in API mode."""
        model_args = {"chat_template_kwargs": {"temperature": 0.7, "max_tokens": 512}}
        with patch.dict(os.environ, {
            "LLM_MODEL_ID": "test-model",
            "BASE_LLM_URL": "https://openrouter.ai/api/v1",
            "LLM_API_KEY": "sk-or-key",
            "LLM_MODEL_ARGUMENTS": json.dumps(model_args)
        }, clear=True):
            with patch('ai.llm.completions.AsyncOpenAI') as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value = mock_client

                mock_response = MagicMock()
                mock_response.choices = [MagicMock()]
                mock_response.choices[0].message.content = "Response with args"
                mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

                completions = Completions()
                result = await completions.completions(
                    system_prompt="System",
                    user_prompt="Prompt: {query}",
                    query="test"
                )

                # Verify extra_body is passed with model arguments
                call_args = mock_client.chat.completions.create.call_args
                assert 'extra_body' in call_args.kwargs
                assert call_args.kwargs['extra_body'] == model_args
                assert result == "Response with args"


@pytest.mark.asyncio
class TestCompletionsClose(SimpleTestCase):
    """Tests for Completions.close() method."""

    async def test_close_success_local_mode(self):
        """Test that close successfully closes the client in local mode."""
        with patch.dict(os.environ, {"LLM_MODEL_ID": "test-model", "BASE_LLM_URL": "http://llm:11436/v1"}, clear=True):
            with patch('ai.llm.completions.AsyncOpenAI') as mock_client_class:
                mock_client = AsyncMock()
                mock_client.close = AsyncMock()
                mock_client_class.return_value = mock_client

                completions = Completions()
                await completions.close()

                mock_client.close.assert_called_once()

    async def test_close_success_api_mode(self):
        """Test that close successfully closes the client in API mode."""
        with patch.dict(os.environ, {
            "LLM_MODEL_ID": "test-model",
            "BASE_LLM_URL": "https://openrouter.ai/api/v1",
            "LLM_API_KEY": "sk-or-key"
        }, clear=True):
            with patch('ai.llm.completions.AsyncOpenAI') as mock_client_class:
                mock_client = AsyncMock()
                mock_client.close = AsyncMock()
                mock_client_class.return_value = mock_client

                completions = Completions()
                await completions.close()

                mock_client.close.assert_called_once()

    async def test_close_handles_error_local_mode(self):
        """Test that close handles errors gracefully in local mode."""
        with patch.dict(os.environ, {"LLM_MODEL_ID": "test-model", "BASE_LLM_URL": "http://llm:11436/v1"}, clear=True):
            with patch('ai.llm.completions.AsyncOpenAI') as mock_client_class:
                mock_client = AsyncMock()
                mock_client.close = AsyncMock(side_effect=Exception("Close failed"))
                mock_client_class.return_value = mock_client

                with patch('ai.llm.completions.logger') as mock_logger:
                    completions = Completions()
                    await completions.close()

                    # Should not raise, but should log error
                    mock_logger.error.assert_called()

    async def test_close_handles_error_api_mode(self):
        """Test that close handles errors gracefully in API mode."""
        with patch.dict(os.environ, {
            "LLM_MODEL_ID": "test-model",
            "BASE_LLM_URL": "https://openrouter.ai/api/v1",
            "LLM_API_KEY": "sk-or-key"
        }, clear=True):
            with patch('ai.llm.completions.AsyncOpenAI') as mock_client_class:
                mock_client = AsyncMock()
                mock_client.close = AsyncMock(side_effect=Exception("Close failed"))
                mock_client_class.return_value = mock_client

                with patch('ai.llm.completions.logger') as mock_logger:
                    completions = Completions()
                    await completions.close()

                    # Should not raise, but should log error
                    mock_logger.error.assert_called()

    async def test_close_logging_local_mode(self):
        """Test that close logs when closing in local mode."""
        with patch.dict(os.environ, {"LLM_MODEL_ID": "test-model", "BASE_LLM_URL": "http://llm:11436/v1"}, clear=True):
            with patch('ai.llm.completions.AsyncOpenAI') as mock_client_class:
                mock_client = AsyncMock()
                mock_client.close = AsyncMock()
                mock_client_class.return_value = mock_client

                with patch('ai.llm.completions.logger') as mock_logger:
                    completions = Completions()
                    await completions.close()

                    # Verify logging was called
                    assert mock_logger.info.called

    async def test_close_logging_api_mode(self):
        """Test that close logs when closing in API mode."""
        with patch.dict(os.environ, {
            "LLM_MODEL_ID": "test-model",
            "BASE_LLM_URL": "https://openrouter.ai/api/v1",
            "LLM_API_KEY": "sk-or-key"
        }, clear=True):
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

    async def test_completions_lifecycle_local_mode(self):
        """Test the full lifecycle of Completions object in local mode."""
        with patch.dict(os.environ, {"LLM_MODEL_ID": "test-model", "BASE_LLM_URL": "http://llm:11436/v1"}, clear=True):
            with patch('ai.llm.completions.AsyncOpenAI') as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value = mock_client

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

    async def test_completions_lifecycle_api_mode(self):
        """Test the full lifecycle of Completions object in API mode."""
        with patch.dict(os.environ, {
            "LLM_MODEL_ID": "test-model",
            "BASE_LLM_URL": "https://openrouter.ai/api/v1",
            "LLM_API_KEY": "sk-or-key"
        }, clear=True):
            with patch('ai.llm.completions.AsyncOpenAI') as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value = mock_client

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

    async def test_multiple_completions_calls_local_mode(self):
        """Test multiple consecutive completions calls in local mode."""
        with patch.dict(os.environ, {"LLM_MODEL_ID": "test-model", "BASE_LLM_URL": "http://llm:11436/v1"}, clear=True):
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

    async def test_multiple_completions_calls_api_mode(self):
        """Test multiple consecutive completions calls in API mode."""
        with patch.dict(os.environ, {
            "LLM_MODEL_ID": "test-model",
            "BASE_LLM_URL": "https://openrouter.ai/api/v1",
            "LLM_API_KEY": "sk-or-key"
        }, clear=True):
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
