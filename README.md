# 📝 Digital Error Notebook (错题本)

An AI-powered web app for Chinese students to capture, review, and quiz on teacher-marked homework/exam mistakes. Uses OpenRouter vision & chat models with RAG-based study assistance.

## ✨ Features

- **📤 Smart Upload** — Upload teacher-corrected papers; AI detects wrong marks (叉/×) and extracts mistakes
- **🔍 Mistake Extraction** — 3-pass vision pipeline (detection → crop → reconciliation) with confidence scoring
- **📚 Notebook** — Browse, filter, and search saved notes by subject, tags, date, or status
- **✏️ Markdown Editor** — Rich note editing with EasyMDE
- **🧠 Quiz Mode** — "Quiz me originally" or "Generate new questions" with AI grading
- **💬 AI Chat** — Notes-aware chat with streaming output, RAG context injection, edit/regenerate
- **🔑 API Key Management** — Users can provide their own OpenRouter key for full model access
- **⚙️ Admin Panel** — Per-user quota management with 6-hour auto-refresh

## 🚀 Quick Start

### 1. Clone & Setup

```bash
git clone https://github.com/YOUR_USERNAME/digital-error-notebook.git
cd digital-error-notebook
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/macOS
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
copy .env.example .env       # Windows
# cp .env.example .env       # Linux/macOS
```

Edit `.env` and set:
- `SECRET_KEY` — a random secret string
- `OPENROUTER_API_KEY` — your OpenRouter API key (admin key)
- `ADMIN_USERNAME` / `ADMIN_PASSWORD`
- `FERNET_KEY` — generate with: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`

### 3. Run

```bash
python run.py
```

Visit [http://localhost:5000](http://localhost:5000)

## 📁 Project Structure

```
digital-error-notebook/
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── extensions.py        # SQLAlchemy, Login Manager
│   ├── models/              # Database models
│   ├── routes/              # API + page blueprints
│   ├── services/            # OpenRouter, vision pipeline, embeddings, quota
│   ├── middleware/           # Quota enforcement
│   ├── utils/               # Crypto, image utilities
│   ├── templates/           # Jinja2 HTML templates
│   └── static/              # CSS, JS
├── config.py                # Configuration
├── run.py                   # Entry point
├── requirements.txt
├── .env.example
└── .gitignore
```

## 🤖 Supported Models

| Type | Model | Notes |
|------|-------|-------|
| Vision | `google/gemini-3-flash-preview` | Fast |
| Vision | `qwen/qwen3.5-397b-a17b` | Default, high quality |
| Chat | `qwen/qwen3.5-397b-a17b` | Default |
| Chat | `qwen/qwen3-235b-a22b-2507` | |
| Chat | `openai/gpt-5-nano` | Limited tier |
| Chat | `openai/gpt-oss-120b:nitro` | |
| Chat | `google/gemini-3-flash-preview` | Limited tier |

## 📄 License

MIT
