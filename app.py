import json
import time
import pypdf
import streamlit as st
from google import genai
from google.genai import types
from google.genai.errors import APIError
from document_builder import rellenar_plantilla_word

st.set_page_config(page_title="Generador de Fichas Bibliográficas", page_icon="📄", layout="wide")

st.title("📄 Generador Automático de Fichas de Resumen")
st.write("Carga un documento PDF para procesarlo, revisar los campos y descargar la ficha en Word (.docx).")

# Cargar credenciales desde Secrets
try:
    api_key = st.secrets["gemini"]["api_keys"][0]
    modelos_disponibles = st.secrets["gemini"].get("models", ["gemini-3.6-flash", "gemini-3.7-flash", "gemini-3.8-flash"])
except Exception:
    st.error("Revisa la configuración de Secrets en Streamlit Cloud.")
    st.stop()

def extraer_texto_pdf(pdf_file):
    reader = pypdf.PdfReader(pdf_file)
    texto = ""
    for page in reader.pages:
        texto += page.extract_text() or ""
    return texto

def analizar_pdf_con_ia(texto_pdf, api_key, lista_modelos):
    client = genai.Client(api_key=api_key)

    prompt = f"""
    Eres un experto analista en revisión bibliográfica e ingeniería hídrica/ambiental.
    Analiza el siguiente texto de un estudio/artículo/informe y completa la información requerida para una ficha estandarizada de resumen.

    TEXTO DEL DOCUMENTO:
    {texto_pdf[:35000]}

    INSTRUCCIONES:
    Responde ÚNICAMENTE con un objeto JSON válido utilizando exactamente esta estructura:

    {{
        "tipo_informacion": "Tipo de documento (ej: Artículo científico, Informe técnico, Ley)",
        "titulo": "Título completo del documento",
        "anio": "Año de publicación",
        "elaborado_por": "Institución, laboratorio o entidad responsable",
        "autores": "Autores del documento separados por punto y coma",
        "link_descarga": "URL o DOI si figura en el documento",
        "alcance_geografico": {{
            "Nacional": false,
            "Inter-Regional": false,
            "Regional": false,
            "Cuenca(s)": false
        }},
        "ambito_geografico": {{
            "region": "Región o zona geográfica descrita",
            "provincia": "Provincia",
            "cuenca": "Cuenca o área específica de estudio"
        }},
        "tipo_antecedente": {{
            "Delimitación para la planificación estratégica": false,
            "Enfoque de Género": false,
            "Caracterización socio-económica y cultural": false,
            "Caracterización física": false,
            "Caracterización infraestructura hídrica, redes hidrométricas y de monitoreo": false,
            "Descripción de la gestión hídrica": false,
            "Balance Hídrico": false,
            "Catastro de iniciativas y medidas": false
        }},
        "objetivo_general": "Objetivo general del estudio",
        "objetivos_especificos": ["Objetivo específico 1", "Objetivo específico 2"],
        "metodologias": ["Punto clave metodológico 1", "Punto clave metodológico 2"],
        "resultados": ["Resultado principal 1", "Resultado principal 2"]
    }}
    """

    for modelo in lista_modelos:
        for intento in range(2):
            try:
                response = client.models.generate_content(
                    model=modelo,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.1,
                    ),
                )
                return json.loads(response.text)
            except APIError as e:
                if e.code == 503:
                    time.sleep(2)
                    continue
                else:
                    raise e
            except Exception as e:
                break
    raise Exception("No se pudo obtener respuesta de la API. Intenta nuevamente.")

# Carga de archivo PDF
uploaded_file = st.file_uploader("Selecciona el archivo PDF a procesar", type=["pdf"])

if uploaded_file is not None:
    if st.button("🔍 Analizar Documento", type="primary"):
        with st.spinner("Procesando PDF y estructurando información..."):
            try:
                texto_extraido = extraer_texto_pdf(uploaded_file)
                datos_json = analizar_pdf_con_ia(texto_extraido, api_key, modelos_disponibles)
                st.session_state["datos_ficha"] = datos_json
                st.success("¡Análisis finalizado con éxito!")
            except Exception as e:
                st.error(f"Error durante el procesamiento: {e}")

# Muestra y descarga de la Ficha en formato Word
if "datos_ficha" in st.session_state:
    st.markdown("---")
    st.subheader("📝 Ficha Generada (Revisión / Descarga)")

    datos = st.session_state["datos_ficha"]

    # Generación del archivo .docx rellenado
    try:
        plantilla_path = "Anexo Ficha revisión bibliográfica.docx" # Asegúrate que coincida con el nombre exacto subido a GitHub
        docx_buffer = rellenar_plantilla_word(plantilla_path, datos)

        st.download_button(
            label="📥 Descargar Ficha en Word (.docx)",
            data=docx_buffer,
            file_name=f"Ficha_Resumen_{datos.get('anio', '2026')}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            type="primary"
        )
    except Exception as e:
        st.warning(f"Asegúrate de que la plantilla Word esté subida a GitHub con el nombre exacto. Detalle: {e}")

    # Muestra los datos estructurados
    st.json(datos)
