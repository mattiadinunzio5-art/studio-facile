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

### Sicurezza
- Validazione di tutti gli input con Pydantic (lunghezze, enum, trim).
- Ricerca: i caratteri jolly SQL (`%`, `_`) sono trattati letteralmente.
- CORS limitato alle origini locali configurate.
- Segreti solo in `.env` (ignorato da git). Nessuna credenziale nel codice.
- Backup consistente con `scripts/backup_db.py`.

- Autenticazione (modalità `multi`): password con scrypt, token di sessione casuali di cui
  si salva solo l'hash, cookie HttpOnly SameSite=Strict, intestazione `X-Nexus-Client`
  obbligatoria per le modifiche via cookie (CSRF), limite ai tentativi di accesso.
- Credenziali dei servizi esterni cifrate con Fernet; mai restituite dalle API.
- Intestazioni di sicurezza (`nosniff`, `DENY`, `no-referrer`, `no-store`).
- Prompt injection: i passaggi sospetti sono segnalati; ai modelli le evidenze arrivano in
  delimitatori neutralizzati con istruzione esplicita di trattarle come dati non fidati;
  i modelli non hanno accesso a strumenti, rete o database.
- Limiti alle operazioni automatiche: un run multi-agente alla volta, numero massimo di passi,
  quote per piano.

### Flusso multi-agente (Fase 5)
```
Domanda ─► Planner ─► Ricerca (strumenti locali: BM25+LSA, eventi, serie)
        ─► Historian · Economist · Quant ─► Skeptic (controanalisi + regole)
        ─► Synthesizer ─► guardie (tipi, evidenze, relazioni) ─► Approvazione utente
```
In modalità locale ogni agente che richiede generazione di testo è registrato come
«non eseguito»; i passi eseguiti indicano esecutore, modello, token e durata.

### Modello dati
Utenti e accesso: `users`, `auth_sessions`, `project_members`, `user_preferences`, `credentials`.
Archivio: `projects`, `documents`, `document_chunks` (+ `chunks_fts`), `sources`, `notes`.
Storia e grafo: `historical_events`, `event_sources`, `knowledge_items`, `entities`, `relations`.
Finanza e laboratorio: `series`, `observations`, `simulation_runs`.
AI e studio: `research_runs`, `agent_steps`, `reports`, `report_sections`, `briefings`.
Operatività: `activity_log`, `notifications`, `search_queries`, `connector_states`.
