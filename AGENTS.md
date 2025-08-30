# Repository Guidelines

## Project Structure & Module Organization
- `backend/`: FastAPI service (UVicorn), AI analysis, document processing, crawler, tests.
- `frontend/`: Streamlit UI and helper utilities.
- `nextjs-frontend/`: Next.js app (`src/app`, `src/components`, `src/services/api.ts`).
- `data/`, `monitoring/`: datasets and ops tooling.
- CI: `.github/workflows/`; Local orchestration: `docker-compose*.yml`.

## Build, Test, and Development Commands
- Backend setup: `cd backend && pip install -r requirements.txt`.
- Run API (dev): `uvicorn main:app --reload --host 0.0.0.0 --port 8000` (alt: `python main.py`).
- Streamlit UI: `cd frontend && pip install -r requirements.txt && streamlit run app.py`.
- Next.js UI: `cd nextjs-frontend && npm install && npm run dev` (build: `npm run build`, start: `npm start`).
- Docker: `docker-compose up -d` (or `-f docker-compose.enhanced.yml up -d`).

## Coding Style & Naming Conventions
- Python: PEP 8, 4‑space indent, add type hints for new/modified code.
- Names: modules/functions `snake_case`, classes `PascalCase`.
- Lint/format: `flake8` (root `.flake8`), `isort` (profile=black); optional `ruff` if available.
- JS/TS: ESLint (Next.js defaults); components `PascalCase`, variables/functions `camelCase`.
- Filenames: Python modules `snake_case.py`; Next.js components in `src/components/` (e.g., `CaseSearch.tsx`).

## Testing Guidelines
- Framework: `pytest` in `backend/`; discovery per `backend/pytest.ini`.
- Conventions: files `test_*.py` or `*_test.py`; classes `Test*`; functions `test_*`.
- Run tests: `cd backend && pytest -v` (or `python run_tests.py`).
- Coverage focus: data parsing, API routes, regressions; mark slow/flaky with `@pytest.mark.slow`.

## Commit & Pull Request Guidelines
- Commits: follow Conventional Commits (e.g., `feat(web_crawler): add filename field`, `fix(date-parsing): improve timestamp handling`).
- PRs: include clear description, linked issues, scope of change, and test evidence; for UI changes, add screenshots or short clips.
- Keep changes scoped and update docs and sample configs when behavior changes.

## Security & Configuration Tips
- Never commit secrets. Use `.env` files (`backend/.env`, `nextjs-frontend/.env.local`).
- Start with `cp backend/.env.example backend/.env` and edit locally.
- Validate large downloads/crawls in a sandbox and respect rate limits.
