# 🚀 AI Growth Skills

A CLI tool that crawls your website and runs AI-powered growth analysis using modular "skills" — each one a focused prompt template designed to surface specific growth, retention, or conversion opportunities.

---

## What It Does

Point it at any website URL and choose an analysis skill. The tool will:

1. **Crawl** up to 6 internal pages of the site
2. **Extract** clean text content from each page
3. **Run** a skill-specific prompt through an LLM (Llama 3.1 8B via HuggingFace)
4. **Print** a structured, actionable growth analysis

---

## Skills Available

| # | Skill | What It Analyzes |
|---|-------|-----------------|
| 1 | **Homepage Messaging** | Clarity, value proposition, hero copy, CTA effectiveness |
| 2 | **Funnel Friction** | Drop-off points, friction in signup/checkout flows, conversion blockers |
| 3 | **CRM Retention** | Lifecycle gaps, re-engagement opportunities, retention messaging |

Each skill lives as a Markdown prompt template in the `skills/` folder — easy to read, edit, or extend.

---

## Getting Started

### 1. Clone the repo

```bash
git clone https://github.com/keswise/ai-growth-skills.git
cd ai-growth-skills
```

### 2. Install dependencies

```bash
pip install requests
```

### 3. Set your HuggingFace API key

```bash
export HF_API_KEY=your_key_here
```

Get a free key at [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens).

### 4. Run

```bash
python run_skill.py
```

You'll be prompted to choose a skill and enter a URL:

```
============================================================
AI GROWTH SKILLS RUNNER
============================================================
1. Homepage Messaging
2. Funnel Friction
3. CRM Retention
============================================================
Choose a skill (1/2/3): 1
Enter website URL: https://example.com

Crawling internal pages...
Fetched 5 pages.
Running skill...

============================================================
RESULT: Homepage Messaging
============================================================
...
```

---

## Adding Your Own Skills

1. Create a new `.md` file in `skills/` with your prompt template
2. Use `{{url}}` and `{{pages}}` as placeholders — they're automatically replaced with the target URL and crawled page content
3. Register it in the `SKILL_MAP` dictionary in `run_skill.py`:

```python
SKILL_MAP = {
    "1": ("Homepage Messaging", "homepage_messaging.md"),
    "2": ("Funnel Friction", "funnel_friction.md"),
    "3": ("CRM Retention", "crm_retention.md"),
    "4": ("Your New Skill", "your_skill.md"),  # ← add here
}
```

---

## Configuration

All settings are at the top of `run_skill.py`:

| Variable | Default | Description |
|----------|---------|-------------|
| `MODEL` | `meta-llama/Llama-3.1-8B-Instruct` | HuggingFace model to use |
| `MAX_PAGES` | `6` | Max pages to crawl per run |
| `MAX_CHARS_PER_PAGE` | `1800` | Max characters extracted per page |
| `REQUEST_TIMEOUT` | `20s` | Timeout for page fetches |

---

## Roadmap Ideas

- [ ] Export results to Markdown or PDF
- [ ] Add more skills (SEO, Pricing Page, Onboarding Flow)
- [ ] Support for OpenAI / Anthropic as model backends
- [ ] Batch mode — run multiple URLs at once
- [ ] Web UI / Streamlit interface

---

## License

MIT
