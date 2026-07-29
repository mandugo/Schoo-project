"""Utility geografiche (Haversine, senza dipendenze esterne)."""

from __future__ import annotations

import math


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
