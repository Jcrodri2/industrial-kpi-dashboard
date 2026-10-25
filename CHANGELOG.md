# Changelog

Todos los cambios relevantes del proyecto. El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y el versionado, [SemVer](https://semver.org/lang/es/).

## [0.1.0] - 2026-10-25

### Agregado

- Generador reproducible de producción diaria sintética por pozo (petróleo, agua, gas y horas en operación).
- Lectura y escritura en CSV.
- Reglas de calidad: duplicados, valores negativos, horas fuera de rango, producción sin operación y fechas faltantes.
- KPIs por pozo y del campo, con declinación mensual por ajuste exponencial.
- Tablero HTML estático con tarjetas, gráficos SVG, tabla por pozo y resumen de calidad.
- Línea de comandos `python -m kpi_dashboard` con modo `--strict` y mensajes claros cuando el CSV no existe, le faltan columnas o trae valores inválidos.
- Política de seguridad de contenido (CSP) en el tablero: no permite scripts ni recursos externos.
- CI con ruff y pytest, análisis con CodeQL, Dependabot y despliegue en GitHub Pages.
