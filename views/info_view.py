"""Pagina Guida / Info (route /info)."""

from __future__ import annotations

from typing import Callable

import flet as ft

from utils.config import (
    DATI_FONTE_LABEL,
    LABEL_TORNA_MAPPA,
    MSG_ATTRIBUTION_OSM,
    UI_ACCENT,
    UI_ACCENT_SOFT,
    UI_BORDER,
    UI_META_COLOR,
    UI_SIDEBAR_BG,
    UI_SURFACE,
    UI_TITLE_COLOR,
)


def _sezione(titolo: str, *paragrafi: str) -> ft.Control:
    return ft.Container(
        padding=ft.Padding.all(16),
        bgcolor=UI_SURFACE,
        border=ft.Border.all(1, UI_BORDER),
        border_radius=12,
        content=ft.Column(
            tight=True,
            spacing=8,
            controls=[
                ft.Row(
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
                            titolo,
                            size=16,
                            weight=ft.FontWeight.W_700,
                            color=UI_TITLE_COLOR,
                        ),
                    ],
                ),
                *[
                    ft.Text(p, size=13, color=UI_META_COLOR)
                    for p in paragrafi
                ],
            ],
        ),
    )


def crea_info_view(*, on_torna: Callable[[], None] | None = None) -> ft.Container:
    """Vista scrollabile con manuale d'uso e info generali."""

    intro = ft.Container(
        padding=ft.Padding.all(16),
        bgcolor=UI_ACCENT_SOFT,
        border=ft.Border.all(1, UI_BORDER),
        border_radius=12,
        content=ft.Column(
            tight=True,
            spacing=6,
            controls=[
                ft.Text(
                    "Scuole Torino Explorer",
                    size=20,
                    weight=ft.FontWeight.W_700,
                    color=UI_TITLE_COLOR,
                ),
                ft.Text(
                    "Esplora le scuole di Torino su mappa OpenStreetMap: filtra per grado "
                    "e distretto, cerca per nome o indirizzo, misura la distanza da casa "
                    "e visualizza un percorso.",
                    size=14,
                    color=UI_TITLE_COLOR,
                ),
            ],
        ),
    )

    sezioni = [
        _sezione(
            "Filtri e ricerca",
            "Usa Grado e Distretti (Tutti / Nessuno) per restringere i risultati. "
            "I filtri si combinano in AND: restano solo le scuole che soddisfano tutti i criteri.",
            "La ricerca testuale filtra su nome, indirizzo e codice scuola.",
            "Azzera filtri ripristina gradi e distretti, svuota la ricerca e riattiva "
            "«Mostra casa» e l’ordinamento per distanza.",
        ),
        _sezione(
            "Risultati e mappa",
            "La mini-lista a sinistra mostra fino a 12 risultati; clicca una scuola "
            "per centrare la mappa e aprire i dettagli.",
            "Aprendo una scuola e mostrando il percorso, i marker dello stesso "
            "distretto restano in evidenza e gli altri si attenuano; nascondendo "
            "il percorso tutto torna normale.",
            "Puoi anche toccare un marker sulla mappa (o l’area vicino al punto). "
            "Ogni marker mostra il numero di distretto e un colore univoco "
            "(vedi legenda in Distretti).",
        ),
        _sezione(
            "Casa e distanze",
            "Il marker casa è il punto di riferimento per le distanze in linea d’aria.",
            "Cambia casa: attiva la modalità e clicca sulla mappa. "
            "Predefinita ripristina le coordinate di default.",
            "Con «Ordina per distanza da casa» i risultati e i marker filtrati "
            "sono ordinati dal più vicino.",
        ),
        _sezione(
            "Percorso e indicazioni",
            "Nel dialog scuola scegli la modalità (a piedi, bici, auto) e premi "
            "«Mostra percorso» per tracciare il percorso sulla mappa (OSRM).",
            "Sotto la mappa resta un riquadro con distanza e tempo finché il percorso "
            "è attivo; puoi chiuderlo da lì o con «Nascondi percorso» nell’header.",
            "«Indicazioni» apre Google Maps con partenza da casa e destinazione la scuola.",
            "Il percorso non parte al solo click: va richiesto esplicitamente.",
        ),
        _sezione(
            "Condivisione",
            "Dal menu ⋮, «Copia link filtri» salva negli appunti un URL con lo stato "
            "attuale (filtri, casa, ordinamento, modalità). Aprendo il link si "
            "ripristinano le stesse impostazioni.",
        ),
        _sezione(
            "Dati e mappe",
            f"{DATI_FONTE_LABEL}: scuole con coordinate valide; quelle senza Lat/Lon "
            "sono escluse dalla mappa.",
            f"Tessere cartografiche: {MSG_ATTRIBUTION_OSM}. "
            "I percorsi usano il servizio pubblico OSRM (rate limit; in produzione "
            "andrebbe self-host o un’altra API).",
        ),
    ]

    corpo = ft.Column(
        scroll=ft.ScrollMode.AUTO,
        expand=True,
        spacing=12,
        controls=[
            intro,
            *sezioni,
            ft.Container(height=8),
            ft.TextButton(
                LABEL_TORNA_MAPPA,
                icon=ft.Icons.ARROW_BACK,
                style=ft.ButtonStyle(color=UI_ACCENT),
                on_click=lambda _e: on_torna() if on_torna else None,
            ),
            ft.Container(height=24),
        ],
    )

    return ft.Container(
        expand=True,
        visible=False,
        bgcolor=UI_SIDEBAR_BG,
        padding=ft.Padding.symmetric(horizontal=24, vertical=16),
        content=ft.Row(
            expand=True,
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.START,
            controls=[
                ft.Container(
                    width=720,
                    expand=True,
                    content=corpo,
                ),
            ],
        ),
    )
