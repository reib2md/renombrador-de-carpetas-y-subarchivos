import csv
import io
from pathlib import Path
import tempfile
import zipfile
import openpyxl
import streamlit as st

st.set_page_config(
    page_title="Renombrador Masivo de Carpetas", page_icon="📁", layout="centered"
)

st.title("📁 Renombrador Masivo de Carpetas y Archivos")
st.markdown(
    "Sube el archivo **.zip** con tus carpetas y la **planilla (Excel/CSV)** para procesarlos."
)

zip_file = st.file_uploader(
    "1. Sube tu carpeta comprimida (.zip)", type=["zip"]
)
excel_file = st.file_uploader(
    "2. Sube tu planilla (.xlsx, .csv)", type=["xlsx", "csv"]
)


def cargar_mapeo(file_obj, filename):
    mapeo = {}
    if filename.endswith(".xlsx"):
        wb = openpyxl.load_workbook(file_obj, data_only=True)
        sheet = wb.active
        for row in sheet.iter_rows(values_only=True):
            if row and len(row) >= 2 and row[0] and row[1]:
                mapeo[str(row[0]).strip()] = str(row[1]).strip()
    elif filename.endswith(".csv"):
        content = file_obj.getvalue().decode("utf-8-sig")
        sample = content[:2048]
        delimiter = ";" if ";" in sample else ","
        reader = csv.reader(content.splitlines(), delimiter=delimiter)
        for row in reader:
            if len(row) >= 2 and row[0].strip() and row[1].strip():
                mapeo[row[0].strip()] = row[1].strip()
    return mapeo


if st.button("🚀 Iniciar Procesamiento", type="primary"):
    if not zip_file or not excel_file:
        st.error(
            "Debes subir tanto el archivo .zip como la planilla para continuar."
        )
    else:
        with st.spinner("Procesando y renombrando estructura..."):
            try:
                mapeo = cargar_mapeo(excel_file, excel_file.name)

                with tempfile.TemporaryDirectory() as temp_dir:
                    temp_path = Path(temp_dir)
                    extract_path = temp_path / "extracted"
                    extract_path.mkdir()

                    # Extraer el ZIP
                    with zipfile.ZipFile(zip_file, "r") as zf:
                        zf.extractall(extract_path)

                    # Detectar carpeta raíz extraída
                    extracted_items = list(extract_path.iterdir())
                    if (
                        len(extracted_items) == 1
                        and extracted_items[0].is_dir()
                    ):
                        root_dir = extracted_items[0]
                    else:
                        root_dir = extract_path

                    log_messages = []
                    carpetas_renombradas = 0
                    archivos_renombrados = 0

                    # Procesar carpetas y archivos
                    for nombre_actual, nombre_nuevo in mapeo.items():
                        carpeta_actual = root_dir / nombre_actual

                        if (
                            not carpeta_actual.exists()
                            or not carpeta_actual.is_dir()
                        ):
                            log_messages.append(
                                f"⚠️ [OMITIDO] No existe la subcarpeta: '{nombre_actual}'"
                            )
                            continue

                        carpeta_nueva = root_dir / nombre_nuevo
                        carpeta_actual.rename(carpeta_nueva)
                        carpetas_renombradas += 1
                        log_messages.append(
                            f"✅ Subcarpeta renombrada: '{nombre_actual}' -> '{nombre_nuevo}'"
                        )

                        archivos = [
                            item
                            for item in carpeta_nueva.iterdir()
                            if item.is_file()
                        ]
                        archivos.sort()

                        for idx, archivo in enumerate(archivos, start=1):
                            ext = archivo.suffix
                            nuevo_nombre_archivo = f"{nombre_nuevo}-{idx}{ext}"
                            destino_archivo = carpeta_nueva / nuevo_nombre_archivo
                            archivo.rename(destino_archivo)
                            archivos_renombrados += 1
                            log_messages.append(
                                f"   └─ Archivo: '{archivo.name}' -> '{nuevo_nombre_archivo}'"
                            )

                    # Recomprimir el resultado
                    output_zip_io = io.BytesIO()
                    with zipfile.ZipFile(
                        output_zip_io, "w", zipfile.ZIP_DEFLATED
                    ) as zip_out:
                        for file_path in root_dir.rglob("*"):
                            if file_path.is_file():
                                arcname = file_path.relative_to(root_dir)
                                zip_out.write(file_path, arcname)

                    output_zip_io.seek(0)

                    st.success(
                        f"Proceso completado: {carpetas_renombradas} subcarpetas y {archivos_renombrados} archivos renombrados."
                    )

                    st.download_button(
                        label="📥 Descargar Resultado (.zip)",
                        data=output_zip_io,
                        file_name=f"renombrado_{zip_file.name}",
                        mime="application/zip",
                    )

                    with st.expander("Ver registro de cambios"):
                        st.code("\n".join(log_messages))

            except Exception as e:
                st.error(f"Error en el procesamiento: {str(e)}")