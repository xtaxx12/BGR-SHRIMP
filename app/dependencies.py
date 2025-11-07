import logging
from functools import lru_cache
from typing import Any

from app.exceptions import ConfigurationError
from app.services.interactive import InteractiveMessageService
from app.services.openai_service import OpenAIService
from app.services.pdf_generator import PDFGenerator
from app.services.pricing import PricingService
from app.services.session import SessionManager
from app.services.whatsapp_sender import WhatsAppSender

logger = logging.getLogger(__name__)

class ServiceContainer:
    """Contenedor de servicios con inyección de dependencias"""

    def __init__(self):
        self._services: dict[str, Any] = {}
        self._initialized = False

    def initialize(self):
        """Inicializar todos los servicios"""
        if self._initialized:
            return

        logger.info("Initializing service container")

        try:
            # Inicializar servicios base
            self._services['pricing'] = PricingService()
            self._services['session'] = SessionManager()
            self._services['pdf_generator'] = PDFGenerator()
            self._services['whatsapp_sender'] = WhatsAppSender()

            # Servicios que dependen de otros
            self._services['interactive'] = InteractiveMessageService(
                self._services['pricing'].excel_service
            )

            # Servicios opcionales
            self._services['openai'] = OpenAIService()

            self._initialized = True
            logger.info("All services initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize services: {e}")
            raise ConfigurationError(f"Service initialization failed: {e}")

    def get_service(self, name: str):
        """Obtener servicio por nombre"""
        if not self._initialized:
            self.initialize()

        service = self._services.get(name)
        if not service:
            raise ValueError(f"Service '{name}' not found")

        return service

    @property
    def pricing_service(self) -> PricingService:
        return self.get_service('pricing')

    @property
    def session_manager(self) -> SessionManager:
        return self.get_service('session')

    @property
    def interactive_service(self) -> InteractiveMessageService:
        return self.get_service('interactive')

    @property
    def pdf_generator(self) -> PDFGenerator:
        return self.get_service('pdf_generator')

    @property
    def whatsapp_sender(self) -> WhatsAppSender:
        return self.get_service('whatsapp_sender')

    @property
    def openai_service(self) -> OpenAIService:
        return self.get_service('openai')

    def health_check(self) -> dict[str, bool]:
        """Verificar salud de todos los servicios"""
        health = {}

        for name, service in self._services.items():
            try:
                # Verificar si el servicio tiene método is_available
                if hasattr(service, 'is_available'):
                    health[name] = service.is_available()
                else:
                    health[name] = True
            except Exception as e:
                logger.error(f"Health check failed for {name}: {e}")
                health[name] = False

        return health

    def reload(self):
        """Recargar todos los servicios"""
        logger.info("Reloading all services")
        self._initialized = False
        self._services.clear()
        self.initialize()

# Singleton del contenedor
_service_container: ServiceContainer | None = None

@lru_cache
def get_service_container() -> ServiceContainer:
    """Obtener instancia singleton del contenedor de servicios"""
    global _service_container
    if _service_container is None:
        _service_container = ServiceContainer()
        _service_container.initialize()
    return _service_container

# Funciones de conveniencia para inyección de dependencias
def get_pricing_service() -> PricingService:
    return get_service_container().pricing_service

def get_session_manager() -> SessionManager:
    return get_service_container().session_manager

def get_interactive_service() -> InteractiveMessageService:
    return get_service_container().interactive_service

def get_pdf_generator() -> PDFGenerator:
    return get_service_container().pdf_generator

def get_whatsapp_sender() -> WhatsAppSender:
    return get_service_container().whatsapp_sender

def get_openai_service() -> OpenAIService:
    return get_service_container().openai_service

# Context manager para transacciones
from contextlib import contextmanager


@contextmanager
def service_transaction():
    """Context manager para operaciones que requieren múltiples servicios"""
    container = get_service_container()
    try:
        yield container
    except Exception as e:
        logger.error(f"Error in service transaction: {e}")
        raise
    finally:
        # Limpiar recursos si es necesario
        pass
