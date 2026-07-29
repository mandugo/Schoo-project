"""Vista mappa: marker scuole filtrati, hit-test, dialog info."""

from __future__ import annotations

from typing import Any

import flet as ft
import pandas as pd
from flet_map import Map, MapLatitudeLongitude, Marker, MarkerLayer, TileLayer

from utils.config import (
    CASA_LAT,
    CASA_LON,
    HIT_TEST_METRI,
    MAPPA_CENTRO_LAT,
    MAPPA_CENTRO_LON,
    MAPPA_ZOOM_DETTAGLIO,
    MAPPA_ZOOM_INIZIALE,
)
from utils.geo import distanza_metri

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

        self.empty_banner = ft.Text(
            "",
            size=14,
            color=ft.Colors.GREY_700,
            visible=False,
        )

        self.root = ft.Column(
            expand=True,
            spacing=0,
            controls=[
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=12, vertical=6),
                    content=self.empty_banner,
                ),
                self.mappa,
            ],
        )

    def colore_per_distretto(self, distretto: int) -> Any:
        return self.colore_distretto.get(
            int(distretto), COLORI_DISTRETTO[int(distretto) % len(COLORI_DISTRETTO)]
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
                    content=ft.GestureDetector(
                        on_tap=lambda e, s=data: self.mostra_scuola(s),
                        content=ft.Icon(ft.Icons.SCHOOL, color=colore, size=22),
                    ),
                    data=data,
                )
            )

        if mostra_casa:
            markers.append(
                Marker(
                    coordinates=MapLatitudeLongitude(CASA_LAT, CASA_LON),
                    content=ft.Icon(ft.Icons.HOME, color=ft.Colors.BLACK, size=30),
                    data={"tipo": "casa"},
                )
            )

        self.livello_marker.markers = markers

        n = len(df)
        if n == 0:
            self.empty_banner.value = "Nessuna scuola trovata con i filtri attuali."
            self.empty_banner.visible = True
        else:
            self.empty_banner.value = ""
            self.empty_banner.visible = False

    def mostra_scuola(self, scuola: dict | pd.Series) -> None:
        if isinstance(scuola, pd.Series):
            scuola = scuola.to_dict()

        distretto = int(scuola["Distretto"])
        colore = self.colore_per_distretto(distretto)
        indirizzo = str(scuola.get("Indirizzo", "") or "")

        async def centra(_e=None):
            await self.mappa.move_to(
                destination=MapLatitudeLongitude(
                    float(scuola["Latitudine"]),
                    float(scuola["Longitudine"]),
                ),
                zoom=MAPPA_ZOOM_DETTAGLIO,
            )
            self._chiudi_dialog()

        async def copia_indirizzo(_e=None):
            await self.page.clipboard.set(indirizzo)
            self.page.show_dialog(
                ft.SnackBar(content=ft.Text("Indirizzo copiato negli appunti"))
            )

        dialog = ft.AlertDialog(
            title=ft.Text("Informazioni scuola"),
            content=ft.Column(
                [
                    ft.Text(str(scuola.get("Nome", "")), size=16, weight=ft.FontWeight.BOLD),
                    ft.Text(f"Indirizzo: {indirizzo}"),
                    ft.Row(
                        [
                            ft.Text("Distretto:"),
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
                    ft.Text(f"Grado: {scuola.get('Grado', '')}"),
                    ft.Text(f"Codice: {scuola.get('Codice', '')}"),
                ],
                tight=True,
                spacing=8,
                width=360,
            ),
            actions=[
                ft.TextButton("Centra sulla mappa", on_click=centra),
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
