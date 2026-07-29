# Scuole Torino Explorer

App desktop/web in Python con [Flet](https://flet.dev) e `flet-map` che mostra le scuole di Torino su OpenStreetMap, con filtri per grado, distretto e ricerca testuale.

## Requisiti

- Python 3.10+
- Dipendenze in `requirements.txt` (`flet`, `flet-map`, `pandas`)

## Installazione

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Avvio

Web (consigliato):

```bash
flet run --web app.py
```

Desktop:

```bash
flet run app.py
```

## Funzionalità

- Marker sulle scuole con coordinate valide
- Filtri AND: grado ∩ distretto ∩ testo (nome / indirizzo / codice)
- Mini-lista risultati in sidebar (cliccabile)
- Contatore scuole visibili e stato vuoto
- Pulsanti Tutti / Nessuno per gradi e distretti
- Marker “casa” attivabile/disattivabile dalla sidebar
- Dialog info con grado, colore distretto, centra mappa, copia indirizzo

## Struttura

```
app.py                 # Entry point
components/sidebar.py  # Filtri, ricerca, mini-lista
views/map_view.py      # Mappa OSM e marker
utils/database.py      # Caricamento CSV (cache) e filtri
utils/state.py         # FilterState di sessione
utils/geo.py           # Distanza Haversine
utils/config.py        # Costanti (casa, zoom, soglie)
data/scuole_coordinate.csv
data/crea_gradi_scuole.py   # Script one-shot (non usato a runtime)
```

## Dati

Dataset: `data/scuole_coordinate.csv`

Colonne: `Distretto`, `Codice`, `Nome`, `Indirizzo`, `Grado`, `Latitudine`, `Longitudine`.

Circa **383** record; **48** senza Lat/Lon vengono esclusi a caricamento (restano **~335** sulla mappa). Non vengono inventate coordinate mancanti.

### Script `crea_gradi_scuole.py`

Utility one-shot che assegna la colonna `Grado` a partire da codice MIUR / nome e riscrive il CSV. Non è importata dall’app: eseguirla solo se serve rigenerare i gradi.

```bash
python data/crea_gradi_scuole.py
```

## Note

- I filtri valgono solo per la sessione corrente (nessuna persistenza).
- Le coordinate del marker casa sono in `utils/config.py` (`CASA_LAT`, `CASA_LON`).
