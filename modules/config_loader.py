import os
from pathlib import Path
from dataclasses import dataclass

import yaml


@dataclass
class ApiConfig:
    provider: str
    api_key: str
    base_url: str
    model: str


@dataclass
class BaiduOcrConfig:
    api_key: str
    secret_key: str


@dataclass
class StyleConfig:
    default: str
    custom_prompt: str


@dataclass
class MonitorConfig:
    check_interval: int
    reply_delay_min: int
    reply_delay_max: int


@dataclass
class Config:
    api: ApiConfig
    baidu_ocr: BaiduOcrConfig
    style: StyleConfig
    monitor: MonitorConfig


def load_config(config_path: str | None = None) -> Config:
    if config_path is None:
        config_path = Path(__file__).parent.parent / "config.yaml"

    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    api_data = data.get("api", {})
    api_key = os.environ.get("DEEPSEEK_API_KEY") or api_data.get("api_key", "")

    api_config = ApiConfig(
        provider=api_data.get("provider", "deepseek"),
        api_key=api_key,
        base_url=api_data.get("base_url", "https://api.deepseek.com"),
        model=api_data.get("model", "deepseek-chat"),
    )

    ocr_data = data.get("baidu_ocr", {})
    baidu_ocr_config = BaiduOcrConfig(
        api_key=os.environ.get("BAIDU_OCR_API_KEY") or ocr_data.get("api_key", ""),
        secret_key=os.environ.get("BAIDU_OCR_SECRET_KEY") or ocr_data.get("secret_key", ""),
    )

    style_data = data.get("style", {})
    style_config = StyleConfig(
        default=style_data.get("default", "阴阳怪气"),
        custom_prompt=style_data.get("custom_prompt", ""),
    )

    monitor_data = data.get("monitor", {})
    monitor_config = MonitorConfig(
        check_interval=monitor_data.get("check_interval", 2),
        reply_delay_min=monitor_data.get("reply_delay_min", 1),
        reply_delay_max=monitor_data.get("reply_delay_max", 3),
    )

    return Config(
        api=api_config,
        baidu_ocr=baidu_ocr_config,
        style=style_config,
        monitor=monitor_config,
    )
