from utils import state
import flet as ft

from utils.database import (
    elenco_distretti,
    conta_per_distretto,
    elenco_gradi,
    conta_per_grado
)

def aggiorna_gradi(e):

    print("EVENTO SCATENATO")

    grado = e.control.data

    if e.control.value:

        if grado not in state.gradi_selezionati:
            state.gradi_selezionati.append(grado)

    else:

        if grado in state.gradi_selezionati:
            state.gradi_selezionati.remove(grado)

    print(state.gradi_selezionati)
def crea_sidebar():

    distretti = elenco_distretti()
    conteggio_distretti = conta_per_distretto()

    gradi = elenco_gradi()
    conteggio_gradi = conta_per_grado()


    lista = ft.Column(
        scroll=ft.ScrollMode.AUTO,
        expand=True
    )


    # ==========================
    # GRADI SCOLASTICI
    # ==========================

    lista.controls.append(
        ft.Text(
            "🎓 Grado scolastico",
            size=22,
            weight=ft.FontWeight.BOLD
        )
    )


    for grado in gradi:

        lista.controls.append(

            ft.Checkbox(
    label=f"{grado} ({conteggio_gradi[grado]})",
    value=True,
    data=grado,
    on_change=lambda e: aggiorna_gradi(e)
)

        )


    lista.controls.append(
        ft.Divider()
    )


    # ==========================
    # DISTRETTI
    # ==========================

    lista.controls.append(
        ft.Text(
            "📍 Distretti",
            size=22,
            weight=ft.FontWeight.BOLD
        )
    )


    for d in distretti:

        lista.controls.append(

            ft.Text(
                f"Distretto {d:02d} ({conteggio_distretti[d]} scuole)",
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