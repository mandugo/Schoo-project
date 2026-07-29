"""Routing stradale via OSRM (on-demand, con cache in memoria)."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Literal

from utils.config import (
    CASA_LAT,
    CASA_LON,
    OSRM_BASE_URL,
    OSRM_TIMEOUT_SEC,
    ROUTING_PROFILO_DEFAULT,
)
from utils.geo import distanza_metri

ProfiloRouting = Literal["foot", "bike", "car"]

_CACHE: dict[tuple, "RouteResult"] = {}


@dataclass(frozen=True)
class RouteResult:
    """Percorso guidato casa → destinazione."""

    distanza_m: float
    durata_s: float
    coordinate: list[tuple[float, float]]  # (lat, lon)
    profilo: str
    sorgente: str  # "osrm" | "haversine"
    ok: bool = True
    errore: str | None = None
    durata_stimata: bool = False


# Velocità medie per stimare la durata quando OSRM pubblico non distingue i profili
_SPEED_MPS = {
    "foot": 1.39,  # ~5 km/h
    "bike": 4.17,  # ~15 km/h
}


def format_durata(secondi: float) -> str:
    s = max(0, int(round(secondi)))
    if s < 60:
        return f"{s} s"
    minuti = s // 60
    if minuti < 60:
        return f"{minuti} min"
    ore, minuti = divmod(minuti, 60)
    if minuti == 0:
        return f"{ore} h"
    return f"{ore} h {minuti} min"


def _cache_key(
    profilo: str,
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> tuple:
    return (
        profilo,
        round(lat1, 5),
        round(lon1, 5),
        round(lat2, 5),
        round(lon2, 5),
    )


def _fallback_haversine(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
    profilo: str,
    errore: str | None = None,
) -> RouteResult:
    d = distanza_metri(lat1, lon1, lat2, lon2)
    # Stima grezza durata se OSRM non risponde (piedi ~5 km/h, bici 15, auto 30 in città)
    velocita = {"foot": 1.4, "bike": 4.2, "car": 8.3}.get(profilo, 1.4)  # m/s
    return RouteResult(
        distanza_m=d,
        durata_s=d / velocita if velocita else d,
        coordinate=[(lat1, lon1), (lat2, lon2)],
        profilo=profilo,
        sorgente="haversine",
        ok=False,
        errore=errore,
        durata_stimata=True,
    )


def calcola_percorso(
    lat_dest: float,
    lon_dest: float,
    *,
    lat_orig: float = CASA_LAT,
    lon_orig: float = CASA_LON,
    profilo: str = ROUTING_PROFILO_DEFAULT,
) -> RouteResult:
    """
    Calcola percorso OSRM (sincrono). Usa cache; in caso di errore torna Haversine.
    Coordinate OSRM: lon,lat — in uscita: (lat, lon) per flet-map.
    """
    profilo = profilo if profilo in ("foot", "bike", "car") else ROUTING_PROFILO_DEFAULT
    key = _cache_key(profilo, lat_orig, lon_orig, lat_dest, lon_dest)
    if key in _CACHE:
        return _CACHE[key]

    coords = f"{lon_orig},{lat_orig};{lon_dest},{lat_dest}"
    url = (
        f"{OSRM_BASE_URL.rstrip('/')}/route/v1/{profilo}/{coords}"
        f"?overview=full&geometries=geojson"
    )

    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "ScuoleTorinoExplorer/1.0"},
        )
        with urllib.request.urlopen(req, timeout=OSRM_TIMEOUT_SEC) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        result = _fallback_haversine(
            lat_orig, lon_orig, lat_dest, lon_dest, profilo, errore=str(exc)
        )
        return result

    if payload.get("code") != "Ok" or not payload.get("routes"):
        result = _fallback_haversine(
            lat_orig,
            lon_orig,
            lat_dest,
            lon_dest,
            profilo,
            errore=str(payload.get("message") or payload.get("code") or "no route"),
        )
        return result

    route = payload["routes"][0]
    geometry = route.get("geometry") or {}
    raw_coords = geometry.get("coordinates") or []
    # GeoJSON: [lon, lat] → (lat, lon)
    points = [(float(c[1]), float(c[0])) for c in raw_coords if len(c) >= 2]
    if len(points) < 2:
        points = [(lat_orig, lon_orig), (lat_dest, lon_dest)]

    distanza_m = float(route.get("distance") or 0.0)
    durata_api = float(route.get("duration") or 0.0)
    # Il demo OSRM pubblico spesso ignora il profilo: stima durata a piedi/bici
    durata_stimata = False
    if profilo in _SPEED_MPS and distanza_m > 0:
        durata_s = distanza_m / _SPEED_MPS[profilo]
        durata_stimata = True
    else:
        durata_s = durata_api

    result = RouteResult(
        distanza_m=distanza_m,
        durata_s=durata_s,
        coordinate=points,
        profilo=profilo,
        sorgente="osrm",
        ok=True,
        errore=None,
        durata_stimata=durata_stimata,
    )
    _CACHE[key] = result
    return result


def svuota_cache_routing() -> None:
    _CACHE.clear()
