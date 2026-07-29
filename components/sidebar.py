"""Sidebar filtri: grado, distretto, ricerca, casa, mini-lista risultati."""

from __future__ import annotations

from typing import Callable

import flet as ft
import pandas as pd

from utils.config import MINI_LISTA_MAX
from utils.database import (
    conta_per_distretto,
    conta_per_grado,
    elenco_distretti,
    elenco_gradi,
)
from utils.state import FilterState


class SidebarController:
    def __init__(
        self,
        state: FilterState,
        *,
        on_seleziona_scuola: Callable[[dict], None] | None = None,
        colore_distretto: Callable[[int], object] | None = None,
    ):
        self.state = state
        self.on_seleziona_scuola = on_seleziona_scuola
        self.colore_distretto = colore_distretto

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

        self.contatore = ft.Text(
            "0 scuole mostrate",
            size=14,
            weight=ft.FontWeight.BOLD,
        )
        self.empty_label = ft.Text(
            "Nessuna scuola trovata",
            size=13,
            color=ft.Colors.GREY_600,
            visible=False,
        )
        self.risultati = ft.Column(spacing=4, scroll=ft.ScrollMode.AUTO, expand=True)

        self.campo_ricerca = ft.TextField(
            hint_text="Nome, indirizzo o codice...",
            on_change=self._on_ricerca,
            dense=True,
        )

        self.switch_casa = ft.Switch(
            label="Mostra casa",
            value=state.mostra_casa,
            on_change=self._on_casa,
        )

        filtri = ft.Column(
            spacing=6,
            tight=True,
            controls=[
                ft.Text("Grado scolastico", size=18, weight=ft.FontWeight.BOLD),
                ft.Row(
                    [
                        ft.TextButton("Tutti", on_click=self._gradi_tutti),
                        ft.TextButton("Nessuno", on_click=self._gradi_nessuno),
                    ],
                    spacing=0,
                ),
                *self._build_grado_checks(),
                ft.Divider(),
                ft.Text("Distretti", size=18, weight=ft.FontWeight.BOLD),
                ft.Row(
                    [
                        ft.TextButton("Tutti", on_click=self._distretti_tutti),
                        ft.TextButton("Nessuno", on_click=self._distretti_nessuno),
                    ],
                    spacing=0,
                ),
                *self._build_distretto_checks(),
                ft.Divider(),
                self.switch_casa,
            ],
        )

        self.root = ft.Container(
            width=340,
            bgcolor=ft.Colors.GREY_100,
            padding=15,
            content=ft.Column(
                expand=True,
                spacing=8,
                controls=[
                    ft.Text("Ricerca scuola", size=18, weight=ft.FontWeight.BOLD),
                    self.campo_ricerca,
                    self.contatore,
                    ft.Divider(),
                    ft.Column(
                        expand=False,
                        height=340,
                        scroll=ft.ScrollMode.AUTO,
                        controls=[filtri],
                    ),
                    ft.Divider(),
                    ft.Text("Risultati", size=16, weight=ft.FontWeight.BOLD),
                    self.empty_label,
                    self.risultati,
                ],
            ),
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

    def _build_distretto_checks(self) -> list[ft.Checkbox]:
        checks = []
        for d in self.distretti:
            cb = ft.Checkbox(
                label=f"Distretto {d:02d} ({self.conteggio_distretti.get(d, 0)})",
                value=d in self.state.distretti,
                data=d,
                on_change=self._on_distretto,
            )
            self._distretto_checks[d] = cb
            checks.append(cb)
        return checks

    def _on_grado(self, e: ft.ControlEvent) -> None:
        self.state.toggle_grado(e.control.data, bool(e.control.value))

    def _on_distretto(self, e: ft.ControlEvent) -> None:
        self.state.toggle_distretto(int(e.control.data), bool(e.control.value))

    def _on_ricerca(self, e: ft.ControlEvent) -> None:
        self.state.set_testo(e.control.value or "")

    def _on_casa(self, e: ft.ControlEvent) -> None:
        self.state.set_mostra_casa(bool(e.control.value))

    def _gradi_tutti(self, _e=None) -> None:
        for grado, cb in self._grado_checks.items():
            cb.value = True
        self.state.set_gradi(list(self.gradi))

    def _gradi_nessuno(self, _e=None) -> None:
        for cb in self._grado_checks.values():
            cb.value = False
        self.state.set_gradi([])

    def _distretti_tutti(self, _e=None) -> None:
        for d, cb in self._distretto_checks.items():
            cb.value = True
        self.state.set_distretti(list(self.distretti))

    def _distretti_nessuno(self, _e=None) -> None:
        for cb in self._distretto_checks.values():
            cb.value = False
        self.state.set_distretti([])

    def aggiorna_risultati(self, df: pd.DataFrame) -> None:
        n = len(df)
        self.contatore.value = f"{n} scuol{'a' if n == 1 else 'e'} mostrat{'a' if n == 1 else 'e'}"

        self.risultati.controls.clear()
        if n == 0:
            self.empty_label.visible = True
        else:
            self.empty_label.visible = False
            mostrati = df.head(MINI_LISTA_MAX)
            for _, row in mostrati.iterrows():
                data = row.to_dict()
                distretto = int(row["Distretto"])
                colore = (
                    self.colore_distretto(distretto)
                    if self.colore_distretto
                    else ft.Colors.BLUE
                )
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
                            f"Distretto {distretto} · {row.get('Grado', '')}",
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
                        color=ft.Colors.GREY_600,
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
) -> SidebarController:
    return SidebarController(
        state,
        on_seleziona_scuola=on_seleziona_scuola,
        colore_distretto=colore_distretto,
    )
