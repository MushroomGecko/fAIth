import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from django.test import SimpleTestCase
from ai.vdb.embedding import Embedding


def create_mock_getenv(**env_vars):
    """Create a mock getenv function with predefined environment variables."""
    def mock_getenv(key, default=None):
        return env_vars.get(key, default)
    return mock_getenv


class TestEmbeddingInit(SimpleTestCase):
    """Tests for Embedding initialization."""

    def test_embedding_init_with_env_variables(self):
        """Test that Embedding initializes with environment variables."""
        env_vars = {
            "EMBEDDING_MODEL_ID": "custom-model",
            "EMBEDDING_URL": "http://example.com",
            "EMBEDDING_PORT": "11435",
            "OPENAI_API_KEY": "sk-test",
            "EMBEDDING_MODEL_QUERY_PROMPT": "Query: {text}",
            "EMBEDDING_MODEL_DOCUMENT_PROMPT": "Document: {text}",
        }
        with patch("ai.vdb.embedding.os.getenv") as mock_getenv:
            mock_getenv.side_effect = create_mock_getenv(**env_vars)
            with patch("ai.vdb.embedding.OpenAI"):
                with patch("ai.vdb.embedding.AsyncOpenAI"):
                    embedding = Embedding()
                    assert embedding.model_name == "custom-model"
                    assert embedding.query_template == "Query: {text}"
                    assert embedding.document_template == "Document: {text}"

    def test_embedding_init_with_default_values(self):
        """Test that Embedding initializes with default values when env vars not set."""
        env_vars = {
            "EMBEDDING_MODEL_ID": "Qwen/Qwen3-Embedding-0.6B",
            "EMBEDDING_URL": "http://localhost",
            "EMBEDDING_PORT": "11435",
            "OPENAI_API_KEY": "sk-noauth",
            "EMBEDDING_MODEL_QUERY_PROMPT": "",
            "EMBEDDING_MODEL_DOCUMENT_PROMPT": "",
        }
        with patch("ai.vdb.embedding.os.getenv") as mock_getenv:
            mock_getenv.side_effect = create_mock_getenv(**env_vars)
            with patch("ai.vdb.embedding.OpenAI"):
                with patch("ai.vdb.embedding.AsyncOpenAI"):
                    embedding = Embedding()
                    assert embedding.model_name == "Qwen/Qwen3-Embedding-0.6B"
                    assert embedding.query_template == ""
                    assert embedding.document_template == ""

    def test_embedding_init_creates_sync_client(self):
        """Test that Embedding creates a synchronous OpenAI client."""
        env_vars = {
            "EMBEDDING_MODEL_ID": "test-model",
            "EMBEDDING_URL": "http://localhost",
            "EMBEDDING_PORT": "11435",
            "OPENAI_API_KEY": "sk-test",
        }
        with patch("ai.vdb.embedding.os.getenv") as mock_getenv:
            mock_getenv.side_effect = create_mock_getenv(**env_vars)
            with patch("ai.vdb.embedding.OpenAI") as mock_openai:
                with patch("ai.vdb.embedding.AsyncOpenAI"):
                    embedding = Embedding()
                    mock_openai.assert_called_once_with(
                        base_url="http://localhost:11435/v1",
                        api_key="sk-test"
                    )
                    assert embedding.client is not None

    def test_embedding_init_creates_async_client(self):
        """Test that Embedding creates an asynchronous OpenAI client."""
        env_vars = {
            "EMBEDDING_MODEL_ID": "test-model",
            "EMBEDDING_URL": "http://localhost",
            "EMBEDDING_PORT": "11435",
            "OPENAI_API_KEY": "sk-test",
        }
        with patch("ai.vdb.embedding.os.getenv") as mock_getenv:
            mock_getenv.side_effect = create_mock_getenv(**env_vars)
            with patch("ai.vdb.embedding.OpenAI"):
                with patch("ai.vdb.embedding.AsyncOpenAI") as mock_async_openai:
                    embedding = Embedding()
                    mock_async_openai.assert_called_once_with(
                        base_url="http://localhost:11435/v1",
                        api_key="sk-test"
                    )
                    assert embedding.async_client is not None

    def test_embedding_init_without_model_raises_error(self):
        """Test that Embedding raises error when model ID is not set."""
        env_vars = {
            "EMBEDDING_MODEL_ID": "",
            "EMBEDDING_URL": "http://localhost",
            "EMBEDDING_PORT": "11435",
            "OPENAI_API_KEY": "sk-test",
        }
        with patch("ai.vdb.embedding.os.getenv") as mock_getenv:
            mock_getenv.side_effect = create_mock_getenv(**env_vars)
            with patch("ai.vdb.embedding.logger") as mock_logger:
                with patch("ai.vdb.embedding.OpenAI"):
                    with patch("ai.vdb.embedding.AsyncOpenAI"):
                        with pytest.raises(ValueError, match="Embedding model ID is not set"):
                            Embedding()
                        mock_logger.error.assert_called_once_with(
                            "Embedding model ID is not set"
                        )

class TestEmbeddingSize(SimpleTestCase):
    """Tests for the embedding_size method."""

    def test_embedding_size_success(self):
        """Test that embedding_size returns correct embedding dimensions."""
        with patch("ai.vdb.embedding.os.getenv") as mock_getenv:
            mock_getenv.side_effect = create_mock_getenv(EMBEDDING_MODEL_ID="test-model")

            with patch("ai.vdb.embedding.OpenAI") as mock_openai_class:
                with patch("ai.vdb.embedding.AsyncOpenAI"):
                    mock_client = MagicMock()
                    mock_openai_class.return_value = mock_client

                    # Mock the embedding response
                    embedding_size = 768
                    mock_embedding_data = MagicMock()
                    mock_embedding_data.embedding = [0.1] * embedding_size  # 768-dimensional embedding
                    mock_response = MagicMock()
                    mock_response.data = [mock_embedding_data]
                    mock_client.embeddings.create.return_value = mock_response

                    embedding = Embedding()
                    size = embedding.embedding_size()

                    assert size == embedding_size
                    mock_client.embeddings.create.assert_called_once_with(
                        model="test-model",
                        input=["Hello, world!"]
                    )

    def test_embedding_size_different_dimensions(self):
        """Test embedding_size with different embedding dimensions."""
        with patch("ai.vdb.embedding.os.getenv") as mock_getenv:
            mock_getenv.side_effect = create_mock_getenv(EMBEDDING_MODEL_ID="test-model")

            with patch("ai.vdb.embedding.OpenAI") as mock_openai_class:
                with patch("ai.vdb.embedding.AsyncOpenAI"):
                    mock_client = MagicMock()
                    mock_openai_class.return_value = mock_client

                    # Mock a 1024-dimensional embedding
                    embedding_size = 1024
                    mock_embedding_data = MagicMock()
                    mock_embedding_data.embedding = [0.5] * embedding_size
                    mock_response = MagicMock()
                    mock_response.data = [mock_embedding_data]
                    mock_client.embeddings.create.return_value = mock_response

                    embedding = Embedding()
                    size = embedding.embedding_size()

                    assert size == embedding_size
                    mock_client.embeddings.create.assert_called_once_with(
                        model="test-model",
                        input=["Hello, world!"]
                    )


class TestEmbedMethod(SimpleTestCase):
    """Tests for the embed method."""

    def test_embed_document_type_without_normalization(self):
        """Test embedding documents without normalization."""
        with patch("ai.vdb.embedding.os.getenv") as mock_getenv:
            mock_getenv.side_effect = create_mock_getenv(
                EMBEDDING_MODEL_ID="test-model",
                EMBEDDING_MODEL_DOCUMENT_PROMPT=""
            )

            with patch("ai.vdb.embedding.OpenAI") as mock_openai_class:
                with patch("ai.vdb.embedding.AsyncOpenAI"):
                    mock_client = MagicMock()
                    mock_openai_class.return_value = mock_client

                    # Mock embeddings
                    mock_embeddings = [
                        MagicMock(embedding=[0.1, 0.2, 0.3]),
                        MagicMock(embedding=[0.4, 0.5, 0.6]),
                    ]
                    mock_response = MagicMock()
                    mock_response.data = mock_embeddings
                    mock_client.embeddings.create.return_value = mock_response

                    embedding = Embedding()
                    result = embedding.embed(
                        ["text1", "text2"],
                        prompt_type="document",
                        normalize=False
                    )

                    assert len(result) == 2
                    assert result[0] == [0.1, 0.2, 0.3]
                    assert result[1] == [0.4, 0.5, 0.6]
                    mock_client.embeddings.create.assert_called_once_with(
                        model="test-model",
                        input=["text1", "text2"]
                    )

    def test_embed_query_type_without_normalization(self):
        """Test embedding queries without normalization."""
        with patch("ai.vdb.embedding.os.getenv") as mock_getenv:
            mock_getenv.side_effect = create_mock_getenv(
                EMBEDDING_MODEL_ID="test-model",
                EMBEDDING_MODEL_QUERY_PROMPT=""
            )

            with patch("ai.vdb.embedding.OpenAI") as mock_openai_class:
                with patch("ai.vdb.embedding.AsyncOpenAI"):
                    mock_client = MagicMock()
                    mock_openai_class.return_value = mock_client

                    mock_embeddings = [MagicMock(embedding=[0.7, 0.8, 0.9])]
                    mock_response = MagicMock()
                    mock_response.data = mock_embeddings
                    mock_client.embeddings.create.return_value = mock_response

                    embedding = Embedding()
                    result = embedding.embed(
                        ["query_text"],
                        prompt_type="query",
                        normalize=False
                    )

                    assert len(result) == 1
                    assert result[0] == [0.7, 0.8, 0.9]

    def test_embed_with_normalization(self):
        """Test that embeddings are normalized correctly."""
        with patch("ai.vdb.embedding.os.getenv") as mock_getenv:
            mock_getenv.side_effect = create_mock_getenv(
                EMBEDDING_MODEL_ID="test-model",
                EMBEDDING_MODEL_DOCUMENT_PROMPT=""
            )

            with patch("ai.vdb.embedding.OpenAI") as mock_openai_class:
                with patch("ai.vdb.embedding.AsyncOpenAI"):
                    mock_client = MagicMock()
                    mock_openai_class.return_value = mock_client

                    # Create an embedding that needs normalization
                    mock_embeddings = [
                        MagicMock(embedding=[3.0, 4.0])  # magnitude = 5.0
                    ]
                    mock_response = MagicMock()
                    mock_response.data = mock_embeddings
                    mock_client.embeddings.create.return_value = mock_response

                    embedding = Embedding()
                    result = embedding.embed(
                        ["text"],
                        prompt_type="document",
                        normalize=True
                    )

                    # After normalization: [3/5, 4/5] = [0.6, 0.8]
                    assert len(result) == 1
                    normalized_embedding = result[0]
                    assert abs(normalized_embedding[0] - 0.6) < 1e-6
                    assert abs(normalized_embedding[1] - 0.8) < 1e-6

    def test_embed_with_document_template(self):
        """Test that document template is applied."""
        with patch("ai.vdb.embedding.os.getenv") as mock_getenv:
            mock_getenv.side_effect = create_mock_getenv(
                EMBEDDING_MODEL_ID="test-model",
                EMBEDDING_MODEL_DOCUMENT_PROMPT="Document: {text}"
            )

            with patch("ai.vdb.embedding.OpenAI") as mock_openai_class:
                with patch("ai.vdb.embedding.AsyncOpenAI"):
                    mock_client = MagicMock()
                    mock_openai_class.return_value = mock_client

                    mock_embeddings = [MagicMock(embedding=[0.1, 0.2])]
                    mock_response = MagicMock()
                    mock_response.data = mock_embeddings
                    mock_client.embeddings.create.return_value = mock_response

                    embedding = Embedding()
                    embedding.embed(
                        ["sample text"],
                        prompt_type="document",
                        normalize=False
                    )

                    # Verify that the template was applied
                    mock_client.embeddings.create.assert_called_once_with(
                        model="test-model",
                        input=["Document: sample text"]
                    )

    def test_embed_with_query_template(self):
        """Test that query template is applied."""
        with patch("ai.vdb.embedding.os.getenv") as mock_getenv:
            mock_getenv.side_effect = create_mock_getenv(
                EMBEDDING_MODEL_ID="test-model",
                EMBEDDING_MODEL_QUERY_PROMPT="Search: {text}"
            )

            with patch("ai.vdb.embedding.OpenAI") as mock_openai_class:
                with patch("ai.vdb.embedding.AsyncOpenAI"):
                    mock_client = MagicMock()
                    mock_openai_class.return_value = mock_client

                    mock_embeddings = [MagicMock(embedding=[0.5, 0.6])]
                    mock_response = MagicMock()
                    mock_response.data = mock_embeddings
                    mock_client.embeddings.create.return_value = mock_response

                    embedding = Embedding()
                    embedding.embed(
                        ["search query"],
                        prompt_type="query",
                        normalize=False
                    )

                    # Verify that the template was applied
                    mock_client.embeddings.create.assert_called_once_with(
                        model="test-model",
                        input=["Search: search query"]
                    )


    def test_embed_invalid_prompt_type(self):
        """Test that invalid prompt type raises error."""
        with patch("ai.vdb.embedding.os.getenv") as mock_getenv:
            mock_getenv.side_effect = create_mock_getenv(EMBEDDING_MODEL_ID="test-model")

            with patch("ai.vdb.embedding.OpenAI") as mock_openai_class:
                with patch("ai.vdb.embedding.AsyncOpenAI"):
                    mock_client = MagicMock()
                    mock_openai_class.return_value = mock_client

                    embedding = Embedding()
                    with pytest.raises(ValueError, match="Unknown prompt type: invalid"):
                        embedding.embed(["text"], prompt_type="invalid")


class TestAsyncEmbedMethod(SimpleTestCase):
    """Tests for the async_embed method."""

    @pytest.mark.asyncio
    async def test_async_embed_document_type_without_normalization(self):
        """Test asynchronously embedding documents without normalization."""
        with patch("ai.vdb.embedding.os.getenv") as mock_getenv:
            mock_getenv.side_effect = create_mock_getenv(
                EMBEDDING_MODEL_ID="test-model",
                EMBEDDING_MODEL_DOCUMENT_PROMPT=""
            )

            with patch("ai.vdb.embedding.OpenAI"):
                with patch("ai.vdb.embedding.AsyncOpenAI") as mock_async_openai_class:
                    mock_async_client = AsyncMock()
                    mock_async_openai_class.return_value = mock_async_client

                    # Mock async embeddings response
                    mock_embeddings = [
                        MagicMock(embedding=[0.1, 0.2, 0.3]),
                        MagicMock(embedding=[0.4, 0.5, 0.6]),
                    ]
                    mock_response = MagicMock()
                    mock_response.data = mock_embeddings
                    mock_async_client.embeddings.create.return_value = mock_response

                    embedding = Embedding()
                    result = await embedding.async_embed(
                        ["text1", "text2"],
                        prompt_type="document",
                        normalize=False
                    )

                    assert len(result) == 2
                    assert result[0] == [0.1, 0.2, 0.3]
                    assert result[1] == [0.4, 0.5, 0.6]

    @pytest.mark.asyncio
    async def test_async_embed_query_type_without_normalization(self):
        """Test asynchronously embedding queries without normalization."""
        with patch("ai.vdb.embedding.os.getenv") as mock_getenv:
            mock_getenv.side_effect = create_mock_getenv(
                EMBEDDING_MODEL_ID="test-model",
                EMBEDDING_MODEL_QUERY_PROMPT=""
            )

            with patch("ai.vdb.embedding.OpenAI"):
                with patch("ai.vdb.embedding.AsyncOpenAI") as mock_async_openai_class:
                    mock_async_client = AsyncMock()
                    mock_async_openai_class.return_value = mock_async_client

                    mock_embeddings = [MagicMock(embedding=[0.7, 0.8, 0.9])]
                    mock_response = MagicMock()
                    mock_response.data = mock_embeddings
                    mock_async_client.embeddings.create.return_value = mock_response

                    embedding = Embedding()
                    result = await embedding.async_embed(
                        ["query_text"],
                        prompt_type="query",
                        normalize=False
                    )

                    assert len(result) == 1
                    assert result[0] == [0.7, 0.8, 0.9]

    @pytest.mark.asyncio
    async def test_async_embed_with_template_formatting(self):
        """Test that template is applied in async embedding."""
        with patch("ai.vdb.embedding.os.getenv") as mock_getenv:
            mock_getenv.side_effect = create_mock_getenv(
                EMBEDDING_MODEL_ID="test-model",
                EMBEDDING_MODEL_DOCUMENT_PROMPT="Doc: {text}"
            )

            with patch("ai.vdb.embedding.OpenAI"):
                with patch("ai.vdb.embedding.AsyncOpenAI") as mock_async_openai_class:
                    mock_async_client = AsyncMock()
                    mock_async_openai_class.return_value = mock_async_client

                    mock_embeddings = [MagicMock(embedding=[0.1, 0.2])]
                    mock_response = MagicMock()
                    mock_response.data = mock_embeddings
                    mock_async_client.embeddings.create.return_value = mock_response

                    embedding = Embedding()
                    await embedding.async_embed(
                        ["sample"],
                        prompt_type="document",
                        normalize=False
                    )

                    # Verify template was applied
                    mock_async_client.embeddings.create.assert_called_once_with(
                        model="test-model",
                        input=["Doc: sample"]
                    )

    @pytest.mark.asyncio
    async def test_async_embed_with_normalization(self):
        """Test that embeddings are normalized in async method."""
        with patch("ai.vdb.embedding.os.getenv") as mock_getenv:
            mock_getenv.side_effect = create_mock_getenv(
                EMBEDDING_MODEL_ID="test-model",
                EMBEDDING_MODEL_DOCUMENT_PROMPT=""
            )

            with patch("ai.vdb.embedding.OpenAI"):
                with patch("ai.vdb.embedding.AsyncOpenAI") as mock_async_openai_class:
                    mock_async_client = AsyncMock()
                    mock_async_openai_class.return_value = mock_async_client

                    # Create an embedding with magnitude 5.0
                    mock_embeddings = [
                        MagicMock(embedding=[3.0, 4.0])
                    ]
                    mock_response = MagicMock()
                    mock_response.data = mock_embeddings
                    mock_async_client.embeddings.create.return_value = mock_response

                    embedding = Embedding()
                    result = await embedding.async_embed(
                        ["text"],
                        prompt_type="document",
                        normalize=True
                    )

                    # After normalization: [0.6, 0.8]
                    assert len(result) == 1
                    normalized_embedding = result[0]
                    assert abs(normalized_embedding[0] - 0.6) < 1e-6
                    assert abs(normalized_embedding[1] - 0.8) < 1e-6

    @pytest.mark.asyncio
    async def test_async_embed_invalid_prompt_type(self):
        """Test that invalid prompt type raises error in async method."""
        with patch("ai.vdb.embedding.os.getenv") as mock_getenv:
            mock_getenv.side_effect = create_mock_getenv(EMBEDDING_MODEL_ID="test-model")

            with patch("ai.vdb.embedding.OpenAI"):
                with patch("ai.vdb.embedding.AsyncOpenAI") as mock_async_openai_class:
                    mock_async_client = AsyncMock()
                    mock_async_openai_class.return_value = mock_async_client

                    embedding = Embedding()
                    with pytest.raises(ValueError, match="Unknown prompt type: async_invalid"):
                        await embedding.async_embed(["text"], prompt_type="async_invalid")


class TestEmbeddingIntegration(SimpleTestCase):
    """Integration tests for Embedding class."""

    @pytest.mark.asyncio
    async def test_sync_and_async_embed_consistency(self):
        """Test that sync and async embed produce same results."""
        with patch("ai.vdb.embedding.os.getenv") as mock_getenv:
            mock_getenv.side_effect = create_mock_getenv(
                EMBEDDING_MODEL_ID="test-model",
                EMBEDDING_MODEL_DOCUMENT_PROMPT=""
            )

            with patch("ai.vdb.embedding.OpenAI") as mock_openai_class:
                with patch("ai.vdb.embedding.AsyncOpenAI") as mock_async_openai_class:
                    mock_client = MagicMock()
                    mock_async_client = AsyncMock()
                    mock_openai_class.return_value = mock_client
                    mock_async_openai_class.return_value = mock_async_client

                    # Same embeddings for both
                    shared_embeddings = [
                        MagicMock(embedding=[0.1, 0.2, 0.3]),
                    ]
                    
                    mock_sync_response = MagicMock()
                    mock_sync_response.data = shared_embeddings
                    mock_client.embeddings.create.return_value = mock_sync_response

                    mock_async_response = MagicMock()
                    mock_async_response.data = shared_embeddings
                    mock_async_client.embeddings.create.return_value = mock_async_response

                    embedding = Embedding()
                    sync_result = embedding.embed(["text"], prompt_type="document")
                    async_result = await embedding.async_embed(["text"], prompt_type="document")

                    assert sync_result == async_result

    def test_embed_normalization_zero_vector(self):
        """Test that zero vectors are handled correctly during normalization."""
        with patch("ai.vdb.embedding.os.getenv") as mock_getenv:
            mock_getenv.side_effect = create_mock_getenv(
                EMBEDDING_MODEL_ID="test-model",
                EMBEDDING_MODEL_DOCUMENT_PROMPT=""
            )

            with patch("ai.vdb.embedding.OpenAI") as mock_openai_class:
                with patch("ai.vdb.embedding.AsyncOpenAI"):
                    mock_client = MagicMock()
                    mock_openai_class.return_value = mock_client

                    # Zero vector
                    mock_embeddings = [
                        MagicMock(embedding=[0.0, 0.0, 0.0])
                    ]
                    mock_response = MagicMock()
                    mock_response.data = mock_embeddings
                    mock_client.embeddings.create.return_value = mock_response

                    embedding = Embedding()
                    result = embedding.embed(
                        ["text"],
                        prompt_type="document",
                        normalize=True
                    )

                    # Zero vector should remain zero
                    assert result[0] == [0.0, 0.0, 0.0]
