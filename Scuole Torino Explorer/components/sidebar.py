import flet as ft
import pandas as pd


def crea_sidebar():

    df = pd.read_csv("data/scuole_coordinate.csv")

    df = df.dropna(subset=["Distretto"])

    distretti = (
        df["Distretto"]
        .astype(int)
        .sort_values()
        .unique()
    )

    lista = ft.Column(
        scroll=ft.ScrollMode.AUTO,
        expand=True
    )

    lista.controls.append(
        ft.Text(
            "📍 Distretti",
            size=22,
            weight=ft.FontWeight.BOLD
        )
    )

    for d in distretti:

        numero = len(
            df[df["Distretto"].astype(int) == d]
        )

        lista.controls.append(
            ft.Text(
                f"Distretto {d:02d}   ({numero} scuole)",
                size=16
            )
        )


    return ft.Container(
        width=320,
        bgcolor=ft.Colors.GREY_100,
        padding=15,
        content=ft.Column(
            expand=True,
            controls=[
                ft.Text(
                    "🔎 Ricerca scuola",
                    size=18,
                    weight=ft.FontWeight.BOLD
                ),

                ft.TextField(
                    hint_text="Cerca..."
                ),

                ft.Divider(),

                lista
            ]
        )
    )