# Repository Guidelines

## Project Structure & Module Organization
- `backend/`: FastAPI service (UVicorn), AI analysis, document processing, crawler, tests (pytest).
- `frontend/`: Streamlit UI and supporting Python utilities.
- `nextjs-frontend/`: Next.js app with `src/app`, `src/components`, `src/services/api.ts`.
- `data/`, `monitoring/`: datasets and ops tooling; `.github/workflows` for CI; `docker-compose*.yml` for local orchestration.

## Build, Test, and Development Commands
- Backend (API):
  - `cd backend && pip install -r requirements.txt`
  - Dev: `uvicorn main:app --reload --host 0.0.0.0 --port 8000`
  - Alt: `python main.py`
- Streamlit (legacy UI):
  - `cd frontend && pip install -r requirements.txt`
  - Run: `streamlit run app.py`
- Next.js (modern UI):
  - `cd nextjs-frontend && npm install`
  - Dev: `npm run dev` • Build: `npm run build` • Start: `npm start`
- Docker: `docker-compose up -d` (or `-f docker-compose.enhanced.yml up -d`).

## Coding Style & Naming Conventions
- Python: PEP 8, 4‑space indent, type hints for new code; modules/functions `snake_case`, classes `PascalCase`.
- Lint/Format: `flake8` (root `.flake8`), `isort` (profile=black), optional `ruff` if installed.
- JS/TS: ESLint (Next.js config), components `PascalCase`, variables/functions `camelCase`.
- Filenames: Python modules `snake_case.py`; Next.js components in `src/components/` (e.g., `CaseSearch.tsx`).

## Testing Guidelines
- Backend uses `pytest` with markers; discovery per `backend/pytest.ini`:
  - Files: `test_*.py` or `*_test.py`; classes `Test*`; functions `test_*`.
  - Run: `cd backend && pytest -v` (or `python run_tests.py`).
- Aim for coverage on data parsing, API routes, and regressions; mark flaky or slow tests with `@pytest.mark.slow`.

## Commit & Pull Request Guidelines
- Conventional Commits observed in history: `feat(scope): …`, `fix(scope): …`, `refactor(scope): …`.
  - Examples: `feat(web_crawler): add filename field`; `fix(date-parsing): improve timestamp handling`.
- PRs: clear description, linked issues, scope of change, test evidence; for UI, include screenshots or short clips.
- Keep changes scoped; update docs (README/AGENTS) and sample configs when behavior changes.

## Security & Configuration Tips
- Never commit secrets; use `.env` files (`backend/.env`, `nextjs-frontend/.env.local`).
- Prefer `cp backend/.env.example backend/.env` then edit locally.
- Validate large downloads/crawls in a sandbox and respect rate limits.

