"""Script manual para validar OpenAI con datos CAD de ejemplo.

No define tests de pytest y no debe ejecutar nada al importarse.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

__test__ = False


def _mask_secret(secret: str) -> str:
    if len(secret) <= 10:
        return "*" * len(secret)
    return f"{secret[:7]}...{secret[-4:]}"


def main(
    input_path: Path | None = None,
    output_path: Path | None = None,
    env_path: Path | None = None,
) -> Path:
    """Ejecuta una prueba manual de presupuesto con OpenAI."""
    from openai import OpenAI

    project_root = Path(__file__).resolve().parent.parent
    env_file = env_path or (project_root / ".env")
    load_dotenv(env_file)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(f"No se encontro OPENAI_API_KEY en {env_file}")

    input_file = input_path or (Path(__file__).resolve().parent / "dwg_deep_analysis.txt")
    if not input_file.exists():
        raise FileNotFoundError(f"No se encontro el archivo de entrada: {input_file}")

    output_file = output_path or (Path(__file__).resolve().parent / "budget_test_result.txt")

    print(f"API Key: {_mask_secret(api_key)}")
    client = OpenAI(api_key=api_key)
    com_data = input_file.read_text(encoding="utf-8")

    print("\n[TEST] Enviando datos COM a GPT-4o para generar partidas...")
    print("(sin imagen, solo datos textuales del CAD)")

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "Eres un ingeniero presupuestista experto. "
                    "Analiza los datos de un archivo CAD y genera un "
                    "presupuesto por partidas constructivas en formato JSON."
                ),
            },
            {
                "role": "user",
                "content": f"""Analiza estos datos extraidos de un archivo DWG de un proyecto de edificacion.
Los datos son de un plano arquitectonico con 28,568 entidades, unidades en Metros.

DATOS DEL CAD:
{com_data[:4000]}

Genera un presupuesto por PARTIDAS con esta estructura JSON:
{{
  "project_name": "nombre estimado del proyecto",
  "budget_items": [
    {{
      "code": "01.01",
      "chapter": "CAPITULO",
      "description": "descripcion de la partida",
      "unit": "m2/m/ud/ml/kg/m3/gl",
      "quantity": 0.0,
      "source": "medido del CAD",
      "notes": ""
    }}
  ],
  "total_items": 0,
  "observations": "observaciones generales"
}}""",
            },
        ],
        max_tokens=4096,
        temperature=0.1,
    )

    result = response.choices[0].message.content
    output_file.write_text(result, encoding="utf-8")

    print(f"\nResultado guardado: {output_file}")
    print(f"Tokens usados: {response.usage.total_tokens}")
    print("\nPrimeras 500 chars del resultado:")
    print(result[:500])
    return output_file


if __name__ == "__main__":
    main()
