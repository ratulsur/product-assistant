from pathlib import Path
import yaml

def load_config():
    """
    Loads the YAML configuration file from product_assistant/config/config.yaml
    regardless of current working directory.
    """
    # This file lives in product_assistant/utils/config_loader.py
    # We want: product_assistant/config/config.yaml
    base_dir = Path(__file__).resolve().parents[1]  # -> product_assistant/
    config_path = base_dir / "config" / "config.yaml"

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
