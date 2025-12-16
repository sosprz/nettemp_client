from __future__ import annotations

import os
from pathlib import Path


_DEFAULT_DIR = Path.home() / ".nettemp_client"


def _env_path(name: str) -> Path | None:
    value = os.environ.get(name)
    if not value:
        return None
    value = value.strip()
    if not value:
        return None
    return Path(value).expanduser()


def get_data_dir() -> Path:
    """
    Directory for runtime/state files (pidfiles, logs, generated configs).

    Defaults to `~/.nettemp_client` and can be overridden via `NETTEMP_DATA_DIR`.
    """
    return _env_path("NETTEMP_DATA_DIR") or _DEFAULT_DIR


def get_config_dir() -> Path:
    """
    Directory for editable configuration files.

    Resolution order:
    1) `NETTEMP_CONFIG_DIR` if set
    2) current working directory if it already contains config files (backward compatible)
    3) `NETTEMP_DATA_DIR` (single-dir setup)
    4) `~/.nettemp_client`
    """
    explicit = _env_path("NETTEMP_CONFIG_DIR")
    if explicit:
        return explicit

    # Preferred single-directory setup: keep editable configs with runtime data.
    data_dir = get_data_dir()
    if (
        (data_dir / "config.conf").exists()
        or (data_dir / "drivers_config.yaml").exists()
        or (data_dir / "mqtt_rules.yaml").exists()
    ):
        return data_dir

    # Backward compatibility: if configs exist next to the code / in the working directory, use them.
    candidates = [
        Path.cwd(),
        Path(__file__).resolve().parent,
        Path(__file__).resolve().parent.parent,
    ]
    for candidate in candidates:
        if (
            (candidate / "config.conf").exists()
            or (candidate / "drivers_config.yaml").exists()
            or (candidate / "mqtt_rules.yaml").exists()
        ):
            return candidate

    return data_dir


def get_config_file() -> Path:
    return get_config_dir() / "config.conf"


def get_drivers_file() -> Path:
    return get_config_dir() / "drivers_config.yaml"


def get_mqtt_rules_file() -> Path:
    return get_config_dir() / "mqtt_rules.yaml"


def get_pidfile() -> Path:
    return get_data_dir() / ".nettemp_client.pid"


def get_theengs_gateway_config_file() -> Path:
    return get_config_dir() / "theengs_gateway_config.json"


def get_mqtt_topic_log_file() -> Path:
    return get_data_dir() / "mqtt_topics.log"
