"""Vista mappa: marker scuole filtrati, hit-test, dialog info."""

from __future__ import annotations

from typing import Any

import flet as ft
import pandas as pd
from flet_map import Map, MapLatitudeLongitude, Marker, MarkerLayer, TileLayer

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
    UI_META_COLOR,
)
from utils.geo import distanza_metri, format_distanza
from utils.database import statistiche_dataset

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


def mappa_colori_distretto(distretti: list[int]) -> dict[int, Any]:
    return {
        d: COLORI_DISTRETTO[i % len(COLORI_DISTRETTO)]
        for i, d in enumerate(sorted(distretti))
    }


class MappaController:
    """Gestisce MarkerLayer, dialog e aggiornamenti filtri."""

    def __init__(self, page: ft.Page):
        self.page = page
        self.df_corrente: pd.DataFrame = pd.DataFrame()
        self.colore_distretto: dict[int, Any] = {}
        self.livello_marker = MarkerLayer(markers=[])
        self._dialog: ft.AlertDialog | None = None

        self.livello_mappa = TileLayer(
            url_template="https://tile.openstreetmap.org/{z}/{x}/{y}.png",
            user_agent_package_name="ScuoleTorinoExplorer",
        )

        self.mappa = Map(
            expand=True,
            initial_center=MapLatitudeLongitude(MAPPA_CENTRO_LAT, MAPPA_CENTRO_LON),
            initial_zoom=MAPPA_ZOOM_INIZIALE,
            layers=[self.livello_mappa, self.livello_marker],
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
            on_tap=lambda e, s=scuola: self.mostra_scuola(s),
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
        # Mantieni palette stabile rispetto a tutti i distretti già visti
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
            markers.append(
                Marker(
                    coordinates=MapLatitudeLongitude(CASA_LAT, CASA_LON),
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

    async def seleziona_scuola(self, scuola: dict | pd.Series) -> None:
        """Centra la mappa sulla scuola e apre il dialog (usato dalla mini-lista)."""
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

    def mostra_scuola(self, scuola: dict | pd.Series) -> None:
        if isinstance(scuola, pd.Series):
            scuola = scuola.to_dict()

        distretto = int(scuola["Distretto"])
        colore = self.colore_per_distretto(distretto)
        indirizzo = str(scuola.get("Indirizzo", "") or "")
        nome = str(scuola.get("Nome", "") or "")
        lat = float(scuola["Latitudine"])
        lon = float(scuola["Longitudine"])
        distanza_m = scuola.get("Distanza_m")
        if distanza_m is None or (isinstance(distanza_m, float) and pd.isna(distanza_m)):
            distanza_m = distanza_metri(CASA_LAT, CASA_LON, lat, lon)

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

        async def apri_indicazioni(_e=None):
            url = (
                "https://www.google.com/maps/dir/?api=1"
                f"&origin={CASA_LAT},{CASA_LON}"
                f"&destination={lat},{lon}"
            )
            await ft.UrlLauncher().launch_url(url)

        dialog = ft.AlertDialog(
            title=ft.Text(nome, size=18, weight=ft.FontWeight.BOLD),
            content=ft.Column(
                [
                    ft.Text(indirizzo, size=13, color=UI_META_COLOR),
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
                        size=13,
                        color=UI_META_COLOR,
                    ),
                    ft.Text(
                        f"Codice: {scuola.get('Codice', '')}",
                        size=12,
                        color=UI_META_COLOR,
                    ),
                    ft.Text(
                        f"Distanza da casa: {format_distanza(float(distanza_m))}",
                        size=13,
                        color=UI_META_COLOR,
                    ),
                ],
                tight=True,
                spacing=8,
                width=360,
            ),
            actions=[
                ft.TextButton("Centra sulla mappa", on_click=centra),
                ft.TextButton("Indicazioni", on_click=apri_indicazioni),
                ft.TextButton("Apri in Google Maps", on_click=apri_google_maps),
                ft.TextButton("Copia indirizzo", on_click=copia_indirizzo),
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
        scuola = self._scuola_vicina(e.coordinates.latitude, e.coordinates.longitude)
        if scuola is not None:
            self.mostra_scuola(scuola)


def crea_mappa(page: ft.Page) -> MappaController:
    return MappaController(page)
