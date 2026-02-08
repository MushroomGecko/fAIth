import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from django.test import SimpleTestCase
from ai.globals import milvus_db_lifespan_manager, completions_lifespan_manager


class TestMilvusDbLifespanManager(SimpleTestCase):
    """Tests for milvus_db_lifespan_manager async context manager."""

    @pytest.mark.asyncio
    async def test_milvus_db_lifespan_manager_initialization_and_close(self):
        """Test that milvus_db_lifespan_manager properly initializes and closes the database."""
        with patch("ai.globals.VectorDatabaseQuerier") as mock_querier_class:
            with patch("ai.globals.logger"):
                mock_milvus_db = AsyncMock()
                mock_querier_class.load_database_and_collections = AsyncMock(return_value=mock_milvus_db)

                async with milvus_db_lifespan_manager() as state:
                    assert "milvus_db" in state
                    assert state["milvus_db"] is mock_milvus_db

                mock_milvus_db.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_milvus_db_lifespan_manager_handles_close_error(self):
        """Test that milvus_db_lifespan_manager handles errors during close gracefully."""
        with patch("ai.globals.VectorDatabaseQuerier") as mock_querier_class:
            with patch("ai.globals.logger"):
                mock_milvus_db = AsyncMock()
                mock_milvus_db.close.side_effect = Exception("Close failed")
                mock_querier_class.load_database_and_collections = AsyncMock(return_value=mock_milvus_db)

                # Should not raise an exception
                async with milvus_db_lifespan_manager() as state:
                    pass

                mock_milvus_db.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_milvus_db_lifespan_manager_closes_on_exception(self):
        """Test that milvus_db_lifespan_manager closes database even when exception occurs during yield."""
        with patch("ai.globals.VectorDatabaseQuerier") as mock_querier_class:
            with patch("ai.globals.logger"):
                mock_milvus_db = AsyncMock()
                mock_querier_class.load_database_and_collections = AsyncMock(return_value=mock_milvus_db)

                try:
                    async with milvus_db_lifespan_manager() as state:
                        raise ValueError("Test error")
                except ValueError:
                    pass

                mock_milvus_db.close.assert_called_once()


class TestCompletionsLifespanManager(SimpleTestCase):
    """Tests for completions_lifespan_manager async context manager."""

    @pytest.mark.asyncio
    async def test_completions_lifespan_manager_initialization_and_close(self):
        """Test that completions_lifespan_manager properly initializes and closes the object."""
        with patch("ai.globals.Completions") as mock_completions_class:
            with patch("ai.globals.logger"):
                mock_completions_obj = MagicMock()
                mock_completions_obj.close = AsyncMock()
                mock_completions_class.return_value = mock_completions_obj

                async with completions_lifespan_manager() as state:
                    assert "completions_obj" in state
                    assert state["completions_obj"] is mock_completions_obj

                mock_completions_obj.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_completions_lifespan_manager_handles_close_error(self):
        """Test that completions_lifespan_manager handles errors during close gracefully."""
        with patch("ai.globals.Completions") as mock_completions_class:
            with patch("ai.globals.logger"):
                mock_completions_obj = MagicMock()
                mock_completions_obj.close = AsyncMock(side_effect=Exception("Close failed"))
                mock_completions_class.return_value = mock_completions_obj

                # Should not raise an exception
                async with completions_lifespan_manager() as state:
                    pass

                mock_completions_obj.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_completions_lifespan_manager_closes_on_exception(self):
        """Test that completions_lifespan_manager closes object even when exception occurs during yield."""
        with patch("ai.globals.Completions") as mock_completions_class:
            with patch("ai.globals.logger"):
                mock_completions_obj = MagicMock()
                mock_completions_obj.close = AsyncMock()
                mock_completions_class.return_value = mock_completions_obj

                try:
                    async with completions_lifespan_manager() as state:
                        raise RuntimeError("Test error")
                except RuntimeError:
                    pass

                mock_completions_obj.close.assert_called_once()


class TestLifespanManagerIntegration(SimpleTestCase):
    """Integration tests for both lifespan managers working together."""

    @pytest.mark.asyncio
    async def test_both_managers_initialize_and_close(self):
        """Test that both managers can be used together and properly close."""
        with patch("ai.globals.VectorDatabaseQuerier") as mock_querier_class:
            with patch("ai.globals.Completions") as mock_completions_class:
                with patch("ai.globals.logger"):
                    mock_milvus_db = AsyncMock()
                    mock_completions_obj = MagicMock()
                    mock_completions_obj.close = AsyncMock()
                    mock_querier_class.load_database_and_collections = AsyncMock(return_value=mock_milvus_db)
                    mock_completions_class.return_value = mock_completions_obj

                    async with milvus_db_lifespan_manager() as db_state:
                        async with completions_lifespan_manager() as comp_state:
                            assert "milvus_db" in db_state
                            assert "completions_obj" in comp_state

                    mock_milvus_db.close.assert_called_once()
                    mock_completions_obj.close.assert_called_once()
