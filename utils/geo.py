"""Utility geografiche (Haversine, senza dipendenze esterne)."""

from __future__ import annotations

import math

import pandas as pd


def distanza_metri(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distanza geodesica approssimata in metri (Haversine)."""
    r = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def format_distanza(metri: float) -> str:
    """Formato leggibile: metri sotto 1 km, altrimenti km con 1 decimale."""
    if metri < 1000:
        return f"{int(round(metri))} m"
    return f"{metri / 1000:.1f} km"


def con_distanza_da(
    df: pd.DataFrame,
    lat: float,
    lon: float,
    *,
    colonna: str = "Distanza_m",
) -> pd.DataFrame:
    """Aggiunge colonna distanza (metri) da un punto di riferimento."""
    out = df.copy()
    if len(out) == 0:
        out[colonna] = pd.Series(dtype=float)
        return out
    out[colonna] = [
        distanza_metri(lat, lon, float(r["Latitudine"]), float(r["Longitudine"]))
        for _, r in out.iterrows()
    ]
    return out
