"""Serializzazione filtri ↔ query string (share web, senza persistenza server)."""

from __future__ import annotations

from urllib.parse import parse_qs, urlencode

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
    scuola = (data.get("scuola") or "").strip() or None

    state = FilterState(
        gradi=gradi,
        distretti=distretti,
        testo=testo,
        mostra_casa=mostra_casa,
        ordina_per_distanza=ordina,
    )
    return state, scuola
