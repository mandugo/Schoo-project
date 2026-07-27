import flet as ft
import pandas as pd
import math

from flet_map import (
    Map,
    Marker,
    MarkerLayer,
    TileLayer,
    MapLatitudeLongitude
)


def crea_mappa(page):

    df = pd.read_csv("data/scuole_coordinate.csv")

    df = df.dropna(
        subset=[
            "Latitudine",
            "Longitudine"
        ]
    )


    colori = [
        ft.Colors.RED,
        ft.Colors.BLUE,
        ft.Colors.GREEN,
        ft.Colors.ORANGE,
        ft.Colors.PURPLE,
        ft.Colors.TEAL,
        ft.Colors.PINK,
        ft.Colors.BROWN,
    ]


    distretti = sorted(
        df["Distretto"]
        .astype(int)
        .unique()
    )


    colore_distretto = {}

    for i, d in enumerate(distretti):
        colore_distretto[d] = colori[i % len(colori)]


    markers = []


    for _, scuola in df.iterrows():

        distretto = int(scuola["Distretto"])

        marker = Marker(

            coordinates=MapLatitudeLongitude(
                float(scuola["Latitudine"]),
                float(scuola["Longitudine"])
            ),

            content=ft.Icon(
                ft.Icons.SCHOOL,
                color=colore_distretto[distretto],
                size=22
            ),

            data=scuola.to_dict()
        )

        markers.append(marker)



    casa = Marker(

        coordinates=MapLatitudeLongitude(
            45.0918,
            7.6357
        ),

        content=ft.Icon(
            ft.Icons.HOME,
            color=ft.Colors.BLACK,
            size=30
        )
    )


    markers.append(casa)


    livello_marker = MarkerLayer(
        markers=markers
    )


    livello_mappa = TileLayer(
        url_template="https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        user_agent_package_name="ScuoleTorinoExplorer"
    )


    def distanza(lat1, lon1, lat2, lon2):

        return math.sqrt(
            (lat1-lat2)**2 +
            (lon1-lon2)**2
        )


    def mostra_scuola(scuola):

        dialog = ft.AlertDialog(

            title=ft.Text("🏫 Informazioni scuola"),

            content=ft.Column(
                [
                    ft.Text(f"Nome: {scuola['Nome']}"),
                    ft.Text(f"Indirizzo: {scuola['Indirizzo']}"),
                    ft.Text(f"Distretto: {scuola['Distretto']}"),
                    ft.Text(f"Codice: {scuola['Codice']}"),
                ],
                tight=True
            ),

            actions=[
                ft.TextButton(
                    "Chiudi",
                    on_click=lambda e: chiudi_dialog(dialog)
                )
            ]
        )

        page.overlay.append(dialog)
        dialog.open = True
        page.update()



    def chiudi_dialog(dialog):

        dialog.open = False
        page.update()



    def evento_mappa(e):

        if e.coordinates is None:
            return


        lat = e.coordinates.latitude
        lon = e.coordinates.longitude


        migliore = None
        distanza_minima = 999


        for _, scuola in df.iterrows():

            d = distanza(
                lat,
                lon,
                float(scuola["Latitudine"]),
                float(scuola["Longitudine"])
            )

            if d < distanza_minima:
                distanza_minima = d
                migliore = scuola


        if migliore is not None and distanza_minima < 0.002:

            mostra_scuola(migliore)



    mappa = Map(

        expand=True,

        initial_center=MapLatitudeLongitude(
            45.0703,
            7.6869
        ),

        initial_zoom=12,

        layers=[
            livello_mappa,
            livello_marker
        ],

        on_event=evento_mappa

    )


    return mappa