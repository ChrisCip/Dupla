---
description: "Verifica si el proyecto puede arrancar localmente y reporta bloqueos concretos"
name: "Verificar Arranque Local"
argument-hint: "script principal opcional (ej: run_full_analysis.py)"
agent: "agent"
---
Objetivo: validar que este proyecto puede iniciar en la maquina local y devolver un diagnostico accionable.

Entrada:
- Script principal (opcional): `$ARGUMENTS`.
- Si no se indica script, usar primero `run_full_analysis.py`; si no existe, detectar el entrypoint desde README.

Pasos:
1. Revisar `requirements.txt` y el comando de instalacion documentado en `README.md`.
2. Configurar el entorno Python del workspace y usar ese interprete para comandos.
3. Instalar dependencias faltantes con `pip install -r requirements.txt`.
4. Buscar rutas absolutas hardcodeadas (ejemplo: `c:\\Users\\...`) en el script principal y dependencias directas.
5. Intentar arranque real del script principal.
6. Si el arranque falla, identificar el primer bloqueo real y proponer la correccion minima.
7. Verificar con una prueba rapida adicional sin dependencias externas (por ejemplo, `python -m cad_automation --help` o `py_compile`).

Formato de salida:
- Estado: `OK` o `BLOQUEADO`.
- Hallazgos: lista corta de problemas con archivo y linea.
- Cambios aplicados: lista de ediciones concretas.
- Comandos ejecutados: lista exacta.
- Siguiente paso minimo para el usuario.

Reglas:
- Priorizar cambios pequenos y reversibles.
- No asumir AutoCAD abierto ni API key cargada: reportarlo como prerequisito externo si aplica.
- No ocultar errores; mostrar el primer traceback relevante resumido.
