import time
import urllib.request
import urllib.error
import logging
from e2b_code_interpreter import Sandbox

logger = logging.getLogger("agent.deployer")

class AppDeployer:
    """
    Clase responsable de automatizar la compilación y el despliegue 
    de la aplicación Next.js dentro del sandbox de E2B.
    
    Encapsula la lógica de dev_server.py para ser usada programáticamente 
    por el sistema multi-agente.
    """
    
    WORKDIR = "/home/user/app"
    PORT = 3000
    SERVER_TIMEOUT = 120  # Tiempo máximo de espera para el despliegue
    BUILD_TIMEOUT = 300   # Timeout extendido para compilación Next.js
    POLL_INTERVAL = 3     # Intervalo de sondeo (polling) para verificar disponibilidad

    def __init__(self, sbx: Sandbox):
        self.sbx = sbx
        self.url = f"https://{sbx.get_host(self.PORT)}"

    def deploy(self) -> str:
        """
        Ejecuta el flujo completo de despliegue.
        
        Retorna:
            URL pública si el despliegue fue exitoso.
            Mensaje de error si falla algún paso.
        """
        try:
            logger.info("AppDeployer | Iniciando flujo de despliegue automatizado...")
            
            # 0. Pequeña espera para asegurar que el sistema de archivos del sandbox esté sincronizado
            time.sleep(2)
            
            # 1. Limpieza y preparación del entorno
            self._prepare_env()
            
            # 2. Compilación (Build)
            self._build()
            
            # 3. Inicio de servidor en segundo plano
            self._start_server()
            
            # 4. Verificación de disponibilidad
            if self._wait_for_ready():
                logger.info("AppDeployer | Despliegue exitoso: %s", self.url)
                return self.url
            else:
                error_msg = f"Timeout: El servidor no respondió en {self.SERVER_TIMEOUT}s."
                logger.error("AppDeployer | %s", error_msg)
                return f"⚠️ Error: {error_msg} Puedes intentar abrirla igualmente: {self.url}"
                
        except Exception as e:
            error_msg = str(e)
            # Manejo de errores específicos de E2B para mayor claridad en el UI
            if "code -1" in error_msg:
                error_msg = "Error E2B (-1): La conexión con el sandbox se interrumpió o el proceso excedió el tiempo límite (Timeout/OOM)."
            
            logger.error("AppDeployer | Excepción durante el despliegue: %s", error_msg)
            return f"❌ Falla en el despliegue automático:\n{error_msg}"

    def _prepare_env(self):
        """Detiene procesos anteriores y limpia el entorno del sandbox."""
        logger.debug("AppDeployer | Deteniendo procesos Node/Next previos...")
        try:
            # Matar cualquier proceso que esté ocupando el puerto o sea de Next.js
            # Permitimos que este paso falle o lance timeout
            self.sbx.commands.run(
                "pkill -u $(id -u) -f next 2>/dev/null; pkill -u $(id -u) -f node 2>/dev/null; sleep 1; exit 0",
                timeout=15
            )
        except Exception as e:
            # Si es el error -1, lo tratamos como debug para no ensuciar la consola, 
            # ya que el sistema es capaz de recuperarse en las fases siguientes.
            if "code -1" in str(e):
                logger.debug("AppDeployer | pkill omitido o no necesario (code -1)")
            else:
                logger.warning("AppDeployer | Aviso en pkill (no crítico): %s", e)

        logger.debug("AppDeployer | Reparando permisos y limpiando caché .next...")
        try:
            # Arreglar permisos y borrar build previo
            self.sbx.commands.run(
                f"sudo chown -R $(id -u):$(id -g) {self.WORKDIR} && rm -rf {self.WORKDIR}/.next",
                timeout=20
            )
        except Exception as e:
            logger.error("AppDeployer | Error crítico en permisos/limpieza: %s", e)
            raise

        try:
            # Eliminar archivos de configuración root
            self.sbx.commands.run("rm -f /home/user/package-lock.json /home/user/package.json", timeout=10)
        except Exception:
            pass
        
        # Restaurar una configuración mínima de next.config.ts por seguridad
        next_config = """import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
};

export default nextConfig;
"""
        self.sbx.files.write(f"{self.WORKDIR}/next.config.ts", next_config)

    def _build(self):
        """Ejecuta la compilación de producción de Next.js."""
        logger.info("AppDeployer | Ejecutando 'npm run build'...")
        try:
            # Aumentamos el timeout y capturamos stdout/stderr
            result = self.sbx.commands.run("npm run build", cwd=self.WORKDIR, timeout=self.BUILD_TIMEOUT)
            
            if result.exit_code != 0:
                stdout = result.stdout[-1000:] if result.stdout else ""
                stderr = result.stderr[-1000:] if result.stderr else ""
                raise Exception(f"La compilación falló (exit={result.exit_code}).\nDetalles:\n{stdout}\n{stderr}")
                
        except Exception as e:
            # Capturar errores del SDK (como el de code -1) y darles un contexto más útil
            error_str = str(e)
            if "code -1" in error_str:
                error_str = "Error: La compilación se interrumpió o excedió el tiempo límite (Timeout/OOM en sandbox)."
            raise Exception(f"E2B ERROR | {error_str}")

    def _start_server(self):
        """Lanza el servidor de producción con npm run start."""
        logger.info("AppDeployer | Lanzando servidor de producción en el puerto %d...", self.PORT)
        try:
            # Se lanza en background (background=True) para que el script de deployment no se bloquee
            self.sbx.commands.run("npm run start -- -H 0.0.0.0", cwd=self.WORKDIR, background=True)
        except Exception as e:
            logger.error("AppDeployer | Error iniciando servidor: %s", e)
            raise Exception(f"No se pudo iniciar el servidor: {e}")

    def _wait_for_ready(self) -> bool:
        """Sondea la URL pública hasta que el servidor devuelva un código exitoso."""
        logger.debug("AppDeployer | Esperando respuesta HTTP del servidor...")
        deadline = time.monotonic() + self.SERVER_TIMEOUT
        while time.monotonic() < deadline:
            if self._is_ready():
                return True
            time.sleep(self.POLL_INTERVAL)
        return False

    def _is_ready(self) -> bool:
        """Verifica si la aplicación responde en la URL pública."""
        try:
            with urllib.request.urlopen(self.url, timeout=5) as resp:
                return resp.status < 500
        except urllib.error.HTTPError as e:
            return e.code < 500  # 404, 403 etc significa que el servidor está arriba
        except Exception:
            return False
