# -*- coding: utf-8 -*-
"""Asistime, visto desde el motor. Esta marca es sólo datos: ver `marca.json`
(bloque «identidad»), `estilo.css` y `plantillas/`. Es el primer cliente que
entró entero por ese camino, sin escribir Python."""
from motor.identidad import cargar as _cargar
globals().update({k: v for k, v in vars(_cargar(__file__)).items() if not k.startswith("__")})
