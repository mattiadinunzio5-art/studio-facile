# Architettura di NEXUS

## Panoramica

```
 Browser ──► Frontend (React/Vite, :5173) ──/api──► Backend FastAPI (:8000, solo 127.0.0.1)
                                                     │
                                ┌────────────────────┼─────────────────────┐
                                ▼                    ▼                     ▼
                         services/ (logica)   integrations/ (fonti)   agents/ (provider AI)
                                │                    │ opzionali, con cache/stato
                                ▼                    ▼
                       SQLAlchemy ORM ──► SQLite (oggi) │ PostgreSQL (domani)
```

### Separazione degli strati (backend)
| Strato | Responsabilità | Regola |
|---|---|---|
| `api/routes` | HTTP, validazione input (Pydantic), codici di stato | nessuna logica di dominio |
| `services` | logica applicativa, registro attività, permessi per owner | riceve sempre l'utente corrente |
| `models` | schema ORM | ogni dato utente ha `owner_id`/`user_id` |
| `integrations` | fonti esterne | un errore di rete è un *esito*, mai un crash |
| `agents` | provider AI | `none` finché l'utente non configura credenziali |
| `core` | config, errori, logging, registro moduli | fonte unica di verità per lo stato dei moduli |

### Decisioni chiave
- **Registro moduli lato backend** (`core/modules.py`): lo stato mostrato dalla UI
  deriva dal codice, così nessuna area può risultare "completa" senza esserlo.
- **Sezioni non disponibili tipizzate** (`UnavailableSection`): la dashboard non può
  restituire dati segnaposto per indicatori, eventi o rapporti; restituisce il motivo
  e la fase prevista.
- **Errori uniformi**: `{"error": {"code", "message", "details"}}` per ogni errore,
  nessun dettaglio interno nei 500.
- **Conferma esplicita** per operazioni distruttive: `DELETE /api/projects/{id}`
  risponde 409 `confirmation_required` senza `confirm=true`.
- **Migrazioni Alembic** con naming convention e `render_as_batch` (compatibili
  SQLite e PostgreSQL). Un test verifica che i modelli coincidano con le migrazioni.
- **Multi-utente predisposto**: in Fase 1 esiste solo l'utente locale e il server
  ascolta su `127.0.0.1`; i servizi filtrano già per proprietario e restituiscono
  404 (non 403) per risorse altrui, per non rivelarne l'esistenza.
- **Connettori**: definizione statica (URL, termini d'uso, chiave richiesta, fase) +
  stato osservato persistito (`connector_states`). Le licenze *non* vengono riassunte
  come certe: si rimanda alla pagina ufficiale dei termini.

### Frontend
- `api/client.ts`: unico punto di accesso HTTP; mappa gli errori del backend in `ApiError`.
- `state/AppState.tsx`: stato globale minimo (backend online, notifiche non lette,
  contenuto del pannello contestuale).
- Layout: sidebar (drawer sotto 1024 px), barra superiore con ricerca globale,
  area centrale, pannello contestuale (drawer sotto 1280 px).
- Nessuna dipendenza esterna a runtime (niente CDN né font remoti).

### Sicurezza (Fase 1)
- Validazione di tutti gli input con Pydantic (lunghezze, enum, trim).
- Ricerca: i caratteri jolly SQL (`%`, `_`) sono trattati letteralmente.
- CORS limitato alle origini locali configurate.
- Segreti solo in `.env` (ignorato da git). Nessuna credenziale nel codice.
- Backup consistente con `scripts/backup_db.py`.

Previsto nelle fasi successive: autenticazione e ruoli (Fase 8), rate limit per le
operazioni automatiche e per i connettori (Fase 4–5), sanitizzazione dei documenti
importati e difesa da prompt injection (Fase 2/5: i documenti sono dati, non istruzioni).

### Modello dati (Fase 1)
`users`, `projects`, `activity_log`, `notifications`, `search_queries`,
`connector_states`, `user_preferences`.
