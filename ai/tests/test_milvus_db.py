import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
from django.test import SimpleTestCase
from ai.vdb.milvus_db import VectorDatabaseBuilder, VectorDatabaseQuerier


def create_mock_getenv(**env_vars):
    """Create a mock getenv function with predefined environment variables."""
    def mock_getenv(key, default=None):
        return env_vars.get(key, default)
    return mock_getenv


class TestVectorDatabaseBuilderInit(SimpleTestCase):
    """Tests for VectorDatabaseBuilder initialization."""

    def test_init_with_default_values(self):
        """Test VectorDatabaseBuilder initialization with default environment variables."""
        env_vars = {
            "MILVUS_URL": "http://localhost",
            "MILVUS_PORT": "19530",
            "MILVUS_DATABASE_NAME": "faith_db",
            "MILVUS_USERNAME": "admin",
            "MILVUS_PASSWORD": "admin",
            "DATABASE_TYPE": "hybrid",
            "EMBEDDING_MODEL_ID": "test-model",
        }
        with patch("ai.vdb.milvus_db.os.getenv") as mock_getenv:
            mock_getenv.side_effect = create_mock_getenv(**env_vars)
            with patch("ai.vdb.milvus_db.Embedding"):
                with patch("ai.vdb.milvus_db.MilvusClient"):
                    builder = VectorDatabaseBuilder()
                    assert builder.milvus_url == "http://localhost"
                    assert builder.milvus_port == "19530"
                    assert builder.milvus_database_name == "faith_db"
                    assert builder.milvus_username == "admin"
                    assert builder.milvus_password == "admin"
                    assert builder.database_type == "hybrid"

    def test_database_type_sparse(self):
        """Test initialization with sparse database type."""
        env_vars = {
            "MILVUS_URL": "http://localhost",
            "MILVUS_PORT": "19530",
            "MILVUS_DATABASE_NAME": "faith_db",
            "MILVUS_USERNAME": "admin",
            "MILVUS_PASSWORD": "admin",
            "DATABASE_TYPE": "sparse",
            "EMBEDDING_MODEL_ID": "test-model",
        }
        with patch("ai.vdb.milvus_db.os.getenv") as mock_getenv:
            mock_getenv.side_effect = create_mock_getenv(**env_vars)
            with patch("ai.vdb.milvus_db.Embedding"):
                with patch("ai.vdb.milvus_db.MilvusClient"):
                    builder = VectorDatabaseBuilder()
                    assert builder.database_type == "sparse"

    def test_database_type_dense(self):
        """Test initialization with dense database type."""
        env_vars = {
            "MILVUS_URL": "http://localhost",
            "MILVUS_PORT": "19530",
            "MILVUS_DATABASE_NAME": "faith_db",
            "MILVUS_USERNAME": "admin",
            "MILVUS_PASSWORD": "admin",
            "DATABASE_TYPE": "dense",
            "EMBEDDING_MODEL_ID": "test-model",
        }
        with patch("ai.vdb.milvus_db.os.getenv") as mock_getenv:
            mock_getenv.side_effect = create_mock_getenv(**env_vars)
            with patch("ai.vdb.milvus_db.Embedding"):
                with patch("ai.vdb.milvus_db.MilvusClient"):
                    builder = VectorDatabaseBuilder()
                    assert builder.database_type == "dense"

    def test_init_with_custom_values(self):
        """Test VectorDatabaseBuilder initialization with custom environment variables."""
        env_vars = {
            "MILVUS_URL": "http://milvus.example.com",
            "MILVUS_PORT": "19531",
            "MILVUS_DATABASE_NAME": "custom_db",
            "MILVUS_USERNAME": "user",
            "MILVUS_PASSWORD": "password",
            "DATABASE_TYPE": "dense",
            "EMBEDDING_MODEL_ID": "test-model",
        }
        with patch("ai.vdb.milvus_db.os.getenv") as mock_getenv:
            mock_getenv.side_effect = create_mock_getenv(**env_vars)
            with patch("ai.vdb.milvus_db.Embedding"):
                with patch("ai.vdb.milvus_db.MilvusClient"):
                    builder = VectorDatabaseBuilder()
                    assert builder.milvus_url == "http://milvus.example.com"
                    assert builder.milvus_port == "19531"
                    assert builder.milvus_database_name == "custom_db"
                    assert builder.database_type == "dense"

    def test_init_invalid_database_type(self):
        """Test that invalid database type raises ValueError."""
        env_vars = {
            "MILVUS_URL": "http://localhost",
            "MILVUS_PORT": "19530",
            "MILVUS_DATABASE_NAME": "faith_db",
            "MILVUS_USERNAME": "admin",
            "MILVUS_PASSWORD": "admin",
            "DATABASE_TYPE": "invalid_type",
            "EMBEDDING_MODEL_ID": "test-model",
        }
        with patch("ai.vdb.milvus_db.os.getenv") as mock_getenv:
            mock_getenv.side_effect = create_mock_getenv(**env_vars)
            with patch("ai.vdb.milvus_db.Embedding"):
                with patch("ai.vdb.milvus_db.logger") as mock_logger:
                    with pytest.raises(ValueError, match="Invalid database type"):
                        VectorDatabaseBuilder()
                    mock_logger.error.assert_called()

    def test_init_creates_milvus_client(self):
        """Test that MilvusClient is created with correct parameters."""
        env_vars = {
            "MILVUS_URL": "http://localhost",
            "MILVUS_PORT": "19530",
            "MILVUS_DATABASE_NAME": "faith_db",
            "MILVUS_USERNAME": "admin",
            "MILVUS_PASSWORD": "admin",
            "DATABASE_TYPE": "hybrid",
            "EMBEDDING_MODEL_ID": "test-model",
        }
        with patch("ai.vdb.milvus_db.os.getenv") as mock_getenv:
            mock_getenv.side_effect = create_mock_getenv(**env_vars)
            with patch("ai.vdb.milvus_db.Embedding"):
                with patch("ai.vdb.milvus_db.MilvusClient") as mock_client_class:
                    VectorDatabaseBuilder()
                    mock_client_class.assert_called_once_with(
                        uri="http://localhost:19530",
                        token="admin:admin"
                    )

    def test_init_creates_embedding_engine(self):
        """Test that Embedding engine is created during initialization."""
        env_vars = {
            "MILVUS_URL": "http://localhost",
            "MILVUS_PORT": "19530",
            "MILVUS_DATABASE_NAME": "faith_db",
            "MILVUS_USERNAME": "admin",
            "MILVUS_PASSWORD": "admin",
            "DATABASE_TYPE": "hybrid",
            "EMBEDDING_MODEL_ID": "test-model",
        }
        with patch("ai.vdb.milvus_db.os.getenv") as mock_getenv:
            mock_getenv.side_effect = create_mock_getenv(**env_vars)
            with patch("ai.vdb.milvus_db.Embedding") as mock_embedding_class:
                with patch("ai.vdb.milvus_db.MilvusClient"):
                    builder = VectorDatabaseBuilder()
                    mock_embedding_class.assert_called_once()
                    assert builder.embedding_engine is not None

class TestLoadDatabase(SimpleTestCase):
    """Tests for load_database method."""

    def test_load_database_success(self):
        """Test successful database loading."""
        env_vars = {
            "MILVUS_URL": "http://localhost",
            "MILVUS_PORT": "19530",
            "MILVUS_DATABASE_NAME": "faith_db",
            "MILVUS_USERNAME": "admin",
            "MILVUS_PASSWORD": "admin",
            "DATABASE_TYPE": "hybrid",
            "EMBEDDING_MODEL_ID": "test-model",
        }
        with patch("ai.vdb.milvus_db.os.getenv") as mock_getenv:
            mock_getenv.side_effect = create_mock_getenv(**env_vars)
            with patch("ai.vdb.milvus_db.Embedding"):
                with patch("ai.vdb.milvus_db.MilvusClient") as mock_client_class:
                    mock_client = MagicMock()
                    mock_client_class.return_value = mock_client

                    builder = VectorDatabaseBuilder()
                    builder.load_database()

                    mock_client.use_database.assert_called_once_with("faith_db")

    def test_load_database_error(self):
        """Test error handling during database loading."""
        env_vars = {
            "MILVUS_URL": "http://localhost",
            "MILVUS_PORT": "19530",
            "MILVUS_DATABASE_NAME": "faith_db",
            "MILVUS_USERNAME": "admin",
            "MILVUS_PASSWORD": "admin",
            "DATABASE_TYPE": "hybrid",
            "EMBEDDING_MODEL_ID": "test-model",
        }
        with patch("ai.vdb.milvus_db.os.getenv") as mock_getenv:
            mock_getenv.side_effect = create_mock_getenv(**env_vars)
            with patch("ai.vdb.milvus_db.Embedding"):
                with patch("ai.vdb.milvus_db.MilvusClient") as mock_client_class:
                    mock_client = MagicMock()
                    mock_client.use_database.side_effect = Exception("Connection failed")
                    mock_client_class.return_value = mock_client

                    builder = VectorDatabaseBuilder()
                    with pytest.raises(Exception, match="Connection failed"):
                        builder.load_database()


class TestLoadOrCreateDatabase(SimpleTestCase):
    """Tests for load_or_create_database method."""

    def test_load_existing_database(self):
        """Test loading an existing database."""
        env_vars = {
            "MILVUS_URL": "http://localhost",
            "MILVUS_PORT": "19530",
            "MILVUS_DATABASE_NAME": "faith_db",
            "MILVUS_USERNAME": "admin",
            "MILVUS_PASSWORD": "admin",
            "DATABASE_TYPE": "hybrid",
            "EMBEDDING_MODEL_ID": "test-model",
        }
        with patch("ai.vdb.milvus_db.os.getenv") as mock_getenv:
            mock_getenv.side_effect = create_mock_getenv(**env_vars)
            with patch("ai.vdb.milvus_db.Embedding"):
                with patch("ai.vdb.milvus_db.MilvusClient") as mock_client_class:
                    with patch("ai.vdb.milvus_db.logger") as mock_logger:
                        mock_client = MagicMock()
                        mock_client.list_databases.return_value = ["faith_db", "other_db"]
                        mock_client_class.return_value = mock_client

                        builder = VectorDatabaseBuilder()
                        builder.load_or_create_database()

                        assert mock_client.create_database.call_count == 0
                        mock_client.use_database.assert_called_with("faith_db")
                        assert mock_logger.info.call_count >= 2

    def test_create_new_database(self):
        """Test creating a new database when no databases exist at all."""
        env_vars = {
            "MILVUS_URL": "http://localhost",
            "MILVUS_PORT": "19530",
            "MILVUS_DATABASE_NAME": "faith_db",
            "MILVUS_USERNAME": "admin",
            "MILVUS_PASSWORD": "admin",
            "DATABASE_TYPE": "hybrid",
            "EMBEDDING_MODEL_ID": "test-model",
        }
        with patch("ai.vdb.milvus_db.os.getenv") as mock_getenv:
            mock_getenv.side_effect = create_mock_getenv(**env_vars)
            with patch("ai.vdb.milvus_db.Embedding"):
                with patch("ai.vdb.milvus_db.MilvusClient") as mock_client_class:
                    with patch("ai.vdb.milvus_db.logger"):
                        mock_client = MagicMock()
                        # No databases exist at all
                        mock_client.list_databases.return_value = []
                        mock_client_class.return_value = mock_client

                        builder = VectorDatabaseBuilder()
                        builder.load_or_create_database()

                        # Should create the database since it doesn't exist
                        mock_client.create_database.assert_called_once_with("faith_db")
                        mock_client.use_database.assert_called_with("faith_db")

    def test_create_new_database_with_existing_databases(self):
        """Test creating a new database when it does not exist in existing databases."""
        env_vars = {
            "MILVUS_URL": "http://localhost",
            "MILVUS_PORT": "19530",
            "MILVUS_DATABASE_NAME": "faith_db",
            "MILVUS_USERNAME": "admin",
            "MILVUS_PASSWORD": "admin",
            "DATABASE_TYPE": "hybrid",
            "EMBEDDING_MODEL_ID": "test-model",
        }
        with patch("ai.vdb.milvus_db.os.getenv") as mock_getenv:
            mock_getenv.side_effect = create_mock_getenv(**env_vars)
            with patch("ai.vdb.milvus_db.Embedding"):
                with patch("ai.vdb.milvus_db.MilvusClient") as mock_client_class:
                    with patch("ai.vdb.milvus_db.logger"):
                        mock_client = MagicMock()
                        mock_client.list_databases.return_value = ["other_db"]
                        mock_client_class.return_value = mock_client

                        builder = VectorDatabaseBuilder()
                        builder.load_or_create_database()

                        mock_client.create_database.assert_called_once_with("faith_db")
                        mock_client.use_database.assert_called_with("faith_db")



    def test_create_database_error(self):
        """Test error handling during database creation."""
        env_vars = {
            "MILVUS_URL": "http://localhost",
            "MILVUS_PORT": "19530",
            "MILVUS_DATABASE_NAME": "faith_db",
            "MILVUS_USERNAME": "admin",
            "MILVUS_PASSWORD": "admin",
            "DATABASE_TYPE": "hybrid",
            "EMBEDDING_MODEL_ID": "test-model",
        }
        with patch("ai.vdb.milvus_db.os.getenv") as mock_getenv:
            mock_getenv.side_effect = create_mock_getenv(**env_vars)
            with patch("ai.vdb.milvus_db.Embedding"):
                with patch("ai.vdb.milvus_db.MilvusClient") as mock_client_class:
                    with patch("ai.vdb.milvus_db.logger"):
                        mock_client = MagicMock()
                        mock_client.list_databases.return_value = []
                        mock_client.create_database.side_effect = Exception("Create failed")
                        mock_client_class.return_value = mock_client

                        builder = VectorDatabaseBuilder()
                        with pytest.raises(Exception, match="Create failed"):
                            builder.load_or_create_database()


class TestListCollectionsInDatabase(SimpleTestCase):
    """Tests for list_collections_in_database method."""

    def test_list_collections_success(self):
        """Test successfully listing collections."""
        env_vars = {
            "MILVUS_URL": "http://localhost",
            "MILVUS_PORT": "19530",
            "MILVUS_DATABASE_NAME": "faith_db",
            "MILVUS_USERNAME": "admin",
            "MILVUS_PASSWORD": "admin",
            "DATABASE_TYPE": "hybrid",
            "EMBEDDING_MODEL_ID": "test-model",
        }
        with patch("ai.vdb.milvus_db.os.getenv") as mock_getenv:
            mock_getenv.side_effect = create_mock_getenv(**env_vars)
            with patch("ai.vdb.milvus_db.Embedding"):
                with patch("ai.vdb.milvus_db.MilvusClient") as mock_client_class:
                    mock_client = MagicMock()
                    mock_collections = ["web", "bsb"]
                    mock_client.list_collections.return_value = mock_collections
                    mock_client_class.return_value = mock_client

                    builder = VectorDatabaseBuilder()
                    result = builder.list_collections_in_database()

                    assert result == mock_collections
                    mock_client.list_collections.assert_called_once_with(db_name="faith_db")

    def test_list_collections_error(self):
        """Test error handling when listing collections fails."""
        env_vars = {
            "MILVUS_URL": "http://localhost",
            "MILVUS_PORT": "19530",
            "MILVUS_DATABASE_NAME": "faith_db",
            "MILVUS_USERNAME": "admin",
            "MILVUS_PASSWORD": "admin",
            "DATABASE_TYPE": "hybrid",
            "EMBEDDING_MODEL_ID": "test-model",
        }
        with patch("ai.vdb.milvus_db.os.getenv") as mock_getenv:
            mock_getenv.side_effect = create_mock_getenv(**env_vars)
            with patch("ai.vdb.milvus_db.Embedding"):
                with patch("ai.vdb.milvus_db.MilvusClient") as mock_client_class:
                    with patch("ai.vdb.milvus_db.logger"):
                        mock_client = MagicMock()
                        mock_client.list_collections.side_effect = Exception("List failed")
                        mock_client_class.return_value = mock_client

                        builder = VectorDatabaseBuilder()
                        with pytest.raises(Exception, match="List failed"):
                            builder.list_collections_in_database()


class TestDropCollection(SimpleTestCase):
    """Tests for drop_collection method."""

    def test_drop_collection_success(self):
        """Test successfully dropping a collection."""
        env_vars = {
            "MILVUS_URL": "http://localhost",
            "MILVUS_PORT": "19530",
            "MILVUS_DATABASE_NAME": "faith_db",
            "MILVUS_USERNAME": "admin",
            "MILVUS_PASSWORD": "admin",
            "DATABASE_TYPE": "hybrid",
            "EMBEDDING_MODEL_ID": "test-model",
        }
        with patch("ai.vdb.milvus_db.os.getenv") as mock_getenv:
            mock_getenv.side_effect = create_mock_getenv(**env_vars)
            with patch("ai.vdb.milvus_db.Embedding"):
                with patch("ai.vdb.milvus_db.MilvusClient") as mock_client_class:
                    mock_client = MagicMock()
                    # Simulate database exists with collections
                    mock_client.list_databases.return_value = ["faith_db"]
                    mock_client.list_collections.side_effect = [
                        ["web", "bsb"],  # Before drop
                        ["web"],  # After drop
                    ]
                    mock_client_class.return_value = mock_client

                    builder = VectorDatabaseBuilder()
                    builder.load_or_create_database()

                    # Verify BSB exists before dropping
                    collections_before = builder.list_collections_in_database()
                    assert "bsb" in collections_before

                    # Drop the BSB collection
                    builder.drop_collection("bsb")

                    # Verify drop was called
                    mock_client.drop_collection.assert_called_once_with(collection_name="bsb")

                    # Verify BSB no longer exists
                    collections_after = builder.list_collections_in_database()
                    assert "bsb" not in collections_after
                    assert "web" in collections_after

    def test_drop_collection_warning(self):
        """Test that warning is logged when dropping non-existent collection."""
        env_vars = {
            "MILVUS_URL": "http://localhost",
            "MILVUS_PORT": "19530",
            "MILVUS_DATABASE_NAME": "faith_db",
            "MILVUS_USERNAME": "admin",
            "MILVUS_PASSWORD": "admin",
            "DATABASE_TYPE": "hybrid",
            "EMBEDDING_MODEL_ID": "test-model",
        }
        with patch("ai.vdb.milvus_db.os.getenv") as mock_getenv:
            mock_getenv.side_effect = create_mock_getenv(**env_vars)
            with patch("ai.vdb.milvus_db.Embedding"):
                with patch("ai.vdb.milvus_db.MilvusClient") as mock_client_class:
                    with patch("ai.vdb.milvus_db.logger") as mock_logger:
                        mock_client = MagicMock()
                        mock_client.list_databases.return_value = ["faith_db"]
                        mock_client.drop_collection.side_effect = Exception("Collection not found")
                        mock_client_class.return_value = mock_client

                        builder = VectorDatabaseBuilder()
                        builder.load_or_create_database()
                        builder.drop_collection("NonExistent")

                        # Should not raise, only warn
                        mock_logger.warning.assert_called()


class TestCreateCollections(SimpleTestCase):
    """Tests for create_collections method."""

    def test_create_all_collections_default(self):
        """Test creating all collections when no specific names are provided."""
        env_vars = {
            "MILVUS_URL": "http://localhost",
            "MILVUS_PORT": "19530",
            "MILVUS_DATABASE_NAME": "faith_db",
            "MILVUS_USERNAME": "admin",
            "MILVUS_PASSWORD": "admin",
            "DATABASE_TYPE": "dense",
            "EMBEDDING_MODEL_ID": "test-model",
        }
        version_selection = ["web", "bsb"]
        with patch("ai.vdb.milvus_db.os.getenv") as mock_getenv:
            mock_getenv.side_effect = create_mock_getenv(**env_vars)
            with patch("ai.vdb.milvus_db.Embedding") as mock_embedding:
                with patch("ai.vdb.milvus_db.MilvusClient") as mock_client_class:
                    with patch("ai.vdb.milvus_db.logger"):
                        with patch("ai.vdb.milvus_db.VERSION_SELECTION", version_selection):
                            with patch("ai.vdb.milvus_db.BIBLE_DATA_ROOT", Path("/data")):
                                with patch("ai.vdb.milvus_db.IN_ORDER_BOOKS", []):
                                    with patch("ai.vdb.milvus_db.CHAPTER_SELECTION", {}):
                                        mock_client = MagicMock()
                                        mock_client.prepare_index_params.return_value = MagicMock()
                                        mock_embedding_instance = MagicMock()
                                        mock_embedding_instance.embedding_size.return_value = 768
                                        mock_embedding.return_value = mock_embedding_instance
                                        mock_client_class.return_value = mock_client

                                        builder = VectorDatabaseBuilder()
                                        builder.create_collections([])

                                        # Should create both collections
                                        assert mock_client.create_collection.call_count == len(version_selection)

    def test_create_specific_collection_valid(self):
        """Test creating specific collections with valid names."""
        env_vars = {
            "MILVUS_URL": "http://localhost",
            "MILVUS_PORT": "19530",
            "MILVUS_DATABASE_NAME": "faith_db",
            "MILVUS_USERNAME": "admin",
            "MILVUS_PASSWORD": "admin",
            "DATABASE_TYPE": "dense",
            "EMBEDDING_MODEL_ID": "test-model",
        }
        version_selection = ["web", "bsb"]
        with patch("ai.vdb.milvus_db.os.getenv") as mock_getenv:
            mock_getenv.side_effect = create_mock_getenv(**env_vars)
            with patch("ai.vdb.milvus_db.Embedding") as mock_embedding:
                with patch("ai.vdb.milvus_db.MilvusClient") as mock_client_class:
                    with patch("ai.vdb.milvus_db.logger"):
                        with patch("ai.vdb.milvus_db.VERSION_SELECTION", version_selection):
                            with patch("ai.vdb.milvus_db.BIBLE_DATA_ROOT", Path("/data")):
                                with patch("ai.vdb.milvus_db.IN_ORDER_BOOKS", []):
                                    with patch("ai.vdb.milvus_db.CHAPTER_SELECTION", {}):
                                        mock_client = MagicMock()
                                        mock_client.prepare_index_params.return_value = MagicMock()
                                        mock_embedding_instance = MagicMock()
                                        mock_embedding_instance.embedding_size.return_value = 768
                                        mock_embedding.return_value = mock_embedding_instance
                                        mock_client_class.return_value = mock_client

                                        builder = VectorDatabaseBuilder()
                                        builder.create_collections(["bsb"])

                                        # Should create only BSB collection
                                        assert mock_client.create_collection.call_count == 1

    def test_create_collection_invalid_name(self):
        """Test error when creating collection with invalid name."""
        env_vars = {
            "MILVUS_URL": "http://localhost",
            "MILVUS_PORT": "19530",
            "MILVUS_DATABASE_NAME": "faith_db",
            "MILVUS_USERNAME": "admin",
            "MILVUS_PASSWORD": "admin",
            "DATABASE_TYPE": "dense",
            "EMBEDDING_MODEL_ID": "test-model",
        }
        version_selection = ["web", "bsb"]
        with patch("ai.vdb.milvus_db.os.getenv") as mock_getenv:
            mock_getenv.side_effect = create_mock_getenv(**env_vars)
            with patch("ai.vdb.milvus_db.Embedding"):
                with patch("ai.vdb.milvus_db.MilvusClient") as mock_client_class:
                    with patch("ai.vdb.milvus_db.logger"):
                        with patch("ai.vdb.milvus_db.VERSION_SELECTION", version_selection):
                            mock_client = MagicMock()
                            mock_client_class.return_value = mock_client

                            builder = VectorDatabaseBuilder()
                            with pytest.raises(ValueError, match="does not exist"):
                                builder.create_collections(["INVALID"])


class TestClose(SimpleTestCase):
    """Tests for close method."""

    def test_close_success(self):
        """Test successfully closing the database connection."""
        env_vars = {
            "MILVUS_URL": "http://localhost",
            "MILVUS_PORT": "19530",
            "MILVUS_DATABASE_NAME": "faith_db",
            "MILVUS_USERNAME": "admin",
            "MILVUS_PASSWORD": "admin",
            "DATABASE_TYPE": "hybrid",
            "EMBEDDING_MODEL_ID": "test-model",
        }
        with patch("ai.vdb.milvus_db.os.getenv") as mock_getenv:
            mock_getenv.side_effect = create_mock_getenv(**env_vars)
            with patch("ai.vdb.milvus_db.Embedding"):
                with patch("ai.vdb.milvus_db.MilvusClient") as mock_client_class:
                    mock_client = MagicMock()
                    mock_client_class.return_value = mock_client

                    builder = VectorDatabaseBuilder()
                    builder.close()

                    mock_client.close.assert_called_once()

    def test_close_error(self):
        """Test error handling during database closing."""
        env_vars = {
            "MILVUS_URL": "http://localhost",
            "MILVUS_PORT": "19530",
            "MILVUS_DATABASE_NAME": "faith_db",
            "MILVUS_USERNAME": "admin",
            "MILVUS_PASSWORD": "admin",
            "DATABASE_TYPE": "hybrid",
            "EMBEDDING_MODEL_ID": "test-model",
        }
        with patch("ai.vdb.milvus_db.os.getenv") as mock_getenv:
            mock_getenv.side_effect = create_mock_getenv(**env_vars)
            with patch("ai.vdb.milvus_db.Embedding"):
                with patch("ai.vdb.milvus_db.MilvusClient") as mock_client_class:
                    with patch("ai.vdb.milvus_db.logger"):
                        mock_client = MagicMock()
                        mock_client.close.side_effect = Exception("Close failed")
                        mock_client_class.return_value = mock_client

                        builder = VectorDatabaseBuilder()
                        with pytest.raises(Exception, match="Close failed"):
                            builder.close()


class TestVectorDatabaseQuerierInit(SimpleTestCase):
    """Tests for VectorDatabaseQuerier initialization."""

    def test_querier_init_with_default_values(self):
        """Test VectorDatabaseQuerier initialization with default values."""
        env_vars = {
            "MILVUS_URL": "http://localhost",
            "MILVUS_PORT": "19530",
            "MILVUS_DATABASE_NAME": "faith_db",
            "MILVUS_USERNAME": "admin",
            "MILVUS_PASSWORD": "admin",
            "DATABASE_TYPE": "hybrid",
            "EMBEDDING_MODEL_ID": "test-model",
        }
        with patch("ai.vdb.milvus_db.os.getenv") as mock_getenv:
            mock_getenv.side_effect = create_mock_getenv(**env_vars)
            with patch("ai.vdb.milvus_db.Embedding"):
                querier = VectorDatabaseQuerier()
                assert querier.milvus_url == "http://localhost"
                assert querier.milvus_port == "19530"
                assert querier.milvus_database_name == "faith_db"
                assert querier.database_type == "hybrid"
                assert querier.async_client is None

    def test_querier_invalid_database_type(self):
        """Test that invalid database type raises ValueError in querier."""
        env_vars = {
            "MILVUS_URL": "http://localhost",
            "MILVUS_PORT": "19530",
            "MILVUS_DATABASE_NAME": "faith_db",
            "MILVUS_USERNAME": "admin",
            "MILVUS_PASSWORD": "admin",
            "DATABASE_TYPE": "bad_type",
            "EMBEDDING_MODEL_ID": "test-model",
        }
        with patch("ai.vdb.milvus_db.os.getenv") as mock_getenv:
            mock_getenv.side_effect = create_mock_getenv(**env_vars)
            with patch("ai.vdb.milvus_db.Embedding"):
                with patch("ai.vdb.milvus_db.logger"):
                    with pytest.raises(ValueError, match="Invalid database type"):
                        VectorDatabaseQuerier()


class TestVectorDatabaseQuerierLoadDatabaseAndCollections(SimpleTestCase):
    """Tests for VectorDatabaseQuerier.load_database_and_collections method."""

    @pytest.mark.asyncio
    async def test_load_database_and_collections_success(self):
        """Test successfully loading database and collections."""
        env_vars = {
            "MILVUS_URL": "http://localhost",
            "MILVUS_PORT": "19530",
            "MILVUS_DATABASE_NAME": "faith_db",
            "MILVUS_USERNAME": "admin",
            "MILVUS_PASSWORD": "admin",
            "DATABASE_TYPE": "hybrid",
            "EMBEDDING_MODEL_ID": "test-model",
        }
        with patch("ai.vdb.milvus_db.os.getenv") as mock_getenv:
            mock_getenv.side_effect = create_mock_getenv(**env_vars)
            with patch("ai.vdb.milvus_db.Embedding"):
                with patch("ai.vdb.milvus_db.AsyncMilvusClient") as mock_async_client_class:
                    with patch("ai.vdb.milvus_db.logger"):
                        mock_temp_client = AsyncMock()
                        mock_temp_client.list_databases.return_value = ["faith_db", "other_db"]
                        
                        mock_collections = ["web", "bsb"]
                        mock_async_client = AsyncMock()
                        mock_async_client.list_collections.return_value = mock_collections
                        
                        mock_async_client_class.side_effect = [mock_temp_client, mock_async_client]

                        querier = await VectorDatabaseQuerier.load_database_and_collections()

                        assert querier.async_client is not None
                        assert mock_async_client.load_collection.call_count == len(mock_collections)

    @pytest.mark.asyncio
    async def test_load_database_not_found(self):
        """Test error when database doesn't exist."""
        env_vars = {
            "MILVUS_URL": "http://localhost",
            "MILVUS_PORT": "19530",
            "MILVUS_DATABASE_NAME": "nonexistent_db",
            "MILVUS_USERNAME": "admin",
            "MILVUS_PASSWORD": "admin",
            "DATABASE_TYPE": "hybrid",
            "EMBEDDING_MODEL_ID": "test-model",
        }
        with patch("ai.vdb.milvus_db.os.getenv") as mock_getenv:
            mock_getenv.side_effect = create_mock_getenv(**env_vars)
            with patch("ai.vdb.milvus_db.Embedding"):
                with patch("ai.vdb.milvus_db.AsyncMilvusClient") as mock_async_client_class:
                    with patch("ai.vdb.milvus_db.logger"):
                        mock_temp_client = AsyncMock()
                        # Simulate no existing databases
                        existing_databases = []
                        mock_temp_client.list_databases.return_value = existing_databases
                        mock_async_client_class.return_value = mock_temp_client

                        # Verify nonexistent_db is not in the list of existing databases
                        assert "nonexistent_db" not in existing_databases

                        with pytest.raises(ValueError, match="does not exist"):
                            await VectorDatabaseQuerier.load_database_and_collections()

    @pytest.mark.asyncio
    async def test_load_database_not_found_in_existing_databases(self):
        """Test error when database doesn't exist."""
        env_vars = {
            "MILVUS_URL": "http://localhost",
            "MILVUS_PORT": "19530",
            "MILVUS_DATABASE_NAME": "nonexistent_db",
            "MILVUS_USERNAME": "admin",
            "MILVUS_PASSWORD": "admin",
            "DATABASE_TYPE": "hybrid",
            "EMBEDDING_MODEL_ID": "test-model",
        }
        with patch("ai.vdb.milvus_db.os.getenv") as mock_getenv:
            mock_getenv.side_effect = create_mock_getenv(**env_vars)
            with patch("ai.vdb.milvus_db.Embedding"):
                with patch("ai.vdb.milvus_db.AsyncMilvusClient") as mock_async_client_class:
                    with patch("ai.vdb.milvus_db.logger"):
                        mock_temp_client = AsyncMock()
                        # Simulate existing databases, but nonexistent_db is not among them
                        existing_databases = ["faith_db", "other_db"]
                        mock_temp_client.list_databases.return_value = existing_databases
                        mock_async_client_class.return_value = mock_temp_client

                        # Verify nonexistent_db is not in the list of existing databases
                        assert "nonexistent_db" not in existing_databases

                        with pytest.raises(ValueError, match="does not exist"):
                            await VectorDatabaseQuerier.load_database_and_collections()


class TestVectorDatabaseQuerierListCollections(SimpleTestCase):
    """Tests for VectorDatabaseQuerier.list_collections_in_database method."""

    @pytest.mark.asyncio
    async def test_list_collections_success(self):
        """Test successfully listing collections asynchronously."""
        env_vars = {
            "MILVUS_URL": "http://localhost",
            "MILVUS_PORT": "19530",
            "MILVUS_DATABASE_NAME": "faith_db",
            "MILVUS_USERNAME": "admin",
            "MILVUS_PASSWORD": "admin",
            "DATABASE_TYPE": "hybrid",
            "EMBEDDING_MODEL_ID": "test-model",
        }
        with patch("ai.vdb.milvus_db.os.getenv") as mock_getenv:
            mock_getenv.side_effect = create_mock_getenv(**env_vars)
            with patch("ai.vdb.milvus_db.Embedding"):
                mock_collections = ["web", "bsb"]
                mock_async_client = AsyncMock()
                mock_async_client.list_collections.return_value = mock_collections

                querier = VectorDatabaseQuerier()
                querier.async_client = mock_async_client

                result = await querier.list_collections_in_database()

                assert result == mock_collections
                mock_async_client.list_collections.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_collections_error(self):
        """Test error handling when listing collections fails."""
        env_vars = {
            "MILVUS_URL": "http://localhost",
            "MILVUS_PORT": "19530",
            "MILVUS_DATABASE_NAME": "faith_db",
            "MILVUS_USERNAME": "admin",
            "MILVUS_PASSWORD": "admin",
            "DATABASE_TYPE": "hybrid",
            "EMBEDDING_MODEL_ID": "test-model",
        }
        with patch("ai.vdb.milvus_db.os.getenv") as mock_getenv:
            mock_getenv.side_effect = create_mock_getenv(**env_vars)
            with patch("ai.vdb.milvus_db.Embedding"):
                with patch("ai.vdb.milvus_db.logger"):
                    mock_async_client = AsyncMock()
                    mock_async_client.list_collections.side_effect = Exception("List failed")

                    querier = VectorDatabaseQuerier()
                    querier.async_client = mock_async_client

                    with pytest.raises(Exception, match="List failed"):
                        await querier.list_collections_in_database()


class TestVectorDatabaseQuerierSearch(SimpleTestCase):
    """Tests for VectorDatabaseQuerier.search method."""

    @pytest.mark.asyncio
    async def test_search_hybrid_mode(self):
        """Test search in hybrid mode."""
        env_vars = {
            "MILVUS_URL": "http://localhost",
            "MILVUS_PORT": "19530",
            "MILVUS_DATABASE_NAME": "faith_db",
            "MILVUS_USERNAME": "admin",
            "MILVUS_PASSWORD": "admin",
            "DATABASE_TYPE": "hybrid",
            "EMBEDDING_MODEL_ID": "test-model",
            "SPARSE_WEIGHT": "0.2",
            "DENSE_WEIGHT": "0.8",
        }
        with patch("ai.vdb.milvus_db.os.getenv") as mock_getenv:
            mock_getenv.side_effect = create_mock_getenv(**env_vars)
            with patch("ai.vdb.milvus_db.Embedding") as mock_embedding_class:
                mock_embedding = AsyncMock()
                mock_embedding.async_embed.return_value = [[0.1, 0.2, 0.3]]
                mock_embedding_class.return_value = mock_embedding

                mock_async_client = AsyncMock()
                mock_async_client.hybrid_search.return_value = [[{"text": "result"}]]

                querier = VectorDatabaseQuerier()
                querier.async_client = mock_async_client

                result = await querier.search("bsb", "God", limit=5)

                assert result == [{"text": "result"}]
                mock_async_client.hybrid_search.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_dense_mode(self):
        """Test search in dense mode."""
        env_vars = {
            "MILVUS_URL": "http://localhost",
            "MILVUS_PORT": "19530",
            "MILVUS_DATABASE_NAME": "faith_db",
            "MILVUS_USERNAME": "admin",
            "MILVUS_PASSWORD": "admin",
            "DATABASE_TYPE": "dense",
            "EMBEDDING_MODEL_ID": "test-model",
        }
        with patch("ai.vdb.milvus_db.os.getenv") as mock_getenv:
            mock_getenv.side_effect = create_mock_getenv(**env_vars)
            with patch("ai.vdb.milvus_db.Embedding") as mock_embedding_class:
                mock_embedding = AsyncMock()
                mock_embedding.async_embed.return_value = [[0.1, 0.2, 0.3]]
                mock_embedding_class.return_value = mock_embedding

                mock_async_client = AsyncMock()
                mock_async_client.search.return_value = [[{"text": "result"}]]

                querier = VectorDatabaseQuerier()
                querier.async_client = mock_async_client

                result = await querier.search("bsb", "God", limit=5)

                assert result == [{"text": "result"}]
                mock_async_client.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_sparse_mode(self):
        """Test search in sparse mode."""
        env_vars = {
            "MILVUS_URL": "http://localhost",
            "MILVUS_PORT": "19530",
            "MILVUS_DATABASE_NAME": "faith_db",
            "MILVUS_USERNAME": "admin",
            "MILVUS_PASSWORD": "admin",
            "DATABASE_TYPE": "sparse",
            "EMBEDDING_MODEL_ID": "test-model",
        }
        with patch("ai.vdb.milvus_db.os.getenv") as mock_getenv:
            mock_getenv.side_effect = create_mock_getenv(**env_vars)
            with patch("ai.vdb.milvus_db.Embedding") as mock_embedding_class:
                mock_embedding = MagicMock()
                mock_embedding_class.return_value = mock_embedding

                mock_async_client = AsyncMock()
                mock_async_client.search.return_value = [[{"text": "result"}]]

                querier = VectorDatabaseQuerier()
                querier.async_client = mock_async_client

                result = await querier.search("bsb", "God", limit=5)

                assert result == [{"text": "result"}]
                mock_async_client.search.assert_called_once()


class TestVectorDatabaseQuerierClose(SimpleTestCase):
    """Tests for VectorDatabaseQuerier.close method."""

    @pytest.mark.asyncio
    async def test_close_with_active_client(self):
        """Test closing when async client is active."""
        env_vars = {
            "MILVUS_URL": "http://localhost",
            "MILVUS_PORT": "19530",
            "MILVUS_DATABASE_NAME": "faith_db",
            "MILVUS_USERNAME": "admin",
            "MILVUS_PASSWORD": "admin",
            "DATABASE_TYPE": "hybrid",
            "EMBEDDING_MODEL_ID": "test-model",
        }
        with patch("ai.vdb.milvus_db.os.getenv") as mock_getenv:
            mock_getenv.side_effect = create_mock_getenv(**env_vars)
            with patch("ai.vdb.milvus_db.Embedding"):
                mock_async_client = AsyncMock()
                mock_async_client.close.return_value = None

                querier = VectorDatabaseQuerier()
                querier.async_client = mock_async_client

                await querier.close()

                mock_async_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_with_no_client(self):
        """Test closing when no async client exists."""
        env_vars = {
            "MILVUS_URL": "http://localhost",
            "MILVUS_PORT": "19530",
            "MILVUS_DATABASE_NAME": "faith_db",
            "MILVUS_USERNAME": "admin",
            "MILVUS_PASSWORD": "admin",
            "DATABASE_TYPE": "hybrid",
            "EMBEDDING_MODEL_ID": "test-model",
        }
        with patch("ai.vdb.milvus_db.os.getenv") as mock_getenv:
            mock_getenv.side_effect = create_mock_getenv(**env_vars)
            with patch("ai.vdb.milvus_db.Embedding"):
                querier = VectorDatabaseQuerier()
                # Should not raise an exception
                await querier.close()
