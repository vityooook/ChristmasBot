from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_LOCALES_DIR = Path(__file__).parent / "locales"
_cache: dict[str, dict] = {}


def _load_locale(lang: str) -> dict:
    if lang not in _cache:
        path = _LOCALES_DIR / f"{lang}.yml"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                _cache[lang] = yaml.safe_load(f) or {}
        else:
            _cache[lang] = {}
    return _cache[lang]


def tr(key: str, lang: str = "ru", **kwargs: Any) -> str:
    """
    Получить текст по ключу из локализации.
    
    Пример: tr("start.welcome", name="Вася") → "Привет, Вася!"
    
    Ключ может быть вложенным: "start.conditions.title"
    """
    data = _load_locale(lang)
    
    # Разбираем вложенные ключи: "start.welcome" → data["start"]["welcome"]
    keys = key.split(".")
    value = data
    for k in keys:
        if isinstance(value, dict):
            value = value.get(k)
        else:
            value = None
            break
    
    if value is None:
        return f"[{key}]"  # Если ключ не найден — показываем placeholder
    
    if isinstance(value, str) and kwargs:
        return value.format(**kwargs)
    
    return str(value)

