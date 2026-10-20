# KABCO - SortAI

SortAI combines AI-based material recognition with a real-world recycling workflow and a B2B marketplace. That makes it a strong fit for the buildathon's Open Frontier track, which covers experimental prototypes and unconventional ideas.

SortAI is a prototype for safer e-waste sorting, category-specific inventory, and a recycler marketplace. The current implementation starts with a dependency-light Python API foundation so the business rules can be tested before adding a mobile client and trained vision model.

## Current phase

Phase 1 establishes the shared taxonomy, safety policy, role-aware demo access, persistent JSON-backed demo records, and a small camera-to-inventory vertical slice. The classifier is explicitly a **mock inference provider**; it must not be presented as a trained model or a safety certification.

Implemented now:

- Category taxonomy and exact crate colours from the project brief.
- Conservative hazardous-item handling and review rules.
- Demo role login for collector, recycler, and administrator.
- `POST /api/scans` mock inference endpoint.
- `POST /api/scans/:id/confirm` confirmation/correction endpoint.
- Persistent confirmed inventory in `data/sortai.json`.
- Health and category endpoints.
- Automated tests for safety policy, permissions, duplicate confirmation, and persistence.

Not implemented yet: real authentication, camera/mobile UI, trained model inference, marketplace bidding, pickup lifecycle, purity inspection, and simulated payments.

## Run locally

Requires Python 3.11 or newer.

```bash
python -m unittest discover -s tests -v
python -m py_compile sortai/domain.py sortai/server.py
python -m sortai.server
```

The API listens on `http://127.0.0.1:3000` by default. Set `PORT` to use another port. The demo JSON store is created at `data/sortai.json`; it is local prototype data and is not suitable for production or multi-user deployment.

## Demo API

```bash
curl http://localhost:3000/health
curl http://localhost:3000/api/categories
curl -X POST http://localhost:3000/api/demo-login -H 'content-type: application/json' -d '{"role":"collector"}'
curl -X POST http://localhost:3000/api/scans -H 'content-type: application/json' -H 'authorization: Bearer demo-collector' -d '{"mode":"whole-device","filename":"old-phone.jpg"}'
curl -X POST http://localhost:3000/api/scans/SCAN_ID/confirm -H 'content-type: application/json' -H 'authorization: Bearer demo-collector' -d '{"confirmedCategory":"pcb"}'
```

See [`docs/architecture.md`](docs/architecture.md) for the audit, gap analysis, architecture, MVP workflow, and phased implementation sequence.
