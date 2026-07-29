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
    UI_META_COLOR,
)
from utils.database import statistiche_dataset
from utils.geo import distanza_metri, format_distanza
from utils.routing import RouteResult, calcola_percorso, format_durata

COLORI_DISTRETTO = [
    ft.Colors.RED,
    ft.Colors.BLUE,
    ft.Colors.GREEN,
    ft.Colors.ORANGE,
    ft.Colors.PURPLE,
    ft.Colors.TEAL,
    ft.Colors.PINK,
    ft.Colors.BROWN,
]

_PROFILO_LABEL = dict(ROUTING_PROFILI)


def mappa_colori_distretto(distretti: list[int]) -> dict[int, Any]:
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
        get_casa: Callable[[], tuple[float, float]] | None = None,
        on_casa_impostata: Callable[[float, float], None] | None = None,
        on_percorso_visibile: Callable[[bool], None] | None = None,
    ):
        self.page = page
        self.get_profilo = get_profilo or (lambda: ROUTING_PROFILO_DEFAULT)
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

        self.root = ft.Column(
            expand=True,
            spacing=0,
            controls=[
                self.mappa,
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=10, vertical=4),
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

    def _marker_scuola(self, colore: Any, scuola: dict) -> ft.Control:
        return ft.GestureDetector(
            on_tap=lambda e, s=scuola: self.page.run_task(self.seleziona_scuola, s),
            content=ft.Container(
                width=MARKER_SCUOLA_SIZE + 6,
                height=MARKER_SCUOLA_SIZE + 6,
                alignment=ft.Alignment.CENTER,
                bgcolor=ft.Colors.with_opacity(0.92, ft.Colors.WHITE),
                border=ft.Border.all(1.5, colore),
                border_radius=(MARKER_SCUOLA_SIZE + 6) / 2,
                content=ft.Icon(
                    ft.Icons.SCHOOL,
                    color=colore,
                    size=MARKER_SCUOLA_SIZE - 4,
                ),
            ),
        )

    def aggiorna_marker(self, df: pd.DataFrame, mostra_casa: bool = True) -> None:
        self.df_corrente = df.copy()
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
                        bgcolor=ft.Colors.with_opacity(0.92, ft.Colors.WHITE),
                        border=ft.Border.all(1.5, ft.Colors.BLACK),
                        border_radius=(MARKER_CASA_SIZE + 4) / 2,
                        content=ft.Icon(
                            ft.Icons.HOME,
                            color=ft.Colors.BLACK,
                            size=MARKER_CASA_SIZE - 6,
                        ),
                    ),
                    data={"tipo": "casa"},
                )
            )

        self.livello_marker.markers = markers

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

    def mostra_percorso(self, route: RouteResult | None) -> None:
        """Disegna (o rimuove) la polilinea del percorso sulla mappa."""
        self._route_corrente = route
        if route is None or len(route.coordinate) < 2:
            self.livello_percorso.polylines = []
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
        """On-demand: calcola OSRM, disegna la traccia e lascia la mappa libera."""
        lat = float(scuola["Latitudine"])
        lon = float(scuola["Longitudine"])
        route = await self._fetch_route(lat, lon)
        self.mostra_percorso(route)

        label_prof = _PROFILO_LABEL.get(route.profilo, route.profilo)
        if route.sorgente == "osrm":
            suffix = " (durata stimata)" if route.durata_stimata else ""
            msg = (
                f"Percorso ({label_prof}): {format_distanza(route.distanza_m)}"
                f" · {format_durata(route.durata_s)}{suffix}"
            )
        else:
            msg = (
                f"Routing non disponibile — stima "
                f"{format_distanza(route.distanza_m)} · ~{format_durata(route.durata_s)}"
            )

        self.page.show_dialog(
            ft.SnackBar(content=ft.Text(msg, max_lines=2), duration=4500)
        )
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

        dialog = ft.AlertDialog(
            modal=True,
            scrollable=False,
            title=ft.Text(nome, size=16, weight=ft.FontWeight.BOLD),
            title_padding=ft.Padding.only(left=20, right=20, top=16, bottom=8),
            content_padding=ft.Padding.symmetric(horizontal=20, vertical=8),
            actions_padding=ft.Padding.only(left=8, right=8, bottom=8),
            inset_padding=ft.Padding.symmetric(horizontal=24, vertical=24),
            content=ft.Column(
                [
                    ft.Text(indirizzo, size=12, color=UI_META_COLOR),
                    ft.Row(
                        [
                            ft.Text("Distretto", size=12, color=UI_META_COLOR),
                            ft.Container(
                                padding=ft.Padding.symmetric(horizontal=8, vertical=2),
                                bgcolor=colore,
                                border_radius=4,
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
                    ft.Text(
                        f"Grado: {scuola.get('Grado', '')}",
                        size=12,
                        color=UI_META_COLOR,
                    ),
                    ft.Text(
                        f"Codice: {scuola.get('Codice', '')}",
                        size=12,
                        color=UI_META_COLOR,
                    ),
                    *meta_percorso,
                ],
                tight=True,
                spacing=6,
                width=320,
            ),
            actions=[
                ft.TextButton("Centra", on_click=centra),
                ft.TextButton("Mostra percorso", on_click=mostra_percorso_mappa),
                ft.TextButton("Nascondi traccia", on_click=nascondi),
                ft.TextButton("Indicazioni Google", on_click=apri_indicazioni_google),
                ft.TextButton("Maps", on_click=apri_google_maps),
                ft.TextButton("Copia", on_click=copia_indirizzo),
                ft.TextButton("Chiudi", on_click=lambda e: self._chiudi_dialog()),
            ],
        )

        self._dialog = dialog
        self.page.show_dialog(dialog)

    def _chiudi_dialog(self) -> None:
        if self._dialog is not None:
            self.page.pop_dialog()
            self._dialog = None

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
    get_casa: Callable[[], tuple[float, float]] | None = None,
    on_casa_impostata: Callable[[float, float], None] | None = None,
    on_percorso_visibile: Callable[[bool], None] | None = None,
) -> MappaController:
    return MappaController(
        page,
        get_profilo=get_profilo,
        get_casa=get_casa,
        on_casa_impostata=on_casa_impostata,
        on_percorso_visibile=on_percorso_visibile,
    )
