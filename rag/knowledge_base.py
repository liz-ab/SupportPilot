"""Load the enterprise knowledge base from JSON plus optional .md/.txt article files."""
import glob
import json
import os
import re
import config
from models.schemas import Article


def _from_dict(raw):
    return Article(
        id=str(raw["id"]), title=raw["title"], category=raw.get("category", "General"),
        content=raw["content"].strip(), ticket_category=raw.get("ticket_category", ""),
        tags=list(raw.get("tags", [])), last_updated=raw.get("last_updated", ""))


def _from_text_file(path, index):
    with open(path, encoding="utf-8") as handle:
        lines = [line.rstrip() for line in handle.read().splitlines()]
    title = re.sub(r"^#+\s*", "", lines[0]).strip() if lines else os.path.basename(path)
    body = "\n".join(lines[1:]).strip()
    return Article(id=f"KBX{index:03d}", title=title, category="General", content=body,
                   last_updated="")


def load_articles():
    articles = []
    if os.path.exists(config.KB_PATH):
        with open(config.KB_PATH, encoding="utf-8") as handle:
            articles = [_from_dict(item) for item in json.load(handle)]
    files = sorted(glob.glob(os.path.join(config.KB_DOCS_DIR, "*.md")) +
                   glob.glob(os.path.join(config.KB_DOCS_DIR, "*.txt")))
    for index, path in enumerate(files, 1):
        articles.append(_from_text_file(path, index))
    return articles


def add_article(title, category, content, ticket_category="", tags=None):
    """Append an article to knowledge_base.json and return it."""
    items = []
    if os.path.exists(config.KB_PATH):
        with open(config.KB_PATH, encoding="utf-8") as handle:
            items = json.load(handle)
    numbers = [int(m.group(1)) for i in items if (m := re.fullmatch(r"KB(\d+)", i["id"]))]
    new_id = f"KB{(max(numbers) if numbers else 0) + 1:03d}"
    item = {"id": new_id, "title": title.strip(), "category": category.strip() or "General",
            "ticket_category": ticket_category, "tags": tags or [], "content": content.strip(),
            "last_updated": __import__("datetime").date.today().isoformat()}
    items.append(item)
    with open(config.KB_PATH, "w", encoding="utf-8") as handle:
        json.dump(items, handle, indent=2)
    return _from_dict(item)
