# API REST

Base `/api`. Documentazione interattiva generata dal codice: `/docs` (Swagger), `/openapi.json`.
Formato errori: `{"error": {"code", "message", "details"}}` — `validation_error` 422,
`not_found` 404, `confirmation_required` 409, `unauthorized` 401, `forbidden` 403,
`quota_exceeded` 403, `csrf` 403, `too_many_attempts` 429, `internal_error` 500.

Operazioni irreversibili o verso altri utenti richiedono `confirm=true`
(eliminazioni, condivisione di progetti).

| Area | Endpoint principali |
|---|---|
| Sistema | `GET /health`, `GET /system/status`, `GET /me`, `GET /modules` |
| Dashboard | `GET /dashboard`, `GET/PUT /dashboard/layout`, `GET /search?q=` |
| Progetti | `GET/POST /projects`, `GET/PATCH/DELETE /projects/{id}`, `GET/POST/DELETE /projects/{id}/members` |
| Documenti | `GET/POST /documents` (multipart), `POST /documents/gutenberg`, `GET /documents/{id}/chunks`, `GET /documents/{id}/file` |
| Bibliografia | `GET/POST /sources`, `PUT/DELETE /sources/{id}`, `POST /sources/{id}/verify` |
| Ricerca | `GET /research/search?q=&mode=hybrid|text|semantic`, `POST /research/ask` |
| Storia | `GET/POST /history/events`, `…/{id}/sources`, `…/{id}/knowledge`, `…/{id}/links`, `GET /history/timeline` |
| Grafo | `GET /graph`, `GET /graph/path`, `GET/POST /graph/entities`, `POST/DELETE /graph/relations` |
| Finanza | `GET /finance/presets`, `GET /finance/series`, `POST /finance/series/import`, `POST /finance/series/upload`, `POST /finance/series/{id}/refresh`, `GET /finance/series/{id}/analysis`, `POST /finance/compare` |
| Credenziali | `GET/PUT /credentials`, `DELETE /credentials/{provider}` |
| AI | `GET/PUT /ai/provider`, `POST/GET /research/runs`, `GET /research/runs/{id}`, `POST /research/runs/{id}/decision` |
| Laboratorio | `POST /lab/simulations/{monte_carlo|monte_carlo_bootstrap|debt|sensitivity|inflation|monetary_policy|regression|backtest}`, `GET/DELETE /lab/simulations/{id}` |
| Studio | `GET/POST /reports`, `POST /reports/from-run/{run_id}`, `PUT /reports/{id}/sections/{sid}`, `POST /reports/{id}/chapters`, `GET /reports/{id}/check`, `POST /reports/{id}/status`, `GET /reports/{id}/export/{pdf|docx}`, `GET/POST /notes`, `GET/POST /briefings` |
| Account | `GET /auth/config`, `POST /auth/register|login|logout|password`, `GET/DELETE /auth/sessions`, `PATCH /me`, `GET /me/usage`, `GET /billing/plans` |
| Admin | `GET /admin/users`, `PATCH /admin/users/{id}`, `GET /admin/stats` |
| Altro | `GET /activity`, `GET /notifications`, `POST /notifications/{id}/read`, `GET /connectors`, `POST /connectors/{id}/check` |
