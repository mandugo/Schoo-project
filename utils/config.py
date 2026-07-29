"""Costanti di configurazione dell'app."""

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
MARKER_SCUOLA_SIZE = 30
MARKER_CASA_SIZE = 30

# Palette UI — slate + teal (civico/mappa, non purple / non cream)
UI_HEADER_BG = "#0B3D4A"
UI_HEADER_FG = "#F5FAFB"
UI_HEADER_MUTED = "#A8C5CC"
UI_SIDEBAR_BG = "#EEF3F5"
UI_SURFACE = "#FFFFFF"
UI_ACCENT = "#1B7A6E"
UI_ACCENT_SOFT = "#D8EFEA"
UI_BORDER = "#C9D6DC"
UI_META_COLOR = "#5C6E76"
UI_TITLE_COLOR = "#0B3D4A"
UI_DIVIDER = "#D5E0E5"
POLYLINE_COLORE = "#1B7A6E"
POLYLINE_SPESSORE = 4.5

# Font (caricato in app.py)
UI_FONT_FAMILY = "DM Sans"
UI_FONT_URL = (
    "https://github.com/googlefonts/dm-fonts/raw/main/Sans/fonts/"
    "ttf/DMSans-Regular.ttf"
)
UI_FONT_BOLD_URL = (
    "https://github.com/googlefonts/dm-fonts/raw/main/Sans/fonts/"
    "ttf/DMSans-SemiBold.ttf"
)

# Copy italiano condiviso
LABEL_AZZERA_FILTRI = "Azzera filtri"
MSG_EMPTY_RISULTATI = "Nessuna scuola con i filtri attuali"
MSG_ATTRIBUTION_OSM = "© OpenStreetMap"
LABEL_CONDIVIDI = "Copia link filtri"
MSG_LINK_COPIATO = "Link filtri copiato negli appunti"
LABEL_ORDINA_DISTANZA = "Ordina per distanza da casa"
LABEL_IMPOSTA_CASA = "Cambia casa"
LABEL_RIPRISTINA_CASA = "Predefinita"
LABEL_NASCONDI_PERCORSO = "Nascondi percorso"
LABEL_LUOGO = "Luogo"
LABEL_ALTRO = "Altro"
LABEL_GUIDA = "Guida"
LABEL_TORNA_MAPPA = "Torna alla mappa"
ROUTE_INFO = "/info"
MSG_IMPOSTA_CASA = "Clicca sulla mappa per impostare la casa"
MSG_CASA_IMPOSTATA = "Casa aggiornata"
DATI_FONTE_LABEL = "Dataset locale CSV"

# Routing OSRM (server pubblico demo — rate limit; per produzione self-host / altra API)
OSRM_BASE_URL = "https://router.project-osrm.org"
OSRM_TIMEOUT_SEC = 8.0
ROUTING_PROFILO_DEFAULT = "foot"  # foot | bike | car
ROUTING_PROFILI = (
    ("foot", "A piedi"),
    ("bike", "In bici"),
    ("car", "In auto"),
)