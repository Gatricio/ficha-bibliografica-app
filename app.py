import os
import time
import json
import re
from io import BytesIO
import streamlit as st
import pypdf
from docxtpl import DocxTemplate
from google import genai
from google.genai import types

# Configuración inicial de la página en Streamlit
st.set_page_config(
    page_title="Generador de Fichas Bibliográficas",
    page_icon="📄",
    layout="wide"
)

# Estilos visuales
st.markdown("""
    <style>
    .main-header { font-size:24px; font-weight:bold; color:#002855; margin-bottom:2px; }
    .sub-header { font-size:14px; color:#555; margin-bottom: 20px; }
    .stButton>button { background-color: #0056B3; color: white; font-weight: bold; width: 100%; }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# OBTENCIÓN DE CONFIGURACIÓN DE GEMINI DESDE SECRETS
# ---------------------------------------------------------
def obtener_configuracion_gemini():
    keys = []
    models = ["gemini-3.6-flash", "gemini-3.7-flash", "gemini-3.8-flash"]

    if "gemini" in st.secrets:
        gemini_sec = st.secrets["gemini"]
        if "api_keys" in gemini_sec and isinstance(gemini_sec["api_keys"], list):
            keys = [k.strip() for k in gemini_sec["api_keys"] if k.strip()]
        if "models" in gemini_sec and isinstance(gemini_sec["models"], list):
            models = [m.strip() for m in gemini_sec["models"] if m.strip()]

    if not keys:
        single_key = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY", ""))
        if single_key:
            keys = [single_key.strip()]

    return keys, models

api_keys, modelos_disponibles = obtener_configuracion_gemini()

# ---------------------------------------------------------
# FUNCIÓN PARA LIMPIAR EL NOMBRE DEL ARCHIVO DE DESCARGA
# ---------------------------------------------------------
def limpiar_nombre_archivo(titulo):
    if not titulo:
        return "Ficha_Resumen.docx"
    # Eliminar caracteres no válidos para nombres de archivos en OS
    nombre_limpio = re.sub(r'[\\/*?:"<>|]', '', titulo)
    # Reemplazar espacios múltiples y saltos de línea
    nombre_limpio = re.sub(r'\s+', '_', nombre_limpio.strip())
    # Limitar la longitud máxima del nombre del archivo
    if len(nombre_limpio) > 100:
        nombre_limpio = nombre_limpio[:100]
    return f"Ficha_{nombre_limpio}.docx"

# ---------------------------------------------------------
# EXTRACCIÓN DE TEXTO DESDE EL PDF
# ---------------------------------------------------------
def extraer_texto_pdf(file_bytes):
    try:
        pdf_reader = pypdf.PdfReader(BytesIO(file_bytes))
        texto = ""
        for page in pdf_reader.pages:
            texto += page.extract_text() or ""
        return texto
    except Exception as e:
        return f"[Error al leer PDF: {str(e)}]"

# ---------------------------------------------------------
# PROCESAMIENTO Y EXTRACCIÓN CON GEMINI IA
# ---------------------------------------------------------
def analizar_documento_con_gemini(texto_pdf):
    if not api_keys:
        st.error("No se encontraron API Keys configuradas en Secrets.")
        return None

    prompt = f"""
    Eres un experto analista en revisión bibliográfica e ingeniería hídrica/ambiental.
    Analiza el siguiente texto de un documento técnico/científico y extrae la información requerida para una ficha de resumen estandarizada.

    TEXTO DEL DOCUMENTO:
    {texto_pdf[:35000]}

    INSTRUCCIONES DE REDACCIÓN Y ESTRUCTURA:
    1. OBJETIVO GENERAL: Redacta un texto breve y continuo que describa el propósito central del estudio.
    2. OBJETIVOS ESPECÍFICOS: Extrae y redacta OBLIGATORIAMENTE ENTRE 3 Y 6 OBJETIVOS ESPECÍFICOS. Deben ser sintéticos, concisos, iniciar con un verbo en infinitivo y abordar aspectos clave puntuales del estudio.
    3. METODOLOGÍAS Y RESULTADOS: Redacta puntos sintéticos claros.

    Responde ÚNICAMENTE con un objeto JSON válido (sin marcas markdown de código ```json) con la siguiente estructura exacta:

    {{
        "tipo_informacion": "Tipo de documento (ej: Artículo científico, Informe técnico, Ley)",
        "titulo": "Título exacto del documento",
        "anio": "Año de publicación",
        "elaborado_por": "Institución o laboratorio que elaboró el estudio",
        "autores": "Autores del documento separados por punto y coma",
        "link_descarga": "URL o DOI si aplica",
        "alcance_geografico": {{
            "Nacional": false,
            "Inter-Regional": false,
            "Regional": false,
            "Cuenca(s)": false
        }},
        "ambito_geografico": {{
            "region": "Región o zona geográfica",
            "provincia": "Provincia",
            "cuenca": "Cuenca hídrica específica"
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
        "objetivo_general": "Evaluación/Análisis de...",
        "objetivos_especificos": [
            "Cuantificar los efectos proyectados...",
            "Evaluar los escenarios...",
            "Proponer opciones de manejo..."
        ],
        "metodologias": ["Punto metodológico 1", "Punto metodológico 2"],
        "resultados": ["Resultado principal 1", "Resultado principal 2"]
    }}
    """

    for key in api_keys:
        client = genai.Client(api_key=key)
        for modelo in modelos_disponibles:
            intentos = 0
            while intentos < 3:
                try:
                    response = client.models.generate_content(
                        model=modelo,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            temperature=0.1,
                        )
                    )
                    if response and response.text:
                        return json.loads(response.text)
                except Exception as e:
                    err_msg = str(e)
                    if "503" in err_msg or "UNAVAILABLE" in err_msg:
                        intentos += 1
                        time.sleep(2 * intentos)
                        continue
                    break
    return None

# ---------------------------------------------------------
# INTERFAZ DE USUARIO STREAMLIT
# ---------------------------------------------------------
st.markdown('<div class="main-header">PLATAFORMA DE REVISIÓN BIBLIOGRÁFICA Y FICHAS DE RESUMEN</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Procesamiento automático de documentos y generación de fichas en Word</div>', unsafe_allow_html=True)

uploaded_file = st.file_uploader("Cargar documento PDF bibliográfico:", type=["pdf"])

if uploaded_file:
    file_bytes = uploaded_file.read()
    if st.button("🔍 Procesar y Extraer Información", type="primary"):
        with st.spinner("Leyendo documento y ejecutando análisis con Gemini IA..."):
            texto = extraer_texto_pdf(file_bytes)
            datos_extraidos = analizar_documento_con_gemini(texto)

            if datos_extraidos:
                st.session_state["datos_ficha"] = datos_extraidos
                st.success("¡Análisis completado exitosamente!")
            else:
                st.error("No se pudo extraer la información del documento.")

if "datos_ficha" in st.session_state:
    st.markdown("---")
    st.subheader("📋 Vista Previa y Descarga de la Ficha")

    datos = st.session_state["datos_ficha"]

    # Generación de la plantilla con docxtpl
    def generar_word_docxtpl(datos_json):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        template_path = os.path.join(base_dir, "Plantilla_Ficha_Bibliografica.docx")

        if not os.path.exists(template_path):
            template_path = os.path.join(base_dir, "Anexo Ficha revisión bibliográfica.docx")

        doc = DocxTemplate(template_path)

        alcance = datos_json.get("alcance_geografico", {})
        antecedentes = datos_json.get("tipo_antecedente", {})
        ambito = datos_json.get("ambito_geografico", {})

        contexto = {
            'TIPO_INFORMACION': datos_json.get("tipo_informacion", ""),
            'TITULO': datos_json.get("titulo", ""),
            'ANIO': datos_json.get("anio", ""),
            'ELABORADO_POR': datos_json.get("elaborado_por", ""),
            'AUTORES': datos_json.get("autores", ""),
            'LINK_DESCARGA': datos_json.get("link_descarga", ""),

            # Marcas de Alcance Geográfico
            'MARCA_NACIONAL': "X" if alcance.get("Nacional") else "",
            'MARCA_INTERREGIONAL': "X" if alcance.get("Inter-Regional") else "",
            'MARCA_REGIONAL': "X" if alcance.get("Regional") else "",
            'MARCA_CUENCA': "X" if alcance.get("Cuenca(s)") else "",

            # Ámbito Geográfico
            'REGION': ambito.get("region", ""),
            'PROVINCIA': ambito.get("provincia", ""),
            'CUENCA': ambito.get("cuenca", ""),

            # Marcas de Tipo de Antecedente
            'M_DELIMITACION': "X" if antecedentes.get("Delimitación para la planificación estratégica") else "",
            'M_GENERO': "X" if antecedentes.get("Enfoque de Género") else "",
            'M_SOCIOECONOMICA': "X" if antecedentes.get("Caracterización socio-económica y cultural") else "",
            'M_FISICA': "X" if antecedentes.get("Caracterización física") else "",
            'M_INFRAESTRUCTURA': "X" if antecedentes.get("Caracterización infraestructura hídrica, redes hidrométricas y de monitoreo") else "",
            'M_GESTION': "X" if antecedentes.get("Descripción de la gestión hídrica") else "",
            'M_BALANCE': "X
