"""Caricamento e filtro del dataset scuole."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd

FILE_CSV = Path(__file__).resolve().parent.parent / "data" / "scuole_coordinate.csv"

_df_cache: pd.DataFrame | None = None


def carica_scuole(*, force_reload: bool = False) -> pd.DataFrame:
    """
    Carica le scuole con coordinate valide (cache in memoria).
    Le righe senza Latitudine/Longitudine vengono escluse.
    """
    global _df_cache

    if _df_cache is not None and not force_reload:
        return _df_cache.copy()

    df = pd.read_csv(FILE_CSV)
    df = df.dropna(subset=["Latitudine", "Longitudine"]).copy()
    df["Distretto"] = df["Distretto"].astype(int)
    _df_cache = df
    return _df_cache.copy()


def statistiche_dataset() -> dict[str, int | str]:
    """Conteggi sul CSV grezzo (inclusi record senza coordinate)."""
    df = pd.read_csv(FILE_CSV)
    totale = len(df)
    con_coord = int(df.dropna(subset=["Latitudine", "Longitudine"]).shape[0])
    senza_coord = totale - con_coord
    mtime = ""
    try:
        from datetime import datetime

        mtime = datetime.fromtimestamp(FILE_CSV.stat().st_mtime).strftime("%Y-%m-%d")
    except OSError:
        pass
    return {
        "totale": totale,
        "con_coordinate": con_coord,
        "senza_coordinate": senza_coord,
        "aggiornato": mtime,
        "file": FILE_CSV.name,
    }


def elenco_distretti() -> list[int]:
    df = carica_scuole()
    return sorted(df["Distretto"].unique().tolist())


def conta_per_distretto() -> dict[int, int]:
    df = carica_scuole()
    counts = df.groupby("Distretto").size()
    return {int(k): int(v) for k, v in counts.items()}


def elenco_gradi() -> list[str]:
    df = carica_scuole()
    return sorted(df["Grado"].unique().tolist())


def conta_per_grado() -> dict[str, int]:
    df = carica_scuole()
    counts = df.groupby("Grado").size()
    return {str(k): int(v) for k, v in counts.items()}


def filtra_scuole(
    gradi: Iterable[str] | None = None,
    distretti: Iterable[int] | None = None,
    testo: str | None = None,
) -> pd.DataFrame:
    """
    Filtra le scuole con logica AND:
    Grado ∩ Distretto ∩ (Nome | Indirizzo | Codice).
    Liste vuote → risultato vuoto per quel criterio.
    """
    df = carica_scuole()

    gradi_list = list(gradi) if gradi is not None else None
    distretti_list = list(distretti) if distretti is not None else None

    if gradi_list is not None:
        if not gradi_list:
            return df.iloc[0:0].copy()
        df = df[df["Grado"].isin(gradi_list)]

    if distretti_list is not None:
        if not distretti_list:
            return df.iloc[0:0].copy()
        distretti_int = [int(d) for d in distretti_list]
        df = df[df["Distretto"].isin(distretti_int)]

    if testo:
        q = str(testo).strip().lower()
        if q:
            mask = (
                df["Nome"].astype(str).str.lower().str.contains(q, na=False)
                | df["Indirizzo"].astype(str).str.lower().str.contains(q, na=False)
                | df["Codice"].astype(str).str.lower().str.contains(q, na=False)
            )
            df = df[mask]

    return df.copy()


# Retrocompatibilità
def filtra_per_grado(gradi_selezionati):
    return filtra_scuole(gradi=gradi_selezionati)
