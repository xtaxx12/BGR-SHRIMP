"""
Tests de Edge Cases para Rate Limiting

Según el perfil QA, debemos cubrir:
- Inputs Vacíos
- Valores Límite
- Comportamiento temporal
- Limpieza de entradas antiguas
"""
import time
from unittest.mock import patch

import pytest

from app.security import RateLimiter, rate_limiter


class TestRateLimiterEdgeCases:
    """Tests de edge cases para RateLimiter según perfil QA."""

    # =========================================================================
    # Tests de Límites (Boundary Testing)
    # =========================================================================

    def test_should_allow_exactly_max_requests(self):
        """Debe permitir exactamente max_requests solicitudes."""
        # Arrange
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        identifier = "test_user_limit"

        # Act & Assert - Las primeras 5 deben ser permitidas
        for i in range(5):
            assert limiter.is_allowed(identifier) is True, f"Request {i+1} debería ser permitida"

    def test_should_reject_request_after_max_reached(self):
        """Debe rechazar la solicitud max_requests + 1."""
        # Arrange
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        identifier = "test_user_reject"

        # Act - Consumir todas las solicitudes permitidas
        for _ in range(5):
            limiter.is_allowed(identifier)

        # Assert - La solicitud 6 debe ser rechazada
        assert limiter.is_allowed(identifier) is False, "Request 6 debería ser rechazada"

    def test_should_allow_request_when_window_expires(self):
        """Debe permitir solicitudes después de que expire la ventana de tiempo."""
        # Arrange
        limiter = RateLimiter(max_requests=2, window_seconds=1)  # 1 segundo de ventana
        identifier = "test_user_expire"

        # Act - Consumir todas las solicitudes
        limiter.is_allowed(identifier)
        limiter.is_allowed(identifier)
        assert limiter.is_allowed(identifier) is False  # Debería estar bloqueado

        # Esperar a que expire la ventana
        time.sleep(1.1)

        # Assert - Ahora debería permitir nuevamente
        assert limiter.is_allowed(identifier) is True, "Debería permitir después de expirar ventana"

    # =========================================================================
    # Tests de Inputs Vacíos/Nulos
    # =========================================================================

    def test_should_handle_empty_identifier(self):
        """Debe manejar identificador vacío sin errores."""
        # Arrange
        limiter = RateLimiter(max_requests=5, window_seconds=60)

        # Act & Assert - No debe lanzar excepción
        result = limiter.is_allowed("")
        assert result is True  # Primera solicitud siempre permitida

    def test_should_handle_none_as_string_identifier(self):
        """Debe manejar 'None' como string identificador."""
        # Arrange
        limiter = RateLimiter(max_requests=5, window_seconds=60)

        # Act & Assert
        result = limiter.is_allowed("None")
        assert result is True

    def test_should_handle_whitespace_identifier(self):
        """Debe manejar identificadores con espacios."""
        # Arrange
        limiter = RateLimiter(max_requests=2, window_seconds=60)
        identifier = "   "

        # Act
        limiter.is_allowed(identifier)
        limiter.is_allowed(identifier)

        # Assert - Debe tratarlo como un identificador único
        assert limiter.is_allowed(identifier) is False

    # =========================================================================
    # Tests de Valores Extremos
    # =========================================================================

    def test_should_handle_very_long_identifier(self):
        """Debe manejar identificadores muy largos."""
        # Arrange
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        long_identifier = "x" * 10000  # 10,000 caracteres

        # Act & Assert - No debe fallar
        result = limiter.is_allowed(long_identifier)
        assert result is True

    def test_should_handle_special_characters_in_identifier(self):
        """Debe manejar caracteres especiales en identificador."""
        # Arrange
        limiter = RateLimiter(max_requests=2, window_seconds=60)
        special_ids = [
            "user@example.com",
            "whatsapp:+593999999999",
            "user<script>alert('xss')</script>",
            "user\n\r\t",
            "用户123",  # Caracteres chinos
            "🔥emoji🔥",
        ]

        # Act & Assert - Ninguno debe fallar
        for identifier in special_ids:
            result = limiter.is_allowed(identifier)
            assert result is True, f"Falló con identificador: {identifier}"

    def test_should_handle_zero_max_requests(self):
        """Debe rechazar todas las solicitudes si max_requests es 0."""
        # Arrange
        limiter = RateLimiter(max_requests=0, window_seconds=60)

        # Act & Assert
        result = limiter.is_allowed("any_user")
        assert result is False, "Debería rechazar con max_requests=0"

    def test_should_handle_negative_max_requests(self):
        """Debe rechazar todas las solicitudes si max_requests es negativo."""
        # Arrange
        limiter = RateLimiter(max_requests=-1, window_seconds=60)

        # Act & Assert
        result = limiter.is_allowed("any_user")
        assert result is False, "Debería rechazar con max_requests negativo"

    # =========================================================================
    # Tests de Aislamiento (Isolation)
    # =========================================================================

    def test_should_track_different_identifiers_separately(self):
        """Debe trackear diferentes identificadores por separado."""
        # Arrange
        limiter = RateLimiter(max_requests=2, window_seconds=60)

        # Act - Usuario 1 consume sus solicitudes
        limiter.is_allowed("user1")
        limiter.is_allowed("user1")
        user1_blocked = not limiter.is_allowed("user1")

        # Usuario 2 debe poder hacer solicitudes
        user2_allowed = limiter.is_allowed("user2")

        # Assert
        assert user1_blocked is True, "User1 debería estar bloqueado"
        assert user2_allowed is True, "User2 debería poder hacer solicitudes"

    # =========================================================================
    # Tests de Limpieza (Cleanup)
    # =========================================================================

    def test_cleanup_should_remove_expired_entries(self):
        """cleanup_old_entries debe eliminar entradas expiradas."""
        # Arrange
        limiter = RateLimiter(max_requests=5, window_seconds=1)
        identifier = "test_cleanup"

        # Act - Hacer solicitudes y esperar a que expiren
        limiter.is_allowed(identifier)
        limiter.is_allowed(identifier)
        time.sleep(1.1)

        # Limpiar
        limiter.cleanup_old_entries()

        # Assert - El identificador debería ser eliminado del diccionario
        assert identifier not in limiter.requests, "Identificador expirado debería ser eliminado"

    def test_cleanup_should_keep_active_entries(self):
        """cleanup_old_entries no debe eliminar entradas activas."""
        # Arrange
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        identifier = "test_active"

        # Act
        limiter.is_allowed(identifier)
        limiter.cleanup_old_entries()

        # Assert - El identificador debería seguir existiendo
        assert identifier in limiter.requests, "Identificador activo no debería ser eliminado"

    def test_cleanup_should_partially_clean_entries(self):
        """cleanup_old_entries debe limpiar solo timestamps expirados."""
        # Arrange
        limiter = RateLimiter(max_requests=10, window_seconds=1)
        identifier = "test_partial"

        # Act - Hacer 2 solicitudes
        limiter.is_allowed(identifier)
        limiter.is_allowed(identifier)
        initial_count = len(limiter.requests[identifier])

        # Esperar a que expiren
        time.sleep(1.1)

        # Hacer 1 solicitud más (dentro de nueva ventana)
        limiter.is_allowed(identifier)

        # Limpiar
        limiter.cleanup_old_entries()

        # Assert - Solo debe quedar 1 timestamp (el reciente)
        assert len(limiter.requests[identifier]) == 1, "Solo debería quedar el timestamp reciente"

    # =========================================================================
    # Tests de Concurrencia Básica
    # =========================================================================

    def test_should_handle_rapid_requests(self):
        """Debe manejar solicitudes rápidas consecutivas."""
        # Arrange
        limiter = RateLimiter(max_requests=100, window_seconds=60)
        identifier = "rapid_user"

        # Act - Hacer 100 solicitudes rápidas
        allowed_count = sum(1 for _ in range(100) if limiter.is_allowed(identifier))

        # Assert
        assert allowed_count == 100, f"Debería permitir 100, permitió {allowed_count}"

        # La siguiente debe ser rechazada
        assert limiter.is_allowed(identifier) is False

    # =========================================================================
    # Tests del Rate Limiter Global
    # =========================================================================

    def test_global_rate_limiter_should_be_initialized(self):
        """El rate_limiter global debe estar inicializado correctamente."""
        # Assert
        assert rate_limiter is not None
        assert rate_limiter.max_requests == 30
        assert rate_limiter.window_seconds == 60


class TestRateLimiterDecorator:
    """Tests para el decorador @rate_limit."""

    @pytest.mark.asyncio
    async def test_rate_limit_decorator_should_block_after_limit(self):
        """El decorador debe bloquear después del límite."""
        from fastapi import HTTPException, Request
        from unittest.mock import AsyncMock, MagicMock

        from app.security import rate_limit

        # Arrange - Crear un rate limiter que bloquee inmediatamente
        @rate_limit()
        async def dummy_endpoint(request: Request):
            return {"status": "ok"}

        # Crear mock request
        mock_request = MagicMock(spec=Request)
        mock_request.client = MagicMock()
        mock_request.client.host = "192.168.1.1"

        # Act - Llamar muchas veces hasta bloquear
        with patch('app.security.rate_limiter') as mock_limiter:
            mock_limiter.is_allowed.return_value = False

            # Assert - Debe lanzar HTTPException 429
            with pytest.raises(HTTPException) as exc_info:
                await dummy_endpoint(mock_request)

            assert exc_info.value.status_code == 429


# Ejecutar tests con: pytest tests/unit/test_rate_limiter_edge_cases.py -v
