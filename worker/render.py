#!/usr/bin/env python3
"""Entrada estable al renderizador compartido, con marca explícita."""
import argparse
from pathlib import Path
from motor.cargador import cargar_marca
from motor.render import desde_linea_de_comandos


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--marca', required=True)
    parser.add_argument('spec')
    parser.add_argument('salida')
    args = parser.parse_args()
    skills = Path(__file__).resolve().parent / '.claude/skills'
    carpeta = (skills / args.marca).resolve()
    if carpeta.parent != skills.resolve() or not (carpeta / 'marca.py').is_file():
        parser.error('Marca desconocida.')
    desde_linea_de_comandos(cargar_marca(carpeta), carpeta,
                            ['render.py', args.spec, args.salida])

if __name__ == '__main__':
    main()
