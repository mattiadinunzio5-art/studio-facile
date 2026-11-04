"""Registro delle otto aree funzionali di NEXUS.

È la fonte unica di verità sullo stato di ogni modulo. Lo stato deve
rispecchiare il codice realmente implementato: un modulo passa a
``available`` solo quando la sua fase è completata e testata.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

ModuleStatus = Literal["in_preparation", "partial", "available"]


@dataclass(frozen=True)
class ModuleDefinition:
    id: str
    code: str
    name: str
    summary: str
    phase: int
    status: ModuleStatus
    planned_features: list[str] = field(default_factory=list)
    implemented_features: list[str] = field(default_factory=list)


MODULES: list[ModuleDefinition] = [
    ModuleDefinition(
        id="historical",
        code="A",
        name="Historical Intelligence",
        summary="Archivio strutturato di eventi storici con cause, conseguenze, fonti e grado di attendibilità.",
        phase=3,
        status="available",
        planned_features=[
            "Schede evento (date, periodo, area, cause, conseguenze, attori, istituzioni)",
            "Fonti bibliografiche e grado di attendibilità per ogni evento",
            "Categorie: storia economica, monetaria, bancaria, industriale, guerre, crisi, imperi",
            "Creazione, modifica e collegamento tra eventi",
        ],
        implemented_features=[
            "Schede evento con date storiche (anche a.C.), periodo, area, paesi, cause, conseguenze, attori, istituzioni",
            "Categorie economiche, grado di attendibilità e avviso per fonti mancanti o non verificate",
            "Collegamento a fonti bibliografiche con pagine e note",
            "Collegamento tra eventi tramite relazioni tipizzate del Knowledge Graph",
        ],
    ),
    ModuleDefinition(
        id="financial",
        code="B",
        name="Financial Intelligence",
        summary="Laboratorio su serie storiche finanziarie e macroeconomiche da fonti aperte documentate.",
        phase=4,
        status="available",
        planned_features=[
            "Serie con fonte, unità, frequenza, periodo, data di aggiornamento e dati mancanti",
            "Rendimenti, volatilità, drawdown, medie mobili, correlazioni",
            "Confronto tra strumenti con armonizzazione esplicita delle frequenze",
            "Connettori FRED, World Bank, IMF, OECD, Eurostat, BIS, Our World in Data",
        ],
        implemented_features=[
            "Import reale da World Bank, Eurostat, Our World in Data e FRED (con chiave), più caricamento CSV",
            "Metadati per ogni serie: fonte, unità, frequenza, periodo, aggiornamento dichiarato dalla fonte, dati mancanti, licenza",
            "Cache su disco e funzionamento con fonte offline (dato marcato come proveniente dalla cache)",
            "Rendimenti, volatilità annualizzata, drawdown, medie mobili, CAGR, trend, test ADF, autocorrelazione, anomalie",
            "Confronto e correlazioni con ricampionamento solo esplicito (frequenza e metodo dichiarati)",
            "Connettori IMF, OECD e BIS non ancora implementati (dichiarati nella pagina Fonti)",
        ],
    ),
    ModuleDefinition(
        id="time-machine",
        code="C",
        name="Historical Time Machine",
        summary="Timeline interattiva con filtro temporale contro il bias del senno di poi.",
        phase=3,
        status="available",
        planned_features=[
            "Selezione per anno, periodo, paese, evento e categoria economica",
            "Distinzione tra conoscenze disponibili all'epoca e scoperte successive",
            "Evoluzione dei sistemi monetari e delle politiche economiche",
        ],
        implemented_features=[
            "Vista a una data con filtri per paese, categoria e intervallo",
            "Filtro anti-senno-di-poi: nasconde eventi successivi, conseguenze retrospettive e informazioni emerse dopo",
            "Informazioni datate (contemporanee, scoperte successive, aperture d'archivio, storiografia)",
            "Indicatori economici disponibili fino alla data, con avviso sulle revisioni",
        ],
    ),
    ModuleDefinition(
        id="knowledge-graph",
        code="D",
        name="Knowledge Graph",
        summary="Rete di entità e relazioni, ciascuna con fonte o marcata come ipotesi AI.",
        phase=3,
        status="available",
        planned_features=[
            "Entità: persone, stati, aziende, banche, istituzioni, eventi, documenti, teorie, indicatori",
            "Relazioni tipizzate (ha causato, ha influenzato, ha finanziato, ...) con fonte obbligatoria",
            "Esplorazione, filtri e schede entità",
        ],
        implemented_features=[
            "Entità di 9 tipi e relazioni di 8 tipi con provenienza obbligatoria (fonte, passaggio o ipotesi)",
            "Esplorazione per focus e profondità, filtri, layout e centralità calcolati con NetworkX",
            "Percorso più breve tra due entità",
        ],
    ),
    ModuleDefinition(
        id="war-room",
        code="E",
        name="Research War Room",
        summary="Ricerca multi-agente (Historian, Economist, Quant, Skeptic, Synthesizer) con approvazione finale.",
        phase=5,
        status="available",
        planned_features=[
            "Flusso: domanda, pianificazione, ricerca, analisi, controanalisi, sintesi, approvazione",
            "Provider AI intercambiabili attivati solo con credenziali fornite dall'utente",
            "Modalità locale senza AI con indicazione esplicita delle funzioni non disponibili",
        ],
        implemented_features=[
            "Flusso completo: pianificazione, ricerca, Historian, Economist, Quant, Skeptic, Synthesizer, approvazione",
            "Provider intercambiabili: Ollama (locale, gratuito), endpoint compatibili OpenAI, Anthropic (con chiave dell'utente)",
            "Modalità locale reale: ricerca, calcoli, estrazione e controanalisi a regole; gli agenti generativi risultano 'non eseguiti'",
            "Controlli sull'output AI: nessuna ipotesi promossa a fatto, riferimenti inesistenti rimossi, tracciamento di modello e token",
            "Documenti trattati come dati non fidati (delimitatori neutralizzati, segnalazione di istruzioni sospette)",
            "Approvazione obbligatoria; le relazioni proposte entrano nel grafo solo come 'ipotesi AI' dopo approvazione",
            "Limiti: un run alla volta, numero massimo di passi automatici",
        ],
    ),
    ModuleDefinition(
        id="economic-lab",
        code="F",
        name="Economic Laboratory",
        summary="Simulazioni Monte Carlo, sensitività, regressioni e backtesting senza look-ahead bias.",
        phase=6,
        status="available",
        planned_features=[
            "Ogni simulazione dichiara ipotesi, variabili, parametri, metodo, dati, risultati e limiti",
            "Backtesting con dati disponibili all'epoca (no look-ahead, no survivorship bias)",
            "Scenari controfattuali etichettati come ipotesi",
        ],
        implemented_features=[
            "Monte Carlo (moto browniano geometrico) e bootstrap a blocchi su rendimenti storici",
            "Dinamica del debito pubblico con rifinanziamento graduale, shock sui tassi, crisi e incertezza stocastica",
            "Analisi di sensitività (tornado), scenari di inflazione, confronto tra regole di Taylor",
            "Regressione OLS con errori HAC, avvisi su regressioni spurie e ricampionamento esplicito",
            "Backtesting con segnale applicato al periodo successivo (no look-ahead), costi e avvisi su sopravvivenza e revisioni",
            "Ogni simulazione dichiara ipotesi, variabili, parametri, metodo, dati, risultati e limiti; i controfattuali sono etichettati",
        ],
    ),
    ModuleDefinition(
        id="research-studio",
        code="G",
        name="Research Studio",
        summary="Produzione di rapporti professionali con citazioni verificabili ed esportazione PDF/DOCX.",
        phase=7,
        status="available",
        planned_features=[
            "Progetti, capitoli, appunti, fonti collegate, grafici e tabelle",
            "Struttura di rapporto in 10 sezioni (abstract ... bibliografia)",
            "Citazioni verificabili; fonti non verificabili segnalate",
            "Importazione PDF, DOCX, CSV ed esportazione PDF/DOCX",
        ],
        implemented_features=[
            "Progetti, rapporti con le 10 sezioni standard, capitoli aggiuntivi ordinabili, appunti collegati a fonti e documenti",
            "Citazioni verificabili [@id, p. N] con numerazione automatica; citazioni non valide e fonti non verificate segnalate",
            "Grafici di serie e simulazioni, tabelle; esportazione PDF (ReportLab) e DOCX (python-docx) con filigrana BOZZA",
            "Approvazione solo dopo il controllo di sezioni, citazioni e allegati; ogni modifica riporta in bozza",
            "Bozza di rapporto generata da una ricerca approvata della War Room",
            "Daily Briefing con data e fonte per ogni voce, generabile a richiesta o con cron (scripts/generate_briefing.py)",
            "Importazione PDF, DOCX, CSV, XLSX, TXT, MD nell'archivio (anche opere personali)",
        ],
    ),
    ModuleDefinition(
        id="business",
        code="H",
        name="NEXUS Business",
        summary="Account, autenticazione, permessi, piani e area amministratore per l'uso SaaS.",
        phase=8,
        status="available",
        planned_features=[
            "Account, autenticazione e profilo",
            "Progetti privati e condivisi con gestione permessi",
            "Piani gratuiti/premium e limiti di utilizzo (nessun pagamento reale)",
            "Area amministratore",
        ],
        implemented_features=[
            "Due modalità: locale personale (predefinita) e multi-utente con account (NEXUS_AUTH_MODE=multi)",
            "Registrazione, accesso, sessioni HttpOnly revocabili, cambio password, protezione CSRF, limite ai tentativi",
            "Separazione completa dei dati per utente; progetti condivisi con ruoli viewer/editor e conferma esplicita",
            "Piani locale/gratuito/premium con limiti d'uso applicati; nessun pagamento reale (interfaccia predisposta)",
            "Area amministratore: utenti, ruoli, piani, disattivazione, statistiche",
        ],
    ),
]

MODULES_BY_ID = {m.id: m for m in MODULES}
