# -*- coding: utf-8 -*-
"""从整理好的资料目录生成 MkDocs 站点源文件。

源目录：F:\\claude\\考试资料-整理
输出：  本仓库的 docs/ 与 mkdocs.yml
"""
from __future__ import annotations

import csv
import html
import shutil
from pathlib import Path
from urllib.parse import quote

import yaml

SRC = Path(r"F:\claude\考试资料-整理")
ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"

SITE_URL = "https://xing-luo13.github.io/study_materials/"
REPO = "Xing-Luo13/study_materials"

# 展示顺序：按培养方案学期，专业选修放在最后
SEMESTERS = [
    ("大一上", "第一学期"),
    ("大一下", "第二学期"),
    ("大二上", "第四学期"),
    ("大二下", "第五学期"),
    ("大三上", "第七学期"),
    ("大三下", "第八学期"),
    ("大四上", "第十学期"),
    ("大四下", "第十一学期"),
    ("专业选修课（培养方案未指定学期）", "培养方案未指定学期"),
]
SEM_ICONS = {
    "大一上": "numeric-1-circle",
    "大一下": "numeric-2-circle",
    "大二上": "numeric-3-circle",
    "大二下": "numeric-4-circle",
    "大三上": "numeric-5-circle",
    "大三下": "numeric-6-circle",
    "大四上": "numeric-7-circle",
    "大四下": "numeric-8-circle",
    "专业选修课（培养方案未指定学期）": "book-plus",
}
CATEGORIES = ["期中", "期末", "其他资料"]
CAT_CLASS = {"期中": "midterm", "期末": "final", "其他资料": "other"}


def esc(text: str) -> str:
    return html.escape(str(text), quote=True)


def href(rel: str) -> str:
    return quote(rel, safe="/")


def fmt_size(num: int) -> str:
    if num >= 1024 * 1024:
        return f"{num / 1048576:.1f} MB"
    if num >= 1024:
        return f"{num / 1024:.0f} KB"
    return f"{num} B"


def load_notes() -> dict[tuple[str, str, str, str], str]:
    notes: dict[tuple[str, str, str, str], str] = {}
    csv_path = SRC / "资料清单.csv"
    with csv_path.open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            key = (row["学期"], row["课程"], row["类别"], row["整理后文件名"])
            notes[key] = (row.get("备注") or "").strip()
    return notes


def collect_tree() -> dict[str, dict[str, dict[str, list[Path]]]]:
    tree: dict[str, dict[str, dict[str, list[Path]]]] = {}
    for sem, _ in SEMESTERS:
        sem_dir = SRC / sem
        if not sem_dir.is_dir():
            continue
        courses: dict[str, dict[str, list[Path]]] = {}
        for course_dir in sorted(p for p in sem_dir.iterdir() if p.is_dir()):
            cats: dict[str, list[Path]] = {}
            for cat in CATEGORIES:
                cat_dir = course_dir / cat
                if not cat_dir.is_dir():
                    continue
                files = sorted(p for p in cat_dir.iterdir() if p.is_file())
                if files:
                    cats[cat] = files
            if cats:
                courses[course_dir.name] = cats
        tree[sem] = courses
    return tree


def copy_files(tree) -> None:
    for sem, courses in tree.items():
        for course, cats in courses.items():
            for cat, files in cats.items():
                dest = DOCS / sem / course / "files" / cat
                dest.mkdir(parents=True, exist_ok=True)
                for src_file in files:
                    shutil.copy2(src_file, dest / src_file.name)


def stats_of(cats: dict[str, list[Path]]) -> tuple[int, int]:
    count = sum(len(v) for v in cats.values())
    size = sum(p.stat().st_size for v in cats.values() for p in v)
    return count, size


def chips_html(sem_courses: dict[str, dict[str, list[Path]]], total_count: int, total_size: int) -> str:
    parts = []
    for cat in CATEGORIES:
        n = sum(len(cats.get(cat, [])) for cats in sem_courses.values())
        if n:
            parts.append(f'<span class="chip chip-{CAT_CLASS[cat]}">{cat} {n}</span>')
    parts.append(f'<span class="chip chip-total">共 {total_count} 份 · {fmt_size(total_size)}</span>')
    return '<div class="stat-chips">' + "".join(parts) + "</div>"


def course_page(sem: str, course: str, cats: dict[str, list[Path]], notes) -> str:
    total, size = stats_of(cats)
    lines = [
        f"# {course}",
        "",
        f'<p class="back-link"><a href="../">← 返回 {esc(sem)}</a></p>',
        "",
        chips_html({course: cats}, total, size),
        "",
    ]
    for cat in CATEGORIES:
        files = cats.get(cat)
        if not files:
            continue
        lines += [
            f"## {cat}",
            "",
            "| 文件 | 格式 | 大小 | 备注 |",
            "|---|---|---:|---|",
        ]
        for f in files:
            note = notes.get((sem, course, cat, f.name), "")
            note = note.replace("|", "\\|")
            ext = f.suffix.lower().lstrip(".") or "file"
            cls = "preview" if ext == "pdf" else "download"
            rel = f"files/{cat}/{f.name}"
            name = esc(f.name)
            lines.append(
                f'| <a class="file-link {cls}" href="{href(rel)}" target="_blank" rel="noopener">'
                f'<span class="ext ext-{esc(ext)}">{esc(ext.upper())}</span>{name}</a> '
                f"| {esc(ext.upper())} | {fmt_size(f.stat().st_size)} | {note or '—'} |"
            )
        lines.append("")
    lines += [
        "!!! info \"使用提示\"",
        "    资料来自网络收集与学长学姐分享，仅供个人学习交流，请勿用于商业用途。"
        "若侵犯了您的权益，请联系删除。",
        "",
    ]
    return "\n".join(lines)


def semester_page(sem: str, plan_sem: str, courses: dict[str, dict[str, list[Path]]], notes) -> str:
    if not courses:
        placeholder = SRC / sem / "暂无资料.md"
        body = ""
        if placeholder.is_file():
            body = placeholder.read_text(encoding="utf-8")
            body = body.split("\n", 1)[1].strip() if body.startswith("#") else body.strip()
        return f"# {sem}\n\n" + body + "\n"
    total = sum(stats_of(c)[0] for c in courses.values())
    size = sum(stats_of(c)[1] for c in courses.values())
    lines = [f"# {sem}", "", chips_html(courses, total, size), ""]
    if plan_sem:
        lines += [f'<p class="sem-note">培养方案：{plan_sem}</p>', ""]
    lines += [
        "| 课程 | 期中 | 期末 | 其他资料 | 合计 |",
        "|---|---:|---:|---:|---:|",
    ]
    for course, cats in courses.items():
        counts = [len(cats.get(cat, [])) for cat in CATEGORIES]
        lines.append(
            f'| <a href="{href(course + "/")}">{esc(course)}</a> '
            f"| {counts[0]} | {counts[1]} | {counts[2]} | {sum(counts)} |"
        )
    lines += ["", "!!! tip \"怎么找资料\"", "    点课程名进入课程页；也可以直接用右上角搜索框搜课程或文件名。", ""]
    return "\n".join(lines)


def inventory_page(tree, notes) -> str:
    lines = [
        "# 资料清单",
        "",
        "全部已公开资料的完整清单（与仓库内 `docs/` 目录一致）。",
        "",
        f'<p><a class="md-button" href="../{href("资料清单.csv")}" download>下载 CSV 清单</a></p>',
        "",
        "| 学期 | 课程 | 类别 | 文件 | 大小 | 备注 |",
        "|---|---|---|---|---:|---|",
    ]
    for sem, courses in tree.items():
        for course, cats in courses.items():
            for cat in CATEGORIES:
                for f in cats.get(cat, []):
                    note = notes.get((sem, course, cat, f.name), "").replace("|", "\\|")
                    rel = f"{sem}/{course}/files/{cat}/{f.name}"
                    lines.append(
                        f"| {esc(sem)} | {esc(course)} | {cat} "
                        f'| <a href="../{href(rel)}" target="_blank" rel="noopener">{esc(f.name)}</a> '
                        f"| {fmt_size(f.stat().st_size)} | {note or '—'} |"
                    )
    lines.append("")
    return "\n".join(lines)


def about_page(total_count: int, total_size: int, course_count: int, course_rows: int) -> str:
    return f"""# 整理说明

- **整理日期**：2026-10-17
- **整理依据**：2023 版计算机科学与技术（国家拔尖计划）培养方案
- **本站范围**：培养方案内课程 + 专业选修课，共 **{course_count} 门课程、{total_count} 份资料（约 {total_size / 1073741824:.2f} GB）**
- **未收录**：非本专业课程（大学化学、工程制图、复变函数与积分变换、理论力学）不在本站发布

## 学期对应关系

培养方案的《指导性教学计划》把夏季小学期也计入“学期”，所以学期编号与通常说的“大几上/下”并不完全一致。

| 本站目录 | 培养方案学期 | 说明 |
|---|---|---|
| 大一上 | 第一学期 | 秋季长学期 |
| 大一下 | 第二学期 | 春季长学期 |
| 大二上 | 第四学期 | 第三学期为大一夏季小学期 |
| 大二下 | 第五学期 | |
| 大三上 | 第七学期 | 第六学期为大二夏季小学期 |
| 大三下 | 第八学期 | |
| 大四上 | 第十学期 | 第九学期为大三夏季小学期 |
| 大四下 | 第十一学期 | |

## 资料分类

每门课程下按考试类型分为三类：

- **期中**：期中试题、期中答案、期中复习资料
- **期末**：期末试题、期末答案、期末复习资料和全课程复习提纲
- **其他资料**：教材、教材习题答案、通用习题集、课程操作说明等

某一类没有资料的课程不会创建空分类。

## 整理规则

1. **只保留培养方案内课程的资料**，非本专业课程不发布。
2. **完全相同的重复文件只保留一份**（按 MD5 校验），共去掉 19 个重复文件。
3. **同一份复习提纲保留最新版**（思修、史纲、毛概、马原、习思想、国防），旧版不收录；共去掉 8 个。
4. **含义不清的文件已重命名**，例如 `main (2).pdf` → `2024-2025学年第二学期 大学物理（上）期中试卷.pdf`。原名见 CSV 清单。
5. **混合合集已拆分**：144 页《南卷汇》按科目拆分；113 页《梧桐资料大物往年题》按期中/期末拆分。
6. **跨课程参考**：大学计算机基础资料放在“计算概论”下；电工电子技术资料分别放在“电路”“电子技术基础”下作补充。

## 资料缺口

以下培养方案课程暂无资料，欢迎补充：

- **大一上**：学术英语素养、体育
- **大一下**：大学物理实验 I-1、英语选修、体育
- **大二上**：算法设计与分析、大学物理实验 I-2、综合工程训练 1、体育
- **大二下**：计算机系统导论、形式语言与编译、综合工程训练 2、体育
- **大三上**：操作系统、计算机网络、计算机组成原理、优化方法基础（整学期无资料）
- **大三下**：人工智能导论、数据库系统、计算机体系结构、数值分析、认知计算与机器学习（整学期无资料）
- **大四上**：项目设计及专业选修（整学期无资料）
- **大四下**：毕业设计、论文写作与发表、计算机科研习课（仅有形势与政策）

## 使用建议

- **数学 / 物理 / 电路**：优先刷近 3–5 年真题，再用彭康 / 南卷汇 / 治学集的分类题集补题型。
- **思政**：直接用钱学组最新版复习提纲，考前一周配合真题回忆版背重点。
- **计算机专业课**：资料包中只有程序设计、离散数学、数据结构的少量资料；OS、网络、组成、数据库等建议另行收集。
- **压缩包**（概率论期中、复积、工图等）保持原样，未解压。

## 免责声明

本站资料均来自网络收集与学长学姐分享，**仅供个人学习交流，请勿用于商业用途**。资料版权归原作者及原单位所有；如有侵权，请在仓库提交 Issue 或联系站主，会尽快删除。

!!! warning "注意"
    试题与答案可能存在错漏，请以课程实际要求为准；涉及培养方案的内容以教务系统为准。
"""


def home_page(tree, total_count: int, total_size: int, course_count: int) -> str:
    cards = []
    for sem, plan_sem in SEMESTERS:
        courses = tree.get(sem, {})
        n = sum(stats_of(c)[0] for c in courses.values())
        m = len(courses)
        icon = SEM_ICONS.get(sem, "book")
        display = "专业选修课" if sem.startswith("专业选修") else sem
        sub = f"{m} 门课程 · {n} 份资料" if n else "暂无资料"
        link = f"{href(sem + '/')}index.md"
        cards.append(
            f'-   :material-{icon}:{{ .lg .middle }} __{esc(display)}__\n\n'
            f"    ---\n\n"
            f"    {sub}\n\n"
            f"    [:octicons-arrow-right-24: 进入]({link})"
        )
    cards_md = "\n\n".join(cards)
    return f"""<div class="hero" markdown>

<span class="hero-kicker">XJTU · 计算机科学与技术</span>

# 西交计算机考试资料库

历届试题、答案与复习资料，按 **学期 → 课程 → 考试类型** 归档，支持站内搜索。

<div class="hero-stats">
  <span><b>{total_count}</b> 份资料</span>
  <span><b>{course_count}</b> 门课程</span>
  <span><b>{total_size / 1073741824:.2f} GB</b></span>
</div>

</div>

## 按学期浏览

<div class="grid cards" markdown>

{cards_md}

</div>

## 快捷入口

<div class="grid cards" markdown>

-   :material-format-list-bulleted:{{ .lg .middle }} __完整资料清单__

    ---

    按课程与类别列出全部 {total_count} 份文件，可下载 CSV。

    [:octicons-arrow-right-24: 查看清单](资料清单.md)

-   :material-information-outline:{{ .lg .middle }} __整理说明__

    ---

    归档规则、学期对应关系、资料缺口与免责声明。

    [:octicons-arrow-right-24: 阅读说明](整理说明.md)

</div>

!!! info "免责声明"
    本站资料来自网络收集与学长学姐分享，仅供个人学习交流，请勿用于商业用途。版权归原作者所有，如有侵权请联系删除。
"""


def build_nav(tree) -> list:
    nav = [{"首页": "index.md"}]
    for sem, plan_sem in SEMESTERS:
        display = "专业选修课" if sem.startswith("专业选修") else sem
        courses = tree.get(sem, {})
        items = [f"{sem}/index.md"]
        for course in courses:
            items.append({course: f"{sem}/{course}/index.md"})
        nav.append({display: items})
    nav.append({"资料清单": "资料清单.md"})
    nav.append({"整理说明": "整理说明.md"})
    return nav


def write_mkdocs(tree) -> None:
    nav_yaml = yaml.safe_dump(
        build_nav(tree), allow_unicode=True, default_flow_style=False, sort_keys=False
    )
    nav_indented = "\n".join("  " + line for line in nav_yaml.rstrip().splitlines())
    config = f"""site_name: 西交计算机 · 考试资料库
site_url: {SITE_URL}
site_description: 西安交通大学计算机科学与技术（国家拔尖计划）课程考试资料整理
site_author: Xing-Luo13
repo_url: https://github.com/{REPO}
repo_name: {REPO}
edit_uri: ""
copyright: 资料仅供学习交流，版权归原作者所有

theme:
  name: material
  language: zh
  font: false
  icon:
    logo: material/bookshelf
    repo: fontawesome/brands/github
  palette:
    - media: "(prefers-color-scheme: light)"
      scheme: default
      primary: indigo
      accent: deep purple
      toggle:
        icon: material/weather-night
        name: 切换到深色模式
    - media: "(prefers-color-scheme: dark)"
      scheme: slate
      primary: indigo
      accent: deep purple
      toggle:
        icon: material/weather-sunny
        name: 切换到浅色模式
  features:
    - navigation.indexes
    - navigation.top
    - navigation.tracking
    - navigation.footer
    - search.suggest
    - search.highlight
    - search.share
    - toc.follow
    - content.code.copy
    - content.tooltips

plugins:
  - search:
      lang:
        - zh
        - en

markdown_extensions:
  - admonition
  - attr_list
  - md_in_html
  - tables
  - toc:
      permalink: true
      toc_depth: 3
  - pymdownx.details
  - pymdownx.emoji:
      emoji_index: !!python/name:material.extensions.emoji.twemoji
      emoji_generator: !!python/name:material.extensions.emoji.to_svg
  - pymdownx.highlight
  - pymdownx.inlinehilite
  - pymdownx.superfences

extra_css:
  - stylesheets/extra.css

nav:
{nav_indented}
"""
    (ROOT / "mkdocs.yml").write_text(config, encoding="utf-8")


def write_readme(stats) -> None:
    total_count, total_size, course_count, _ = stats
    (ROOT / "README.md").write_text(
        f"""# 西交计算机考试资料库

西安交通大学计算机科学与技术（国家拔尖计划）课程考试资料整理。

- 站点：{SITE_URL}
- 资料：{course_count} 门课程，{total_count} 份文件，约 {total_size / 1073741824:.2f} GB
- 结构：学期 → 课程 → 期中 / 期末 / 其他资料

资料来自网络收集与学长学姐分享，仅供个人学习交流，请勿用于商业用途。如有侵权请联系删除。

## 本地构建

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt
.venv/Scripts/mkdocs serve
```
""",
        encoding="utf-8",
    )


def main() -> None:
    if DOCS.exists():
        shutil.rmtree(DOCS)
    DOCS.mkdir(parents=True)
    (DOCS / "stylesheets").mkdir()
    (DOCS / "stylesheets" / "extra.css").write_text(CSS, encoding="utf-8")

    notes = load_notes()
    tree = collect_tree()
    copy_files(tree)

    course_count = sum(len(courses) for courses in tree.values())
    total_count = sum(stats_of(c)[0] for courses in tree.values() for c in courses.values())
    total_size = sum(stats_of(c)[1] for courses in tree.values() for c in courses.values())

    for sem, plan_sem in SEMESTERS:
        sem_dir = DOCS / sem
        sem_dir.mkdir(parents=True, exist_ok=True)
        courses = tree.get(sem, {})
        (sem_dir / "index.md").write_text(
            semester_page(sem, plan_sem, courses, notes), encoding="utf-8"
        )
        for course, cats in courses.items():
            course_dir = sem_dir / course
            course_dir.mkdir(parents=True, exist_ok=True)
            (course_dir / "index.md").write_text(
                course_page(sem, course, cats, notes), encoding="utf-8"
            )

    (DOCS / "index.md").write_text(
        home_page(tree, total_count, total_size, course_count), encoding="utf-8"
    )
    (DOCS / "资料清单.md").write_text(inventory_page(tree, notes), encoding="utf-8")
    shutil.copy2(SRC / "资料清单.csv", DOCS / "资料清单.csv")
    (DOCS / "整理说明.md").write_text(
        about_page(total_count, total_size, course_count, len(tree)), encoding="utf-8"
    )

    write_mkdocs(tree)
    write_readme((total_count, total_size, course_count, len(tree)))

    print(f"courses={course_count} materials={total_count} size={total_size/1048576:.1f}MB")


CSS = r"""
/* ---------- 字体：优先系统中文字体，避免依赖 Google Fonts ---------- */
:root {
  --md-text-font: "Noto Sans SC", "Source Han Sans SC", "PingFang SC",
    "Microsoft YaHei", "Segoe UI", system-ui, sans-serif;
  --md-code-font: "JetBrains Mono", "Cascadia Code", Consolas, monospace;
}

.md-grid {
  max-width: 76rem;
}

/* ---------- 首页 Hero ---------- */
.hero {
  padding: 2.6rem 2rem;
  margin: 0.5rem 0 1.6rem;
  border-radius: 1rem;
  background: linear-gradient(135deg, #3949ab 0%, #5e35b1 55%, #7b1fa2 100%);
  color: #fff;
  box-shadow: 0 10px 30px rgba(57, 73, 171, 0.25);
}

.hero h1 {
  color: #fff !important;
  font-weight: 700;
  margin: 0.2rem 0 0.6rem;
}

.hero p {
  color: rgba(255, 255, 255, 0.88);
  font-size: 0.95rem;
  margin: 0;
}

.hero-kicker {
  display: inline-block;
  font-size: 0.72rem;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  opacity: 0.85;
  border: 1px solid rgba(255, 255, 255, 0.45);
  border-radius: 99px;
  padding: 0.15rem 0.7rem;
}

.hero-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 1.6rem;
  margin-top: 1.4rem;
  font-size: 0.85rem;
}

.hero-stats b {
  display: block;
  font-size: 1.5rem;
  line-height: 1.2;
}

[data-md-color-scheme="slate"] .hero {
  background: linear-gradient(135deg, #283593 0%, #4527a0 55%, #6a1b9a 100%);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.45);
}

/* ---------- 统计胶囊 ---------- */
.stat-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin: 0.4rem 0 1.2rem;
}

.chip {
  display: inline-block;
  padding: 0.16rem 0.7rem;
  border-radius: 99px;
  font-size: 0.74rem;
  font-weight: 600;
  line-height: 1.6;
  border: 1px solid transparent;
}

.chip-midterm {
  color: #1565c0;
  background: rgba(21, 101, 192, 0.12);
  border-color: rgba(21, 101, 192, 0.25);
}

.chip-final {
  color: #c62828;
  background: rgba(198, 40, 40, 0.12);
  border-color: rgba(198, 40, 40, 0.25);
}

.chip-other {
  color: #5d4037;
  background: rgba(93, 64, 55, 0.1);
  border-color: rgba(93, 64, 55, 0.22);
}

.chip-total {
  color: var(--md-default-fg-color);
  background: var(--md-default-fg-color--lightest);
  border-color: var(--md-default-fg-color--lighter);
}

[data-md-color-scheme="slate"] .chip-midterm { color: #90caf9; background: rgba(144, 202, 249, 0.12); }
[data-md-color-scheme="slate"] .chip-final { color: #ef9a9a; background: rgba(239, 154, 154, 0.12); }
[data-md-color-scheme="slate"] .chip-other { color: #bcaaa4; background: rgba(188, 170, 164, 0.12); }

/* ---------- 文件链接 ---------- */
.file-link {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  text-decoration: none !important;
  font-weight: 500;
}

.file-link:hover {
  text-decoration: underline !important;
}

.ext {
  display: inline-block;
  min-width: 2.5rem;
  padding: 0.05rem 0.3rem;
  border-radius: 0.25rem;
  font-size: 0.62rem;
  font-weight: 700;
  text-align: center;
  letter-spacing: 0.03em;
  color: #fff;
  background: #78909c;
  flex: none;
}

.ext-pdf { background: #d32f2f; }
.ext-zip, .ext-rar { background: #f57c00; }
.ext-doc, .ext-docx { background: #2b579a; }

/* ---------- 表格 ---------- */
.md-typeset table:not([class]) th {
  background: var(--md-default-fg-color--lightest);
  font-weight: 600;
}

.md-typeset table:not([class]) tr:hover {
  background: var(--md-default-fg-color--lightest);
}

/* ---------- 卡片 ---------- */
.md-typeset .grid.cards > ul > li {
  border-radius: 0.55rem;
  transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;
}

.md-typeset .grid.cards > ul > li:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 22px rgba(0, 0, 0, 0.12);
  border-color: var(--md-accent-fg-color);
}

.md-typeset .grid.cards .lg {
  color: var(--md-primary-fg-color);
}

/* ---------- 其它 ---------- */
.back-link {
  margin: -0.4rem 0 0.8rem;
}

.back-link a {
  font-size: 0.8rem;
  color: var(--md-default-fg-color--light);
}

.sem-note {
  color: var(--md-default-fg-color--light);
  font-size: 0.8rem;
  margin-top: -0.6rem;
}
"""


if __name__ == "__main__":
    main()
