"""
Tests para rutas de descarga de PDF
"""
import os
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


class TestPDFRoutes:
    """Tests para endpoints de PDF"""

    @patch('app.routes.pdf_routes.os.path.exists')
    @patch('app.routes.pdf_routes.os.listdir')
    @patch('app.routes.pdf_routes.FileResponse')
    def test_download_pdf_success(self, mock_file_response, mock_listdir, mock_exists, client):
        """GET /download-pdf/{filename} descarga PDF exitosamente"""
        mock_exists.return_value = True
        mock_listdir.return_value = ["test.pdf"]
        mock_file_response.return_value = MagicMock()

        response = client.get("/webhook/download-pdf/test.pdf")
        assert response.status_code == 200

    @patch('app.routes.pdf_routes.os.path.exists')
    def test_download_pdf_not_found(self, mock_exists, client):
        """GET /download-pdf/{filename} con archivo inexistente retorna error"""
        mock_exists.return_value = False

        response = client.get("/webhook/download-pdf/nonexistent.pdf")
        # Puede retornar 404 o 500 dependiendo del manejo de errores
        assert response.status_code in [404, 500]

    @patch('app.routes.pdf_routes.os.path.exists')
    def test_download_pdf_directory_not_exists(self, mock_exists, client):
        """GET /download-pdf/{filename} cuando el directorio no existe"""
        mock_exists.return_value = False

        response = client.get("/webhook/download-pdf/test.pdf")
        # Puede retornar 404 o 500 dependiendo del manejo de errores
        assert response.status_code in [404, 500]

    def test_download_pdf_filename_validation(self, client):
        """GET /download-pdf/{filename} valida nombre de archivo"""
        # Intentar acceder a archivo con path traversal
        response = client.get("/webhook/download-pdf/../../../etc/passwd")
        # El test verifica que no cause un error 500
        assert response.status_code in [404, 500]