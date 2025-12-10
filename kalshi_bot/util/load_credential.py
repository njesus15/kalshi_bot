import tomli
from pathlib import Path


def load_credentials() -> tuple[str, str]:
    secrets = tomli.load(open(Path("~/.secrets.toml"), "rb"))
    api = secrets["api"]["kalshi"]
    pk = secrets["crypto"]["private_key_pem"]
    return api, pk