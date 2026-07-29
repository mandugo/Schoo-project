"""Serializzazione filtri ↔ query string (share web, senza persistenza server)."""

from __future__ import annotations

from urllib.parse import parse_qs, urlencode

from utils.config import CASA_LAT, CASA_LON
from utils.state import FilterState


def encode_filtri(
    state: FilterState,
    *,
    tutti_gradi: list[str],
    tutti_distretti: list[int],
    scuola_codice: str | None = None,
) -> str:
    """
    Codifica lo stato filtri in query string (senza '?').
    Omesso = "tutti" per gradi/distretti (URL più corta).
    """
    params: dict[str, str] = {}

    if state.gradi and set(state.gradi) != set(tutti_gradi):
        params["g"] = ",".join(state.gradi)
    elif not state.gradi:
        params["g"] = ""

    if state.distretti and set(state.distretti) != set(tutti_distretti):
        params["d"] = ",".join(str(d) for d in sorted(state.distretti))
    elif not state.distretti:
        params["d"] = ""

    if state.testo.strip():
        params["q"] = state.testo.strip()

    if not state.mostra_casa:
        params["casa"] = "0"

    if not state.ordina_per_distanza:
        params["ord"] = "0"

    if state.profilo_routing and state.profilo_routing != "foot":
        params["modo"] = state.profilo_routing

    if (
        abs(state.casa_lat - CASA_LAT) > 1e-5
        or abs(state.casa_lon - CASA_LON) > 1e-5
    ):
        params["home"] = f"{state.casa_lat:.5f},{state.casa_lon:.5f}"

    if scuola_codice:
        params["scuola"] = scuola_codice

    return urlencode(params)


def decode_filtri(
    query: str | dict,
    *,
    tutti_gradi: list[str],
    tutti_distretti: list[int],
) -> tuple[FilterState, str | None]:
    """
    Decodifica query → FilterState + eventuale codice scuola.
    Accetta stringa 'a=1&b=2' o dict già parsato.
    """
    if isinstance(query, str):
        raw = parse_qs(query.lstrip("?"), keep_blank_values=True)
        data = {k: (v[0] if v else "") for k, v in raw.items()}
    else:
        data = {k: ("" if v is None else str(v)) for k, v in query.items()}

    if "g" not in data:
        gradi = list(tutti_gradi)
    elif data["g"].strip() == "":
        gradi = []
    else:
        richiesti = [x.strip() for x in data["g"].split(",") if x.strip()]
        gradi = [g for g in richiesti if g in tutti_gradi]

    if "d" not in data:
        distretti = list(tutti_distretti)
    elif data["d"].strip() == "":
        distretti = []
    else:
        distretti = []
        for part in data["d"].split(","):
            part = part.strip()
            if not part:
                continue
            try:
                d = int(part)
            except ValueError:
                continue
            if d in tutti_distretti:
                distretti.append(d)

    testo = data.get("q", "") or ""
    mostra_casa = data.get("casa", "1") != "0"
    ordina = data.get("ord", "1") != "0"
    profilo = data.get("modo", "foot") or "foot"
    if profilo not in ("foot", "bike", "car"):
        profilo = "foot"
    scuola = (data.get("scuola") or "").strip() or None

    casa_lat, casa_lon = CASA_LAT, CASA_LON
    home = (data.get("home") or "").strip()
    if home and "," in home:
        try:
            parts = home.split(",", 1)
            casa_lat = float(parts[0])
            casa_lon = float(parts[1])
        except ValueError:
            pass

    state = FilterState(
        gradi=gradi,
        distretti=distretti,
        testo=testo,
        mostra_casa=mostra_casa,
        ordina_per_distanza=ordina,
        profilo_routing=profilo,
        casa_lat=casa_lat,
        casa_lon=casa_lon,
    )
    return state, scuola
