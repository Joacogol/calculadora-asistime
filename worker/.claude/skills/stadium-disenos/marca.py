# -*- coding: utf-8 -*-
"""Stadium, visto desde el motor. Esta marca es sólo datos: ver `marca.json`
(bloque «identidad»), `estilo.css` y `plantillas/`. Lo que hay que saber está
en `motor/identidad.py`."""
from motor.identidad import cargar as _cargar
globals().update({k: v for k, v in vars(_cargar(__file__)).items() if not k.startswith("__")})
