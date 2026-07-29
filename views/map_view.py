"""Vista mappa: marker scuole filtrati, hit-test, dialog info, percorso OSRM."""

from __future__ import annotations

import asyncio
from typing import Any, Callable

import flet as ft
import pandas as pd
from flet_map import (
    Map,
    MapLatitudeLongitude,
    Marker,
    MarkerLayer,
    PolylineLayer,
    PolylineMarker,
    TileLayer,
)

from utils.config import (
    CASA_LAT,
    CASA_LON,
    DATI_FONTE_LABEL,
    HIT_TEST_METRI,
    LABEL_ALTRO,
    LABEL_NASCONDI_PERCORSO,
    MAPPA_CENTRO_LAT,
    MAPPA_CENTRO_LON,
    MAPPA_ZOOM_DETTAGLIO,
    MAPPA_ZOOM_INIZIALE,
    MARKER_CASA_SIZE,
    MARKER_SCUOLA_SIZE,
    MSG_ATTRIBUTION_OSM,
    MSG_CASA_IMPOSTATA,
    MSG_IMPOSTA_CASA,
    POLYLINE_COLORE,
    POLYLINE_SPESSORE,
    ROUTING_PROFILO_DEFAULT,
    ROUTING_PROFILI,
    UI_ACCENT,
    UI_ACCENT_SOFT,
    UI_BORDER,
    UI_HEADER_BG,
    UI_META_COLOR,
    UI_SURFACE,
    UI_TITLE_COLOR,
)
from utils.database import statistiche_dataset
from utils.geo import distanza_metri, format_distanza
from utils.routing import RouteResult, calcola_percorso, format_durata

# Palette ampia (≥31) — hue a angolo aureo + luminosità/saturazione alternate
def _hsl_to_hex(h: float, s: float, lightness: float) -> str:
    """h in [0,360), s/l in [0,1] → #RRGGBB."""
    h = h % 360.0
    c = (1 - abs(2 * lightness - 1)) * s
    x = c * (1 - abs((h / 60.0) % 2 - 1))
    m = lightness - c / 2
    if h < 60:
        r, g, b = c, x, 0.0
    elif h < 120:
        r, g, b = x, c, 0.0
    elif h < 180:
        r, g, b = 0.0, c, x
    elif h < 240:
        r, g, b = 0.0, x, c
    elif h < 300:
        r, g, b = x, 0.0, c
    else:
        r, g, b = c, 0.0, x
    return "#{:02X}{:02X}{:02X}".format(
        int(round((r + m) * 255)),
        int(round((g + m) * 255)),
        int(round((b + m) * 255)),
    )


def _genera_palette_distretti(n: int = 36) -> list[str]:
    colori: list[str] = []
    for i in range(n):
        h = (i * 137.508) % 360.0
        s = 0.58 + (i % 3) * 0.10
        lightness = 0.36 + (i % 2) * 0.10 + ((i // 3) % 2) * 0.04
        colori.append(_hsl_to_hex(h, min(s, 0.82), min(lightness, 0.52)))
    return colori


COLORI_DISTRETTO = _genera_palette_distretti(36)

_PROFILO_LABEL = dict(ROUTING_PROFILI)


def mappa_colori_distretto(distretti: list[int]) -> dict[int, Any]:
    """Assegna un colore univoco per distretto (cicla solo oltre la palette)."""
    return {
        d: COLORI_DISTRETTO[i % len(COLORI_DISTRETTO)]
        for i, d in enumerate(sorted(distretti))
    }


class MappaController:
    """Gestisce MarkerLayer, percorso, dialog e aggiornamenti filtri."""

    def __init__(
        self,
        page: ft.Page,
        *,
        get_profilo: Callable[[], str] | None = None,
        set_profilo: Callable[[str], None] | None = None,
        get_casa: Callable[[], tuple[float, float]] | None = None,
        on_casa_impostata: Callable[[float, float], None] | None = None,
        on_percorso_visibile: Callable[[bool], None] | None = None,
    ):
        self.page = page
        self.get_profilo = get_profilo or (lambda: ROUTING_PROFILO_DEFAULT)
        self.set_profilo = set_profilo
        self.get_casa = get_casa or (lambda: (CASA_LAT, CASA_LON))
        self.on_casa_impostata = on_casa_impostata
        self.on_percorso_visibile = on_percorso_visibile
        self._mode_imposta_casa = False
        self.df_corrente: pd.DataFrame = pd.DataFrame()
        self.colore_distretto: dict[int, Any] = {}
        self.livello_marker = MarkerLayer(markers=[])
        self.livello_percorso = PolylineLayer(polylines=[])
        self._dialog: ft.AlertDialog | None = None
        self._route_corrente: RouteResult | None = None
        self._scuola_percorso_nome: str = ""
        self._mostra_casa = True
        self._distretto_evidenziato: int | None = None
        self._codice_selezionato: str | None = None

        self.livello_mappa = TileLayer(
            url_template="https://tile.openstreetmap.org/{z}/{x}/{y}.png",
            user_agent_package_name="ScuoleTorinoExplorer",
        )

        self.mappa = Map(
            expand=True,
            initial_center=MapLatitudeLongitude(MAPPA_CENTRO_LAT, MAPPA_CENTRO_LON),
            initial_zoom=MAPPA_ZOOM_INIZIALE,
            layers=[self.livello_mappa, self.livello_percorso, self.livello_marker],
            on_tap=self._on_tap,
        )

        self.attribution = ft.Text(
            MSG_ATTRIBUTION_OSM,
            size=11,
            color=UI_META_COLOR,
        )

        stats = statistiche_dataset()
        aggiornato = stats.get("aggiornato") or "n/d"
        self.dati_meta = ft.Text(
            (
                f"{DATI_FONTE_LABEL} · {stats['con_coordinate']}/{stats['totale']} "
                f"con coordinate · {stats['senza_coordinate']} escluse · "
                f"agg. {aggiornato}"
            ),
            size=11,
            color=UI_META_COLOR,
        )

        self._banner_titolo = ft.Text(
            "",
            size=15,
            weight=ft.FontWeight.W_700,
            color=UI_TITLE_COLOR,
            max_lines=1,
            overflow=ft.TextOverflow.ELLIPSIS,
        )
        self._banner_dettaglio = ft.Text(
            "",
            size=14,
            color=UI_META_COLOR,
            max_lines=2,
            overflow=ft.TextOverflow.ELLIPSIS,
        )
        self.banner_percorso = ft.Container(
            visible=False,
            padding=ft.Padding.symmetric(horizontal=16, vertical=14),
            bgcolor=UI_ACCENT_SOFT,
            border=ft.Border.only(
                top=ft.BorderSide(1, UI_BORDER),
                bottom=ft.BorderSide(1, UI_BORDER),
            ),
            content=ft.Row(
                spacing=14,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(
                        width=44,
                        height=44,
                        bgcolor=UI_HEADER_BG,
                        border_radius=22,
                        alignment=ft.Alignment.CENTER,
                        content=ft.Icon(ft.Icons.ROUTE, color=UI_SURFACE, size=22),
                    ),
                    ft.Column(
                        expand=True,
                        spacing=4,
                        tight=True,
                        controls=[self._banner_titolo, self._banner_dettaglio],
                    ),
                    ft.IconButton(
                        icon=ft.Icons.CLOSE,
                        icon_size=22,
                        icon_color=UI_META_COLOR,
                        tooltip=LABEL_NASCONDI_PERCORSO,
                        on_click=lambda _e: self.nascondi_percorso(),
                    ),
                ],
            ),
        )

        self.root = ft.Column(
            expand=True,
            spacing=0,
            controls=[
                self.mappa,
                self.banner_percorso,
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=12, vertical=6),
                    bgcolor=UI_SURFACE,
                    border=ft.Border.only(top=ft.BorderSide(1, UI_BORDER)),
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            self.dati_meta,
                            self.attribution,
                        ],
                    ),
                ),
            ],
        )

    def colore_per_distretto(self, distretto: int) -> Any:
        return self.colore_distretto.get(
            int(distretto), COLORI_DISTRETTO[int(distretto) % len(COLORI_DISTRETTO)]
        )

    def _ruolo_marker(self, scuola: dict) -> str:
        """normale | dimmed | stesso | selezionato — in base al dialog aperto."""
        if self._distretto_evidenziato is None:
            return "normale"
        codice = str(scuola.get("Codice", "") or "")
        if self._codice_selezionato and codice == self._codice_selezionato:
            return "selezionato"
        try:
            d = int(scuola["Distretto"])
        except (KeyError, TypeError, ValueError):
            return "dimmed"
        if d == self._distretto_evidenziato:
            return "stesso"
        return "dimmed"

    def _marker_scuola(self, colore: Any, scuola: dict) -> ft.Control:
        ruolo = self._ruolo_marker(scuola)
        try:
            label = str(int(scuola["Distretto"]))
        except (KeyError, TypeError, ValueError):
            label = "?"

        if ruolo == "selezionato":
            size = MARKER_SCUOLA_SIZE + 10
            border_w = 3.0
            text_size = 13
            opacity = 1.0
            shadow_blur = 10
            shadow_op = 0.4
            bgcolor = UI_SURFACE
            text_color = colore
            border_color = colore
        elif ruolo == "stesso":
            size = MARKER_SCUOLA_SIZE + 4
            border_w = 2.5
            text_size = 12
            opacity = 1.0
            shadow_blur = 8
            shadow_op = 0.32
            bgcolor = ft.Colors.with_opacity(0.95, UI_SURFACE)
            text_color = colore
            border_color = colore
        elif ruolo == "dimmed":
            size = MARKER_SCUOLA_SIZE - 2
            border_w = 1.5
            text_size = 10
            opacity = 0.28
            shadow_blur = 2
            shadow_op = 0.1
            bgcolor = UI_SURFACE
            text_color = ft.Colors.with_opacity(0.55, colore)
            border_color = ft.Colors.with_opacity(0.45, colore)
        else:
            size = MARKER_SCUOLA_SIZE
            border_w = 2.0
            text_size = 11
            opacity = 1.0
            shadow_blur = 5
            shadow_op = 0.28
            bgcolor = UI_SURFACE
            text_color = colore
            border_color = colore

        return ft.GestureDetector(
            on_tap=lambda e, s=scuola: self.page.run_task(self.seleziona_scuola, s),
            content=ft.Container(
                width=size,
                height=size,
                alignment=ft.Alignment.CENTER,
                opacity=opacity,
                bgcolor=bgcolor,
                border=ft.Border.all(border_w, border_color),
                border_radius=size / 2,
                shadow=ft.BoxShadow(
                    blur_radius=shadow_blur,
                    color=ft.Colors.with_opacity(shadow_op, ft.Colors.BLACK),
                    offset=ft.Offset(0, 1),
                ),
                content=ft.Text(
                    label,
                    size=text_size,
                    weight=ft.FontWeight.W_700,
                    color=text_color,
                    text_align=ft.TextAlign.CENTER,
                ),
            ),
        )

    def aggiorna_marker(self, df: pd.DataFrame, mostra_casa: bool = True) -> None:
        self.df_corrente = df.copy()
        self._mostra_casa = mostra_casa

        # Se la scuola evidenziata non è più nei risultati, spegni l'effetto
        if self._codice_selezionato and len(df):
            presenti = set(df["Codice"].astype(str))
            if self._codice_selezionato not in presenti:
                self._distretto_evidenziato = None
                self._codice_selezionato = None
        elif self._codice_selezionato and len(df) == 0:
            self._distretto_evidenziato = None
            self._codice_selezionato = None

        distretti = sorted(df["Distretto"].astype(int).unique().tolist()) if len(df) else []
        for d in distretti:
            if d not in self.colore_distretto:
                idx = len(self.colore_distretto)
                self.colore_distretto[d] = COLORI_DISTRETTO[idx % len(COLORI_DISTRETTO)]

        markers: list[Marker] = []

        for _, scuola in df.iterrows():
            data = scuola.to_dict()
            distretto = int(scuola["Distretto"])
            colore = self.colore_per_distretto(distretto)

            markers.append(
                Marker(
                    coordinates=MapLatitudeLongitude(
                        float(scuola["Latitudine"]),
                        float(scuola["Longitudine"]),
                    ),
                    content=self._marker_scuola(colore, data),
                    data=data,
                )
            )

        if mostra_casa:
            casa_lat, casa_lon = self.get_casa()
            markers.append(
                Marker(
                    coordinates=MapLatitudeLongitude(casa_lat, casa_lon),
                    content=ft.Container(
                        width=MARKER_CASA_SIZE + 4,
                        height=MARKER_CASA_SIZE + 4,
                        alignment=ft.Alignment.CENTER,
                        bgcolor=UI_HEADER_BG,
                        border=ft.Border.all(2, UI_SURFACE),
                        border_radius=(MARKER_CASA_SIZE + 4) / 2,
                        shadow=ft.BoxShadow(
                            blur_radius=6,
                            color=ft.Colors.with_opacity(0.35, ft.Colors.BLACK),
                            offset=ft.Offset(0, 1),
                        ),
                        content=ft.Icon(
                            ft.Icons.HOME,
                            color=UI_SURFACE,
                            size=MARKER_CASA_SIZE - 8,
                        ),
                    ),
                    data={"tipo": "casa"},
                )
            )

        self.livello_marker.markers = markers

    def _imposta_evidenza_distretto(
        self,
        distretto: int | None,
        codice: str | None = None,
    ) -> None:
        self._distretto_evidenziato = (
            int(distretto) if distretto is not None else None
        )
        self._codice_selezionato = str(codice) if codice else None
        if len(self.df_corrente):
            self.aggiorna_marker(self.df_corrente, mostra_casa=self._mostra_casa)

    def avvia_imposta_casa(self) -> None:
        """Prossimo tap sulla mappa imposta le coordinate di casa."""
        self._mode_imposta_casa = True
        self.page.show_dialog(
            ft.SnackBar(content=ft.Text(MSG_IMPOSTA_CASA), duration=4000)
        )
        self.page.update()

    def _notifica_percorso_visibile(self) -> None:
        visibile = bool(self.livello_percorso.polylines)
        if self.on_percorso_visibile is not None:
            self.on_percorso_visibile(visibile)

    def _aggiorna_banner_percorso(self, route: RouteResult | None) -> None:
        if route is None or len(route.coordinate) < 2:
            self.banner_percorso.visible = False
            self._banner_titolo.value = ""
            self._banner_dettaglio.value = ""
            return

        label_prof = _PROFILO_LABEL.get(route.profilo, route.profilo)
        destinazione = self._scuola_percorso_nome or "Scuola"
        self._banner_titolo.value = f"Percorso → {destinazione}"

        if route.sorgente == "osrm":
            stima = " · durata stimata" if route.durata_stimata else ""
            self._banner_dettaglio.value = (
                f"{label_prof} · {format_distanza(route.distanza_m)}"
                f" · {format_durata(route.durata_s)}{stima}"
            )
        else:
            self._banner_dettaglio.value = (
                f"Routing non disponibile — stima {label_prof}: "
                f"{format_distanza(route.distanza_m)} · ~{format_durata(route.durata_s)}"
            )
        self.banner_percorso.visible = True

    def mostra_percorso(self, route: RouteResult | None) -> None:
        """Disegna (o rimuove) la polilinea del percorso sulla mappa."""
        self._route_corrente = route
        if route is None or len(route.coordinate) < 2:
            self.livello_percorso.polylines = []
            self._scuola_percorso_nome = ""
            # Senza percorso: niente evidenza distretto
            self._imposta_evidenza_distretto(None)
        else:
            self.livello_percorso.polylines = [
                PolylineMarker(
                    coordinates=[
                        MapLatitudeLongitude(lat, lon) for lat, lon in route.coordinate
                    ],
                    color=POLYLINE_COLORE,
                    stroke_width=POLYLINE_SPESSORE,
                    border_stroke_width=1.5,
                    border_color=ft.Colors.WHITE,
                )
            ]
        self._aggiorna_banner_percorso(route)
        self._notifica_percorso_visibile()

    def nascondi_percorso(self) -> None:
        self.mostra_percorso(None)
        self.page.update()

    async def _fetch_route(self, lat: float, lon: float) -> RouteResult:
        profilo = self.get_profilo()
        casa_lat, casa_lon = self.get_casa()
        return await asyncio.to_thread(
            calcola_percorso,
            lat,
            lon,
            lat_orig=casa_lat,
            lon_orig=casa_lon,
            profilo=profilo,
        )

    async def seleziona_scuola(self, scuola: dict | pd.Series) -> None:
        """Centra la mappa e apre il dialog (senza chiamare il routing)."""
        if isinstance(scuola, pd.Series):
            scuola = scuola.to_dict()

        await self.mappa.move_to(
            destination=MapLatitudeLongitude(
                float(scuola["Latitudine"]),
                float(scuola["Longitudine"]),
            ),
            zoom=MAPPA_ZOOM_DETTAGLIO,
        )
        self.mostra_scuola(scuola)
        self.page.update()

    async def calcola_percorso_scuola(self, scuola: dict) -> None:
        """On-demand: traccia + evidenza distretto finché il percorso resta attivo."""
        if isinstance(scuola, pd.Series):
            scuola = scuola.to_dict()
        lat = float(scuola["Latitudine"])
        lon = float(scuola["Longitudine"])
        self._scuola_percorso_nome = str(scuola.get("Nome", "") or "Scuola")
        route = await self._fetch_route(lat, lon)
        # Evidenza prima del disegno così i marker si aggiornano insieme alla traccia
        try:
            distretto = int(scuola["Distretto"])
        except (KeyError, TypeError, ValueError):
            distretto = None
        self._imposta_evidenza_distretto(
            distretto,
            str(scuola.get("Codice", "") or ""),
        )
        self.mostra_percorso(route)
        self.page.update()

    def mostra_scuola(
        self,
        scuola: dict | pd.Series,
        *,
        route: RouteResult | None = None,
    ) -> None:
        if isinstance(scuola, pd.Series):
            scuola = scuola.to_dict()

        distretto = int(scuola["Distretto"])
        colore = self.colore_per_distretto(distretto)
        indirizzo = str(scuola.get("Indirizzo", "") or "")
        nome = str(scuola.get("Nome", "") or "")
        lat = float(scuola["Latitudine"])
        lon = float(scuola["Longitudine"])
        distanza_aria = scuola.get("Distanza_m")
        if distanza_aria is None or (
            isinstance(distanza_aria, float) and pd.isna(distanza_aria)
        ):
            casa_lat, casa_lon = self.get_casa()
            distanza_aria = distanza_metri(casa_lat, casa_lon, lat, lon)

        async def centra(_e=None):
            await self.mappa.move_to(
                destination=MapLatitudeLongitude(lat, lon),
                zoom=MAPPA_ZOOM_DETTAGLIO,
            )
            self._chiudi_dialog()

        async def copia_indirizzo(_e=None):
            await self.page.clipboard.set(indirizzo)
            self.page.show_dialog(
                ft.SnackBar(content=ft.Text("Indirizzo copiato negli appunti"))
            )

        async def apri_google_maps(_e=None):
            url = f"https://www.google.com/maps?q={lat},{lon}"
            await ft.UrlLauncher().launch_url(url)

        async def apri_indicazioni_google(_e=None):
            casa_lat, casa_lon = self.get_casa()
            url = (
                "https://www.google.com/maps/dir/?api=1"
                f"&origin={casa_lat},{casa_lon}"
                f"&destination={lat},{lon}"
            )
            await ft.UrlLauncher().launch_url(url)

        async def mostra_percorso_mappa(_e=None):
            self._chiudi_dialog()
            await self.calcola_percorso_scuola(scuola)

        def nascondi(_e=None):
            self.nascondi_percorso()
            self._chiudi_dialog()

        def on_profilo_select(e: ft.ControlEvent) -> None:
            profilo = e.control.value or ROUTING_PROFILO_DEFAULT
            if self.set_profilo is not None:
                self.set_profilo(profilo)

        meta_percorso: list[ft.Control] = [
            ft.Text(
                f"Linea d'aria: {format_distanza(float(distanza_aria))}",
                size=12,
                color=UI_META_COLOR,
            ),
        ]
        if route is not None:
            label_prof = _PROFILO_LABEL.get(route.profilo, route.profilo)
            if route.sorgente == "osrm":
                suffix = " (durata stimata)" if route.durata_stimata else ""
                meta_percorso.append(
                    ft.Text(
                        f"Percorso ({label_prof}): {format_distanza(route.distanza_m)}"
                        f" · {format_durata(route.durata_s)}{suffix}",
                        size=13,
                        weight=ft.FontWeight.W_500,
                    )
                )
            else:
                meta_percorso.append(
                    ft.Text(
                        f"Percorso non disponibile — stima linea d'aria "
                        f"({format_distanza(route.distanza_m)}, ~{format_durata(route.durata_s)})",
                        size=12,
                        color=ft.Colors.ORANGE_800,
                    )
                )

        dropdown_profilo = ft.Dropdown(
            label="Modalità percorso",
            dense=True,
            value=self.get_profilo() or ROUTING_PROFILO_DEFAULT,
            options=[
                ft.DropdownOption(key=k, text=label) for k, label in ROUTING_PROFILI
            ],
            on_select=on_profilo_select,
        )

        menu_altro = ft.PopupMenuButton(
            icon=ft.Icons.MORE_VERT,
            tooltip=LABEL_ALTRO,
            items=[
                ft.PopupMenuItem(content="Centra sulla mappa", on_click=centra),
                ft.PopupMenuItem(content="Nascondi traccia", on_click=nascondi),
                ft.PopupMenuItem(content="Apri in Google Maps", on_click=apri_google_maps),
                ft.PopupMenuItem(content="Copia indirizzo", on_click=copia_indirizzo),
            ],
        )

        dialog = ft.AlertDialog(
            modal=True,
            scrollable=False,
            bgcolor=UI_SURFACE,
            on_dismiss=lambda _e: self._su_dismiss_dialog(),
            title=ft.Text(
                nome,
                size=17,
                weight=ft.FontWeight.W_700,
                color=UI_TITLE_COLOR,
            ),
            title_padding=ft.Padding.only(left=20, right=20, top=18, bottom=8),
            content_padding=ft.Padding.symmetric(horizontal=20, vertical=8),
            actions_padding=ft.Padding.only(left=12, right=12, bottom=12),
            inset_padding=ft.Padding.symmetric(horizontal=24, vertical=24),
            content=ft.Column(
                [
                    ft.Text(indirizzo, size=12, color=UI_META_COLOR),
                    ft.Row(
                        [
                            ft.Text("Distretto", size=12, color=UI_META_COLOR),
                            ft.Container(
                                padding=ft.Padding.symmetric(horizontal=8, vertical=3),
                                bgcolor=colore,
                                border_radius=6,
                                content=ft.Text(
                                    str(distretto),
                                    color=ft.Colors.WHITE,
                                    size=12,
                                    weight=ft.FontWeight.BOLD,
                                ),
                            ),
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Container(
                        padding=ft.Padding.symmetric(horizontal=10, vertical=8),
                        bgcolor=UI_ACCENT_SOFT,
                        border_radius=8,
                        content=ft.Column(
                            tight=True,
                            spacing=2,
                            controls=[
                                ft.Text(
                                    f"Grado: {scuola.get('Grado', '')}",
                                    size=12,
                                    color=UI_TITLE_COLOR,
                                ),
                                ft.Text(
                                    f"Codice: {scuola.get('Codice', '')}",
                                    size=12,
                                    color=UI_META_COLOR,
                                ),
                            ],
                        ),
                    ),
                    *meta_percorso,
                    dropdown_profilo,
                ],
                tight=True,
                spacing=8,
                width=320,
            ),
            actions=[
                ft.FilledButton(
                    "Mostra percorso",
                    icon=ft.Icons.ROUTE,
                    style=ft.ButtonStyle(bgcolor=UI_ACCENT, color=ft.Colors.WHITE),
                    on_click=mostra_percorso_mappa,
                ),
                ft.OutlinedButton(
                    "Indicazioni",
                    icon=ft.Icons.DIRECTIONS,
                    style=ft.ButtonStyle(color=UI_ACCENT, side=ft.BorderSide(1, UI_ACCENT)),
                    on_click=apri_indicazioni_google,
                ),
                menu_altro,
                ft.TextButton(
                    "Chiudi",
                    style=ft.ButtonStyle(color=UI_META_COLOR),
                    on_click=lambda e: self._chiudi_dialog(),
                ),
            ],
        )

        self._dialog = dialog
        self.page.show_dialog(dialog)

    def _su_dismiss_dialog(self) -> None:
        self._dialog = None

    def _chiudi_dialog(self) -> None:
        if self._dialog is not None:
            self.page.pop_dialog()
            self._dialog = None
        # L'evidenza distretto resta se c'è un percorso attivo;
        # si spegne solo con nascondi_percorso / mostra_percorso(None).

    def _scuola_vicina(self, lat: float, lon: float) -> dict | None:
        if self.df_corrente is None or len(self.df_corrente) == 0:
            return None

        migliore = None
        dist_min = float("inf")

        for _, scuola in self.df_corrente.iterrows():
            d = distanza_metri(
                lat,
                lon,
                float(scuola["Latitudine"]),
                float(scuola["Longitudine"]),
            )
            if d < dist_min:
                dist_min = d
                migliore = scuola

        if migliore is not None and dist_min <= HIT_TEST_METRI:
            return migliore.to_dict()
        return None

    def _on_tap(self, e) -> None:
        if e.coordinates is None:
            return
        lat = e.coordinates.latitude
        lon = e.coordinates.longitude

        if self._mode_imposta_casa:
            self._mode_imposta_casa = False
            if self.on_casa_impostata is not None:
                self.on_casa_impostata(lat, lon)
            self.page.show_dialog(
                ft.SnackBar(content=ft.Text(MSG_CASA_IMPOSTATA), duration=3000)
            )
            return

        scuola = self._scuola_vicina(lat, lon)
        if scuola is not None:
            self.page.run_task(self.seleziona_scuola, scuola)


def crea_mappa(
    page: ft.Page,
    *,
    get_profilo: Callable[[], str] | None = None,
    set_profilo: Callable[[str], None] | None = None,
    get_casa: Callable[[], tuple[float, float]] | None = None,
    on_casa_impostata: Callable[[float, float], None] | None = None,
    on_percorso_visibile: Callable[[bool], None] | None = None,
) -> MappaController:
    return MappaController(
        page,
        get_profilo=get_profilo,
        set_profilo=set_profilo,
        get_casa=get_casa,
        on_casa_impostata=on_casa_impostata,
        on_percorso_visibile=on_percorso_visibile,
    )
