"""
Tests unitarios para app/security.py

Cubre:
- validate_phone_number() con diferentes formatos
- sanitize_input() con caracteres especiales y límites
- verify_admin_token() con tokens válidos e inválidos
- rate_limit decorator con casos de límite
- SecureTempFile context manager
- RateLimiter clase con cleanup
- TwilioWebhookValidator
- validate_twilio_webhook decorator
- add_security_headers
"""
import os
import time
import tempfile
from unittest.mock import MagicMock, Mock, patch, AsyncMock
from collections import defaultdict

import pytest
from fastapi import HTTPException, Request, Response
from fastapi.security import HTTPAuthorizationCredentials

from app.security import (
    RateLimiter,
    TwilioWebhookValidator,
    validate_phone_number,
    sanitize_input,
    verify_admin_token,
    rate_limit,
    SecureTempFile,
    add_security_headers,
    validate_twilio_webhook,
    rate_limiter,
    webhook_validator
)


class TestValidatePhoneNumber:
    """Tests para validate_phone_number()"""

    def test_valid_phone_number(self):
        """Test número de teléfono válido"""
        assert validate_phone_number("whatsapp:+593981234567") is True
        assert validate_phone_number("whatsapp:+14155238886") is True
        assert validate_phone_number("whatsapp:+5215512345678") is True

    def test_valid_phone_number_min_length(self):
        """Test número con longitud mínima (7 dígitos)"""
        assert validate_phone_number("whatsapp:+1234567") is True

    def test_valid_phone_number_max_length(self):
        """Test número con longitud máxima (15 dígitos)"""
        assert validate_phone_number("whatsapp:+123456789012345") is True

    def test_invalid_prefix(self):
        """Test número sin prefijo whatsapp:+"""
        assert validate_phone_number("+593981234567") is False
        assert validate_phone_number("593981234567") is False
        assert validate_phone_number("whatsapp:593981234567") is False

    def test_invalid_non_digit_characters(self):
        """Test número con caracteres no numéricos"""
        assert validate_phone_number("whatsapp:+593-981-234-567") is False
        assert validate_phone_number("whatsapp:+593 981 234 567") is False
        assert validate_phone_number("whatsapp:+593abc1234567") is False
        assert validate_phone_number("whatsapp:+(593)981234567") is False

    def test_invalid_too_short(self):
        """Test número demasiado corto"""
        assert validate_phone_number("whatsapp:+123456") is False
        assert validate_phone_number("whatsapp:+1") is False

    def test_invalid_too_long(self):
        """Test número demasiado largo"""
        assert validate_phone_number("whatsapp:+1234567890123456") is False

    def test_empty_string(self):
        """Test string vacío"""
        assert validate_phone_number("") is False

    def test_invalid_format_variations(self):
        """Test variaciones de formatos inválidos"""
        assert validate_phone_number("whatsapp:+") is False
        assert validate_phone_number("whatsapp:") is False
        assert validate_phone_number("tel:+593981234567") is False


class TestSanitizeInput:
    """Tests para sanitize_input()"""

    def test_normal_text(self):
        """Test texto normal sin caracteres especiales"""
        assert sanitize_input("Hola mundo") == "Hola mundo"
        assert sanitize_input("Test 123") == "Test 123"

    def test_unicode_characters(self):
        """Test caracteres Unicode (español, emojis)"""
        result = sanitize_input("Hola ¿cómo estás?")
        assert "Hola" in result
        assert "cómo" in result

    def test_allowed_whitespace(self):
        """Test espacios, tabs y saltos de línea permitidos"""
        text = "Line 1\nLine 2\tTabbed\rCarriage"
        result = sanitize_input(text)
        assert "Line 1" in result
        assert "Line 2" in result

    def test_max_length_truncation(self):
        """Test que trunca al máximo de caracteres"""
        long_text = "a" * 2000
        result = sanitize_input(long_text, max_length=1000)
        assert len(result) == 1000

    def test_default_max_length(self):
        """Test límite por defecto de 1000 caracteres"""
        long_text = "b" * 1500
        result = sanitize_input(long_text)
        assert len(result) == 1000

    def test_control_characters_removed(self):
        """Test que remueve caracteres de control"""
        text = "Hello\x00World\x01Test\x1F"
        result = sanitize_input(text)
        assert result == "HelloWorldTest"

    def test_strip_whitespace(self):
        """Test que hace strip de espacios al inicio/final"""
        assert sanitize_input("  texto  ") == "texto"
        assert sanitize_input("\n\ntext\n\n") == "text"

    def test_empty_string(self):
        """Test string vacío"""
        assert sanitize_input("") == ""

    def test_none_input(self):
        """Test None como entrada"""
        assert sanitize_input(None) == ""

    def test_only_control_characters(self):
        """Test string solo con caracteres de control"""
        result = sanitize_input("\x00\x01\x02\x03")
        assert result == ""

    def test_mixed_valid_invalid(self):
        """Test mezcla de caracteres válidos e inválidos"""
        text = "Valid\x00Invalid\x01Mix"
        result = sanitize_input(text)
        assert result == "ValidInvalidMix"


class TestVerifyAdminToken:
    """Tests para verify_admin_token()"""

    def test_valid_token(self):
        """Test token válido"""
        with patch.dict(os.environ, {"ADMIN_API_TOKEN": "secret_token_123"}):
            credentials = HTTPAuthorizationCredentials(
                scheme="Bearer",
                credentials="secret_token_123"
            )
            assert verify_admin_token(credentials) is True

    def test_invalid_token(self):
        """Test token inválido"""
        with patch.dict(os.environ, {"ADMIN_API_TOKEN": "secret_token_123"}):
            credentials = HTTPAuthorizationCredentials(
                scheme="Bearer",
                credentials="wrong_token"
            )
            assert verify_admin_token(credentials) is False

    def test_empty_token(self):
        """Test token vacío"""
        with patch.dict(os.environ, {"ADMIN_API_TOKEN": "secret_token_123"}):
            credentials = HTTPAuthorizationCredentials(
                scheme="Bearer",
                credentials=""
            )
            assert verify_admin_token(credentials) is False

    def test_missing_env_token(self):
        """Test cuando no está configurado ADMIN_API_TOKEN"""
        with patch.dict(os.environ, {}, clear=True):
            credentials = HTTPAuthorizationCredentials(
                scheme="Bearer",
                credentials="any_token"
            )
            assert verify_admin_token(credentials) is False

    def test_timing_attack_resistance(self):
        """Test que usa comparación segura (secrets.compare_digest)"""
        with patch.dict(os.environ, {"ADMIN_API_TOKEN": "secret"}):
            # Debe usar secrets.compare_digest para prevenir timing attacks
            import secrets
            with patch('secrets.compare_digest', return_value=True) as mock_compare:
                credentials = HTTPAuthorizationCredentials(
                    scheme="Bearer",
                    credentials="secret"
                )
                verify_admin_token(credentials)
                mock_compare.assert_called_once()


class TestRateLimiter:
    """Tests para la clase RateLimiter"""

    def test_allows_requests_within_limit(self):
        """Test que permite requests dentro del límite"""
        limiter = RateLimiter(max_requests=3, window_seconds=60)

        assert limiter.is_allowed("user1") is True
        assert limiter.is_allowed("user1") is True
        assert limiter.is_allowed("user1") is True

    def test_blocks_requests_exceeding_limit(self):
        """Test que bloquea requests que exceden el límite"""
        limiter = RateLimiter(max_requests=3, window_seconds=60)

        limiter.is_allowed("user1")
        limiter.is_allowed("user1")
        limiter.is_allowed("user1")

        # Cuarto request debe ser bloqueado
        assert limiter.is_allowed("user1") is False

    def test_different_identifiers_independent(self):
        """Test que diferentes identificadores son independientes"""
        limiter = RateLimiter(max_requests=2, window_seconds=60)

        assert limiter.is_allowed("user1") is True
        assert limiter.is_allowed("user1") is True
        assert limiter.is_allowed("user1") is False  # user1 bloqueado

        # user2 debe tener su propio límite
        assert limiter.is_allowed("user2") is True
        assert limiter.is_allowed("user2") is True

    def test_requests_expire_after_window(self):
        """Test que los requests expiran después de la ventana"""
        limiter = RateLimiter(max_requests=2, window_seconds=1)

        assert limiter.is_allowed("user1") is True
        assert limiter.is_allowed("user1") is True
        assert limiter.is_allowed("user1") is False  # Bloqueado

        # Esperar que expire la ventana
        time.sleep(1.1)

        # Ahora debe permitir nuevamente
        assert limiter.is_allowed("user1") is True

    def test_cleanup_old_entries(self):
        """Test limpieza de entradas antiguas"""
        limiter = RateLimiter(max_requests=5, window_seconds=1)

        # Crear algunas entradas
        limiter.is_allowed("user1")
        limiter.is_allowed("user2")
        limiter.is_allowed("user3")

        # Esperar que expiren
        time.sleep(1.1)

        # Limpiar
        limiter.cleanup_old_entries()

        # Las entradas deben haberse eliminado
        assert len(limiter.requests) == 0

    def test_cleanup_preserves_recent_entries(self):
        """Test que cleanup preserva entradas recientes"""
        limiter = RateLimiter(max_requests=5, window_seconds=60)

        limiter.is_allowed("user1")
        limiter.cleanup_old_entries()

        # La entrada reciente debe permanecer
        assert "user1" in limiter.requests


class TestRateLimitDecorator:
    """Tests para el decorador rate_limit"""

    @pytest.mark.asyncio
    async def test_allows_request_within_limit(self):
        """Test que permite requests dentro del límite"""
        # Mock request
        mock_request = Mock(spec=Request)
        mock_request.client = Mock()
        mock_request.client.host = "192.168.1.1"

        # Función decorada
        @rate_limit()
        async def test_endpoint(request: Request):
            return {"status": "ok"}

        # Crear un nuevo rate limiter para este test
        with patch('app.security.rate_limiter') as mock_limiter:
            mock_limiter.is_allowed.return_value = True

            result = await test_endpoint(mock_request)
            assert result == {"status": "ok"}

    @pytest.mark.asyncio
    async def test_blocks_request_exceeding_limit(self):
        """Test que bloquea requests que exceden el límite"""
        mock_request = Mock(spec=Request)
        mock_request.client = Mock()
        mock_request.client.host = "192.168.1.1"

        @rate_limit()
        async def test_endpoint(request: Request):
            return {"status": "ok"}

        with patch('app.security.rate_limiter') as mock_limiter:
            mock_limiter.is_allowed.return_value = False

            with pytest.raises(HTTPException) as exc_info:
                await test_endpoint(mock_request)

            assert exc_info.value.status_code == 429
            assert "Too many requests" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_custom_identifier_function(self):
        """Test con función personalizada de identificación"""
        mock_request = Mock(spec=Request)

        def custom_identifier(request, *args, **kwargs):
            return "custom_id_123"

        @rate_limit(identifier_func=custom_identifier)
        async def test_endpoint(request: Request):
            return {"status": "ok"}

        with patch('app.security.rate_limiter') as mock_limiter:
            mock_limiter.is_allowed.return_value = True

            await test_endpoint(mock_request)
            mock_limiter.is_allowed.assert_called_once_with("custom_id_123")

    @pytest.mark.asyncio
    async def test_handles_missing_client(self):
        """Test manejo cuando request.client es None"""
        mock_request = Mock(spec=Request)
        mock_request.client = None

        @rate_limit()
        async def test_endpoint(request: Request):
            return {"status": "ok"}

        with patch('app.security.rate_limiter') as mock_limiter:
            mock_limiter.is_allowed.return_value = True

            await test_endpoint(mock_request)
            # Debe usar "unknown" como identifier
            mock_limiter.is_allowed.assert_called_once_with("unknown")

    @pytest.mark.asyncio
    async def test_cleanup_triggered_randomly(self):
        """Test que cleanup se activa aleatoriamente"""
        mock_request = Mock(spec=Request)
        mock_request.client = Mock()
        mock_request.client.host = "192.168.1.1"

        @rate_limit()
        async def test_endpoint(request: Request):
            return {"status": "ok"}

        with patch('app.security.rate_limiter') as mock_limiter:
            mock_limiter.is_allowed.return_value = True

            # Forzar que randbelow retorne 0 (dispara cleanup)
            with patch('secrets.randbelow', return_value=0):
                await test_endpoint(mock_request)
                mock_limiter.cleanup_old_entries.assert_called_once()


class TestSecureTempFile:
    """Tests para SecureTempFile context manager"""

    def test_creates_temp_file(self):
        """Test que crea archivo temporal"""
        with SecureTempFile() as temp_path:
            assert temp_path is not None
            assert os.path.exists(temp_path)

    def test_deletes_temp_file_on_exit(self):
        """Test que elimina archivo al salir del contexto"""
        temp_path = None
        with SecureTempFile() as path:
            temp_path = path
            assert os.path.exists(temp_path)

        # Debe haberse eliminado
        assert not os.path.exists(temp_path)

    def test_custom_suffix(self):
        """Test con sufijo personalizado"""
        with SecureTempFile(suffix=".pdf") as temp_path:
            assert temp_path.endswith(".pdf")
            assert os.path.exists(temp_path)

    def test_deletes_file_even_on_exception(self):
        """Test que elimina archivo incluso si hay excepción"""
        temp_path = None
        try:
            with SecureTempFile() as path:
                temp_path = path
                raise ValueError("Test error")
        except ValueError:
            pass

        # Debe haberse eliminado de todas formas
        assert not os.path.exists(temp_path)

    def test_handles_already_deleted_file(self):
        """Test que maneja archivo ya eliminado"""
        with SecureTempFile() as temp_path:
            # Eliminar manualmente
            os.unlink(temp_path)
        # No debe lanzar error

    def test_creates_writable_file(self):
        """Test que el archivo es escribible"""
        with SecureTempFile(suffix=".txt") as temp_path:
            with open(temp_path, 'w') as f:
                f.write("test content")

            with open(temp_path, 'r') as f:
                content = f.read()

            assert content == "test content"


class TestTwilioWebhookValidator:
    """Tests para TwilioWebhookValidator"""

    def test_valid_signature(self):
        """Test validación de firma válida"""
        auth_token = "test_token_123"
        validator = TwilioWebhookValidator(auth_token)

        # Simular datos reales
        url = "https://example.com/webhook"
        params = {"From": "whatsapp:+123", "Body": "Hello"}

        # Generar firma válida
        import base64
        import hashlib
        import hmac

        data = url + "Body" + "Hello" + "From" + "whatsapp:+123"
        expected_signature = base64.b64encode(
            hmac.new(
                auth_token.encode('utf-8'),
                data.encode('utf-8'),
                hashlib.sha1
            ).digest()
        ).decode()

        assert validator.validate_request(url, params, expected_signature) is True

    def test_invalid_signature(self):
        """Test firma inválida"""
        validator = TwilioWebhookValidator("test_token")

        url = "https://example.com/webhook"
        params = {"From": "whatsapp:+123", "Body": "Hello"}
        invalid_signature = "invalid_signature_xyz"

        assert validator.validate_request(url, params, invalid_signature) is False

    def test_empty_signature(self):
        """Test firma vacía"""
        validator = TwilioWebhookValidator("test_token")

        url = "https://example.com/webhook"
        params = {"From": "whatsapp:+123"}

        assert validator.validate_request(url, params, "") is False

    def test_params_sorted_alphabetically(self):
        """Test que los parámetros se ordenan alfabéticamente"""
        auth_token = "test_token"
        validator = TwilioWebhookValidator(auth_token)

        url = "https://example.com/webhook"
        # Parámetros en orden no alfabético
        params = {"Zebra": "z", "Apple": "a", "Mango": "m"}

        # Generar firma con orden correcto
        import base64
        import hashlib
        import hmac

        data = url + "Apple" + "a" + "Mango" + "m" + "Zebra" + "z"
        expected_signature = base64.b64encode(
            hmac.new(
                auth_token.encode('utf-8'),
                data.encode('utf-8'),
                hashlib.sha1
            ).digest()
        ).decode()

        assert validator.validate_request(url, params, expected_signature) is True


class TestValidateTwilioWebhookDecorator:
    """Tests para el decorador validate_twilio_webhook"""

    @pytest.mark.asyncio
    async def test_skips_validation_in_non_production(self):
        """Test que omite validación en ambiente no producción"""
        mock_request = AsyncMock(spec=Request)

        @validate_twilio_webhook
        async def test_endpoint():
            return {"status": "ok"}

        with patch('app.security.settings') as mock_settings:
            mock_settings.is_production = False

            result = await test_endpoint(mock_request)
            assert result == {"status": "ok"}

    @pytest.mark.asyncio
    async def test_validates_in_production(self):
        """Test que valida en producción"""
        mock_request = AsyncMock(spec=Request)
        mock_request.url = "https://example.com/webhook"
        mock_request.headers = {"X-Twilio-Signature": "valid_signature"}
        mock_request.form = AsyncMock(return_value={"Body": "test"})

        @validate_twilio_webhook
        async def test_endpoint():
            return {"status": "ok"}

        with patch('app.security.settings') as mock_settings:
            mock_settings.is_production = True
            mock_settings.TWILIO_AUTH_TOKEN = "test_token"

            with patch('app.security.webhook_validator') as mock_validator:
                mock_validator.validate_request.return_value = True

                result = await test_endpoint(mock_request)
                assert result == {"status": "ok"}

    @pytest.mark.asyncio
    async def test_raises_403_on_invalid_signature(self):
        """Test que lanza 403 con firma inválida"""
        mock_request = AsyncMock(spec=Request)
        mock_request.url = "https://example.com/webhook"
        mock_request.headers = {"X-Twilio-Signature": "invalid"}
        mock_request.form = AsyncMock(return_value={"Body": "test"})
        mock_request.client = Mock()
        mock_request.client.host = "192.168.1.1"

        @validate_twilio_webhook
        async def test_endpoint():
            return {"status": "ok"}

        with patch('app.security.settings') as mock_settings:
            mock_settings.is_production = True
            mock_settings.TWILIO_AUTH_TOKEN = "test_token"

            with patch('app.security.webhook_validator') as mock_validator:
                mock_validator.validate_request.return_value = False

                with pytest.raises(HTTPException) as exc_info:
                    await test_endpoint(mock_request)

                assert exc_info.value.status_code == 403
                assert "Invalid signature" in exc_info.value.detail


class TestAddSecurityHeaders:
    """Tests para add_security_headers"""

    def test_adds_all_security_headers(self):
        """Test que agrega todos los headers de seguridad"""
        response = Response()

        result = add_security_headers(response)

        assert result.headers["X-Content-Type-Options"] == "nosniff"
        assert result.headers["X-Frame-Options"] == "DENY"
        assert result.headers["X-XSS-Protection"] == "1; mode=block"
        assert "Strict-Transport-Security" in result.headers
        assert "max-age=31536000" in result.headers["Strict-Transport-Security"]
        assert result.headers["Content-Security-Policy"] == "default-src 'self'"

    def test_returns_same_response_object(self):
        """Test que retorna el mismo objeto de respuesta"""
        response = Response()
        result = add_security_headers(response)

        assert result is response

    def test_headers_on_response_with_content(self):
        """Test headers en respuesta con contenido"""
        response = Response(content="test content", media_type="text/plain")

        result = add_security_headers(response)

        assert result.headers["X-Content-Type-Options"] == "nosniff"
        assert result.body == b"test content"


class TestGlobalInstances:
    """Tests para las instancias globales"""

    def test_rate_limiter_instance_exists(self):
        """Test que existe instancia global de rate_limiter"""
        assert rate_limiter is not None
        assert isinstance(rate_limiter, RateLimiter)
        assert rate_limiter.max_requests == 30
        assert rate_limiter.window_seconds == 60

    def test_webhook_validator_instance_exists(self):
        """Test que existe instancia global de webhook_validator"""
        assert webhook_validator is not None
        assert isinstance(webhook_validator, TwilioWebhookValidator)