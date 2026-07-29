"""Scuole Torino Explorer — entry point."""

import flet as ft

from components.sidebar import crea_sidebar
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

    def applica_filtri():
        df = filtra_scuole(
            gradi=state.gradi,
            distretti=state.distretti,
            testo=state.testo,
        )
        mappa.aggiorna_marker(df, mostra_casa=state.mostra_casa)
        sidebar.aggiorna_risultati(df)
        page.update()

    sidebar = crea_sidebar(
        state,
        on_seleziona_scuola=mappa.mostra_scuola,
        colore_distretto=mappa.colore_per_distretto,
    )

    state.set_on_change(applica_filtri)

    header = ft.Container(
        height=60,
        bgcolor=ft.Colors.BLUE_700,
        padding=15,
        content=ft.Text(
            "Scuole Torino Explorer",
            size=25,
            color=ft.Colors.WHITE,
            weight=ft.FontWeight.BOLD,
        ),
    )

    layout = ft.Row(
        expand=True,
        spacing=0,
        controls=[
            sidebar.root,
            ft.VerticalDivider(width=1),
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

    # Primo render con filtri di default (tutti)
    applica_filtri()


ft.run(main)
