"""Registro dei connettori a fonti aperte.

In Fase 1 i connettori sono *dichiarati* ma non scaricano dati: l'unica
operazione reale è il controllo di raggiungibilità dell'host. L'importazione
delle serie arriva in Fase 4.

Licenze e limiti d'uso: NON vengono riassunti qui come fatti certi. Ogni voce
rimanda alla pagina ufficiale dei termini, da verificare prima di qualsiasi uso
(in particolare commerciale).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConnectorDefinition:
    id: str
    name: str
    category: str  # macro | finance | history | library
    homepage: str
    check_url: str
    terms_url: str
    requires_api_key: bool
    planned_phase: int
    notes: str
    implemented: bool = False


CONNECTORS: list[ConnectorDefinition] = [
    ConnectorDefinition(
        id="fred",
        name="FRED (Federal Reserve Bank of St. Louis)",
        category="macro",
        homepage="https://fred.stlouisfed.org/",
        check_url="https://fred.stlouisfed.org/",
        terms_url="https://fred.stlouisfed.org/legal/",
        requires_api_key=True,
        planned_phase=4,
        notes="L'API richiede una chiave gratuita. Alcune serie sono di terzi con diritti propri.",
        implemented=True,
    ),
    ConnectorDefinition(
        id="world-bank",
        name="World Bank Open Data",
        category="macro",
        homepage="https://data.worldbank.org/",
        check_url="https://api.worldbank.org/v2/country?format=json&per_page=1",
        terms_url="https://www.worldbank.org/en/about/legal/terms-of-use-for-datasets",
        requires_api_key=False,
        planned_phase=4,
        notes="Licenza indicata per singolo dataset.",
        implemented=True,
    ),
    ConnectorDefinition(
        id="imf",
        name="IMF Data",
        category="macro",
        homepage="https://data.imf.org/",
        check_url="https://data.imf.org/",
        terms_url="https://www.imf.org/en/About/copyright-and-terms",
        requires_api_key=False,
        planned_phase=4,
        notes="Verificare i termini di riutilizzo prima dell'uso commerciale.",
    ),
    ConnectorDefinition(
        id="owid",
        name="Our World in Data",
        category="macro",
        homepage="https://ourworldindata.org/",
        check_url="https://ourworldindata.org/",
        terms_url="https://ourworldindata.org/faqs#can-i-use-or-reproduce-your-data",
        requires_api_key=False,
        planned_phase=4,
        notes="I dati di terze parti restano soggetti alle licenze delle fonti originali.",
        implemented=True,
    ),
    ConnectorDefinition(
        id="eurostat",
        name="Eurostat",
        category="macro",
        homepage="https://ec.europa.eu/eurostat",
        check_url="https://ec.europa.eu/eurostat",
        terms_url="https://ec.europa.eu/eurostat/about-us/policies/copyright",
        requires_api_key=False,
        planned_phase=4,
        notes="Verificare le eccezioni indicate nella policy sul copyright.",
        implemented=True,
    ),
    ConnectorDefinition(
        id="oecd",
        name="OECD Data",
        category="macro",
        homepage="https://data-explorer.oecd.org/",
        check_url="https://data-explorer.oecd.org/",
        terms_url="https://www.oecd.org/en/about/terms-conditions.html",
        requires_api_key=False,
        planned_phase=4,
        notes="Verificare termini e limiti di frequenza delle richieste.",
    ),
    ConnectorDefinition(
        id="bis",
        name="BIS Data Portal",
        category="finance",
        homepage="https://data.bis.org/",
        check_url="https://data.bis.org/",
        terms_url="https://www.bis.org/terms_conditions.htm",
        requires_api_key=False,
        planned_phase=4,
        notes="Verificare i termini di riutilizzo delle statistiche.",
    ),
    ConnectorDefinition(
        id="gutenberg",
        name="Project Gutenberg",
        category="library",
        homepage="https://www.gutenberg.org/",
        check_url="https://www.gutenberg.org/",
        terms_url="https://www.gutenberg.org/policy/permission.html",
        requires_api_key=False,
        planned_phase=2,
        notes="Importazione di singoli testi su richiesta. Lo stato di pubblico dominio dipende dal paese; il marchio ha regole proprie. "
        "Il sito vieta l'accesso automatizzato massivo: usare i mirror/feed indicati.",
        implemented=True,
    ),
]

CONNECTORS_BY_ID = {c.id: c for c in CONNECTORS}
