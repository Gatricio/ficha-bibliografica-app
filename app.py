import json
import pypdf
import streamlit as st
from google import genai
from google.genai import types

# Configuración de página
st.set_page_config(page_title="Generador de Fichas Bibliográficas", page_icon="📄", layout="wide")

st.title("📄 Generador Automático de Fichas de Resumen")
st.write("Carga un documento en formato PDF para procesarlo y extraer la información técnica.")

# Obtener clave de API desde Secrets (sintaxis para tu configuración de listas)
try:
    api_key = st.secrets["gemini"]["api_keys"][0]
except Exception:
    st.error("No se encontró la clave de API en los Secrets de Streamlit. Por favor, revisa la configuración.")
    st.stop()

def extraer_texto_pdf(pdf_file):
    """Extrae el texto legible de un archivo PDF."""
    reader = pypdf.PdfReader(pdf_file)
    texto = ""
    for page in reader.pages:
        texto += page.extract_text() or ""
    return texto

def analizar_pdf_con_ia(texto_pdf, api_key):
    """Envía el texto extraído a Gemini para obtener los campos de la ficha en formato JSON."""
    client = genai.Client(api_key=api_key)

    prompt = f"""
    Eres un experto analista en revisión bibliográfica e ingeniería hídrica/ambiental.
    Analiza el siguiente texto de un estudio/artículo/informe y completa la información requerida para una ficha estandarizada de resumen.

    TEXTO DEL DOCUMENTO:
    {texto_pdf[:35000]}

    INSTRUCCIONES:
    Responde ÚNICAMENTE con un objeto JSON válido (sin texto antes ni después) utilizando exactamente esta estructura:

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

    # Usando gemini-3.6-flash según la regla definida
    response = client.models.generate_content(
        model='gemini-3.6-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.1,
        ),
    )

    return json.loads(response.text)

# Interfaz de usuario: Carga de archivo
uploaded_file = st.file_uploader("Selecciona el archivo PDF a procesar", type=["pdf"])

if uploaded_file is not None:
    if st.button("🔍 Analizar Documento", type="primary"):
        with st.spinner("Procesando PDF con Inteligencia Artificial..."):
            try:
                texto_extraido = extraer_texto_pdf(uploaded_file)
                datos_json = analizar_pdf_con_ia(texto_extraido, api_key)
                st.session_state["datos_ficha"] = datos_json
                st.success("¡Análisis finalizado con éxito!")
            except Exception as e:
                st.error(f"Ocurrió un error durante el procesamiento: {e}")

# Muestra los datos analizados
if "datos_ficha" in st.session_state:
    st.subheader("📋 Datos Extraídos para la Ficha")
    st.json(st.session_state["datos_ficha"])
