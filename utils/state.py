"""Stato filtri dell'explorer (sessione corrente, senza persistenza)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from utils.config import CASA_LAT, CASA_LON


OnChange = Callable[[], None]


@dataclass
class FilterState:
    gradi: list[str] = field(default_factory=list)
    distretti: list[int] = field(default_factory=list)
    testo: str = ""
    mostra_casa: bool = True
    ordina_per_distanza: bool = True
    profilo_routing: str = "foot"
    casa_lat: float = CASA_LAT
    casa_lon: float = CASA_LON
    _on_change: OnChange | None = field(default=None, repr=False, compare=False)

    def set_on_change(self, callback: OnChange | None) -> None:
        self._on_change = callback

    def notify(self) -> None:
        if self._on_change is not None:
            self._on_change()

    def set_gradi(self, gradi: list[str], *, notify: bool = True) -> None:
        self.gradi = list(gradi)
        if notify:
            self.notify()

    def set_distretti(self, distretti: list[int], *, notify: bool = True) -> None:
        self.distretti = [int(d) for d in distretti]
        if notify:
            self.notify()

    def set_testo(self, testo: str, *, notify: bool = True) -> None:
        self.testo = testo or ""
        if notify:
            self.notify()

    def set_mostra_casa(self, value: bool, *, notify: bool = True) -> None:
        self.mostra_casa = bool(value)
        if notify:
            self.notify()

    def set_ordina_per_distanza(self, value: bool, *, notify: bool = True) -> None:
        self.ordina_per_distanza = bool(value)
        if notify:
            self.notify()

    def set_profilo_routing(self, value: str, *, notify: bool = True) -> None:
        self.profilo_routing = value or "foot"
        if notify:
            self.notify()

    def set_casa(
        self,
        lat: float,
        lon: float,
        *,
        notify: bool = True,
    ) -> None:
        self.casa_lat = float(lat)
        self.casa_lon = float(lon)
        if notify:
            self.notify()

    def ripristina_casa_default(self, *, notify: bool = True) -> None:
        self.set_casa(CASA_LAT, CASA_LON, notify=notify)

    def toggle_grado(self, grado: str, selected: bool) -> None:
        if selected:
            if grado not in self.gradi:
                self.gradi.append(grado)
        else:
            self.gradi = [g for g in self.gradi if g != grado]
        self.notify()

    def toggle_distretto(self, distretto: int, selected: bool) -> None:
        d = int(distretto)
        if selected:
            if d not in self.distretti:
                self.distretti.append(d)
        else:
            self.distretti = [x for x in self.distretti if x != d]
        self.notify()
