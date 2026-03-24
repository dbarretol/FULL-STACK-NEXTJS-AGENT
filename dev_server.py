"""
Script independiente para levantar el servidor de desarrollo en el sandbox E2B activo.
Ejecutar en una terminal separada mientras el agente está corriendo:

    python dev_server.py

Lee el sandbox_id desde .sandbox_id (generado automáticamente al iniciar el agente).
Mata cualquier proceso Node.js previo, lanza `npm run dev` y muestra la URL pública.
"""
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from e2b_code_interpreter import Sandbox

WORKDIR = "/home/user/app"
PORT = 3000
POLL_INTERVAL = 3
SERVER_TIMEOUT = 120  # segundos esperando que levante


def _read_sandbox_id() -> str:
    """Lee el sandbox_id desde .sandbox_id."""
    id_file = Path(".sandbox_id")
    if not id_file.exists():
        print("❌ No se encontró .sandbox_id — inicia el agente primero.")
        sys.exit(1)
    sandbox_id = id_file.read_text().strip()
    if not sandbox_id:
        print("❌ .sandbox_id está vacío.")
        sys.exit(1)
    return sandbox_id


def _get_url(sbx: Sandbox) -> str:
    """Retorna la URL pública del sandbox en el puerto configurado."""
    return f"https://{sbx.get_host(PORT)}"


def _is_ready(url: str) -> bool:
    """Verifica si el servidor responde en la URL dada."""
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            return resp.status < 500
    except urllib.error.HTTPError as e:
        return e.code < 500
    except Exception:
        return False


def main() -> None:
    """Conecta al sandbox activo y levanta el servidor de desarrollo."""
    sandbox_id = _read_sandbox_id()
    print(f"🔌 Conectando al sandbox: {sandbox_id}")

    sbx = Sandbox.connect(sandbox_id)
    url = _get_url(sbx)
    print(f"🌐 URL pública: {url}")

    # Mata procesos Node.js previos para liberar el puerto
    print("🔄 Deteniendo servidor anterior (si existe)...")
    try:
        sbx.commands.run(
            f"pkill -u $(id -u) -f next 2>/dev/null; pkill -u $(id -u) -f node 2>/dev/null; sleep 1; exit 0",
            timeout=10,
        )
    except Exception:
        pass

    # Diagnóstico previo: verificar que el directorio y package.json existen
    print("🔍 Verificando entorno...")
    try:
        check = sbx.commands.run(
            f"ls {WORKDIR}/package.json 2>&1 && cat {WORKDIR}/package.json | python3 -c \"import sys,json; s=json.load(sys.stdin); print('scripts:', list(s.get('scripts',{{}}).keys()))\"",
            timeout=10,
        )
        print(f"   package.json: {check.stdout.strip()}")
    except Exception as e:
        print(f"   ⚠️  No se encontró package.json en {WORKDIR}: {e}")
        print("   El agente aún no ha generado la app. Ejecuta el agente primero.")
        return

    # Arregla ownership y limpia .next
    print("🧹 Arreglando permisos y limpiando caché .next...")
    try:
        result = sbx.commands.run(
            f"sudo chown -R $(id -u):$(id -g) {WORKDIR} && rm -rf {WORKDIR}/.next",
            timeout=20,
        )
        print(f"   chown+rm: exit={result.exit_code} {result.stderr.strip() if result.stderr else ''}")
    except Exception as e:
        print(f"   ⚠️  {e}")

    # Elimina el package-lock.json suelto en /home/user que confunde a Turbopack
    try:
        sbx.commands.run("rm -f /home/user/package-lock.json /home/user/package.json", timeout=5)
    except Exception:
        pass

    # Lanza el servidor con background=True (E2B mantiene el proceso vivo)
    log_file = "/tmp/dev_server.log"
    print(f"🚀 Iniciando: npm run dev -- -H 0.0.0.0")
    proc = sbx.commands.run(
        "npm run dev -- -H 0.0.0.0",
        cwd=WORKDIR,
        background=True,
    )
    time.sleep(5)
    # Leer output inicial del proceso background
    try:
        log = sbx.commands.run(f"cat {log_file} 2>/dev/null", timeout=5)
        if log.stdout.strip():
            print(f"   📋 Log inicial:\n   " + log.stdout.strip().replace("\n", "\n   "))
    except Exception:
        pass

    # Espera a que el servidor esté listo
    print(f"⏳ Esperando que el servidor levante (máx {SERVER_TIMEOUT}s)...")
    deadline = time.monotonic() + SERVER_TIMEOUT
    attempt = 0
    while time.monotonic() < deadline:
        attempt += 1
        if _is_ready(url):
            print(f"\n✅ Servidor listo en {attempt * POLL_INTERVAL}s")
            print(f"\n🌐 Abre en el navegador: {url}\n")
            return
        # Mostrar estado del puerto cada 15s para diagnóstico
        if attempt % 5 == 0:
            try:
                log = sbx.commands.run(f"tail -8 {log_file} 2>/dev/null", timeout=5)
                print(f"\n   📋 Log ({attempt * POLL_INTERVAL}s):\n   " + (log.stdout.strip() or "(vacío)").replace("\n", "\n   "))
            except Exception:
                pass
        print(f"   [{attempt * POLL_INTERVAL}s] Esperando...", end="\r")
        time.sleep(POLL_INTERVAL)

    # Timeout: mostrar log completo
    print(f"\n⚠️  El servidor no respondió en {SERVER_TIMEOUT}s.")
    try:
        log = sbx.commands.run(f"cat {log_file} 2>/dev/null", timeout=5)
        print(f"\n📋 Log completo:\n{log.stdout.strip() or '(vacío)'}")
    except Exception:
        pass
    print(f"\n   Intenta abrir igualmente: {url}")


if __name__ == "__main__":
    main()
