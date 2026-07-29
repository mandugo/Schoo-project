"""Costanti di configurazione dell'app."""

import flet as ft

# Marker "casa" (disattivabile dalla sidebar)
CASA_LAT = 45.0918
CASA_LON = 7.6357

# Centro iniziale mappa (Torino)
MAPPA_CENTRO_LAT = 45.0703
MAPPA_CENTRO_LON = 7.6869
MAPPA_ZOOM_INIZIALE = 12
MAPPA_ZOOM_DETTAGLIO = 15

# Soglia hit-test click mappa (metri)
HIT_TEST_METRI = 100.0

# Quanti risultati mostrare nella mini-lista sidebar
MINI_LISTA_MAX = 12

# Layout responsive
SIDEBAR_WIDTH = 340
VIEWPORT_NARROW_PX = 800

# Marker scuole
MARKER_SCUOLA_SIZE = 26
MARKER_CASA_SIZE = 30

# Palette UI (allineamento leggero, non brand-heavy)
UI_HEADER_BG = ft.Colors.BLUE_700
UI_SIDEBAR_BG = ft.Colors.GREY_100
UI_META_COLOR = ft.Colors.GREY_700

# Copy italiano condiviso
LABEL_AZZERA_FILTRI = "Azzera filtri"
MSG_EMPTY_RISULTATI = "Nessuna scuola con i filtri attuali"
MSG_ATTRIBUTION_OSM = "© OpenStreetMap"
LABEL_CONDIVIDI = "Copia link filtri"
MSG_LINK_COPIATO = "Link filtri copiato negli appunti"
LABEL_ORDINA_DISTANZA = "Ordina per distanza da casa"
DATI_FONTE_LABEL = "Dataset locale CSV"
