import os
import subprocess
import shutil
import zipfile

PROJECT_DIR = os.path.join(os.path.dirname(__file__), "DuplaExtractor")
BUNDLE_DIR = os.path.join(os.path.dirname(__file__), "DuplaExtractor.bundle")
OUTPUT_ZIP = os.path.join(os.path.dirname(__file__), "DuplaExtractor.zip")

PACKAGE_XML = """<?xml version="1.0" encoding="utf-8"?>
<ApplicationPackage SchemaVersion="1.0" AppVersion="1.0.0" ProductCode="{7E43A0B8-893A-4A07-B2D1-9D87BDF4B9E2}" Author="Dupla" Name="DuplaExtractor" Description="Extrae datos de bloques y superficies a JSON">
  <CompanyDetails Name="Dupla" Url="https://dupla.local" Email="noreply@dupla.local" />
  <Components>
    <RuntimeRequirements OS="Win64" Platform="AutoCAD" SeriesMin="R24.0" SeriesMax="R24.3" />
    <ComponentEntry AppName="DuplaExtractor" Version="1.0.0" ModuleName="./Contents/DuplaExtractor.dll" AppDescription="Extractor de cantidades" LoadOnCommandInvocation="True" LoadOnAutoCADStartup="True">
      <Commands GroupName="DuplaCommands">
        <Command Global="ExtractDuplaData" Local="ExtractDuplaData" />
      </Commands>
    </ComponentEntry>
  </Components>
</ApplicationPackage>
"""


def create_bundle():
    if not os.path.isdir(PROJECT_DIR):
        raise FileNotFoundError(f"No existe el proyecto C#: {PROJECT_DIR}")

    env = os.environ.copy()
    env.setdefault("DOTNET_CLI_HOME", os.path.join(os.path.dirname(PROJECT_DIR), ".dotnet_cli"))
    env.setdefault("DOTNET_CLI_TELEMETRY_OPTOUT", "1")

    print("1. Compilando el proyecto C# existente...")
    subprocess.run(["dotnet", "build", "-c", "Release"], cwd=PROJECT_DIR, check=True, env=env)

    print("2. Preparando la carpeta .bundle...")
    if os.path.exists(BUNDLE_DIR):
        shutil.rmtree(BUNDLE_DIR)
    os.makedirs(os.path.join(BUNDLE_DIR, "Contents"))

    with open(os.path.join(BUNDLE_DIR, "PackageContents.xml"), "w", encoding="utf-8") as f:
        f.write(PACKAGE_XML)

    # Copiar el DLL compilado y sus dependencias (ej. System.Text.Json)
    release_dir = os.path.join(PROJECT_DIR, "bin", "Release", "net48")
    for file_name in os.listdir(release_dir):
        if file_name.endswith(".dll"):
            lower_name = file_name.lower()
            # Ignorar dlls de autocad en el paquete final (por si acaso el ExcludeAssets no los limpia del todo)
            if not lower_name.startswith("ac") and not lower_name.startswith("ad") and not lower_name.startswith("autocad"):
                shutil.copy(os.path.join(release_dir, file_name), os.path.join(BUNDLE_DIR, "Contents"))

    print("3. Comprimiendo en formato ZIP para la nube...")
    with zipfile.ZipFile(OUTPUT_ZIP, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(BUNDLE_DIR):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, os.path.dirname(BUNDLE_DIR))
                zipf.write(file_path, arcname)

    print(f"Plugin C# compilado y empaquetado como '{os.path.basename(OUTPUT_ZIP)}'.")


if __name__ == "__main__":
    create_bundle()
