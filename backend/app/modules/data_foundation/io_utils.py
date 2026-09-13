from __future__ import annotations

from pathlib import Path
from typing import Any
import csv
import json
import os
import time

def read_json(path: Path | str) -> Any:
    path_obj = Path(path) if isinstance(path, str) else path
    with path_obj.open("r", encoding="utf-8") as handle:
        return json.load(handle)

def read_csv(path: Path | str) -> list[dict[str, str]]:
    path_obj = Path(path) if isinstance(path, str) else path
    with path_obj.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))

def write_csv(path: Path | str, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path_obj = Path(path) if isinstance(path, str) else path
    path_obj.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = fieldnames or (list(rows[0].keys()) if rows else [])
    for attempt in range(5):
        try:
            if path_obj.exists():
                try:
                    os.chmod(path_obj, 0o666)
                except Exception:
                    pass
            with path_obj.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
                writer.writeheader()
                writer.writerows(rows)
            return
        except PermissionError:
            time.sleep(0.5)

def write_json(path: Path | str, value: Any) -> None:
    path_obj = Path(path) if isinstance(path, str) else path
    path_obj.parent.mkdir(parents=True, exist_ok=True)
    path_obj.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

def write_md(path: Path | str, text: str | list[str]) -> None:
    path_obj = Path(path) if isinstance(path, str) else path
    path_obj.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(text, list):
        text_content = "\n".join(text)
    else:
        text_content = text
    path_obj.write_text(text_content.strip() + "\n", encoding="utf-8")
