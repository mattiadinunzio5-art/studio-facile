# Roadmap e stato

| Fase | Contenuto | Stato |
|---|---|---|
| 1 | Foundation: architettura, DB, backend, frontend, dashboard | ✅ |
| 2 | Research Core: import, estrazione, ricerca BM25+semantica, citazioni, risposte | ✅ |
| 3 | Historical Intelligence, Time Machine, Knowledge Graph | ✅ |
| 4 | Financial Intelligence: connettori, indicatori, grafici, analisi | ✅ |
| 5 | AI Research / War Room: agenti, planner, controanalisi, sintesi, approvazione | ✅ |
| 6 | Economic Lab: simulazioni, backtesting, modelli, scenari | ✅ |
| 7 | Research Studio: rapporti, appunti, export PDF/DOCX, Daily Briefing | ✅ |
| 8 | Business: account, permessi, piani, amministrazione | ✅ |

Test automatici: 178 backend (pytest), 36 frontend (Vitest + Testing Library),
typecheck TypeScript, E2E responsive su 25 pagine × 3 larghezze (Playwright).

## Limiti noti e lavoro futuro (dichiarati, non simulati)
- **Connettori**: IMF, OECD e BIS sono dichiarati ma non importano ancora dati.
  FRED richiede una chiave gratuita dell'utente. Nessuna quotazione in tempo reale.
- **Dati point-in-time**: le serie sono nella versione attuale (revisioni incluse);
  Time Machine e backtest lo segnalano. Non esiste un archivio di vintage storici.
- **Ricerca semantica**: predefinita LSA (scikit-learn). Gli embedding neurali
  (sentence-transformers) sono opzionali e non sono stati scaricati nei test.
- **OCR**: i PDF scansionati senza testo vengono rifiutati con messaggio esplicito.
- **Provider AI**: testati con risposte simulate a livello HTTP/SDK; nessuna chiamata
  reale a modelli a pagamento è stata eseguita durante lo sviluppo.
- **Daily Briefing**: nessuna fonte di notizie correnti; la programmazione si fa con cron.
- **Pagamenti**: solo interfaccia (`billing.PaymentProvider`); i piani li assegna un admin.
- **Condivisione**: si condividono progetti, rapporti e appunti; i documenti dell'archivio
  restano privati del proprietario. Nessun invio di email (inviti per account esistenti).
- **Rate limit** dei login in memoria (per processo): con più processi serve un backend condiviso.
- **PostgreSQL**: architettura predisposta (URL configurabile, migrazioni portabili, ricerca
  testuale con fallback); l'indice full-text tsvector non è ancora implementato.
