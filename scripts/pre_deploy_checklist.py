"""
Script de checklist de pre-despliegue automatizado
Valida que el sistema esté listo para despliegue a producción
"""
import sys
import os
import json
import time
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import requests

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings


class PreDeploymentChecker:
    """Valida requisitos de pre-despliegue"""
    
    def __init__(self):
        self.results = []
        self.warnings = []
        self.critical_failures = []
    
    def check_item(self, name: str, check_func, is_critical: bool = True) -> Dict:
        """Ejecuta una verificación y registra el resultado"""
        print(f"\n{'='*80}")
        print(f"Verificando: {name}")
        print(f"{'='*80}\n")
        
        start = time.time()
        
        try:
            passed, details, warning = check_func()
            duration = time.time() - start
            
            result = {
                'name': name,
                'passed': passed,
                'is_critical': is_critical,
                'duration': duration,
                'details': details,
                'warning': warning,
                'timestamp': datetime.now().isoformat()
            }
            
            if passed:
                status = "✅ PASÓ"
                if warning:
                    status += " ⚠️"
                    self.warnings.append(f"{name}: {warning}")
            else:
                status = "❌ FALLÓ"
                if is_critical:
                    self.critical_failures.append(name)
            
            print(f"\n{status} - {name} ({duration:.3f}s)")
            print(f"Detalles: {details}")
            if warning:
                print(f"⚠️  Advertencia: {warning}")
            
            self.results.append(result)
            return result
            
        except Exception as e:
            duration = time.time() - start
            
            result = {
                'name': name,
                'passed': False,
                'is_critical': is_critical,
                'duration': duration,
                'details': f"Error: {str(e)}",
                'warning': None,
                'timestamp': datetime.now().isoformat()
            }
            
            print(f"\n❌ ERROR - {name} ({duration:.3f}s)")
            print(f"Error: {str(e)}")
            
            if is_critical:
                self.critical_failures.append(name)
            
            self.results.append(result)
            return result
    
    # ========================================================================
    # SECCIÓN 1: VALIDACIÓN DE VARIABLES DE ENTORNO
    # ========================================================================
    
    def check_required_env_vars(self) -> Tuple[bool, str, Optional[str]]:
        """Verifica que todas las variables de entorno requeridas estén configuradas"""
        required_vars = {
            'TWILIO_ACCOUNT_SID': 'Twilio Account SID',
            'TWILIO_AUTH_TOKEN': 'Twilio Auth Token',
            'TWILIO_WHATSAPP_NUMBER': 'Número de WhatsApp de Twilio',
        }
        
        missing = []
        configured = []
        
        for var, description in required_vars.items():
            value = os.getenv(var)
            if not value or value == f"your_{var.lower()}_here":
                missing.append(f"{var} ({description})")
            else:
                configured.append(var)
        
        if missing:
            return False, f"Variables faltantes: {', '.join(missing)}", None
        
        return True, f"Todas las variables requeridas configuradas: {', '.join(configured)}", None
    
    def check_optional_env_vars(self) -> Tuple[bool, str, Optional[str]]:
        """Verifica variables de entorno opcionales"""
        optional_vars = {
            'GOOGLE_SHEETS_ID': 'Google Sheets ID',
            'GOOGLE_SHEETS_CREDENTIALS': 'Credenciales de Google Sheets',
            'OPENAI_API_KEY': 'OpenAI API Key',
        }
        
        configured = []
        missing = []
        
        for var, description in optional_vars.items():
            value = os.getenv(var)
            if value and value != f"your_{var.lower()}_here":
                configured.append(var)
            else:
                missing.append(var)
        
        warning = None
        if missing:
            warning = f"Variables opcionales no configuradas: {', '.join(missing)}"
        
        details = f"Configuradas: {', '.join(configured) if configured else 'ninguna'}"
        return True, details, warning
    
    def check_security_env_vars(self) -> Tuple[bool, str, Optional[str]]:
        """Verifica configuración de seguridad"""
        issues = []
        warnings = []
        
        # Verificar SECRET_KEY
        secret_key = os.getenv('SECRET_KEY')
        if not secret_key:
            issues.append("SECRET_KEY no configurada")
        elif len(secret_key) < 32:
            warnings.append("SECRET_KEY debería tener al menos 32 caracteres")
        
        # Verificar ADMIN_API_TOKEN
        admin_token = os.getenv('ADMIN_API_TOKEN')
        if not admin_token:
            warnings.append("ADMIN_API_TOKEN no configurada (endpoints admin desprotegidos)")
        elif len(admin_token) < 20:
            warnings.append("ADMIN_API_TOKEN debería ser más largo")
        
        # Verificar ENVIRONMENT
        environment = os.getenv('ENVIRONMENT', 'development')
        if environment != 'production':
            warnings.append(f"ENVIRONMENT={environment} (debería ser 'production')")
        
        # Verificar DEBUG
        debug = os.getenv('DEBUG', 'false').lower()
        if debug == 'true':
            issues.append("DEBUG=true en producción es un riesgo de seguridad")
        
        if issues:
            return False, f"Problemas: {'; '.join(issues)}", None
        
        warning = '; '.join(warnings) if warnings else None
        return True, "Configuración de seguridad básica OK", warning
    
    def check_production_config(self) -> Tuple[bool, str, Optional[str]]:
        """Verifica configuración específica de producción"""
        warnings = []
        
        # Verificar ALLOWED_HOSTS
        allowed_hosts = os.getenv('ALLOWED_HOSTS', '*')
        if allowed_hosts == '*':
            warnings.append("ALLOWED_HOSTS='*' permite cualquier host")
        
        # Verificar CORS_ORIGINS
        cors_origins = os.getenv('CORS_ORIGINS', '*')
        if cors_origins == '*':
            warnings.append("CORS_ORIGINS='*' permite cualquier origen")
        
        # Verificar BASE_URL
        base_url = os.getenv('BASE_URL', '')
        if not base_url or 'localhost' in base_url:
            warnings.append("BASE_URL no configurada para producción")
        
        # Verificar rate limiting
        rate_limit = int(os.getenv('RATE_LIMIT_MAX_REQUESTS', '30'))
        if rate_limit > 100:
            warnings.append(f"RATE_LIMIT_MAX_REQUESTS={rate_limit} es muy alto")
        
        warning = '; '.join(warnings) if warnings else None
        details = f"ENVIRONMENT={os.getenv('ENVIRONMENT', 'development')}, BASE_URL={base_url}"
        
        return True, details, warning
    
    # ========================================================================
    # SECCIÓN 2: CONECTIVIDAD CON SERVICIOS EXTERNOS
    # ========================================================================
    
    def check_twilio_connectivity(self) -> Tuple[bool, str, Optional[str]]:
        """Verifica conectividad con Twilio"""
        try:
            from twilio.rest import Client
            
            account_sid = settings.TWILIO_ACCOUNT_SID
            auth_token = settings.TWILIO_AUTH_TOKEN
            
            if not account_sid or not auth_token:
                return False, "Credenciales de Twilio no configuradas", None
            
            # Intentar crear cliente y hacer una llamada simple
            client = Client(account_sid, auth_token)
            
            # Verificar cuenta
            account = client.api.accounts(account_sid).fetch()
            
            return True, f"Conectado a Twilio - Account: {account.friendly_name}, Status: {account.status}", None
            
        except ImportError:
            return False, "Librería twilio no instalada", None
        except Exception as e:
            return False, f"Error conectando a Twilio: {str(e)}", None
    
    def check_google_sheets_connectivity(self) -> Tuple[bool, str, Optional[str]]:
        """Verifica conectividad con Google Sheets"""
        try:
            sheets_id = settings.GOOGLE_SHEETS_ID
            credentials = settings.GOOGLE_SHEETS_CREDENTIALS
            
            if not sheets_id or not credentials:
                return True, "Google Sheets no configurado (usando Excel local)", "Funcionalidad opcional no disponible"
            
            import gspread
            from google.oauth2.service_account import Credentials
            import json
            
            # Parsear credenciales
            creds_dict = json.loads(credentials)
            
            # Crear credenciales
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets.readonly',
                'https://www.googleapis.com/auth/drive.readonly'
            ]
            creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
            
            # Conectar
            client = gspread.authorize(creds)
            
            # Intentar abrir la hoja
            sheet = client.open_by_key(sheets_id)
            
            return True, f"Conectado a Google Sheets: {sheet.title}", None
            
        except ImportError:
            return True, "Librerías de Google Sheets no instaladas (usando Excel local)", "Funcionalidad opcional no disponible"
        except Exception as e:
            return True, f"Error conectando a Google Sheets: {str(e)} (usando Excel local)", "Funcionalidad opcional no disponible"
    
    def check_openai_connectivity(self) -> Tuple[bool, str, Optional[str]]:
        """Verifica conectividad con OpenAI"""
        try:
            api_key = settings.OPENAI_API_KEY
            
            if not api_key:
                return True, "OpenAI no configurado", "Funcionalidad opcional no disponible"
            
            # Verificar que la API key tiene formato válido
            if not api_key.startswith('sk-'):
                return False, "OpenAI API key tiene formato inválido", None
            
            # Intentar hacer una llamada simple
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(
                'https://api.openai.com/v1/models',
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return True, "Conectado a OpenAI API", None
            else:
                return False, f"OpenAI API respondió con status {response.status_code}", None
                
        except requests.exceptions.Timeout:
            return False, "Timeout conectando a OpenAI API", None
        except Exception as e:
            return True, f"Error verificando OpenAI: {str(e)}", "Funcionalidad opcional puede no estar disponible"
    
    def check_excel_file_access(self) -> Tuple[bool, str, Optional[str]]:
        """Verifica acceso al archivo Excel de precios"""
        excel_path = settings.EXCEL_PATH
        
        if not os.path.exists(excel_path):
            return False, f"Archivo Excel no encontrado: {excel_path}", None
        
        # Verificar que se puede leer
        try:
            import openpyxl
            wb = openpyxl.load_workbook(excel_path, read_only=True, data_only=True)
            sheet_names = wb.sheetnames
            wb.close()
            
            return True, f"Archivo Excel accesible: {len(sheet_names)} hojas encontradas", None
            
        except ImportError:
            return False, "Librería openpyxl no instalada", None
        except Exception as e:
            return False, f"Error leyendo Excel: {str(e)}", None
    
    # ========================================================================
    # SECCIÓN 3: CONFIGURACIÓN DE SEGURIDAD
    # ========================================================================
    
    def check_https_configuration(self) -> Tuple[bool, str, Optional[str]]:
        """Verifica configuración HTTPS"""
        base_url = settings.BASE_URL
        
        if not base_url:
            return False, "BASE_URL no configurada", None
        
        if base_url.startswith('https://'):
            return True, f"HTTPS configurado: {base_url}", None
        elif base_url.startswith('http://'):
            if 'localhost' in base_url or '127.0.0.1' in base_url:
                return True, "HTTP en desarrollo (localhost)", "En producción debe usar HTTPS"
            else:
                return False, f"HTTP en producción: {base_url}", None
        else:
            return False, f"Protocolo inválido en BASE_URL: {base_url}", None
    
    def check_rate_limiting_config(self) -> Tuple[bool, str, Optional[str]]:
        """Verifica configuración de rate limiting"""
        max_requests = settings.RATE_LIMIT_MAX_REQUESTS
        window_seconds = settings.RATE_LIMIT_WINDOW_SECONDS
        
        warnings = []
        
        if max_requests > 100:
            warnings.append(f"Max requests muy alto: {max_requests}")
        
        if window_seconds < 30:
            warnings.append(f"Ventana muy corta: {window_seconds}s")
        
        details = f"{max_requests} requests por {window_seconds}s"
        warning = '; '.join(warnings) if warnings else None
        
        return True, details, warning
    
    def check_token_configuration(self) -> Tuple[bool, str, Optional[str]]:
        """Verifica configuración de tokens"""
        issues = []
        warnings = []
        
        # Verificar SECRET_KEY
        if not settings.SECRET_KEY:
            issues.append("SECRET_KEY no configurada")
        
        # Verificar ADMIN_API_TOKEN
        if not settings.ADMIN_API_TOKEN:
            warnings.append("ADMIN_API_TOKEN no configurada")
        
        # Verificar tokens de Twilio
        if not settings.TWILIO_AUTH_TOKEN:
            issues.append("TWILIO_AUTH_TOKEN no configurada")
        
        if issues:
            return False, f"Tokens faltantes: {', '.join(issues)}", None
        
        warning = '; '.join(warnings) if warnings else None
        return True, "Tokens principales configurados", warning
    
    def check_security_headers(self) -> Tuple[bool, str, Optional[str]]:
        """Verifica que los headers de seguridad estén implementados"""
        try:
            from app.security import add_security_headers
            
            # Verificar que la función existe
            if not callable(add_security_headers):
                return False, "Función add_security_headers no es callable", None
            
            return True, "Headers de seguridad implementados", None
            
        except ImportError:
            return False, "Módulo de seguridad no encontrado", None
    
    # ========================================================================
    # SECCIÓN 4: LOGS Y MONITOREO
    # ========================================================================
    
    def check_log_directory(self) -> Tuple[bool, str, Optional[str]]:
        """Verifica que el directorio de logs existe y es escribible"""
        log_dir = 'logs'
        
        if not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir)
                return True, f"Directorio de logs creado: {log_dir}", None
            except Exception as e:
                return False, f"No se pudo crear directorio de logs: {str(e)}", None
        
        # Verificar que es escribible
        test_file = os.path.join(log_dir, '.write_test')
        try:
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            return True, f"Directorio de logs escribible: {log_dir}", None
        except Exception as e:
            return False, f"Directorio de logs no escribible: {str(e)}", None
    
    def check_logging_configuration(self) -> Tuple[bool, str, Optional[str]]:
        """Verifica configuración de logging"""
        try:
            from app.logging_config import setup_logging
            
            # Verificar que la función existe
            if not callable(setup_logging):
                return False, "Función setup_logging no es callable", None
            
            # Verificar archivos de log esperados
            expected_logs = ['app.log', 'errors.log', 'security.log', 'business.log']
            existing_logs = []
            
            for log_file in expected_logs:
                log_path = os.path.join('logs', log_file)
                if os.path.exists(log_path):
                    existing_logs.append(log_file)
            
            details = f"Sistema de logging configurado. Logs existentes: {', '.join(existing_logs) if existing_logs else 'ninguno'}"
            warning = None if existing_logs else "No hay archivos de log existentes (se crearán al iniciar)"
            
            return True, details, warning
            
        except ImportError:
            return False, "Módulo logging_config no encontrado", None
    
    def check_monitoring_setup(self) -> Tuple[bool, str, Optional[str]]:
        """Verifica configuración de monitoreo"""
        warnings = []
        
        # Verificar Sentry
        sentry_dsn = os.getenv('SENTRY_DSN')
        if not sentry_dsn:
            warnings.append("Sentry no configurado")
        
        # Verificar métricas
        enable_metrics = os.getenv('ENABLE_METRICS', 'false').lower()
        if enable_metrics != 'true':
            warnings.append("Métricas no habilitadas")
        
        # Verificar health check endpoint
        try:
            from app.main import app
            # El health check debería estar en la aplicación
            details = "Sistema de monitoreo básico disponible"
        except:
            details = "Sistema de monitoreo limitado"
        
        warning = '; '.join(warnings) if warnings else None
        return True, details, warning
    
    def check_backup_configuration(self) -> Tuple[bool, str, Optional[str]]:
        """Verifica configuración de backup"""
        # Verificar que existe el archivo de sesiones
        sessions_file = 'data/sessions.json'
        
        if not os.path.exists('data'):
            return False, "Directorio data/ no existe", None
        
        details = f"Directorio de datos existe"
        warning = None
        
        if not os.path.exists(sessions_file):
            warning = "Archivo sessions.json no existe (se creará al iniciar)"
        else:
            # Verificar tamaño
            size = os.path.getsize(sessions_file)
            details += f", sessions.json: {size} bytes"
        
        return True, details, warning
    
    # ========================================================================
    # EJECUCIÓN Y REPORTE
    # ========================================================================
    
    def run_all_checks(self):
        """Ejecuta todas las verificaciones"""
        print("\n" + "="*80)
        print("🔍 CHECKLIST DE PRE-DESPLIEGUE")
        print("="*80)
        
        # SECCIÓN 1: Variables de entorno
        print("\n" + "="*80)
        print("📋 SECCIÓN 1: VARIABLES DE ENTORNO")
        print("="*80)
        
        self.check_item("Variables de entorno requeridas", 
                       self.check_required_env_vars, is_critical=True)
        self.check_item("Variables de entorno opcionales", 
                       self.check_optional_env_vars, is_critical=False)
        self.check_item("Variables de seguridad", 
                       self.check_security_env_vars, is_critical=True)
        self.check_item("Configuración de producción", 
                       self.check_production_config, is_critical=False)
        
        # SECCIÓN 2: Conectividad
        print("\n" + "="*80)
        print("🌐 SECCIÓN 2: CONECTIVIDAD CON SERVICIOS EXTERNOS")
        print("="*80)
        
        self.check_item("Conectividad con Twilio", 
                       self.check_twilio_connectivity, is_critical=True)
        self.check_item("Conectividad con Google Sheets", 
                       self.check_google_sheets_connectivity, is_critical=False)
        self.check_item("Conectividad con OpenAI", 
                       self.check_openai_connectivity, is_critical=False)
        self.check_item("Acceso a archivo Excel", 
                       self.check_excel_file_access, is_critical=True)
        
        # SECCIÓN 3: Seguridad
        print("\n" + "="*80)
        print("🔒 SECCIÓN 3: CONFIGURACIÓN DE SEGURIDAD")
        print("="*80)
        
        self.check_item("Configuración HTTPS", 
                       self.check_https_configuration, is_critical=True)
        self.check_item("Configuración de rate limiting", 
                       self.check_rate_limiting_config, is_critical=False)
        self.check_item("Configuración de tokens", 
                       self.check_token_configuration, is_critical=True)
        self.check_item("Headers de seguridad", 
                       self.check_security_headers, is_critical=False)
        
        # SECCIÓN 4: Logs y monitoreo
        print("\n" + "="*80)
        print("📊 SECCIÓN 4: LOGS Y MONITOREO")
        print("="*80)
        
        self.check_item("Directorio de logs", 
                       self.check_log_directory, is_critical=True)
        self.check_item("Configuración de logging", 
                       self.check_logging_configuration, is_critical=False)
        self.check_item("Sistema de monitoreo", 
                       self.check_monitoring_setup, is_critical=False)
        self.check_item("Configuración de backup", 
                       self.check_backup_configuration, is_critical=False)
    
    def print_summary(self):
        """Imprime resumen de verificaciones"""
        total = len(self.results)
        passed = sum(1 for r in self.results if r['passed'])
        failed = total - passed
        critical_total = sum(1 for r in self.results if r['is_critical'])
        critical_passed = sum(1 for r in self.results if r['is_critical'] and r['passed'])
        
        print("\n" + "="*80)
        print("📊 RESUMEN DE CHECKLIST DE PRE-DESPLIEGUE")
        print("="*80)
        print(f"\nTotal de verificaciones: {total}")
        print(f"✅ Pasadas: {passed}")
        print(f"❌ Falladas: {failed}")
        print(f"📈 Tasa de éxito: {(passed/total*100):.1f}%")
        print(f"\n🔴 Verificaciones críticas: {critical_passed}/{critical_total}")
        
        if self.warnings:
            print(f"\n⚠️  Advertencias ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"   • {warning}")
        
        if self.critical_failures:
            print(f"\n❌ Fallos críticos ({len(self.critical_failures)}):")
            for failure in self.critical_failures:
                print(f"   • {failure}")
        
        print("\n" + "="*80)
        
        # Determinar si el sistema está listo para despliegue
        if not self.critical_failures:
            print("✅ SISTEMA LISTO PARA DESPLIEGUE")
            if self.warnings:
                print("   ⚠️  Hay advertencias que deberían revisarse")
            return True
        else:
            print("❌ SISTEMA NO LISTO PARA DESPLIEGUE")
            print("   Corrige los fallos críticos antes de continuar")
            return False
    
    def save_report(self, filename: str = 'pre_deploy_checklist_report.json'):
        """Guarda reporte en formato JSON"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_checks': len(self.results),
                'passed': sum(1 for r in self.results if r['passed']),
                'failed': sum(1 for r in self.results if not r['passed']),
                'critical_checks': sum(1 for r in self.results if r['is_critical']),
                'critical_passed': sum(1 for r in self.results if r['is_critical'] and r['passed']),
                'warnings_count': len(self.warnings),
                'ready_for_deployment': len(self.critical_failures) == 0
            },
            'results': self.results,
            'warnings': self.warnings,
            'critical_failures': self.critical_failures
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Reporte guardado en: {filename}")
        return filename


def main():
    """Función principal"""
    checker = PreDeploymentChecker()
    
    # Ejecutar todas las verificaciones
    checker.run_all_checks()
    
    # Mostrar resumen
    ready = checker.print_summary()
    
    # Guardar reporte
    checker.save_report()
    
    return 0 if ready else 1


if __name__ == "__main__":
    try:
        exit_code = main()
        print("="*80)
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Proceso interrumpido por el usuario")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ Error inesperado: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
