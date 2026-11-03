# Roadmap e stato delle fasi

| Fase | Contenuto | Stato |
|---|---|---|
| 1 | Foundation: architettura, DB, backend, frontend, dashboard | ✅ completata (in attesa di approvazione) |
| 2 | Research Core: import documenti, estrazione testo, ricerca, citazioni, RAG | ⏳ non iniziata |
| 3 | Historical Intelligence, Time Machine, Knowledge Graph | ⏳ |
| 4 | Financial Intelligence: connettori, indicatori, grafici, analisi | ⏳ |
| 5 | AI Research / War Room: agenti, planner, controanalisi, approvazione | ⏳ |
| 6 | Economic Lab: simulazioni, backtesting, scenari | ⏳ |
| 7 | Research Studio: rapporti, esportazione PDF/DOCX | ⏳ |
| 8 | Business: account, permessi, preparazione SaaS | ⏳ |

## Fase 1 — funzionalità effettivamente completate
- Backend FastAPI con API REST documentate (OpenAPI su `/docs`), errori uniformi, logging.
- Database SQLite con migrazioni Alembic (predisposto per PostgreSQL).
- Bootstrap automatico: migrazioni, utente locale, notifica di benvenuto.
- Registro delle 8 aree con fase prevista e funzionalità pianificate.
- Progetti di ricerca: crea, modifica, archivia/ripristina, elimina con conferma esplicita.
- Registro attività di tutte le operazioni.
- Notifiche: elenco, segna letta, segna tutte.
- Ricerca globale testuale (progetti + catalogo moduli) con storico delle ricerche e
  dichiarazione degli ambiti non ancora ricercabili.
- Fonti: 8 connettori dichiarati con link ai termini d'uso; verifica reale di
  raggiungibilità (HTTP, latenza, errore) con stato persistito.
- Dashboard con 9 widget personalizzabili (ordine/visibilità salvati nel DB).
- Pagina Sistema: stato DB, modalità AI, provider (nessuno attivo).
- UI responsive (375 / 768 / 1440 px verificati), sidebar, ricerca, pannello contestuale.
- Script: setup, avvio, test, dati DEMO etichettati, backup.

## Fase 1 — non incluso (per scelta di fase)
- Nessun import di documenti, eventi, serie o grafici (fasi 2–4).
- Nessun agente AI e nessuna configurazione di credenziali (Fase 5).
- Nessuna autenticazione: utente locale unico, server su 127.0.0.1 (Fase 8).
- Dashboard: personalizzazione di ordine e visibilità; non ancora ridimensionamento widget.
- Cache e rate-limit dei connettori arriveranno con l'importazione dati (Fase 4).
