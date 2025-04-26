
import streamlit as st
import fitz  # PyMuPDF
import io
import re
from PyPDF2 import PdfReader, PdfWriter
from unidecode import unidecode

st.set_page_config(page_title="ETIQUETAS + DANFE MODO TURBO 🚀", layout="wide")
st.title("ETIQUETAS + DANFE MODO TURBO 🚀")
st.write("Organize etiquetas e DANFEs em ordem de peso automaticamente!")

# Upload
uploaded_etiqueta = st.file_uploader("📦 Envie o arquivo de Etiquetas", type=["pdf"], key="etiquetas")
uploaded_danfe = st.file_uploader("📄 Envie o arquivo de DANFEs", type=["pdf"], key="danfes")

if uploaded_etiqueta and uploaded_danfe:
    pdf_etiquetas_bytes = uploaded_etiqueta.read()
    pdf_danfes_bytes = uploaded_danfe.read()

    pdf_etiquetas = fitz.open(stream=pdf_etiquetas_bytes, filetype="pdf")
    pdf_danfes = fitz.open(stream=pdf_danfes_bytes, filetype="pdf")

    def extrair_nome_etiqueta(texto):
        for linha in texto.splitlines():
            if "destinatário" in linha.lower():
                partes = linha.split(":")
                if len(partes) > 1 and partes[1].strip():
                    nome = partes[1].strip().lower()
                    nome = re.sub(r'\s+', ' ', nome)[:30]
                    return nome
        linhas = texto.splitlines()
        for idx, linha in enumerate(linhas):
            if "destinatário" in linha.lower() and idx+1 < len(linhas):
                nome = linhas[idx+1].strip().lower()
                nome = re.sub(r'\s+', ' ', nome)[:30]
                return nome
        return None

    def extrair_peso(texto):
        linhas = texto.splitlines()
        for idx, linha in enumerate(linhas):
            if "peso (kg)" in linha.lower() and idx+1 < len(linhas):
                peso_texto = linhas[idx+1].strip().replace(",", ".")
                try:
                    return round(float(peso_texto), 3)
                except:
                    return None
            elif "peso" in linha.lower():
                match = re.search(r'([0-9]+[.,]?[0-9]*)', linha)
                if match:
                    try:
                        return round(float(match.group(1).replace(",", ".")), 3)
                    except:
                        return None
        return None

    def extrair_nome_danfe(texto):
        for linha in texto.splitlines():
            if "endereço de entrega:" in linha.lower():
                depois = linha.split(":", 1)[-1].strip()
                nome_cliente = depois.split(",")[0].strip().lower()
                nome_cliente = re.sub(r'\s+', ' ', nome_cliente)[:30]
                return nome_cliente
        return None

    mapa_etiquetas = {}
    for i in range(len(pdf_etiquetas)):
        texto = pdf_etiquetas[i].get_text()
        nome = extrair_nome_etiqueta(texto)
        peso = extrair_peso(texto)
        if nome:
            mapa_etiquetas[i] = (nome, peso)

    mapa_danfes = {}
    for i in range(len(pdf_danfes)):
        texto = pdf_danfes[i].get_text()
        nome = extrair_nome_danfe(texto)
        if nome:
            mapa_danfes[i] = nome

    normalize = lambda x: unidecode(x.strip().lower()).replace("  ", " ")

    danfes_usadas = set()
    pares = []

    for idx_etiqueta, (nome_etiqueta, peso) in mapa_etiquetas.items():
        nome_norm = normalize(nome_etiqueta)
        achou = False
        for idx_danfe, nome_danfe in mapa_danfes.items():
            if idx_danfe in danfes_usadas:
                continue
            if normalize(nome_danfe) == nome_norm:
                pares.append((idx_etiqueta, idx_danfe, peso))
                danfes_usadas.add(idx_danfe)
                achou = True
                break

    etiquetas_sem_danfe = [idx for idx in mapa_etiquetas.keys() if idx not in [p[0] for p in pares]]
    danfe_sem_etiqueta = [idx for idx in mapa_danfes.keys() if idx not in [p[1] for p in pares]]

    pares_com_peso = [p for p in pares if p[2] is not None]
    pares_sem_peso = [p for p in pares if p[2] is None]
    pares_ordenados = sorted(pares_com_peso, key=lambda x: x[2]) + pares_sem_peso

    reader_etiquetas = PdfReader(io.BytesIO(pdf_etiquetas_bytes))
    reader_danfes = PdfReader(io.BytesIO(pdf_danfes_bytes))
    writer = PdfWriter()

    for idx_etiqueta, idx_danfe, peso in pares_ordenados:
        writer.add_page(reader_etiquetas.pages[idx_etiqueta])
        writer.add_page(reader_danfes.pages[idx_danfe])

    for idx in etiquetas_sem_danfe:
        writer.add_page(reader_etiquetas.pages[idx])

    for idx in danfe_sem_etiqueta:
        writer.add_page(reader_danfes.pages[idx])

    output_stream = io.BytesIO()
    writer.write(output_stream)

    st.success("📄 Arquivo gerado com sucesso!")
    st.download_button(
        label="📥 Baixar Etiquetas + DANFEs Ordenadas",
        data=output_stream.getvalue(),
        file_name="Etiquetas_DANFEs_Combinadas_Por_Peso_FINAL.pdf",
        mime="application/pdf"
    )

    st.info(f"✅ Total de etiquetas casadas com DANFE: {len(pares)}")
    st.info(f"🚚 Total de etiquetas sem DANFE: {len(etiquetas_sem_danfe)}")
    st.info(f"📄 Total de DANFEs sem etiqueta: {len(danfe_sem_etiqueta)}")
    st.info(f"⚖️ Total de etiquetas com peso: {sum(1 for _,peso in mapa_etiquetas.values() if peso is not None)}")
    st.info(f"⚖️ Total de etiquetas sem peso: {sum(1 for _,peso in mapa_etiquetas.values() if peso is None)}")
