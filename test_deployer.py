import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Añadir el directorio actual al path para importar lib
sys.path.append(os.getcwd())

from lib.deployer import AppDeployer

class TestAppDeployer(unittest.TestCase):
    def setUp(self):
        self.mock_sbx = MagicMock()
        # Simular comportamiento de get_host
        self.mock_sbx.get_host.return_value = "sandbox-uuid.e2b.dev"
        self.deployer = AppDeployer(self.mock_sbx)

    @patch("time.sleep", return_value=None) # Acelerar el test
    @patch("urllib.request.urlopen")
    def test_deploy_success_flow(self, mock_urlopen, mock_sleep):
        """Verifica que el flujo completo se ejecute correctamente en caso de éxito."""
        # 1. Mock de comandos exitosos
        # Los comandos se ejecutan en orden: pkill, chown, rm, build, start
        self.mock_sbx.commands.run.return_value = MagicMock(exit_code=0, stdout="Success")
        
        # 2. Mock de respuesta HTTP exitosa (poll para disponibilidad)
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_resp
        
        url = self.deployer.deploy()
        
        # Verificaciones
        self.assertEqual(url, "https://sandbox-uuid.e2b.dev")
        self.mock_sbx.commands.run.assert_any_call("npm run build", cwd="/home/user/app", timeout=180)
        self.mock_sbx.commands.run.assert_any_call("npm run start -- -H 0.0.0.0", cwd="/home/user/app", background=True)

    def test_deploy_build_error_logs(self):
        """Verifica que los errores de build se capturen y reporten."""
        # Simular error en npm run build (el 4to comando en ejecutarse)
        side_effects = [
            MagicMock(exit_code=0), # pkill
            MagicMock(exit_code=0), # chown
            MagicMock(exit_code=0), # rm
            MagicMock(exit_code=1, stdout="Error: Type Mismatch in page.tsx", stderr="FAIL") # build
        ]
        self.mock_sbx.commands.run.side_effect = side_effects
        
        result = self.deployer.deploy()
        
        self.assertIn("La compilación falló", result)
        self.assertIn("Type Mismatch", result)

    @patch("time.monotonic")
    @patch("time.sleep", return_value=None)
    @patch("urllib.request.urlopen")
    def test_deploy_timeout(self, mock_urlopen, mock_sleep, mock_time):
        """Verifica el comportamiento cuando el servidor nunca responde (timeout)."""
        self.mock_sbx.commands.run.return_value = MagicMock(exit_code=0)
        
        # Simular que el servidor siempre falla
        mock_urlopen.side_effect = Exception("Connection Refused")
        
        # Simular paso del tiempo para el timeout (120s)
        mock_time.side_effect = [0, 10, 20, 130] # El 4to valor supera el timeout de 120s
        
        result = self.deployer.deploy()
        
        self.assertIn("Timeout: El servidor no respondió", result)

if __name__ == "__main__":
    unittest.main()
