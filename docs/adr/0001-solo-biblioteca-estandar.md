# ADR 0001: usar solo la biblioteca estándar de Python

- Estado: aceptada
- Fecha: 2026-10-24

## Contexto

El tablero debe correr en cualquier equipo con Python, construirse en segundos en CI y publicarse como un archivo HTML estático. Las librerías habituales de datos y gráficos (pandas, matplotlib, plotly) suman decenas de megas y actualizaciones de seguridad que mantener.

## Decisión

La versión 0.1 usa solo la biblioteca estándar: `csv` para los datos, cálculos propios con `math` para los KPIs y SVG escrito a mano para los gráficos.

## Consecuencias

- Instalación inmediata, sin dependencias en tiempo de ejecución y con menos superficie de ataque.
- El tablero es un único HTML que funciona sin conexión.
- Los gráficos son más simples que los de una librería; si el proyecto necesita interactividad, se evaluará en un ADR nuevo.
