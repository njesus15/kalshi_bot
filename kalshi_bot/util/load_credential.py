import tomli
from pathlib import Path


def load_credentials() -> tuple[str, str]:
    secrets_path = Path.home() / ".secrets.toml"
    with open(secrets_path, "rb") as f:
        secrets = tomli.load(f)
    api = secrets["api"]["kalshi"]
    pk = secrets["crypto"]["private_key_pem"]
    return api, pk