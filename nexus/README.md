# NEXUS — Historical & Financial Intelligence Platform

Piattaforma locale (e in futuro SaaS) che collega ricerca storica, dati economici,
documenti e analisi quantitativa in un archivio di conoscenza verificabile.

**Stato: Fase 1 — Foundation completata.** Gli otto moduli analitici sono
dichiarati *in preparazione* e non simulano alcuna funzionalità.
Vedi [`docs/ROADMAP.md`](docs/ROADMAP.md).

## Principi
- Budget 0 €: solo software open-source; nessun servizio esterno obbligatorio.
- Funziona offline. Le fonti esterne sono opzionali e il loro stato è sempre visibile.
- Nessun dato inventato: ciò che non è disponibile viene dichiarato come tale.
- I dati dimostrativi sono marcati (`is_demo`, badge **DEMO**).
- Modalità supervisionata: le operazioni irreversibili richiedono conferma esplicita
  e tutto è tracciato nel registro attività.
- Nessun provider AI attivo finché l'utente non configura volontariamente le credenziali (Fase 5).

## Requisiti
- Python ≥ 3.11 (testato con 3.13), Node.js ≥ 20 (testato con 22), npm.
- Facoltativo: [`uv`](https://github.com/astral-sh/uv) per installazioni Python più rapide.

## Avvio rapido
```bash
cd nexus
scripts/setup.sh          # virtualenv + dipendenze + migrazioni + npm install
scripts/dev.sh            # backend su 127.0.0.1:8000, frontend su http://127.0.0.1:5173
```
Documentazione interattiva delle API: http://127.0.0.1:8000/docs

Facoltativo:
```bash
backend/.venv/bin/python scripts/seed_demo.py   # 2 progetti vuoti etichettati DEMO
backend/.venv/bin/python scripts/backup_db.py   # backup consistente in nexus/backups/
```

## Test
```bash
scripts/test.sh                                   # pytest + typecheck + vitest
NEXUS_URL=http://127.0.0.1:5173 node scripts/check_responsive.cjs   # E2E responsive (app avviata)
```

## Configurazione
Tutte le opzioni sono variabili `NEXUS_*` (vedi [`.env.example`](.env.example)).
Il database predefinito è `nexus/data/nexus.db` (SQLite). Per PostgreSQL basta
impostare `NEXUS_DATABASE_URL` e installare il driver (`psycopg`).

## Struttura
```
nexus/
├── backend/            FastAPI + SQLAlchemy + Alembic
│   ├── nexus/
│   │   ├── api/        router REST, schemi Pydantic, dipendenze
│   │   ├── core/       configurazione, logging, errori, registro moduli
│   │   ├── database/   engine, sessioni, base ORM, migrazioni programmatiche
│   │   ├── models/     tabelle ORM
│   │   ├── services/   logica applicativa (progetti, attività, dashboard, …)
│   │   ├── security/   identità utente (Fase 1: utente locale)
│   │   ├── integrations/ registro connettori + verifica raggiungibilità
│   │   ├── agents/     registro provider AI (nessuno attivo)
│   │   └── research/ history/ finance/ simulations/   (fasi 2–6)
│   ├── migrations/     Alembic
│   └── tests/          pytest
├── frontend/           React + TypeScript + Vite + Tailwind
│   └── src/{api,components,pages,lib,state,test}
├── docs/               architettura, roadmap, API
├── scripts/            setup, avvio, test, seed demo, backup, test responsive
├── data/               database locale (non versionato)
└── .env.example
```
