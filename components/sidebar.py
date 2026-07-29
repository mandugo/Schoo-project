"""Sidebar filtri: ricerca, grado/distretti, luogo (casa), mini-lista."""

from __future__ import annotations

from typing import Callable

import flet as ft
import pandas as pd

from utils.config import (
    LABEL_AZZERA_FILTRI,
    LABEL_IMPOSTA_CASA,
    LABEL_LUOGO,
    LABEL_ORDINA_DISTANZA,
    LABEL_RIPRISTINA_CASA,
    MINI_LISTA_MAX,
    MSG_EMPTY_RISULTATI,
    ROUTING_PROFILO_DEFAULT,
    SIDEBAR_WIDTH,
    UI_ACCENT,
    UI_ACCENT_SOFT,
    UI_BORDER,
    UI_DIVIDER,
    UI_META_COLOR,
    UI_SIDEBAR_BG,
    UI_SURFACE,
    UI_TITLE_COLOR,
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
        on_imposta_casa: Callable[[], None] | None = None,
        on_ripristina_casa: Callable[[], None] | None = None,
    ):
        self.state = state
        self.on_seleziona_scuola = on_seleziona_scuola
        self.colore_distretto = colore_distretto
        self.on_conteggio = on_conteggio
        self.on_imposta_casa = on_imposta_casa
        self.on_ripristina_casa = on_ripristina_casa

        self.gradi = elenco_gradi()
        self.distretti = elenco_distretti()
        self.conteggio_gradi = conta_per_grado()
        self.conteggio_distretti = conta_per_distretto()

        if not state.gradi:
            state.gradi = list(self.gradi)
        if not state.distretti:
            state.distretti = list(self.distretti)

        self._grado_checks: dict[str, ft.Checkbox] = {}
        self._distretto_checks: dict[int, ft.Checkbox] = {}

        self.risultati = ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO, expand=True)

        self._clear_btn = ft.IconButton(
            icon=ft.Icons.CLEAR,
            icon_size=18,
            icon_color=UI_META_COLOR,
            tooltip="Cancella ricerca",
            on_click=self._clear_ricerca,
            visible=False,
        )
        self.campo_ricerca = ft.TextField(
            hint_text="Nome, indirizzo o codice...",
            on_change=self._on_ricerca,
            dense=True,
            bgcolor=UI_SURFACE,
            border_color=UI_BORDER,
            focused_border_color=UI_ACCENT,
            cursor_color=UI_ACCENT,
            suffix=self._clear_btn,
        )

        self.btn_azzera = ft.TextButton(
            LABEL_AZZERA_FILTRI,
            icon=ft.Icons.FILTER_ALT_OFF,
            style=ft.ButtonStyle(color=UI_ACCENT),
            on_click=lambda _e: self.azzera_filtri(),
        )

        self.switch_casa = ft.Switch(
            label="Mostra casa",
            value=state.mostra_casa,
            active_color=UI_ACCENT,
            on_change=self._on_casa,
        )
        self.switch_ordina = ft.Switch(
            label=LABEL_ORDINA_DISTANZA,
            value=state.ordina_per_distanza,
            active_color=UI_ACCENT,
            on_change=self._on_ordina,
        )

        self.chip_casa = ft.Container(
            padding=ft.Padding.symmetric(horizontal=10, vertical=8),
            bgcolor=UI_ACCENT_SOFT,
            border=ft.Border.all(1, UI_BORDER),
            border_radius=10,
            content=ft.Row(
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(ft.Icons.HOME_OUTLINED, size=16, color=UI_ACCENT),
                    ft.Text(
                        self._testo_coords_casa(),
                        size=12,
                        color=UI_TITLE_COLOR,
                        weight=ft.FontWeight.W_500,
                    ),
                ],
            ),
        )
        self.btn_imposta_casa = ft.TextButton(
            LABEL_IMPOSTA_CASA,
            icon=ft.Icons.ADD_LOCATION_ALT,
            style=ft.ButtonStyle(color=UI_ACCENT),
            on_click=self._click_imposta_casa,
        )
        self.btn_ripristina_casa = ft.TextButton(
            LABEL_RIPRISTINA_CASA,
            icon=ft.Icons.RESTORE,
            style=ft.ButtonStyle(color=UI_META_COLOR),
            on_click=self._click_ripristina_casa,
        )

        self.empty_state = ft.Container(
            visible=False,
            padding=ft.Padding.all(14),
            bgcolor=UI_SURFACE,
            border=ft.Border.all(1, UI_BORDER),
            border_radius=12,
            content=ft.Column(
                spacing=6,
                tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.START,
                controls=[
                    ft.Icon(ft.Icons.SEARCH_OFF, size=22, color=UI_META_COLOR),
                    ft.Text(
                        MSG_EMPTY_RISULTATI,
                        size=13,
                        color=UI_TITLE_COLOR,
                        weight=ft.FontWeight.W_500,
                    ),
                    ft.TextButton(
                        LABEL_AZZERA_FILTRI,
                        style=ft.ButtonStyle(color=UI_ACCENT),
                        on_click=lambda _e: self.azzera_filtri(),
                    ),
                ],
            ),
        )

        tile_grado = ft.ExpansionTile(
            title=ft.Text(
                "Grado", size=14, weight=ft.FontWeight.W_700, color=UI_TITLE_COLOR
            ),
            dense=True,
            expanded=True,
            maintain_state=True,
            bgcolor=UI_SURFACE,
            collapsed_bgcolor=UI_SURFACE,
            expanded_cross_axis_alignment=ft.CrossAxisAlignment.START,
            controls_padding=ft.Padding.only(left=8, right=8, bottom=8),
            controls=[
                ft.Row(
                    [
                        ft.TextButton("Tutti", style=ft.ButtonStyle(color=UI_ACCENT), on_click=self._gradi_tutti),
                        ft.TextButton("Nessuno", style=ft.ButtonStyle(color=UI_META_COLOR), on_click=self._gradi_nessuno),
                    ],
                    spacing=0,
                ),
                *self._build_grado_checks(),
            ],
        )

        tile_distretti = ft.ExpansionTile(
            title=ft.Text(
                "Distretti", size=14, weight=ft.FontWeight.W_700, color=UI_TITLE_COLOR
            ),
            dense=True,
            expanded=False,
            maintain_state=True,
            bgcolor=UI_SURFACE,
            collapsed_bgcolor=UI_SURFACE,
            expanded_cross_axis_alignment=ft.CrossAxisAlignment.START,
            controls_padding=ft.Padding.only(left=8, right=8, bottom=8),
            controls=[
                ft.Row(
                    [
                        ft.TextButton("Tutti", style=ft.ButtonStyle(color=UI_ACCENT), on_click=self._distretti_tutti),
                        ft.TextButton("Nessuno", style=ft.ButtonStyle(color=UI_META_COLOR), on_click=self._distretti_nessuno),
                    ],
                    spacing=0,
                ),
                *self._build_distretto_checks(),
                ft.Divider(height=12, color=UI_DIVIDER),
                ft.Text("Legenda", size=12, weight=ft.FontWeight.W_500, color=UI_META_COLOR),
                self._build_legenda(),
            ],
        )

        blocco_luogo = ft.Container(
            padding=ft.Padding.all(12),
            bgcolor=UI_SURFACE,
            border=ft.Border.all(1, UI_BORDER),
            border_radius=12,
            content=ft.Column(
                tight=True,
                spacing=6,
                controls=[
                    self._section_title(LABEL_LUOGO),
                    self.chip_casa,
                    ft.Row(
                        [self.btn_imposta_casa, self.btn_ripristina_casa],
                        spacing=0,
                        wrap=True,
                    ),
                    self.switch_casa,
                    self.switch_ordina,
                ],
            ),
        )

        self.body = ft.Column(
            expand=True,
            spacing=10,
            controls=[
                self._section_title("Ricerca scuola", size=15),
                self.campo_ricerca,
                self.btn_azzera,
                ft.Container(
                    bgcolor=UI_SURFACE,
                    border=ft.Border.all(1, UI_BORDER),
                    border_radius=12,
                    clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                    content=tile_grado,
                ),
                ft.Container(
                    bgcolor=UI_SURFACE,
                    border=ft.Border.all(1, UI_BORDER),
                    border_radius=12,
                    clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                    content=tile_distretti,
                ),
                blocco_luogo,
                ft.Divider(height=1, color=UI_DIVIDER),
                self._section_title("Risultati"),
                self.empty_state,
                self.risultati,
            ],
        )

        self.root = ft.Container(
            width=SIDEBAR_WIDTH,
            bgcolor=UI_SIDEBAR_BG,
            padding=14,
            content=self.body,
        )

    @staticmethod
    def _section_title(text: str, size: float = 14) -> ft.Control:
        return ft.Row(
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(
                    width=3,
                    height=14,
                    bgcolor=UI_ACCENT,
                    border_radius=2,
                ),
                ft.Text(
                    text,
                    size=size,
                    weight=ft.FontWeight.W_700,
                    color=UI_TITLE_COLOR,
                ),
            ],
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

    def _testo_coords_casa(self) -> str:
        return f"Casa: {self.state.casa_lat:.5f}, {self.state.casa_lon:.5f}"

    def aggiorna_label_casa(self) -> None:
        self.chip_casa.content = ft.Row(
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Icon(ft.Icons.HOME_OUTLINED, size=16, color=UI_ACCENT),
                ft.Text(
                    self._testo_coords_casa(),
                    size=12,
                    color=UI_TITLE_COLOR,
                    weight=ft.FontWeight.W_500,
                ),
            ],
        )

    def _click_imposta_casa(self, _e=None) -> None:
        if self.on_imposta_casa is not None:
            self.on_imposta_casa()

    def _click_ripristina_casa(self, _e=None) -> None:
        if self.on_ripristina_casa is not None:
            self.on_ripristina_casa()
        else:
            self.state.ripristina_casa_default()
            self.aggiorna_label_casa()

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
        """Ripristina gradi/distretti tutti, testo vuoto, casa visibile, ordina on."""
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
        self.state.set_profilo_routing(ROUTING_PROFILO_DEFAULT, notify=False)
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
        self.aggiorna_label_casa()

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
                    ft.Container(
                        bgcolor=UI_SURFACE,
                        border=ft.Border.all(1, UI_BORDER),
                        border_radius=10,
                        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                        content=ft.ListTile(
                            dense=True,
                            title=ft.Text(
                                str(row["Nome"]),
                                size=13,
                                weight=ft.FontWeight.W_500,
                                color=UI_TITLE_COLOR,
                                max_lines=2,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                            subtitle=ft.Text(
                                f"Distretto {distretto} · {row.get('Grado', '')}{dist_txt}",
                                size=11,
                                color=UI_META_COLOR,
                            ),
                            leading=ft.Container(
                                width=34,
                                height=34,
                                alignment=ft.Alignment.CENTER,
                                bgcolor=UI_ACCENT_SOFT,
                                border_radius=17,
                                content=ft.Icon(ft.Icons.SCHOOL, color=colore, size=18),
                            ),
                            on_click=lambda e, s=data: self._click_risultato(s),
                        ),
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
    on_imposta_casa: Callable[[], None] | None = None,
    on_ripristina_casa: Callable[[], None] | None = None,
    on_profilo_cambiato: Callable[[str], None] | None = None,
) -> SidebarController:
    # on_profilo_cambiato ignorato (profilo solo nel dialog); tenuto per compatibilità call-site
    _ = on_profilo_cambiato
    return SidebarController(
        state,
        on_seleziona_scuola=on_seleziona_scuola,
        colore_distretto=colore_distretto,
        on_conteggio=on_conteggio,
        on_imposta_casa=on_imposta_casa,
        on_ripristina_casa=on_ripristina_casa,
    )
