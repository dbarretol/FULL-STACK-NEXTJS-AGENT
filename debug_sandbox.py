import sys
import os
from pathlib import Path
from dotenv import load_dotenv
from e2b_code_interpreter import Sandbox

load_dotenv()

WORKDIR = "/home/user/app"

def check_sandbox():
    id_file = Path(".sandbox_id")
    if not id_file.exists():
        print("Sandbox ID file not found.")
        return

    sandbox_id = id_file.read_text().strip()
    print(f"Connecting to sandbox: {sandbox_id}")
    
    try:
        sbx = Sandbox.connect(sandbox_id)
        
        # Check disk space
        print("\n--- Disk Space ---")
        res = sbx.commands.run("df -h /home/user", timeout=10)
        print(res.stdout)
        
        # Check memory
        print("\n--- Memory (before build) ---")
        res = sbx.commands.run("free -m", timeout=10)
        print(res.stdout)
        
        # ATTEMPT BUILD
        print("\n--- Attempting Build (Timeout 300s) ---")
        try:
            res = sbx.commands.run("npm run build", cwd=WORKDIR, timeout=300)
            print(f"Build Exit Code: {res.exit_code}")
            if res.exit_code != 0:
                print(f"Build Output: {res.stdout[-500:]}")
                print(f"Build Stderr: {res.stderr[-500:]}")
        except Exception as e:
            print(f"Build Exception: {e}")
        
        # Check memory after build
        print("\n--- Memory (after build) ---")
        res = sbx.commands.run("free -m", timeout=10)
        print(res.stdout)
        
        # Check app directory and node_modules
        print("\n--- App Directory & node_modules ---")
        res = sbx.commands.run(f"ls -la {WORKDIR}/node_modules/.bin/next || echo 'next binary not found'", timeout=10)
        print(res.stdout)
        
        # Check for processes on port 3000
        print("\n--- Port 3000 ---")
        res = sbx.commands.run("ss -tlnp | grep :3000 || echo 'Nothing on port 3000'", timeout=10)
        print(res.stdout)
        
        # Check current processes
        print("\n--- Processes ---")
        res = sbx.commands.run("ps aux | grep -E 'node|next'", timeout=10)
        print(res.stdout)
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_sandbox()
