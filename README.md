# Creator Opportunity Engine

**Multimodal, multi-agent audience intelligence.** It turns real audience conversations (YouTube, Reddit, CSV, screenshots,
audio, video) into explainable content opportunities, answering *"What should this creator make next, and why?"*

```
INPUT → ingest → clean → multimodal fusion → embeddings → HDBSCAN clusters
      → [LangGraph agents] sentiment/intent → demand → trend → competition → GhostGap
      → recommendation (Gemini + RAG over FAISS) → explanation → MongoDB → dashboard
```

## Architecture
```
backend/app/
  main.py                    FastAPI app
  api/        upload.py (all ingestion) analysis.py opportunities.py analytics.py creator_studio.py search.py health.py
  agents/     orchestrator.py (LangGraph graph)  state.py
              ingestion · multimodal · topic · sentiment · demand · trend · competition · ghostgap · recommendation · explanation
  ml/         cleaning · embeddings · clustering · sentiment (zero-shot prototypes) · trends · competition · scoring (GhostGap, central)
  services/   youtube · reddit · gemini · whisper · media · media_pipeline · vector (FAISS) · csv · source · progress
  models/     analysis.py (Pydantic schemas validating all LLM output)
  db/         mongodb.py          demo/  demo_comments.csv (synthetic, labelled "Demo Dataset")
frontend/src/ api.js · App.jsx (state + polling) · pages/ · components/ · CreatorStudio.jsx · live.css
```

## Setup
**MongoDB** — `docker run -d -p 27017:27017 --name mongo mongo:7` (or install Community Edition; Atlas works via `MONGODB_URI`).

**Backend**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt                         # also install ffmpeg (needed for audio/video)
cp ../.env.example ../.env                              # then fill in keys
uvicorn app.main:app --reload                           # http://127.0.0.1:8000/docs
```
**Frontend** — `cd frontend && npm install && npm run dev` (set `VITE_API_URL` if the API is not on `http://127.0.0.1:8000`).
npm packages (already in package.json): react, react-dom, vite, axios, recharts, lucide-react.

**Keys** (all server-side, in `.env`; never in the frontend)
- `YOUTUBE_API_KEY` — Google Cloud Console → create project → enable *YouTube Data API v3* → Credentials → API key. Free quota is 10,000 units/day; each comment page costs 1 unit, each competition search 100 units (max 8 per analysis).
- `GEMINI_API_KEY` — https://aistudio.google.com/apikey. Model names are configurable via `GEMINI_MODELS` (comma-separated fallback chain).
- `REDDIT_CLIENT_ID/SECRET/USER_AGENT` — https://www.reddit.com/prefs/apps → *create app* → type **script**; user agent like `creator-engine/0.1 by your_username`.

## Tests
`cd backend && pytest` — 19 tests. External services are mocked at the network/client boundary (respx, a fake Gemini client, a fake Whisper model);
everything downstream is the real code. A test-only hashing embedder replaces MiniLM so tests run offline: they verify mechanics, persistence and
data-dependence, **not** MiniLM's semantic quality.

## End-to-end manual test
1. `GET /api/health` (or the sidebar) shows what is connected. 2. Creator Studio → YouTube → paste a URL → 250 → *Analyze Audience*.
3. Watch the 12 real pipeline steps. 4. Overview / Opportunities / Analytics update. 5. Open an opportunity → evidence, breakdown, trend.
6. Creator Studio → pick a format → *Generate Content Brief*. 7. Paste a different URL: topics, scores and briefs change.
8. Upload two different CSVs (e.g. Python vs Kubernetes comments): different topics/scores.
9. Media tab: upload a text CSV + a screenshot + an audio clip, tick all, *Analyze*: related signals merge into one topic (see `modality_mix`).
No keys? *Load Demo Dataset* runs the same pipeline on a clearly labelled synthetic sample.

## Agents (LangGraph nodes, shared typed state)
Ingestion · Multimodal · Topic · Sentiment/Intent · Demand · Trend · Competition · GhostGap · Recommendation (RAG) · Explanation.

## ML vs LLM
| Stage | Method |
|---|---|
| Cleaning, spam, duplicates, language, timestamps | rules, `langdetect`, embedding cosine (near-duplicates ≥ 0.95) |
| Embeddings | sentence-transformers all-MiniLM-L6-v2 (384-d) |
| Clustering | HDBSCAN (silhouette-selected KMeans fallback, reported honestly) |
| Intent / sentiment / pain | **zero-shot via embedding prototypes** (no LLM) — a heuristic; validate on hand-labelled data before quoting accuracy |
| Demand, trend, freshness, engagement, GhostGap | Python/Pandas statistics, formula in `ml/scoring.py` |
| Competition | YouTube Data API search → volume / recency / relevance score (`ml/competition.py`) |
| Image understanding, topic naming, recommendations, content briefs | Gemini (JSON validated by Pydantic) |
| Audio/video transcription | Whisper (local); video frames → Gemini Vision |
| Retrieval | FAISS inner-product index over normalised embeddings |

## GhostGap
`0.30·Demand + 0.20·Trend + 0.20·Pain + 0.10·Engagement + 0.10·Freshness − 0.10·Competition`, min-max normalised to 0-100
(80+ Critical, 60+ High, 40+ Moderate, 20+ Emerging, else Low). Weights/thresholds live only in `backend/app/ml/scoring.py`.
**Unmeasurable components are excluded and the range is re-normalised** (never treated as 0, never invented): no timestamps → no Trend/Freshness;
no YouTube key → no Competition; no likes → no Engagement. Every opportunity stores the per-component points ("Demand 13.4 / 30").
The quadrant (Ghost Gap / Saturated / Niche / Low value) uses demand vs competition at 50/50 and is `null` when competition is unavailable.

## Where each dashboard number comes from
| Number | Source |
|---|---|
| Audience comments | analyzed records after cleaning (`audience_records`) |
| Total engagement | sum of likes + replies of analyzed records |
| Avg opportunity | mean GhostGap over topics · Avg trend: mean over topics that have timestamps (else "n/a") |
| Topic / demand / pain / trend / competition | per cluster, computed by the agents above; shown as `n/a` + reason when unavailable |
| Platform / sentiment / intent / modality charts | counts over analyzed records |
| Recommendations / briefs | Gemini, grounded in retrieved comments; citations not matching retrieved evidence are dropped, and a recommendation with none is rejected |

## Known limitations
- Needs a real run with MiniLM to tune clustering (`min_cluster_size`, near-duplicate threshold); only the stub embedder was exercised in development.
- Gemini, YouTube, Reddit and Whisper paths are tested against mocks, not live services.
- Frontend stays JavaScript (JSX), not TypeScript. Video generation is intentionally not offered. Neo4j is not included.
- The legacy CSV-script backend (`backend/main.py`, `backend/ai/`, `data/`) is untouched and unused by the new UI.
