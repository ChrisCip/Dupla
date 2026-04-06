# Plantillas GA-FO (opcional)

Coloca aquí el archivo oficial para exportación Excel **idéntica al formulario** (formato, estilos y cabeceras):

- **`GA-FO-01-(06-2025)-V02- Pliego de Condiciones - Arquitectura.xlsx`** (prioritario)
- `GA-FO-01-pliego.xlsx` — alias si renombrás el mismo archivo
- `GA-FO-03-control-planos.xlsx` — Control Entrega de Planos

El backend detecta la fila de cabecera (partida, descripción, cantidad, etc.), inserta filas antes de una fila `TOTAL` si hace falta y rellena grupos + partidas conservando estilos de la plantilla.

Si no hay plantilla, se genera un `.xlsx` genérico con columnas del dominio.
