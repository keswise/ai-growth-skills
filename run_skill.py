import os
import re
from collections import deque
from pathlib import Path
from urllib.parse import urljoin, urlparse, urldefrag

import requests

API_URL = "https://router.huggingface.co/v1/chat/completions"
API_KEY = os.getenv("HF_API_KEY", "YOUR_API_KEY")

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

MODEL = "meta-llama/Llama-3.1-8B-Instruct"

BASE_DIR = Path(__file__).resolve().parent
SKILLS_DIR = BASE_DIR / "skills"

SKILL_MAP = {
    "1": ("Homepage Messaging", "homepage_messaging.md"),
    "2": ("Funnel Friction", "funnel_friction.md"),
    "3": ("CRM Retention", "crm_retention.md"),
}

# Crawl settings
MAX_PAGES = 6
MAX_CHARS_PER_PAGE = 1800
REQUEST_TIMEOUT = 20

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

SKIP_EXTENSIONS = (
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".ico",
    ".pdf", ".zip", ".rar", ".mp4", ".mp3", ".avi", ".mov",
    ".css", ".js", ".xml", ".json", ".woff", ".woff2", ".ttf",
)

SKIP_PATH_HINTS = (
    "/cdn-cgi/",
    "/wp-json/",
    "/api/",
)


def load_skill_file(filename: str) -> str:
    path = SKILLS_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Skill file not found: {path}")
    return path.read_text(encoding="utf-8")


def normalize_url(url: str) -> str:
    url = url.strip()
    parsed = urlparse(url)
    if not parsed.scheme:
        url = f"https://{url}"
    return urldefrag(url)[0]


def same_domain(url_a: str, url_b: str) -> bool:
    return urlparse(url_a).netloc == urlparse(url_b).netloc


def should_skip_url(url: str) -> bool:
    lowered = url.lower()
    if lowered.startswith("mailto:") or lowered.startswith("tel:") or lowered.startswith("javascript:"):
        return True
    if any(lowered.endswith(ext) for ext in SKIP_EXTENSIONS):
        return True
    if any(hint in lowered for hint in SKIP_PATH_HINTS):
        return True
    return False


def fetch_page_html(url: str) -> str:
    response = requests.get(
        url,
        headers={"User-Agent": USER_AGENT},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()

    content_type = response.headers.get("Content-Type", "").lower()
    if "text/html" not in content_type:
        raise ValueError(f"Skipping non-HTML content: {content_type}")

    return response.text


def extract_links(html: str, base_url: str) -> list[str]:
    hrefs = re.findall(r'href=["\'](.*?)["\']', html, flags=re.IGNORECASE)
    links = []

    for href in hrefs:
        full_url = urljoin(base_url, href)
        full_url = normalize_url(full_url)

        if should_skip_url(full_url):
            continue
        if not same_domain(base_url, full_url):
            continue

        links.append(full_url)

    # de-duplicate while preserving order
    seen = set()
    unique_links = []
    for link in links:
        if link not in seen:
            seen.add(link)
            unique_links.append(link)

    return unique_links


def clean_html_to_text(html: str, max_chars: int = MAX_CHARS_PER_PAGE) -> str:
    html = re.sub(r"(?is)<script.*?>.*?</script>", " ", html)
    html = re.sub(r"(?is)<style.*?>.*?</style>", " ", html)
    html = re.sub(r"(?is)<noscript.*?>.*?</noscript>", " ", html)

    html = re.sub(
        r"(?i)</(title|h1|h2|h3|h4|p|li|a|button|section|div|span|nav|header|footer)>",
        "\n",
        html,
    )
    html = re.sub(r"(?i)<br\s*/?>", "\n", html)

    text = re.sub(r"(?s)<.*?>", " ", html)

    replacements = {
        "&nbsp;": " ",
        "&amp;": "&",
        "&lt;": "<",
        "&gt;": ">",
        "&quot;": '"',
        "&#39;": "'",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)

    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    lines = [line for line in lines if line]

    deduped = []
    prev = None
    for line in lines:
        if line != prev:
            deduped.append(line)
        prev = line

    final_text = "\n".join(deduped)
    return final_text[:max_chars]


def crawl_site(start_url: str, max_pages: int = MAX_PAGES) -> list[tuple[str, str]]:
    visited = set()
    queue = deque([start_url])
    pages: list[tuple[str, str]] = []

    while queue and len(pages) < max_pages:
        current_url = queue.popleft()
        if current_url in visited:
            continue
        visited.add(current_url)

        try:
            html = fetch_page_html(current_url)
            text = clean_html_to_text(html)
            if text:
                pages.append((current_url, text))

            for link in extract_links(html, current_url):
                if link not in visited and link not in queue:
                    queue.append(link)

        except Exception:
            # Skip pages that fail; keep crawling
            continue

    return pages


def format_pages_for_prompt(pages: list[tuple[str, str]]) -> str:
    blocks = []
    for index, (url, content) in enumerate(pages, start=1):
        block = (
            f"Page {index}\n"
            f"URL: {url}\n"
            f"Content:\n{content}\n"
        )
        blocks.append(block)

    return "\n\n".join(blocks)


def build_prompt(skill_template: str, url: str, pages_text: str) -> str:
    prompt = skill_template.replace("{{url}}", url.strip())
    prompt = prompt.replace("{{pages}}", pages_text.strip())
    return prompt


def call_ai(prompt: str) -> str:
    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a sharp growth, CRM, lifecycle, and product marketing analyst. "
                    "Use the provided website pages as the primary source of truth. "
                    "If the content is insufficient, say so instead of guessing."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 1200,
    }

    response = requests.post(API_URL, headers=HEADERS, json=payload, timeout=120)

    if response.status_code != 200:
        raise Exception(f"Error {response.status_code}: {response.text}")

    data = response.json()
    return data["choices"][0]["message"]["content"]


def clean_output(text: str) -> str:
    text = text.replace("\r", "")
    text = text.replace("**", "")
    text = text.replace("##", "")

    lines = [line.rstrip() for line in text.split("\n")]
    cleaned_lines = []
    prev_blank = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if not prev_blank:
                cleaned_lines.append("")
            prev_blank = True
        else:
            cleaned_lines.append(stripped)
            prev_blank = False

    return "\n".join(cleaned_lines).strip()


def print_menu() -> None:
    print("\n" + "=" * 60)
    print("AI GROWTH SKILLS RUNNER")
    print("=" * 60)
    for key, (label, _) in SKILL_MAP.items():
        print(f"{key}. {label}")
    print("=" * 60)


def get_user_choice() -> str:
    choice = input("Choose a skill (1/2/3): ").strip()
    if choice not in SKILL_MAP:
        raise ValueError("Invalid choice. Please enter 1, 2, or 3.")
    return choice


def get_url() -> str:
    url = input("Enter website URL: ").strip()
    if not url:
        raise ValueError("URL cannot be empty.")
    return normalize_url(url)


def main() -> None:
    try:
        if API_KEY == "YOUR_API_KEY":
            print("Warning: set HF_API_KEY before running.\n")

        print_menu()
        choice = get_user_choice()
        url = get_url()

        skill_name, filename = SKILL_MAP[choice]
        template = load_skill_file(filename)

        print("\nCrawling internal pages...\n")
        pages = crawl_site(url, max_pages=MAX_PAGES)

        if not pages:
            raise Exception("Could not fetch any crawlable HTML pages from this site.")

        pages_text = format_pages_for_prompt(pages)
        prompt = build_prompt(template, url, pages_text)

        print(f"Fetched {len(pages)} pages.")
        print("Running skill...\n")

        result = call_ai(prompt)
        cleaned = clean_output(result)

        print("=" * 60)
        print(f"RESULT: {skill_name}")
        print("=" * 60)
        print(f"Start URL: {url}")
        print(f"Pages analyzed: {len(pages)}\n")
        print(cleaned)
        print("\n" + "=" * 60)

    except FileNotFoundError as e:
        print(f"File error: {e}")
    except requests.exceptions.RequestException as e:
        print(f"Network error while fetching webpage or calling API: {e}")
    except ValueError as e:
        print(f"Input error: {e}")
    except Exception as e:
        print(f"Something went wrong: {e}")


if __name__ == "__main__":
    main()