import time
import logging
from typing import Callable, Any, Tuple

logger = logging.getLogger(__name__)



def retry(func: Callable, retries: int = 3, delay: float = 0.5, exceptions: Tuple = (Exception,), args: tuple = (), kwargs: dict = None) -> Any:
	"""Simple retry helper with fixed backoff.

	Parameters:
	- func: callable a ejecutar
	- retries: número de reintentos
	- delay: retardo en segundos entre reintentos
	- exceptions: tupla de excepciones que disparan reintento
	- args: tuple de argumentos posicionales para pasar a func
	- kwargs: dict de argumentos por palabra clave para pasar a func

	Retorna lo que retorne func o lanza la última excepción si todos los intentos fallan.
	"""
	if kwargs is None:
		kwargs = {}
	last_exc = None
	for attempt in range(retries):
		try:
			return func(*args, **kwargs)
		except exceptions as e:
			last_exc = e
			logger.warning(f"Intento {attempt+1}/{retries} fallido para {func}: {e}")
			time.sleep(delay)
	# Si fallaron todos los intentos, propagar la última excepción
	logger.error(f"Todos los {retries} reintentos fallaron para {func}: {last_exc}")
	raise last_exc

