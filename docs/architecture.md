# SortAI architecture and repository audit

## Audit snapshot — 19 October 2026

The workspace contained only OmniRush/OpenCode metadata (`opencode.jsonc` and `.opencode/`) and one plugin dependency. There was no application source, framework, database, test suite, build script, or Git history to preserve. Therefore there is no existing end-user functionality to reuse or repair.

## Recommended architecture

The first implementation uses Python standard-library HTTP APIs and modules to keep the foundation runnable without installing an application framework. The intended target is:

- `mobile_app/`: React Native or Flutter collector client, selected after the API contract is stable.
- `recycler_dashboard/`: responsive web client using the same API.
- `sortai/domain.py`: shared taxonomy and safety/business rules during the prototype phase.
- `sortai/server.py`: API adapter and demo authentication boundary.
- `data/`: local demo persistence only; migrate to PostgreSQL behind repositories before multi-user use.
- `vision_engine/`: provider interface with mock and eventual on-device/model-backed implementations.
- `tests/`: API and domain tests.

The mock provider is intentionally separate from the safety policy. A prediction is never a safety certification, and hazardous or uncertain results require review.

## Minimum viable demonstration

1. Select a clearly labelled collector demo role.
2. Upload/capture an image placeholder and request a mock prediction.
3. Display category, confidence, source, crate colour, and conservative safety guidance.
4. Confirm or correct the result, creating persistent inventory.
5. Show threshold eligibility for a material lot.
6. Publish an eligible lot, accept a category-eligible recycler bid, schedule pickup, record measured weight/purity, and create a clearly simulated payment record.

The first slice implemented in this phase covers steps 1–4 at API level. Steps 5–6 are the next dependent work because they require inventory reservation and marketplace state transitions.

## Gap analysis

Missing from the initial workspace: UI, real authentication, persistent database, image storage, model inference, role-based API authorization, crate/inventory workflows, thresholds, marketplace, pickup, purity, payment, translations, offline queue, observability, and deployment configuration.

## Sequence and dependencies

1. Stabilise taxonomy, safety policy, roles, API contracts, and test harness. **Current phase.**
2. Add mobile-first shell and collector scan flow against these endpoints.
3. Replace JSON store with a repository/database layer and add migrations.
4. Add measured inventory, thresholds, lots, reservation, and audit events.
5. Add recycler verification states, eligible listings, bidding, and conflict-safe acceptance.
6. Add pickup, purity, dispute, and simulated payment lifecycle.
7. Add real model adapter only after dataset/evaluation evidence exists; keep mock mode explicit.
8. Run end-to-end, device, offline, accessibility, and security checks.

## Known limitations

The current Python API uses deterministic demo tokens and a JSON file. It is not secure, concurrent, or suitable for real users. The classifier returns a mock result derived from the filename, not computer vision. No claim is made about accuracy, recycler authorisation, safety, payment, or regulatory compliance.
