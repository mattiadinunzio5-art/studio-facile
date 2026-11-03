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
        status="in_preparation",
        planned_features=[
            "Schede evento (date, periodo, area, cause, conseguenze, attori, istituzioni)",
            "Fonti bibliografiche e grado di attendibilità per ogni evento",
            "Categorie: storia economica, monetaria, bancaria, industriale, guerre, crisi, imperi",
            "Creazione, modifica e collegamento tra eventi",
        ],
    ),
    ModuleDefinition(
        id="financial",
        code="B",
        name="Financial Intelligence",
        summary="Laboratorio su serie storiche finanziarie e macroeconomiche da fonti aperte documentate.",
        phase=4,
        status="in_preparation",
        planned_features=[
            "Serie con fonte, unità, frequenza, periodo, data di aggiornamento e dati mancanti",
            "Rendimenti, volatilità, drawdown, medie mobili, correlazioni",
            "Confronto tra strumenti con armonizzazione esplicita delle frequenze",
            "Connettori FRED, World Bank, IMF, OECD, Eurostat, BIS, Our World in Data",
        ],
    ),
    ModuleDefinition(
        id="time-machine",
        code="C",
        name="Historical Time Machine",
        summary="Timeline interattiva con filtro temporale contro il bias del senno di poi.",
        phase=3,
        status="in_preparation",
        planned_features=[
            "Selezione per anno, periodo, paese, evento e categoria economica",
            "Distinzione tra conoscenze disponibili all'epoca e scoperte successive",
            "Evoluzione dei sistemi monetari e delle politiche economiche",
        ],
    ),
    ModuleDefinition(
        id="knowledge-graph",
        code="D",
        name="Knowledge Graph",
        summary="Rete di entità e relazioni, ciascuna con fonte o marcata come ipotesi AI.",
        phase=3,
        status="in_preparation",
        planned_features=[
            "Entità: persone, stati, aziende, banche, istituzioni, eventi, documenti, teorie, indicatori",
            "Relazioni tipizzate (ha causato, ha influenzato, ha finanziato, ...) con fonte obbligatoria",
            "Esplorazione, filtri e schede entità",
        ],
    ),
    ModuleDefinition(
        id="war-room",
        code="E",
        name="Research War Room",
        summary="Ricerca multi-agente (Historian, Economist, Quant, Skeptic, Synthesizer) con approvazione finale.",
        phase=5,
        status="in_preparation",
        planned_features=[
            "Flusso: domanda, pianificazione, ricerca, analisi, controanalisi, sintesi, approvazione",
            "Provider AI intercambiabili attivati solo con credenziali fornite dall'utente",
            "Modalità locale senza AI con indicazione esplicita delle funzioni non disponibili",
        ],
    ),
    ModuleDefinition(
        id="economic-lab",
        code="F",
        name="Economic Laboratory",
        summary="Simulazioni Monte Carlo, sensitività, regressioni e backtesting senza look-ahead bias.",
        phase=6,
        status="in_preparation",
        planned_features=[
            "Ogni simulazione dichiara ipotesi, variabili, parametri, metodo, dati, risultati e limiti",
            "Backtesting con dati disponibili all'epoca (no look-ahead, no survivorship bias)",
            "Scenari controfattuali etichettati come ipotesi",
        ],
    ),
    ModuleDefinition(
        id="research-studio",
        code="G",
        name="Research Studio",
        summary="Produzione di rapporti professionali con citazioni verificabili ed esportazione PDF/DOCX.",
        phase=7,
        status="in_preparation",
        planned_features=[
            "Progetti, capitoli, appunti, fonti collegate, grafici e tabelle",
            "Struttura di rapporto in 10 sezioni (abstract ... bibliografia)",
            "Citazioni verificabili; fonti non verificabili segnalate",
            "Importazione PDF, DOCX, CSV ed esportazione PDF/DOCX",
        ],
        implemented_features=[
            "Progetti di ricerca: creazione, modifica, archiviazione, eliminazione con conferma (Fase 1)",
        ],
    ),
    ModuleDefinition(
        id="business",
        code="H",
        name="NEXUS Business",
        summary="Account, autenticazione, permessi, piani e area amministratore per l'uso SaaS.",
        phase=8,
        status="in_preparation",
        planned_features=[
            "Account, autenticazione e profilo",
            "Progetti privati e condivisi con gestione permessi",
            "Piani gratuiti/premium e limiti di utilizzo (nessun pagamento reale)",
            "Area amministratore",
        ],
        implemented_features=[
            "Modello utente e separazione dei dati per owner_id (Fase 1, utente locale unico)",
        ],
    ),
]

MODULES_BY_ID = {m.id: m for m in MODULES}
