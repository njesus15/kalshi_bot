import os
import subprocess
import sys


from kalshi_bot.util.logger import get_logger


CONFIG_DIR = "../config"


logger = get_logger('signal_runner')

def get_configs():
    return [
        os.path.join(CONFIG_DIR, f)
        for f in os.listdir(CONFIG_DIR)
        if f.endswith(".json")
    ]

def main():
    configs = get_configs(s)

    if not configs:
        logger.info("No configs found!")
        return

    procs = []

    for cfg in configs:
        cmd = [
            sys.executable,
            "run_signal.py",
            "--config_path", cfg,
        ]
        procs.append((cfg, subprocess.Popen(cmd)))

    for cfg, p in procs:
        rc = p.wait()
        if rc != 0:
            print(f"❌ {cfg} failed with code {rc}")
        else:
            print(f"✅ {cfg} finished")

if __name__ == '__main__':
    main()