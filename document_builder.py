import io
from docx import Document

def rellenar_plantilla_word(plantilla_path, datos):
    """
    Recibe la ruta de la plantilla .docx y el diccionario 'datos' extraído por la IA,
    y devuelve un buffer en memoria del documento rellenado.
    """
    doc = Document(plantilla_path)

    # Si la plantilla contiene tablas (como el Anexo Ficha)
    if doc.tables:
        tabla = doc.tables[0] # Asumimos la tabla principal
        
        # Mapeo y rellenado según la estructura del Anexo
        # TIPO DE INFORMACIÓN
        try:
            tabla.cell(0, 1).text = str(datos.get("tipo_informacion", ""))
            tabla.cell(1, 1).text = str(datos.get("titulo", ""))
            tabla.cell(2, 1).text = str(datos.get("anio", ""))
            tabla.cell(3, 1).text = str(datos.get("elaborado_por", ""))
            tabla.cell(4, 1).text = str(datos.get("autores", ""))
            tabla.cell(5, 1).text = str(datos.get("link_descarga", ""))
        except IndexError:
            pass

        # Alcance Geográfico (Marcación con "X")
        alcance = datos.get("alcance_geografico", {})
        # Ajustamos marcas "X" en la fila de marcación si corresponde
        try:
            if alcance.get("Nacional"): tabla.cell(7, 0).text = "X"
            if alcance.get("Inter-Regional"): tabla.cell(7, 1).text = "X"
            if alcance.get("Regional"): tabla.cell(7, 2).text = "X"
            if alcance.get("Cuenca(s)"): tabla.cell(7, 3).text = "X"
        except IndexError:
            pass

        # Ámbito Geográfico
        ambito = datos.get("ambito_geografico", {})
        try:
            tabla.cell(9, 0).text = str(ambito.get("region", ""))
            tabla.cell(9, 1).text = str(ambito.get("provincia", ""))
            tabla.cell(9, 2).text = str(ambito.get("cuenca", ""))
        except IndexError:
            pass

        # Tipo de Antecedente (Marcación con "X")
        antecedentes = datos.get("tipo_antecedente", {})
        try:
            m_keys = [
                "Delimitación para la planificación estratégica",
                "Enfoque de Género",
                "Caracterización socio-económica y cultural",
                "Caracterización física",
                "Caracterización infraestructura hídrica, redes hidrométricas y de monitoreo",
                "Descripción de la gestión hídrica",
                "Balance Hídrico",
                "Catastro de iniciativas y medidas"
            ]
            for idx, key in enumerate(m_keys):
                if antecedentes.get(key):
                    tabla.cell(11, idx).text = "X"
        except IndexError:
            pass

    # Rellenado de Secciones de Texto (Objetivos, Metodología, Resultados)
    # Buscamos en los párrafos o celdas correspondientes
    for i, p in enumerate(doc.paragraphs):
        text = p.text.strip()
        
        if "OBJETIVO(S) DE LA INFORMACIÓN" in text or "OBJETIVOS" in text:
            p.text = "OBJETIVO(S) DE LA INFORMACIÓN\n"
            p.add_run(f"Objetivo general:\n{datos.get('objetivo_general', '')}\n\n")
            p.add_run("Objetivos específicos:\n")
            for obj in datos.get("objetivos_especificos", []):
                p.add_run(f"• {obj}\n")

        elif "METODOLOGÍA(S)" in text:
            p.text = "METODOLOGÍA(S) RELEVANTE(S) DE INTERÉS PARA EL ESTUDIO\n"
            for met in datos.get("metodologias", []):
                p.add_run(f"• {met}\n")

        elif "RESULTADOS" in text:
            p.text = "RESULTADOS (VARIABLES Y/O DATOS) DE INTERÉS PARA EL ESTUDIO\n"
            for res in datos.get("resultados", []):
                p.add_run(f"• {res}\n")

    # Guardar en buffer en memoria para Streamlit
    file_stream = io.BytesIO()
    doc.save(file_stream)
    file_stream.seek(0)
    return file_stream
