from html import escape


def html_escape(value: str | None) -> str:
    return escape(value or "", quote=False)


def truncate(value: str, limit: int = 200) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 3] + "..."


def normalize_title(value: str | None, fallback: str = "this group") -> str:
    clean = (value or "").strip()
    return clean or fallback
