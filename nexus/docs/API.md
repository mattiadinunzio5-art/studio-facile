# API REST (Fase 1)

Base: `/api`. Documentazione interattiva generata automaticamente: `/docs` (Swagger) e `/openapi.json`.

| Metodo | Percorso | Descrizione |
|---|---|---|
| GET | `/health` | Verifica del backend |
| GET | `/system/status` | Database, ambiente, modalità e provider AI |
| GET | `/me` | Utente corrente (Fase 1: locale) |
| GET | `/modules`, `/modules/{id}` | Le 8 aree e il loro stato reale |
| GET | `/dashboard` | Dati aggregati della dashboard |
| GET/PUT | `/dashboard/layout` | Ordine e visibilità dei widget |
| GET/POST | `/projects` | Elenco (`?status=active\|archived`) / creazione |
| GET/PATCH | `/projects/{id}` | Dettaglio / modifica (titolo, descrizione, stato) |
| DELETE | `/projects/{id}?confirm=true` | Eliminazione (senza `confirm` → 409) |
| GET | `/activity?limit&offset` | Registro attività |
| GET | `/notifications?unread_only` | Notifiche |
| POST | `/notifications/{id}/read`, `/notifications/read-all` | Segna come lette |
| GET | `/connectors` | Fonti dichiarate e ultimo stato osservato |
| POST | `/connectors/{id}/check` | Verifica raggiungibilità (nessun dato scaricato) |
| GET | `/search?q=` | Ricerca globale (2–200 caratteri) |
| GET | `/search/recent` | Ultime ricerche distinte |

Formato errori: `{"error": {"code": "...", "message": "...", "details": ...}}`
(`validation_error` 422, `not_found` 404, `confirmation_required` 409, `internal_error` 500).
