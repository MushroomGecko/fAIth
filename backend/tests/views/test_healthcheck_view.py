from unittest.mock import patch, MagicMock
import json
import asyncio
from django.test import SimpleTestCase, RequestFactory
from rest_framework import status

from backend.views.healthcheck import healthcheck


class TestHealthcheckView(SimpleTestCase):
    """Tests for healthcheck endpoint."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.factory = RequestFactory()
    
    def _call_healthcheck(self, request):
        """Helper to call async healthcheck function."""
        return asyncio.run(healthcheck(request))

    def test_healthcheck_with_get_request(self):
        """Test that healthcheck responds to GET requests."""
        request = self.factory.get('/healthcheck/')
        
        with patch('backend.views.healthcheck.connection') as mock_connection:
            mock_cursor = MagicMock()
            mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
            mock_connection.cursor.return_value.__exit__.return_value = None
            
            response = self._call_healthcheck(request)
            
            # Verify request method is GET
            assert request.method == 'GET'
            # Verify response was generated successfully
            assert response.status_code == status.HTTP_200_OK

    def test_healthcheck_success_database_connected(self):
        """Test that healthcheck returns 200 OK when database is connected."""
        request = self.factory.get('/healthcheck/')
        
        with patch('backend.views.healthcheck.connection') as mock_connection:
            mock_cursor = MagicMock()
            mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
            mock_connection.cursor.return_value.__exit__.return_value = None
            
            response = self._call_healthcheck(request)
            
            # Verify successful response
            assert response.status_code == status.HTTP_200_OK
            assert json.loads(response.content)['status'] == 'OK'
    
    def test_healthcheck_database_query_executed(self):
        """Test that healthcheck executes the database query correctly."""
        request = self.factory.get('/healthcheck/')
        
        with patch('backend.views.healthcheck.connection') as mock_connection:
            mock_cursor = MagicMock()
            mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
            mock_connection.cursor.return_value.__exit__.return_value = None
            
            self._call_healthcheck(request)
            
            # Verify the specific query was executed
            assert mock_cursor.execute.called
            assert mock_cursor.execute.call_count == 1
            assert mock_cursor.execute.call_args[0][0] == "SELECT 1"
    
    def test_healthcheck_failure_database_disconnected(self):
        """Test that healthcheck returns 503 when database is not connected."""
        request = self.factory.get('/healthcheck/')
        
        error_message = "connection refused"
        with patch('backend.views.healthcheck.connection') as mock_connection:
            mock_connection.cursor.side_effect = Exception(error_message)
            
            response = self._call_healthcheck(request)
            
            # Verify error response
            assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
            data = json.loads(response.content)
            assert data['status'] == 'error'
            assert error_message in data['message']
    
    def test_healthcheck_failure_database_timeout(self):
        """Test that healthcheck returns 503 on database timeout."""
        request = self.factory.get('/healthcheck/')
        
        error_message = "database connection timeout"
        with patch('backend.views.healthcheck.connection') as mock_connection:
            mock_connection.cursor.return_value.__enter__.side_effect = TimeoutError(error_message)
            
            response = self._call_healthcheck(request)
            
            # Verify error response
            assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
            data = json.loads(response.content)
            assert data['status'] == 'error'
            assert error_message in data['message']
    
    def test_healthcheck_returns_json_response(self):
        """Test that healthcheck returns proper JSON response."""
        request = self.factory.get('/healthcheck/')
        
        with patch('backend.views.healthcheck.connection') as mock_connection:
            mock_cursor = MagicMock()
            mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
            mock_connection.cursor.return_value.__exit__.return_value = None
            
            response = self._call_healthcheck(request)
            
            # Verify response has required fields
            data = json.loads(response.content)
            assert 'status' in data
            assert isinstance(data, dict)
    
    def test_healthcheck_error_response_includes_message(self):
        """Test that error response includes error message."""
        request = self.factory.get('/healthcheck/')
        
        error_message = "permission denied"
        with patch('backend.views.healthcheck.connection') as mock_connection:
            mock_connection.cursor.side_effect = PermissionError(error_message)
            
            response = self._call_healthcheck(request)
            
            # Verify error response includes message
            assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
            data = json.loads(response.content)
            assert 'message' in data
            assert error_message in data['message']
    
    def test_healthcheck_handles_generic_exception(self):
        """Test that healthcheck handles any exception gracefully."""
        request = self.factory.get('/healthcheck/')
        
        error_message = "Unexpected error occurred"
        with patch('backend.views.healthcheck.connection') as mock_connection:
            mock_connection.cursor.side_effect = Exception(error_message)
            
            response = self._call_healthcheck(request)
            
            # Verify error response
            assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
            data = json.loads(response.content)
            assert data['status'] == 'error'
    
    def test_healthcheck_uses_context_manager(self):
        """Test that healthcheck properly uses cursor context manager."""
        request = self.factory.get('/healthcheck/')
        
        with patch('backend.views.healthcheck.connection') as mock_connection:
            mock_cursor = MagicMock()
            mock_context_manager = MagicMock()
            mock_context_manager.__enter__ = MagicMock(return_value=mock_cursor)
            mock_context_manager.__exit__ = MagicMock(return_value=None)
            mock_connection.cursor.return_value = mock_context_manager
            
            self._call_healthcheck(request)
            
            # Verify context manager was used
            assert mock_context_manager.__enter__.called
            assert mock_context_manager.__enter__.call_count == 1
            assert mock_context_manager.__exit__.called
            assert mock_context_manager.__exit__.call_count == 1
    
    def test_healthcheck_logging_on_error(self):
        """Test that healthcheck logs errors."""
        request = self.factory.get('/healthcheck/')
        
        error_message = "Unexpected error occurred"
        with patch('backend.views.healthcheck.connection') as mock_connection, patch('backend.views.healthcheck.logger') as mock_logger:
            mock_connection.cursor.side_effect = Exception(error_message)
            
            self._call_healthcheck(request)
            
            # Verify error was logged
            assert mock_logger.error.called
            assert mock_logger.error.call_count == 1
            assert error_message in str(mock_logger.error.call_args)
    
    def test_healthcheck_multiple_sequential_requests(self):
        """Test that multiple healthcheck requests work correctly."""
        with patch('backend.views.healthcheck.connection') as mock_connection:
            mock_cursor = MagicMock()
            mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
            mock_connection.cursor.return_value.__exit__.return_value = None
            
            # Make multiple requests
            request1 = self.factory.get('/healthcheck/')
            response1 = self._call_healthcheck(request1)
            
            request2 = self.factory.get('/healthcheck/')
            response2 = self._call_healthcheck(request2)
            
            # Verify both requests succeeded
            assert response1.status_code == status.HTTP_200_OK
            assert response2.status_code == status.HTTP_200_OK
            
            # Verify database was queried twice
            assert mock_cursor.execute.call_count == 2
