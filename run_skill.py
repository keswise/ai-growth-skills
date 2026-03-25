import os
from pathlib import Path
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


def load_skill_file(filename: str) -> str:
    path = SKILLS_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Skill file not found: {path}")

    return path.read_text(encoding="utf-8")


def build_prompt(skill_template: str, url: str) -> str:
    return skill_template.replace("{{url}}", url.strip())


def call_ai(prompt: str) -> str:
    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a sharp growth, CRM, and product marketing analyst. "
                    "Follow the requested output structure exactly."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 1000,
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
    return url


def main() -> None:
    try:
        if API_KEY == "YOUR_API_KEY":
            print("Warning: Replace YOUR_API_KEY or set HF_API_KEY as an environment variable.\n")

        print_menu()
        choice = get_user_choice()
        url = get_url()

        skill_name, filename = SKILL_MAP[choice]
        template = load_skill_file(filename)
        prompt = build_prompt(template, url)

        print("\nRunning skill...\n")
        result = call_ai(prompt)
        cleaned = clean_output(result)

        print("=" * 60)
        print(f"RESULT: {skill_name}")
        print("=" * 60)
        print(f"URL: {url}\n")
        print(cleaned)
        print("\n" + "=" * 60)

    except FileNotFoundError as e:
        print(f"File error: {e}")
    except ValueError as e:
        print(f"Input error: {e}")
    except Exception as e:
        print(f"Something went wrong: {e}")


if __name__ == "__main__":
    main()
