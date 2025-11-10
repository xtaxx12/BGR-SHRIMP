"""
Tests unitarios para app/services/utils_new.py

Cubre:
- retry() función con diferentes escenarios:
  - Éxitos en primer intento
  - Éxitos después de reintentos
  - Fallos después de todos los reintentos
  - Diferentes tipos de excepciones
  - Parámetros personalizados (retries, delay, exceptions)
  - Paso de argumentos y kwargs a la función
"""
import time
from unittest.mock import Mock, patch, call

import pytest

from app.services.utils_new import retry


class TestRetryFunction:
    """Tests para la función retry()"""

    def test_success_on_first_attempt(self):
        """Test éxito en el primer intento"""
        mock_func = Mock(return_value="success")

        result = retry(mock_func, retries=3)

        assert result == "success"
        assert mock_func.call_count == 1

    def test_success_after_one_retry(self):
        """Test éxito después de un reintento"""
        mock_func = Mock(side_effect=[ValueError("error"), "success"])

        result = retry(mock_func, retries=3, delay=0.01)

        assert result == "success"
        assert mock_func.call_count == 2

    def test_success_after_multiple_retries(self):
        """Test éxito después de múltiples reintentos"""
        mock_func = Mock(side_effect=[
            ValueError("error1"),
            ValueError("error2"),
            "success"
        ])

        result = retry(mock_func, retries=3, delay=0.01)

        assert result == "success"
        assert mock_func.call_count == 3

    def test_fails_after_all_retries(self):
        """Test fallo después de todos los reintentos"""
        mock_func = Mock(side_effect=ValueError("persistent error"))

        with pytest.raises(ValueError, match="persistent error"):
            retry(mock_func, retries=3, delay=0.01)

        assert mock_func.call_count == 3

    def test_respects_retry_count(self):
        """Test que respeta el número de reintentos"""
        mock_func = Mock(side_effect=RuntimeError("error"))

        with pytest.raises(RuntimeError):
            retry(mock_func, retries=5, delay=0.01)

        assert mock_func.call_count == 5

    def test_single_retry(self):
        """Test con un solo reintento (retries=1 significa 1 intento total)"""
        mock_func = Mock(side_effect=ValueError("error"))

        # Con retries=1, solo se ejecuta una vez
        with pytest.raises(ValueError):
            retry(mock_func, retries=1, delay=0.01)

        assert mock_func.call_count == 1

    def test_delay_between_retries(self):
        """Test que aplica delay entre reintentos"""
        mock_func = Mock(side_effect=[ValueError("error"), "success"])

        start = time.time()
        result = retry(mock_func, retries=3, delay=0.1)
        duration = time.time() - start

        # Debe haber esperado al menos el delay
        assert duration >= 0.1
        assert result == "success"

    def test_custom_exceptions(self):
        """Test con excepciones personalizadas a capturar"""
        mock_func = Mock(side_effect=[ValueError("error"), "success"])

        # Solo reintenta en ValueError
        result = retry(
            mock_func,
            retries=3,
            delay=0.01,
            exceptions=(ValueError,)
        )

        assert result == "success"

    def test_exception_not_in_list_propagates(self):
        """Test que excepciones no en la lista se propagan inmediatamente"""
        mock_func = Mock(side_effect=KeyError("key error"))

        # Solo captura ValueError, KeyError debe propagarse
        with pytest.raises(KeyError):
            retry(
                mock_func,
                retries=3,
                delay=0.01,
                exceptions=(ValueError,)
            )

        # Solo debe intentarse una vez
        assert mock_func.call_count == 1

    def test_multiple_exception_types(self):
        """Test con múltiples tipos de excepciones"""
        mock_func = Mock(side_effect=[
            ValueError("val error"),
            KeyError("key error"),
            "success"
        ])

        result = retry(
            mock_func,
            retries=3,
            delay=0.01,
            exceptions=(ValueError, KeyError)
        )

        assert result == "success"
        assert mock_func.call_count == 3

    def test_passes_args_to_function(self):
        """Test que pasa argumentos posicionales a la función"""
        mock_func = Mock(return_value="result")

        result = retry(
            mock_func,
            retries=3,
            args=(1, 2, 3)
        )

        mock_func.assert_called_with(1, 2, 3)
        assert result == "result"

    def test_passes_kwargs_to_function(self):
        """Test que pasa argumentos por palabra clave a la función"""
        mock_func = Mock(return_value="result")

        result = retry(
            mock_func,
            retries=3,
            kwargs={'key1': 'val1', 'key2': 'val2'}
        )

        mock_func.assert_called_with(key1='val1', key2='val2')
        assert result == "result"

    def test_passes_both_args_and_kwargs(self):
        """Test que pasa tanto args como kwargs"""
        mock_func = Mock(return_value="result")

        result = retry(
            mock_func,
            retries=3,
            args=(1, 2),
            kwargs={'key': 'value'}
        )

        mock_func.assert_called_with(1, 2, key='value')
        assert result == "result"

    def test_default_kwargs_is_empty_dict(self):
        """Test que kwargs por defecto es dict vacío"""
        mock_func = Mock(return_value="result")

        # No especificar kwargs
        result = retry(mock_func, retries=3, args=(1,))

        mock_func.assert_called_with(1)
        assert result == "result"

    def test_default_exceptions_is_base_exception(self):
        """Test que por defecto captura Exception"""
        mock_func = Mock(side_effect=[
            Exception("generic error"),
            "success"
        ])

        result = retry(mock_func, retries=3, delay=0.01)

        assert result == "success"
        assert mock_func.call_count == 2

    def test_logs_warnings_on_retry(self):
        """Test que registra warnings en cada reintento"""
        mock_func = Mock(side_effect=[
            ValueError("error1"),
            ValueError("error2"),
            "success"
        ])

        with patch('app.services.utils_new.logger') as mock_logger:
            result = retry(mock_func, retries=3, delay=0.01)

            # Debe registrar advertencias para los 2 intentos fallidos
            assert mock_logger.warning.call_count == 2
            assert result == "success"

    def test_logs_error_on_final_failure(self):
        """Test que registra error cuando fallan todos los intentos"""
        mock_func = Mock(side_effect=ValueError("persistent error"))

        with patch('app.services.utils_new.logger') as mock_logger:
            with pytest.raises(ValueError):
                retry(mock_func, retries=3, delay=0.01)

            # Debe registrar 3 warnings (uno por cada intento)
            # y 1 error final
            assert mock_logger.warning.call_count == 3
            assert mock_logger.error.call_count == 1

    def test_returns_correct_value_types(self):
        """Test que retorna correctamente diferentes tipos de valores"""
        # Retornar entero
        mock_func = Mock(return_value=42)
        assert retry(mock_func, retries=3) == 42

        # Retornar dict
        mock_func = Mock(return_value={'key': 'value'})
        assert retry(mock_func, retries=3) == {'key': 'value'}

        # Retornar None
        mock_func = Mock(return_value=None)
        assert retry(mock_func, retries=3) is None

        # Retornar lista
        mock_func = Mock(return_value=[1, 2, 3])
        assert retry(mock_func, retries=3) == [1, 2, 3]

    def test_zero_delay(self):
        """Test con delay de 0 (sin espera)"""
        mock_func = Mock(side_effect=[ValueError("error"), "success"])

        start = time.time()
        result = retry(mock_func, retries=3, delay=0)
        duration = time.time() - start

        # No debe haber delay significativo
        assert duration < 0.1
        assert result == "success"

    def test_preserves_exception_details(self):
        """Test que preserva detalles de la excepción original"""
        class CustomError(Exception):
            def __init__(self, msg, code):
                super().__init__(msg)
                self.code = code

        mock_func = Mock(side_effect=CustomError("error", 500))

        with pytest.raises(CustomError) as exc_info:
            retry(mock_func, retries=3, delay=0.01)

        assert exc_info.value.code == 500
        assert str(exc_info.value) == "error"


class TestRetryWithRealFunctions:
    """Tests de retry con funciones reales (no mocks)"""

    def test_retry_with_lambda(self):
        """Test retry con función lambda"""
        counter = {'attempts': 0}

        def func():
            counter['attempts'] += 1
            if counter['attempts'] < 3:
                raise ValueError("Not yet")
            return "success"

        result = retry(func, retries=5, delay=0.01)

        assert result == "success"
        assert counter['attempts'] == 3

    def test_retry_with_stateful_function(self):
        """Test retry con función con estado"""
        class Counter:
            def __init__(self):
                self.count = 0

            def increment(self):
                self.count += 1
                if self.count < 2:
                    raise ValueError("Try again")
                return self.count

        counter = Counter()
        result = retry(counter.increment, retries=3, delay=0.01)

        assert result == 2
        assert counter.count == 2

    def test_retry_with_complex_arguments(self):
        """Test retry con argumentos complejos"""
        def complex_func(a, b, c=None, d=None):
            if a + b < 10:
                raise ValueError("Sum too small")
            return {'a': a, 'b': b, 'c': c, 'd': d}

        # Primera vez falla, segunda vez éxito
        counter = {'calls': 0}

        def tracked_func(a, b, c=None, d=None):
            counter['calls'] += 1
            if counter['calls'] == 1:
                raise ValueError("First call fails")
            return complex_func(a, b, c, d)

        result = retry(
            tracked_func,
            retries=3,
            delay=0.01,
            args=(5, 6),
            kwargs={'c': 'C', 'd': 'D'}
        )

        assert result == {'a': 5, 'b': 6, 'c': 'C', 'd': 'D'}

    def test_retry_calculation_function(self):
        """Test retry con función de cálculo"""
        attempts = {'count': 0}

        def divide(a, b):
            attempts['count'] += 1
            if attempts['count'] < 2:
                # Simular error temporal
                raise ZeroDivisionError("Temporary error")
            return a / b

        result = retry(
            divide,
            retries=3,
            delay=0.01,
            args=(10, 2)
        )

        assert result == 5.0
        assert attempts['count'] == 2


class TestRetryEdgeCases:
    """Tests de casos extremos para retry()"""

    def test_large_retry_count(self):
        """Test con número muy grande de reintentos"""
        mock_func = Mock(side_effect=[ValueError("error")] * 99 + ["success"])

        result = retry(mock_func, retries=100, delay=0)

        assert result == "success"
        assert mock_func.call_count == 100

    def test_function_that_returns_false(self):
        """Test que función que retorna False no se considera fallo"""
        mock_func = Mock(return_value=False)

        result = retry(mock_func, retries=3)

        assert result is False
        assert mock_func.call_count == 1  # No debe reintentar

    def test_function_that_returns_none(self):
        """Test que función que retorna None no se considera fallo"""
        mock_func = Mock(return_value=None)

        result = retry(mock_func, retries=3)

        assert result is None
        assert mock_func.call_count == 1

    def test_empty_exception_tuple(self):
        """Test con tupla vacía de excepciones (no captura nada)"""
        mock_func = Mock(side_effect=ValueError("error"))

        # Con tupla vacía, no captura ninguna excepción
        with pytest.raises(ValueError):
            retry(mock_func, retries=3, delay=0.01, exceptions=())

        assert mock_func.call_count == 1

    def test_exception_in_cleanup_path(self):
        """Test manejo de excepciones en path de cleanup"""
        call_count = {'count': 0}

        def problematic_func():
            call_count['count'] += 1
            if call_count['count'] == 1:
                raise ValueError("First error")
            elif call_count['count'] == 2:
                raise KeyError("Second error")
            return "success"

        result = retry(
            problematic_func,
            retries=3,
            delay=0.01,
            exceptions=(ValueError, KeyError)
        )

        assert result == "success"
        assert call_count['count'] == 3
