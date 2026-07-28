import pandas as pd


FILE_CSV = "data/scuole_coordinate.csv"


def carica_scuole():
    """
    Carica tutte le scuole dal CSV.
    """

    df = pd.read_csv(FILE_CSV)

    df = df.dropna(
        subset=[
            "Latitudine",
            "Longitudine"
        ]
    )

    return df


def elenco_distretti():
    """
    Restituisce tutti i distretti ordinati.
    """

    df = carica_scuole()

    return (
        df["Distretto"]
        .astype(int)
        .sort_values()
        .unique()
    )


def conta_per_distretto():
    """
    Restituisce il numero di scuole per distretto.
    """

    df = carica_scuole()

    risultato = {}

    for d in elenco_distretti():

        risultato[d] = len(
            df[
                df["Distretto"].astype(int) == d
            ]
        )

    return risultato


def elenco_gradi():
    """
    Restituisce i gradi presenti nel database.
    """

    df = carica_scuole()

    return sorted(
        df["Grado"].unique()
    )


def conta_per_grado():
    """
    Restituisce il numero di scuole per grado.
    """

    df = carica_scuole()

    risultato = {}

    for grado in elenco_gradi():

        risultato[grado] = len(
            df[df["Grado"] == grado]
        )

    return risultato
def filtra_per_grado(gradi_selezionati):
    """
    Restituisce solo le scuole appartenenti
    ai gradi selezionati.
    """

    df = carica_scuole()

    if not gradi_selezionati:
        return df.iloc[0:0]

    return df[df["Grado"].isin(gradi_selezionati)]