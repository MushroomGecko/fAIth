"""Tests for the lifespan managers used in Django's lifespan event system."""

from unittest.mock import AsyncMock, patch

import pytest

from ai.lifespan_manager import milvus_db_lifespan_manager, completions_lifespan_manager


class TestMilvusDbLifespanManager:
    """Test suite for the Milvus database lifespan manager."""

    @pytest.mark.asyncio
    async def test_milvus_db_lifespan_yields_state(self):
        """Lifespan manager should yield a state dict with milvus_db key."""
        with patch("ai.lifespan_manager.VectorDatabaseQuerier") as mock_vdb_class:
            mock_vdb_instance = AsyncMock()
            mock_vdb_class.load_database_and_collections = AsyncMock(return_value=mock_vdb_instance)

            async with milvus_db_lifespan_manager() as state:
                assert isinstance(state, dict)
                assert "milvus_db" in state
                assert state["milvus_db"] is mock_vdb_instance

    @pytest.mark.asyncio
    async def test_milvus_db_lifespan_closes_connection(self):
        """Lifespan manager should call close on the database instance during cleanup."""
        with patch("ai.lifespan_manager.VectorDatabaseQuerier") as mock_vdb_class:
            mock_vdb_instance = AsyncMock()
            mock_vdb_class.load_database_and_collections = AsyncMock(return_value=mock_vdb_instance)

            async with milvus_db_lifespan_manager():
                pass

            mock_vdb_instance.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_milvus_db_lifespan_logs_initialization(self):
        """Lifespan manager should log initialization message."""
        with patch("ai.lifespan_manager.VectorDatabaseQuerier") as mock_vdb_class, \
             patch("ai.lifespan_manager.logger") as mock_logger:
            mock_vdb_instance = AsyncMock()
            mock_vdb_class.load_database_and_collections = AsyncMock(return_value=mock_vdb_instance)

            async with milvus_db_lifespan_manager():
                pass

            mock_logger.info.assert_any_call("Initializing Async Milvus database lifecycle manager")

    @pytest.mark.asyncio
    async def test_milvus_db_lifespan_logs_shutdown(self):
        """Lifespan manager should log shutdown message."""
        with patch("ai.lifespan_manager.VectorDatabaseQuerier") as mock_vdb_class, \
             patch("ai.lifespan_manager.logger") as mock_logger:
            mock_vdb_instance = AsyncMock()
            mock_vdb_class.load_database_and_collections = AsyncMock(return_value=mock_vdb_instance)

            async with milvus_db_lifespan_manager():
                pass

            mock_logger.info.assert_any_call("Closing Async Milvus database")

    @pytest.mark.asyncio
    async def test_milvus_db_lifespan_handles_close_error(self):
        """Lifespan manager should catch and log errors during close."""
        with patch("ai.lifespan_manager.VectorDatabaseQuerier") as mock_vdb_class, \
             patch("ai.lifespan_manager.logger") as mock_logger:
            mock_vdb_instance = AsyncMock()
            mock_vdb_instance.close.side_effect = RuntimeError("Close error")
            mock_vdb_class.load_database_and_collections = AsyncMock(return_value=mock_vdb_instance)

            async with milvus_db_lifespan_manager():
                pass

            mock_logger.error.assert_called()
            assert "Error closing Async Milvus database" in mock_logger.error.call_args[0][0]

    @pytest.mark.asyncio
    async def test_milvus_db_lifespan_closes_on_exception(self):
        """Lifespan manager should close database even when exception occurs during yield."""
        with patch("ai.lifespan_manager.VectorDatabaseQuerier") as mock_vdb_class:
            mock_vdb_instance = AsyncMock()
            mock_vdb_class.load_database_and_collections = AsyncMock(return_value=mock_vdb_instance)

            try:
                async with milvus_db_lifespan_manager():
                    raise ValueError("Test error during yield")
            except ValueError:
                pass

            mock_vdb_instance.close.assert_called_once()

class TestCompletionsLifespanManager:
    """Test suite for the LLM Completions lifespan manager."""

    @pytest.mark.asyncio
    async def test_completions_lifespan_yields_state(self):
        """Lifespan manager should yield a state dict with completions_obj key."""
        with patch("ai.lifespan_manager.Completions") as mock_completions_class:
            mock_completions_instance = AsyncMock()
            mock_completions_class.return_value = mock_completions_instance

            async with completions_lifespan_manager() as state:
                assert isinstance(state, dict)
                assert "completions_obj" in state
                assert state["completions_obj"] is mock_completions_instance

    @pytest.mark.asyncio
    async def test_completions_lifespan_closes_connection(self):
        """Lifespan manager should call close on the completions object during cleanup."""
        with patch("ai.lifespan_manager.Completions") as mock_completions_class:
            mock_completions_instance = AsyncMock()
            mock_completions_class.return_value = mock_completions_instance

            async with completions_lifespan_manager():
                pass

            mock_completions_instance.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_completions_lifespan_logs_initialization(self):
        """Lifespan manager should log initialization message."""
        with patch("ai.lifespan_manager.Completions") as mock_completions_class, \
             patch("ai.lifespan_manager.logger") as mock_logger:
            mock_completions_instance = AsyncMock()
            mock_completions_class.return_value = mock_completions_instance

            async with completions_lifespan_manager():
                pass

            mock_logger.info.assert_any_call("Initializing Completions object lifecycle manager")

    @pytest.mark.asyncio
    async def test_completions_lifespan_logs_shutdown(self):
        """Lifespan manager should log shutdown message."""
        with patch("ai.lifespan_manager.Completions") as mock_completions_class, \
             patch("ai.lifespan_manager.logger") as mock_logger:
            mock_completions_instance = AsyncMock()
            mock_completions_class.return_value = mock_completions_instance

            async with completions_lifespan_manager():
                pass

            mock_logger.info.assert_any_call("Closing Completions object")

    @pytest.mark.asyncio
    async def test_completions_lifespan_handles_close_error(self):
        """Lifespan manager should catch and log errors during close."""
        with patch("ai.lifespan_manager.Completions") as mock_completions_class, \
             patch("ai.lifespan_manager.logger") as mock_logger:
            mock_completions_instance = AsyncMock()
            mock_completions_instance.close.side_effect = RuntimeError("Close error")
            mock_completions_class.return_value = mock_completions_instance

            async with completions_lifespan_manager():
                pass

            mock_logger.error.assert_called()
            assert "Error closing Completions object" in mock_logger.error.call_args[0][0]

    @pytest.mark.asyncio
    async def test_completions_lifespan_closes_on_exception(self):
        """Lifespan manager should close completions even when exception occurs during yield."""
        with patch("ai.lifespan_manager.Completions") as mock_completions_class:
            mock_completions_instance = AsyncMock()
            mock_completions_class.return_value = mock_completions_instance

            try:
                async with completions_lifespan_manager():
                    raise RuntimeError("Test error during yield")
            except RuntimeError:
                pass

            mock_completions_instance.close.assert_called_once()


class TestLifespanManagerIntegration:
    """Integration tests for both lifespan managers working together."""

    @pytest.mark.asyncio
    async def test_both_managers_initialize_and_close(self):
        """Test that both managers can be used together and properly close."""
        with patch("ai.lifespan_manager.VectorDatabaseQuerier") as mock_vdb_class, \
             patch("ai.lifespan_manager.Completions") as mock_completions_class:
            mock_vdb_instance = AsyncMock()
            mock_completions_instance = AsyncMock()
            mock_vdb_class.load_database_and_collections = AsyncMock(return_value=mock_vdb_instance)
            mock_completions_class.return_value = mock_completions_instance

            async with milvus_db_lifespan_manager() as db_state:
                async with completions_lifespan_manager() as comp_state:
                    assert "milvus_db" in db_state
                    assert "completions_obj" in comp_state

            mock_vdb_instance.close.assert_called_once()
            mock_completions_instance.close.assert_called_once()
