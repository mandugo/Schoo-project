"""Sidebar filtri: accordion grado/distretti/opzioni, ricerca, mini-lista."""

from __future__ import annotations

from typing import Callable

import flet as ft
import pandas as pd

from utils.config import (
    LABEL_AZZERA_FILTRI,
    LABEL_ORDINA_DISTANZA,
    MINI_LISTA_MAX,
    MSG_EMPTY_RISULTATI,
    SIDEBAR_WIDTH,
    UI_META_COLOR,
    UI_SIDEBAR_BG,
)
from utils.database import (
    conta_per_distretto,
    conta_per_grado,
    elenco_distretti,
    elenco_gradi,
)
from utils.geo import format_distanza
from utils.state import FilterState


def format_conteggio_scuole(n: int) -> str:
    if n == 1:
        return "1 scuola mostrata"
    return f"{n} scuole mostrate"


class SidebarController:
    def __init__(
        self,
        state: FilterState,
        *,
        on_seleziona_scuola: Callable[[dict], None] | None = None,
        colore_distretto: Callable[[int], object] | None = None,
        on_conteggio: Callable[[int], None] | None = None,
    ):
        self.state = state
        self.on_seleziona_scuola = on_seleziona_scuola
        self.colore_distretto = colore_distretto
        self.on_conteggio = on_conteggio

        self.gradi = elenco_gradi()
        self.distretti = elenco_distretti()
        self.conteggio_gradi = conta_per_grado()
        self.conteggio_distretti = conta_per_distretto()

        # Default: tutto selezionato
        if not state.gradi:
            state.gradi = list(self.gradi)
        if not state.distretti:
            state.distretti = list(self.distretti)

        self._grado_checks: dict[str, ft.Checkbox] = {}
        self._distretto_checks: dict[int, ft.Checkbox] = {}

        self.risultati = ft.Column(spacing=4, scroll=ft.ScrollMode.AUTO, expand=True)

        self._clear_btn = ft.IconButton(
            icon=ft.Icons.CLEAR,
            icon_size=18,
            tooltip="Cancella ricerca",
            on_click=self._clear_ricerca,
            visible=False,
        )
        self.campo_ricerca = ft.TextField(
            hint_text="Nome, indirizzo o codice...",
            on_change=self._on_ricerca,
            dense=True,
            suffix=self._clear_btn,
        )

        self.btn_azzera = ft.TextButton(
            LABEL_AZZERA_FILTRI,
            icon=ft.Icons.FILTER_ALT_OFF,
            on_click=lambda _e: self.azzera_filtri(),
        )

        self.switch_casa = ft.Switch(
            label="Mostra casa",
            value=state.mostra_casa,
            on_change=self._on_casa,
        )
        self.switch_ordina = ft.Switch(
            label=LABEL_ORDINA_DISTANZA,
            value=state.ordina_per_distanza,
            on_change=self._on_ordina,
        )

        self.empty_state = ft.Column(
            visible=False,
            spacing=4,
            tight=True,
            controls=[
                ft.Text(
                    MSG_EMPTY_RISULTATI,
                    size=13,
                    color=UI_META_COLOR,
                ),
                ft.TextButton(
                    LABEL_AZZERA_FILTRI,
                    on_click=lambda _e: self.azzera_filtri(),
                ),
            ],
        )

        tile_grado = ft.ExpansionTile(
            title=ft.Text("Grado", size=14, weight=ft.FontWeight.BOLD),
            dense=True,
            expanded=True,
            maintain_state=True,
            expanded_cross_axis_alignment=ft.CrossAxisAlignment.START,
            controls_padding=ft.Padding.only(left=4, right=4, bottom=4),
            controls=[
                ft.Row(
                    [
                        ft.TextButton("Tutti", on_click=self._gradi_tutti),
                        ft.TextButton("Nessuno", on_click=self._gradi_nessuno),
                    ],
                    spacing=0,
                ),
                *self._build_grado_checks(),
            ],
        )

        tile_distretti = ft.ExpansionTile(
            title=ft.Text("Distretti", size=14, weight=ft.FontWeight.BOLD),
            dense=True,
            expanded=False,
            maintain_state=True,
            expanded_cross_axis_alignment=ft.CrossAxisAlignment.START,
            controls_padding=ft.Padding.only(left=4, right=4, bottom=4),
            controls=[
                ft.Row(
                    [
                        ft.TextButton("Tutti", on_click=self._distretti_tutti),
                        ft.TextButton("Nessuno", on_click=self._distretti_nessuno),
                    ],
                    spacing=0,
                ),
                *self._build_distretto_checks(),
                ft.Divider(height=12),
                ft.Text("Legenda", size=12, weight=ft.FontWeight.W_500, color=UI_META_COLOR),
                self._build_legenda(),
            ],
        )

        tile_opzioni = ft.ExpansionTile(
            title=ft.Text("Opzioni", size=14, weight=ft.FontWeight.BOLD),
            dense=True,
            expanded=False,
            maintain_state=True,
            expanded_cross_axis_alignment=ft.CrossAxisAlignment.START,
            controls_padding=ft.Padding.only(left=4, right=4, bottom=4),
            controls=[self.switch_casa, self.switch_ordina],
        )

        self.body = ft.Column(
            expand=True,
            spacing=6,
            controls=[
                ft.Text("Ricerca scuola", size=16, weight=ft.FontWeight.BOLD),
                self.campo_ricerca,
                self.btn_azzera,
                tile_grado,
                tile_distretti,
                tile_opzioni,
                ft.Divider(),
                ft.Text("Risultati", size=14, weight=ft.FontWeight.BOLD),
                self.empty_state,
                self.risultati,
            ],
        )

        self.root = ft.Container(
            width=SIDEBAR_WIDTH,
            bgcolor=UI_SIDEBAR_BG,
            padding=12,
            content=self.body,
        )

    def _colore(self, distretto: int) -> object:
        if self.colore_distretto is not None:
            return self.colore_distretto(distretto)
        return ft.Colors.BLUE

    @staticmethod
    def _pallino(colore: object, size: float = 10) -> ft.Container:
        return ft.Container(
            width=size,
            height=size,
            bgcolor=colore,
            border_radius=size,
            border=ft.Border.all(1, ft.Colors.with_opacity(0.35, ft.Colors.BLACK)),
        )

    def _build_grado_checks(self) -> list[ft.Checkbox]:
        checks = []
        for grado in self.gradi:
            cb = ft.Checkbox(
                label=f"{grado} ({self.conteggio_gradi.get(grado, 0)})",
                value=grado in self.state.gradi,
                data=grado,
                on_change=self._on_grado,
            )
            self._grado_checks[grado] = cb
            checks.append(cb)
        return checks

    def _build_distretto_checks(self) -> list[ft.Control]:
        rows: list[ft.Control] = []
        for d in self.distretti:
            cb = ft.Checkbox(
                label=f"Distretto {d:02d} ({self.conteggio_distretti.get(d, 0)})",
                value=d in self.state.distretti,
                data=d,
                on_change=self._on_distretto,
            )
            self._distretto_checks[d] = cb
            rows.append(
                ft.Row(
                    [self._pallino(self._colore(d)), cb],
                    spacing=6,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                )
            )
        return rows

    def _build_legenda(self) -> ft.Row:
        items: list[ft.Control] = []
        for d in self.distretti:
            items.append(
                ft.Row(
                    [
                        self._pallino(self._colore(d), size=8),
                        ft.Text(f"{d:02d}", size=11, color=UI_META_COLOR),
                    ],
                    spacing=4,
                    tight=True,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                )
            )
        return ft.Row(
            controls=items,
            wrap=True,
            spacing=8,
            run_spacing=4,
        )

    def _on_grado(self, e: ft.ControlEvent) -> None:
        self.state.toggle_grado(e.control.data, bool(e.control.value))

    def _on_distretto(self, e: ft.ControlEvent) -> None:
        self.state.toggle_distretto(int(e.control.data), bool(e.control.value))

    def _on_ricerca(self, e: ft.ControlEvent) -> None:
        testo = e.control.value or ""
        self._clear_btn.visible = bool(testo.strip())
        self.state.set_testo(testo)

    def _clear_ricerca(self, _e=None) -> None:
        self.campo_ricerca.value = ""
        self._clear_btn.visible = False
        self.state.set_testo("")

    def _on_casa(self, e: ft.ControlEvent) -> None:
        self.state.set_mostra_casa(bool(e.control.value))

    def _on_ordina(self, e: ft.ControlEvent) -> None:
        self.state.set_ordina_per_distanza(bool(e.control.value))

    def _gradi_tutti(self, _e=None) -> None:
        for cb in self._grado_checks.values():
            cb.value = True
        self.state.set_gradi(list(self.gradi))

    def _gradi_nessuno(self, _e=None) -> None:
        for cb in self._grado_checks.values():
            cb.value = False
        self.state.set_gradi([])

    def _distretti_tutti(self, _e=None) -> None:
        for cb in self._distretto_checks.values():
            cb.value = True
        self.state.set_distretti(list(self.distretti))

    def _distretti_nessuno(self, _e=None) -> None:
        for cb in self._distretto_checks.values():
            cb.value = False
        self.state.set_distretti([])

    def azzera_filtri(self) -> None:
        """Ripristina lo stato iniziale: gradi/distretti tutti, testo vuoto, casa=True."""
        for cb in self._grado_checks.values():
            cb.value = True
        for cb in self._distretto_checks.values():
            cb.value = True
        self.campo_ricerca.value = ""
        self._clear_btn.visible = False
        self.switch_casa.value = True
        self.switch_ordina.value = True

        self.state.set_gradi(list(self.gradi), notify=False)
        self.state.set_distretti(list(self.distretti), notify=False)
        self.state.set_testo("", notify=False)
        self.state.set_mostra_casa(True, notify=False)
        self.state.set_ordina_per_distanza(True, notify=False)
        self.state.notify()

    def applica_stato_ui(self) -> None:
        """Allinea checkbox/switch/campo allo stato (es. dopo decode URL)."""
        for grado, cb in self._grado_checks.items():
            cb.value = grado in self.state.gradi
        for d, cb in self._distretto_checks.items():
            cb.value = d in self.state.distretti
        self.campo_ricerca.value = self.state.testo
        self._clear_btn.visible = bool(self.state.testo.strip())
        self.switch_casa.value = self.state.mostra_casa
        self.switch_ordina.value = self.state.ordina_per_distanza

    def aggiorna_risultati(self, df: pd.DataFrame) -> None:
        n = len(df)
        if self.on_conteggio is not None:
            self.on_conteggio(n)

        self.risultati.controls.clear()
        if n == 0:
            self.empty_state.visible = True
        else:
            self.empty_state.visible = False
            mostrati = df.head(MINI_LISTA_MAX)
            for _, row in mostrati.iterrows():
                data = row.to_dict()
                distretto = int(row["Distretto"])
                colore = self._colore(distretto)
                dist_txt = ""
                if "Distanza_m" in row and pd.notna(row["Distanza_m"]):
                    dist_txt = f" · {format_distanza(float(row['Distanza_m']))}"
                self.risultati.controls.append(
                    ft.ListTile(
                        dense=True,
                        title=ft.Text(
                            str(row["Nome"]),
                            size=13,
                            max_lines=2,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                        subtitle=ft.Text(
                            f"Distretto {distretto} · {row.get('Grado', '')}{dist_txt}",
                            size=11,
                        ),
                        leading=ft.Icon(ft.Icons.SCHOOL, color=colore, size=20),
                        on_click=lambda e, s=data: self._click_risultato(s),
                    )
                )
            if n > MINI_LISTA_MAX:
                self.risultati.controls.append(
                    ft.Text(
                        f"… e altre {n - MINI_LISTA_MAX}",
                        size=12,
                        color=UI_META_COLOR,
                    )
                )

    def _click_risultato(self, scuola: dict) -> None:
        if self.on_seleziona_scuola is not None:
            self.on_seleziona_scuola(scuola)


def crea_sidebar(
    state: FilterState,
    *,
    on_seleziona_scuola: Callable[[dict], None] | None = None,
    colore_distretto: Callable[[int], object] | None = None,
    on_conteggio: Callable[[int], None] | None = None,
) -> SidebarController:
    return SidebarController(
        state,
        on_seleziona_scuola=on_seleziona_scuola,
        colore_distretto=colore_distretto,
        on_conteggio=on_conteggio,
    )
