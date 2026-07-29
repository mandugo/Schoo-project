"""Scuole Torino Explorer — entry point."""

from __future__ import annotations

import flet as ft

from components.sidebar import crea_sidebar, format_conteggio_scuole
from utils.config import (
    LABEL_AZZERA_FILTRI,
    LABEL_CONDIVIDI,
    LABEL_NASCONDI_PERCORSO,
    MSG_LINK_COPIATO,
    SIDEBAR_WIDTH,
    UI_ACCENT,
    UI_BORDER,
    UI_FONT_BOLD_URL,
    UI_FONT_FAMILY,
    UI_FONT_URL,
    UI_HEADER_BG,
    UI_HEADER_FG,
    UI_HEADER_MUTED,
    UI_SIDEBAR_BG,
    VIEWPORT_NARROW_PX,
)
from utils.database import elenco_distretti, elenco_gradi, filtra_scuole
from utils.geo import con_distanza_da
from utils.share import decode_filtri, encode_filtri
from utils.state import FilterState
from views.map_view import crea_mappa, mappa_colori_distretto


def main(page: ft.Page):
    page.title = "Scuole Torino Explorer"
    page.padding = 0
    page.bgcolor = UI_SIDEBAR_BG
    page.fonts = {
        UI_FONT_FAMILY: UI_FONT_URL,
        f"{UI_FONT_FAMILY} SemiBold": UI_FONT_BOLD_URL,
    }
    page.theme = ft.Theme(
        font_family=UI_FONT_FAMILY,
        color_scheme_seed=UI_ACCENT,
        use_material3=True,
        scaffold_bgcolor=UI_SIDEBAR_BG,
    )

    # Dimensioni utili in desktop; innocue / ignorate in web
    try:
        page.window.width = 1500
        page.window.height = 900
    except Exception:
        pass

    tutti_gradi = elenco_gradi()
    tutti_distretti = elenco_distretti()

    # Stato da URL (web) oppure default
    state = FilterState(mostra_casa=True, ordina_per_distanza=True)
    scuola_da_url: str | None = None
    syncing_url = {"skip": False}

    try:
        page.query()
        raw = page.query.to_dict
        if raw:
            decoded, scuola_da_url = decode_filtri(
                raw,
                tutti_gradi=tutti_gradi,
                tutti_distretti=tutti_distretti,
            )
            state = decoded
    except Exception:
        pass

    def on_seleziona_scuola(scuola: dict) -> None:
        page.run_task(mappa.seleziona_scuola, scuola)

    def set_profilo(profilo: str) -> None:
        state.set_profilo_routing(profilo, notify=False)
        mappa.nascondi_percorso()

    def on_percorso_visibile(visibile: bool) -> None:
        btn_nascondi_percorso.visible = visibile
        page.update()

    def on_casa_impostata(lat: float, lon: float) -> None:
        mappa.nascondi_percorso()
        state.set_casa(lat, lon)
        sidebar.aggiorna_label_casa()

    def on_imposta_casa() -> None:
        mappa.avvia_imposta_casa()

    def on_ripristina_casa() -> None:
        mappa.nascondi_percorso()
        state.ripristina_casa_default()
        sidebar.aggiorna_label_casa()

    mappa = crea_mappa(
        page,
        get_profilo=lambda: state.profilo_routing,
        set_profilo=set_profilo,
        get_casa=lambda: (state.casa_lat, state.casa_lon),
        on_casa_impostata=on_casa_impostata,
        on_percorso_visibile=on_percorso_visibile,
    )
    mappa.colore_distretto = mappa_colori_distretto(tutti_distretti)

    header_contatore = ft.Container(
        padding=ft.Padding.symmetric(horizontal=10, vertical=4),
        bgcolor=ft.Colors.with_opacity(0.18, UI_HEADER_FG),
        border_radius=20,
        content=ft.Text(
            format_conteggio_scuole(0),
            size=13,
            color=UI_HEADER_FG,
            weight=ft.FontWeight.W_500,
        ),
    )

    def aggiorna_conteggio(n: int) -> None:
        header_contatore.content = ft.Text(
            format_conteggio_scuole(n),
            size=13,
            color=UI_HEADER_FG,
            weight=ft.FontWeight.W_500,
        )

    btn_nascondi_percorso = ft.IconButton(
        icon=ft.Icons.LAYERS_CLEAR,
        icon_color=UI_HEADER_FG,
        tooltip=LABEL_NASCONDI_PERCORSO,
        visible=False,
        on_click=lambda _e: mappa.nascondi_percorso(),
    )

    sidebar = crea_sidebar(
        state,
        on_seleziona_scuola=on_seleziona_scuola,
        colore_distretto=mappa.colore_per_distretto,
        on_conteggio=aggiorna_conteggio,
        on_imposta_casa=on_imposta_casa,
        on_ripristina_casa=on_ripristina_casa,
    )
    sidebar.applica_stato_ui()

    def aggiorna_url() -> None:
        if syncing_url["skip"]:
            return
        qs = encode_filtri(
            state,
            tutti_gradi=tutti_gradi,
            tutti_distretti=tutti_distretti,
        )
        route = f"/?{qs}" if qs else "/"
        try:
            if page.route != route:
                # Ignora il prossimo on_route_change generato da push_route
                syncing_url["skip"] = True
                page.push_route(route)
        except Exception:
            syncing_url["skip"] = False

    def applica_filtri():
        df = filtra_scuole(
            gradi=state.gradi,
            distretti=state.distretti,
            testo=state.testo,
        )
        df = con_distanza_da(df, state.casa_lat, state.casa_lon)
        if state.ordina_per_distanza and len(df):
            df = df.sort_values("Distanza_m", ascending=True)
        mappa.aggiorna_marker(df, mostra_casa=state.mostra_casa)
        sidebar.aggiorna_risultati(df)
        aggiorna_url()
        page.update()

    state.set_on_change(applica_filtri)

    async def copia_link_filtri(_e=None):
        qs = encode_filtri(
            state,
            tutti_gradi=tutti_gradi,
            tutti_distretti=tutti_distretti,
        )
        base = (page.url or "").rstrip("/")
        if qs:
            link = f"{base}/?{qs}" if base else f"?{qs}"
        else:
            link = f"{base}/" if base else "/"
        await page.clipboard.set(link)
        page.show_dialog(ft.SnackBar(content=ft.Text(MSG_LINK_COPIATO)))

    btn_menu = ft.IconButton(
        icon=ft.Icons.MENU,
        icon_color=UI_HEADER_FG,
        tooltip="Filtri",
        visible=False,
        on_click=lambda _e: page.show_drawer(),
    )

    menu_header = ft.PopupMenuButton(
        icon=ft.Icons.MORE_VERT,
        icon_color=UI_HEADER_FG,
        tooltip="Menu",
        items=[
            ft.PopupMenuItem(
                content=LABEL_CONDIVIDI,
                icon=ft.Icons.LINK,
                on_click=copia_link_filtri,
            ),
            ft.PopupMenuItem(
                content=LABEL_AZZERA_FILTRI,
                icon=ft.Icons.FILTER_ALT_OFF,
                on_click=lambda _e: sidebar.azzera_filtri(),
            ),
        ],
    )

    header = ft.Container(
        height=58,
        bgcolor=UI_HEADER_BG,
        padding=ft.Padding.symmetric(horizontal=14, vertical=8),
        shadow=ft.BoxShadow(
            blur_radius=12,
            color=ft.Colors.with_opacity(0.25, ft.Colors.BLACK),
            offset=ft.Offset(0, 2),
        ),
        content=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Row(
                    spacing=6,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        btn_menu,
                        ft.Column(
                            spacing=0,
                            tight=True,
                            controls=[
                                ft.Text(
                                    "Scuole Torino",
                                    size=18,
                                    color=UI_HEADER_FG,
                                    weight=ft.FontWeight.W_700,
                                    font_family=f"{UI_FONT_FAMILY} SemiBold",
                                ),
                                ft.Text(
                                    "Explorer",
                                    size=11,
                                    color=UI_HEADER_MUTED,
                                    weight=ft.FontWeight.W_500,
                                ),
                            ],
                        ),
                    ],
                ),
                ft.Row(
                    spacing=6,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        header_contatore,
                        btn_nascondi_percorso,
                        menu_header,
                    ],
                ),
            ],
        ),
    )

    sidebar_slot = sidebar.root
    divider = ft.VerticalDivider(width=1, color=UI_BORDER)

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

    def on_route_change(_e=None):
        if syncing_url["skip"]:
            syncing_url["skip"] = False
            return
        try:
            page.query()
            raw = page.query.to_dict
        except Exception:
            return
        decoded, scuola_codice = decode_filtri(
            raw,
            tutti_gradi=tutti_gradi,
            tutti_distretti=tutti_distretti,
        )
        state.gradi = decoded.gradi
        state.distretti = decoded.distretti
        state.testo = decoded.testo
        state.mostra_casa = decoded.mostra_casa
        state.ordina_per_distanza = decoded.ordina_per_distanza
        state.profilo_routing = decoded.profilo_routing
        state.casa_lat = decoded.casa_lat
        state.casa_lon = decoded.casa_lon
        sidebar.applica_stato_ui()
        # Evita riscrittura URL identica durante questo ciclo
        syncing_url["skip"] = True
        try:
            df = filtra_scuole(
                gradi=state.gradi,
                distretti=state.distretti,
                testo=state.testo,
            )
            df = con_distanza_da(df, state.casa_lat, state.casa_lon)
            if state.ordina_per_distanza and len(df):
                df = df.sort_values("Distanza_m", ascending=True)
            mappa.aggiorna_marker(df, mostra_casa=state.mostra_casa)
            sidebar.aggiorna_risultati(df)
            page.update()
        finally:
            syncing_url["skip"] = False
        if scuola_codice:
            _apri_scuola_codice(scuola_codice)

    def _apri_scuola_codice(codice: str) -> None:
        df = filtra_scuole(
            gradi=state.gradi,
            distretti=state.distretti,
            testo=state.testo,
        )
        match = df[df["Codice"].astype(str) == str(codice)]
        if len(match) == 0:
            return
        row = match.iloc[0].to_dict()
        df_dist = con_distanza_da(match, state.casa_lat, state.casa_lon)
        row["Distanza_m"] = float(df_dist.iloc[0]["Distanza_m"])
        page.run_task(mappa.seleziona_scuola, row)

    page.on_resize = on_resize
    page.on_route_change = on_route_change
    applica_layout(page.width)

    # Primo render
    applica_filtri()

    if scuola_da_url:
        _apri_scuola_codice(scuola_da_url)


ft.run(main)
