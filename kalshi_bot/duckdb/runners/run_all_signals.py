import os
import subprocess
import sys


from kalshi_bot.util.logger import get_logger

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CONFIG_DIR = BASE_DIR.parent / "config"


logger = get_logger('signal_runner')

def get_configs():
    return [
        os.path.join(CONFIG_DIR, f)
        for f in os.listdir(CONFIG_DIR)
        if f.endswith(".json")
    ]

def main():
    configs = get_configs()

    if not configs:
        logger.info("No configs found!")
        return

    procs = []

    for cfg in configs:
        cmd = [
            sys.executable,
            f"{BASE_DIR}/run_signal.py",
            "--config_path", cfg,
        ]
        print("COMD", cmd)
        procs.append((cfg, subprocess.Popen(cmd)))

    for cfg, p in procs:
        rc = p.wait()
        if rc != 0:
            print(f"❌ {cfg} failed with code {rc}")
        else:
            print(f"✅ {cfg} finished")

if __name__ == '__main__':
    main()