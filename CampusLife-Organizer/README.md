# CampusOne

CampusOne is a campus-life demo with four connected modules:

- **SmartFlow** forecasts arrivals and illustrative queue wait times from class end times, estimated visit share, walking-time assumptions, and counter service rates. It does not collect GPS or represent live campus measurements.
- **QuietCollab** matches student profiles by complementary skills, common interests, and project goal. Profile comparisons are deterministic; introductions are optional.
- **HackaSync** creates and persists event agendas with setup, work blocks, breaks, submission deadlines, and judging.
- **PocketPal** lets students publish and browse small campus gigs. Payment and task arrangements happen outside the demo.

The numerical forecast and matching logic are deterministic. The existing AI adapter remains available for text-oriented verification work, but it does not create forecast statistics or approve consequential decisions.

## Stack

- Frontend: React, TypeScript, Vite, Tailwind CSS
- Backend: Python, FastAPI, Pydantic, SQLAlchemy
- Local persistence: SQLite

## Run locally (Windows)

1. Create the Python environment and install dependencies:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

2. Configure AI access if needed. Copy `.env.example` to `.env`, then set `AI_PROVIDER`, `GEMMA_API_KEY`, and `GEMMA_MODEL`. Keep `.env` private. The app defaults to mock mode without credentials.

3. Start the API from the repository root:
   ```powershell
   .\.venv\Scripts\python.exe -m uvicorn backend.app:app --reload --port 8000
   ```

4. Start the frontend in another terminal:
   ```powershell
   cd frontend
   npm install
   npm run dev
   ```

5. Open http://localhost:5173. Vite proxies `/api` calls to the local API.

## Demo accounts

- Student: `student@campusos.edu` / `campus123`
- Staff: `staff@campusos.edu` / `campus123`
- Sample teammate: `rohan@campusos.edu` / `campus123`

## Tests

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests -q
cd frontend
npm run build
npm run lint
```

Sample campus records and forecast inputs are demonstration data. Do not treat them as live observations or institutional records.
