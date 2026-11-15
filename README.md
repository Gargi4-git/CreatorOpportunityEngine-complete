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

---
## Research & workspace features (added)

| Page | What it does | Where the numbers come from |
|---|---|---|
| **Evaluation → Model evaluation** | Hand-label comments (blind, predictions hidden) or import a labelled CSV; reports accuracy, macro-F1, per-class P/R/F1, confusion matrix and the **majority-class baseline** for intent and sentiment; clustering quality (noise ratio, silhouette, Davies-Bouldin); topic recovery (ARI/NMI) if you label topics; **GhostGap ablation** (drop / use-only-one component, Kendall τ, does #1 change); **MiniLM vs lexical-baseline** comparison. | Your labels + stored embeddings/clusters; scikit-learn / SciPy. Nothing is reported below 20 labels. |
| **Evaluation → Closed-loop validation** | Track a recommended opportunity; after publishing, compare real performance with the prediction made at the time. Outcome = 100·r/(1+r), r = views/day ÷ the channel's median views/day over its last 10 videos (YouTube API) or your own manual numbers. Reports Spearman/Pearson/Kendall, hit-rates, per-component correlation. | YouTube Data API or manual entry. Videos < 14 days old are excluded by default; n < 10 is labelled "anecdotal". |
| **GhostGap Lab** | Sliders re-rank topics live; Monte-Carlo sensitivity (500 random re-weightings within ±X%) gives P(rank #1) per topic and the stability of the top pick; one-at-a-time tornado table; **learned weights** (non-negative ridge on tracked outcomes, leave-one-out R²; flagged exploratory below 20 videos or when LOO R² ≤ 0; previewable, never applied automatically). | `ml/scoring.py`, `ml/sensitivity.py`, `ml/learned_weights.py` |
| **History & Compare** | Lists every analysis; compares two side by side (topics matched by centroid cosine, with deltas); follows topics across repeated analyses of the same channel / subreddit / file. | Stored embeddings; analyses made with different embedding models are refused. |
| **Content Planner** | Idea → Scripted → Published board (owned by the `users` collection). "Mark published" records the video URL and starts closed-loop tracking. Save from the opportunity modal or a generated brief. | MongoDB `plan_items`, `validations` |
| **Knowledge Graph** | Source → Topic → Pain point, Topic → Opportunity → Content (networkx, PageRank). Pain points are key phrases from the cluster's high-pain comments; a phrase shared by several topics links them. Content nodes appear only when a recommendation exists or you saved the item to the planner. | Real analysis data |
| **Channel analysis** (YouTube tab → *Whole channel*) | Last N videos × comments per video; per-video breakdown on each opportunity; analyses of one channel are linked in History. | YouTube Data API |
| **Better competition** | YouTube volume + recency + **topic coverage** (embedding similarity of top-result title+description to the topic) + Stack Overflow (public API, no key) + Reddit search (if configured). A source that fails is omitted and the weights renormalised. | `ml/competition.py`, `services/supply_service.py` |
| **Multilingual** (checkbox) | Uses `paraphrase-multilingual-MiniLM-L12-v2` and keeps non-English comments (language mix reported). | `MULTILINGUAL_MODEL` |

Tests: `cd backend && pytest` (36 tests: the original 19 + 17 for these features; external APIs mocked, test-only embedder).
Caveats: validation and learned weights need real tracked videos to mean anything; outcomes use views/day, which is noisy for young videos;
Stack Overflow supply is most meaningful for technical topics; the multilingual model downloads on first use.
