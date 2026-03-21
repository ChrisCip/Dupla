"""Test: Verificar API key OpenAI y hacer un analisis de prueba."""
import sys, os
sys.path.insert(0, r"c:\Users\chris\Documents\Dupla")

from dotenv import load_dotenv
load_dotenv(r"c:\Users\chris\Documents\Dupla\.env")

from openai import OpenAI

api_key = os.getenv("OPENAI_API_KEY")
print(f"API Key: {api_key[:15]}...{api_key[-8:]}")

client = OpenAI(api_key=api_key)

# Test simple: enviar los datos COM como texto y pedir partidas
com_data = open(r"c:\Users\chris\Documents\Dupla\dwg_deep_analysis.txt", "r", encoding="utf-8").read()

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
}}"""
        },
    ],
    max_tokens=4096,
    temperature=0.1,
)

result = response.choices[0].message.content

# Guardar resultado
output_path = r"c:\Users\chris\Documents\Dupla\budget_test_result.txt"
with open(output_path, "w", encoding="utf-8") as f:
    f.write(result)

print(f"\nResultado guardado: {output_path}")
print(f"Tokens usados: {response.usage.total_tokens}")
print(f"\nPrimeras 500 chars del resultado:")
print(result[:500])
