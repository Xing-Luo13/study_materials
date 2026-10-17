# -*- coding: utf-8 -*-
"""检查 site/ 内所有本地链接是否指向真实文件。"""
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

SITE = Path(__file__).resolve().parent.parent / "site"
PREFIX = "/study_materials"


def main() -> int:
    missing, checked = [], 0
    for html_file in SITE.rglob("*.html"):
        text = html_file.read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r'(?:href|src)="([^"]+)"', text):
            raw = m.group(1)
            if raw.startswith(("http://", "https://", "mailto:", "#", "javascript:", "data:")):
                continue
            path = unquote(urlsplit(raw).path)
            if not path:
                continue
            if path == PREFIX or path.startswith(PREFIX + "/"):
                target = SITE / path[len(PREFIX):].lstrip("/")
            else:
                target = (html_file.parent / path).resolve()
            if path.endswith("/") or target.is_dir():
                target = target / "index.html"
            checked += 1
            if not target.exists():
                missing.append((str(html_file.relative_to(SITE)), raw))
    print(f"checked={checked} missing={len(missing)}")
    for row in missing[:20]:
        print("MISSING:", row)
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
