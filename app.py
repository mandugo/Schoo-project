"""Scuole Torino Explorer — entry point."""

import flet as ft

from components.sidebar import crea_sidebar, format_conteggio_scuole
from utils.config import (
    LABEL_AZZERA_FILTRI,
    SIDEBAR_WIDTH,
    UI_HEADER_BG,
    VIEWPORT_NARROW_PX,
)
from utils.database import elenco_distretti, filtra_scuole
from utils.state import FilterState
from views.map_view import crea_mappa, mappa_colori_distretto


def main(page: ft.Page):
    page.title = "Scuole Torino Explorer"
    page.padding = 0

    # Dimensioni utili in desktop; innocue / ignorate in web
    try:
        page.window.width = 1500
        page.window.height = 900
    except Exception:
        pass

    state = FilterState(mostra_casa=True)
    mappa = crea_mappa(page)

    # Palette stabile su tutti i distretti del dataset
    mappa.colore_distretto = mappa_colori_distretto(elenco_distretti())

    header_contatore = ft.Text(
        format_conteggio_scuole(0),
        size=14,
        color=ft.Colors.WHITE,
    )

    def aggiorna_conteggio(n: int) -> None:
        header_contatore.value = format_conteggio_scuole(n)

    def on_seleziona_scuola(scuola: dict) -> None:
        page.run_task(mappa.seleziona_scuola, scuola)

    sidebar = crea_sidebar(
        state,
        on_seleziona_scuola=on_seleziona_scuola,
        colore_distretto=mappa.colore_per_distretto,
        on_conteggio=aggiorna_conteggio,
    )

    def applica_filtri():
        df = filtra_scuole(
            gradi=state.gradi,
            distretti=state.distretti,
            testo=state.testo,
        )
        mappa.aggiorna_marker(df, mostra_casa=state.mostra_casa)
        sidebar.aggiorna_risultati(df)
        page.update()

    state.set_on_change(applica_filtri)

    btn_menu = ft.IconButton(
        icon=ft.Icons.MENU,
        icon_color=ft.Colors.WHITE,
        tooltip="Filtri",
        visible=False,
        on_click=lambda _e: page.show_drawer(),
    )

    btn_azzera_header = ft.IconButton(
        icon=ft.Icons.FILTER_ALT_OFF,
        icon_color=ft.Colors.WHITE,
        tooltip=LABEL_AZZERA_FILTRI,
        on_click=lambda _e: sidebar.azzera_filtri(),
    )

    header = ft.Container(
        height=56,
        bgcolor=UI_HEADER_BG,
        padding=ft.Padding.symmetric(horizontal=12, vertical=8),
        content=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Row(
                    spacing=4,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        btn_menu,
                        ft.Text(
                            "Scuole Torino Explorer",
                            size=20,
                            color=ft.Colors.WHITE,
                            weight=ft.FontWeight.BOLD,
                        ),
                    ],
                ),
                ft.Row(
                    spacing=4,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[header_contatore, btn_azzera_header],
                ),
            ],
        ),
    )

    sidebar_slot = sidebar.root
    divider = ft.VerticalDivider(width=1)

    layout = ft.Row(
        expand=True,
        spacing=0,
        controls=[
            sidebar_slot,
            divider,
            mappa.root,
        ],
    )

    page.add(
        ft.Column(
            expand=True,
            spacing=0,
            controls=[header, layout],
        )
    )

    # Drawer riusa lo stesso body della sidebar (un solo controller)
    drawer_host = ft.Container(
        width=SIDEBAR_WIDTH,
        padding=8,
        bgcolor=sidebar.root.bgcolor,
        content=None,
    )
    page.drawer = ft.NavigationDrawer(
        controls=[drawer_host],
    )

    narrow_mode = {"active": False}

    def _enter_narrow() -> None:
        if narrow_mode["active"]:
            return
        narrow_mode["active"] = True
        # Sposta il body nel drawer; nasconde la sidebar fissa
        sidebar.root.content = None
        sidebar.root.visible = False
        sidebar.root.width = 0
        divider.visible = False
        drawer_host.content = sidebar.body
        btn_menu.visible = True

    def _exit_narrow() -> None:
        if not narrow_mode["active"]:
            return
        narrow_mode["active"] = False
        try:
            page.close_drawer()
        except Exception:
            pass
        drawer_host.content = None
        sidebar.root.content = sidebar.body
        sidebar.root.visible = True
        sidebar.root.width = SIDEBAR_WIDTH
        divider.visible = True
        btn_menu.visible = False

    def applica_layout(width: float | None) -> None:
        if width is None or width <= 0:
            return
        if width < VIEWPORT_NARROW_PX:
            _enter_narrow()
        else:
            _exit_narrow()

    def on_resize(e: ft.PageResizeEvent):
        applica_layout(e.width)
        page.update()

    page.on_resize = on_resize
    # Layout iniziale (web/desktop)
    applica_layout(page.width)

    # Primo render con filtri di default (tutti)
    applica_filtri()


ft.run(main)
