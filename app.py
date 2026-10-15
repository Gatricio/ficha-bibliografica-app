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

# Estilos visuales corporativos
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
    nombre_limpio = re.sub(r'[\\/*?:"<>|]', '', titulo)
    nombre_limpio = re.sub(r'\s+', '_', nombre_limpio.strip())
    if len(nombre_limpio) > 100:
        nombre_limpio = nombre_limpio[:100]
    return f"Ficha_{nombre_limpio}.docx"

# ---------------------------------------------------------
# EXTRACCIÓN RÁPIDA DE TEXTO (OPTIMIZADA)
# ---------------------------------------------------------
@st.cache_data(show_spinner=False)
def extraer_texto_optimizado(file_bytes):
    """
    Extrae únicamente las secciones clave (primeras páginas y resumen)
    para acelerar drásticamente el procesamiento por la IA.
    """
    try:
        pdf_reader = pypdf.PdfReader(BytesIO(file_bytes))
        num_paginas = len(pdf_reader.pages)
        
        texto_inicio = ""
        # Leer máximo las primeras 4 páginas (donde están título, autores, abstract, objetivos y metodología)
        paginas_a_leer = min(4, num_paginas)
        for i in range(paginas_a_leer):
            texto_inicio += pdf_reader.pages[i].extract_text() or ""
            
        # Si el documento es largo, agregar la última página (conclusiones/resultados)
        texto_final = ""
        if num_paginas > 4:
            texto_final = pdf_reader.pages[-1].extract_text() or ""

        texto_acotado = (texto_inicio + "\n\n...[SECCIÓN INTERMEDIA OMITIDA POR VELOCIDAD]...\n\n" + texto_final)[:12000]
        return texto_acotado
    except Exception as e:
        return f"[Error al leer PDF: {str(e)}]"

# ---------------------------------------------------------
# PROCESAMIENTO ULTRARRÁPIDO CON GEMINI IA
# ---------------------------------------------------------
@st.cache_data(show_spinner=False)
def analizar_documento_rapido(texto_pdf):
    if not api_keys:
        return None

    prompt = f"""
    Eres un experto analista bibliográfico hídrico. Extrae rápidamente la información requerida del siguiente documento.

    TEXTO DEL DOCUMENTO:
    {texto_pdf}

    INSTRUCCIONES DE REDACCIÓN Y ESTRUCTURA:
    1. OBJETIVO GENERAL: Redacta un texto breve y continuo con el propósito central.
    2. OBJETIVOS ESPECÍFICOS: Extrae OBLIGATORIAMENTE ENTRE 3 Y 6 OBJETIVOS ESPECÍFICOS breves iniciando con verbo en infinitivo.
    3. METODOLOGÍAS Y RESULTADOS: Redacta puntos sintéticos.

    Responde ÚNICAMENTE con un objeto JSON válido (sin código markdown) con esta estructura exacta:

    {{
        "tipo_informacion": "Tipo de documento (ej: Artículo científico, Informe técnico)",
        "titulo": "Título exacto",
        "anio": "Año de publicación",
        "elaborado_por": "Institución o departamento",
        "autores": "Autores separados por punto y coma",
        "link_descarga": "URL o DOI si aplica",
        "alcance_geografico": {{
            "Nacional": false,
            "Inter-Regional": false,
            "Regional": false,
            "Cuenca(s)": false
        }},
        "ambito_geografico": {{
            "region": "Región",
            "provincia": "Provincia",
            "cuenca": "Cuenca hídrica"
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
        "objetivos_especificos": ["Cuantificar...", "Evaluar...", "Proponer..."],
        "metodologias": ["Punto 1", "Punto 2"],
        "resultados": ["Resultado 1", "Resultado 2"]
    }}
    """

    for key in api_keys:
        client = genai.Client(api_key=key)
        for modelo in modelos_disponibles:
            try:
                response = client.models.generate_content(
                    model=modelo,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.0,  # Respuesta directa sin vacilaciones
                        max_output_tokens=1500,  # Limite para acelerar la generación
                    )
                )
                if response and response.text:
                    return json.loads(response.text)
            except Exception:
                continue
    return None

# ---------------------------------------------------------
# INTERFAZ DE USUARIO STREAMLIT
# ---------------------------------------------------------
st.markdown('<div class="main-header">PLATAFORMA DE REVISIÓN BIBLIOGRÁFICA Y FICHAS DE RESUMEN</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Procesamiento ultra-rápido de documentos y generación de fichas en Word</div>', unsafe_allow_html=True)

uploaded_file = st.file_uploader("Cargar documento PDF bibliográfico:", type=["pdf"])

if uploaded_file:
    file_bytes = uploaded_file.read()
    if st.button("⚡ Procesar al Instante", type="primary"):
        with st.spinner("Procesando documento en segundos..."):
            texto = extraer_texto_optimizado(file_bytes)
            datos_extraidos = analizar_documento_rapido(texto)

            if datos_extraidos:
                st.session_state["datos_ficha"] = datos_extraidos
                st.success("¡Ficha generada exitosamente!")
            else:
                st.error("Ocurrió un error. Revisa la configuración de API.")

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
            'M_BALANCE': "X" if antecedentes.get("Balance Hídrico") else "",
            'M_CATASTRO': "X" if antecedentes.get("Catastro de iniciativas y medidas") else "",

            # Bloques de Texto y Listas
            'OBJETIVO_GENERAL': datos_json.get("objetivo_general", ""),
            'OBJETIVOS_ESPECIFICOS': datos_json.get("objetivos_especificos", []),
            'METODOLOGIAS': datos_json.get("metodologias", []),
            'RESULTADOS': datos_json.get("resultados", [])
        }

        doc.render(contexto)
        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer

    # Definir nombre dinámico del archivo
    nombre_salida = limpiar_nombre_archivo(datos.get("titulo", ""))

    # Botón de Descarga
    st.download_button(
        label=f"📥 Descargar Ficha: {nombre_salida}",
        data=generar_word_docxtpl(datos),
        file_name=nombre_salida,
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        use_container_width=True
    )

    # Vista previa JSON
    st.json(datos)
