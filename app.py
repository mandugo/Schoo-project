import flet as ft

from components.sidebar import crea_sidebar
from views.map_view import crea_mappa


def main(page: ft.Page):

    page.title = "Scuole Torino Explorer"

    page.window.width = 1500
    page.window.height = 900

    page.padding = 0


    header = ft.Container(
        height=60,
        bgcolor=ft.Colors.BLUE_700,
        padding=15,
        content=ft.Text(
            "🏫 Scuole Torino Explorer",
            size=25,
            color=ft.Colors.WHITE,
            weight=ft.FontWeight.BOLD
        )
    )


    layout = ft.Row(
        expand=True,
        spacing=0,
        controls=[
            crea_sidebar(),

            ft.VerticalDivider(width=1),

            crea_mappa(page)
        ]
    )


    page.add(
        ft.Column(
            expand=True,
            spacing=0,
            controls=[
                header,
                layout
            ]
        )
    )


ft.app(target=main)