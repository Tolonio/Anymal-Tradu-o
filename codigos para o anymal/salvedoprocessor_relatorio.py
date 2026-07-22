import xml.etree.ElementTree as ET
import lxml.etree as lxml_ET
from deep_translator import GoogleTranslator
from weasyprint import HTML, CSS
import os
import io
import json
import zipfile
import re
import unicodedata
import pathlib
from datetime import datetime, timedelta

# ==============================================================================
# CONFIGURAÇÕES E ESTADO GLOBAL (Para a barra de progresso do Flask)
# ==============================================================================
PASTA_REMOTA = "/home/integration/.ros/reports"
ARQUIVO_CACHE = 'cache_traducoes.json'

status_progresso = {"porcentagem": 0, "mensagem": "Aguardando..."}

def atualizar_progresso(pct, msg):
    status_progresso["porcentagem"] = pct
    status_progresso["mensagem"] = msg

# ==============================================================================
# 0. CONFIGURAÇÃO DA PERSISTÊNCIA DE DADOS (Do seu código original)
# ==============================================================================
def carregar_cache():
    if os.path.exists(ARQUIVO_CACHE):
        try:
            with open(ARQUIVO_CACHE, 'r', encoding='utf-8') as f: return json.load(f)
        except Exception: pass
    return {}

def salvar_cache(cache_dados):
    with open(ARQUIVO_CACHE, 'w', encoding='utf-8') as f:
        json.dump(cache_dados, f, ensure_ascii=False, indent=4)

# ==============================================================================
# 1. DICIONÁRIO FIXO E UTILITÁRIOS (Do seu código original)
# ==============================================================================
dicionario_anymal = {
    "Started mission": "Iniciou a missão", "Paused mission": "Missão pausada",
    "Resumed mission": "Missão retomada", "Navigating to": "Navegando para",
    "Successfully navigated to": "Navegou com sucesso para", "Failed to navigate to": "Falha ao navegar para",
    "The action goal failed during execution.": "A meta de ação falhou durante a execução.",
    "Inspecting": "Inspecionando", "from here": "daqui",
    "Successfully took image of": "Capturada imagem com sucesso de",
    "Successfully analyzed temperature of": "Temperatura analisada com sucesso de",
    "Successfully executed mission": "Missão executada com sucesso",
    "Failed to execute mission": "Falha ao executar a missão",
    "No valid battery state message received.": "Nenhuma mensagem válida de estado da bateria recebida.",
    "is above the threshold of": "está acima do limite de",
    "SwitchOperational Mode: Failed to connect to the Operational Mode Manager.": "Falha ao conectar ao Gerenciador de Modo Operacional.",
    "Performing Switch Operational Mode Dock failed": "Falha ao realizar o acoplamento do Modo Operacional."
}

def converter_fuso_horario(hora_utc):
    if not hora_utc: return ""
    try:
        tempo = datetime.strptime(hora_utc, "%H:%M:%S")
        tempo_brasilia = tempo - timedelta(hours=3)
        return tempo_brasilia.strftime("%H:%M:%S")
    except ValueError:
        return hora_utc

def sanitizar_nome(nome):
    """Garante que o nome da foto não tenha caracteres inválidos"""
    nome = nome.replace("'", "").replace('"', '')
    nome = unicodedata.normalize('NFKD', nome).encode('ASCII', 'ignore').decode('ASCII')
    nome = re.sub(r'[^\w\s-]', '', nome).strip()
    return re.sub(r'[-\s]+', '_', nome)

def normalizar_caminho(caminho):
    """Remove o './' da frente dos caminhos se existir"""
    c = caminho.replace('\\', '/')
    return c[2:] if c.startswith('./') else c

def listar_diretorio_nativo(caminho):
    itens = []
    if not os.path.exists(caminho): return None
    for nome in os.listdir(caminho):
        if not nome.startswith('.'):
            caminho_abs = os.path.join(caminho, nome)
            itens.append({'nome': nome, 'is_dir': os.path.isdir(caminho_abs), 'caminho_absoluto': caminho_abs})
    itens.sort(key=lambda x: (not x['is_dir'], x['nome'].lower()))
    return itens

# ==============================================================================
# 2. MOTOR DE TRADUÇÃO INTELIGENTE (Do seu código original)
# ==============================================================================
def traduzir_mensagem(texto_original, tradutor_api, memoria_json):
    if not texto_original: return ""
    texto_traduzido = texto_original
    modificado = False
    
    for en, pt in dicionario_anymal.items():
        if en in texto_traduzido:
            texto_traduzido = texto_traduzido.replace(en, pt)
            modificado = True
            
    if modificado: return texto_traduzido
    if texto_original in memoria_json: return memoria_json[texto_original]
    
    try:
        traducao_api = tradutor_api.translate(texto_original)
        memoria_json[texto_original] = traducao_api
        salvar_cache(memoria_json)
        return traducao_api
    except Exception: return texto_original

# ==============================================================================
# 3. MOTOR PRINCIPAL: PDF + ZIP NATIVO (Baseado no seu fluxo seguro)
# ==============================================================================
def gerar_relatorio_nativo(caminho_missao):
    atualizar_progresso(10, "Lendo ficheiros da missão...")
    tradutor = GoogleTranslator(source='en', target='pt')
    memoria_json = carregar_cache()
    
    caminho_xml = os.path.join(caminho_missao, 'report.xml')
    caminho_xsl = os.path.join(caminho_missao, 'stylesheet.xsl')
    
    if not os.path.exists(caminho_xsl): caminho_xsl = os.path.join(PASTA_REMOTA, 'stylesheet.xsl')
    if not os.path.exists(caminho_xml): raise Exception(f"report.xml não encontrado na pasta: {caminho_missao}")

    # --- ETAPA A: TRATAMENTO DE DADOS E TRADUÇÃO ---
    atualizar_progresso(25, "Extraindo e traduzindo dados...")
    tree = ET.parse(caminho_xml)
    root = tree.getroot()
    
    for tag in ['name', 'location']:
        elemento = root.find(tag)
        if elemento is not None and elemento.text:
            try: elemento.text = tradutor.translate(elemento.text)
            except Exception: pass
                
    tag_data = root.find('date')
    if tag_data is not None and tag_data.text:
        data_original = tag_data.text.strip()
        try:
            if '/' in data_original: tag_data.text = datetime.strptime(data_original, '%Y/%m/%d').strftime('%d/%m/%Y')
            elif '-' in data_original: tag_data.text = datetime.strptime(data_original, '%Y-%m-%d').strftime('%d/%m/%Y')
        except Exception: pass 
            
    entradas_brutas = root.findall('entry')
    entradas_validas = []
    
    for entry in entradas_brutas:
        level = entry.find('level')
        if level is not None and level.text and level.text.strip().upper() == 'WARN':
            root.remove(entry)
        else:
            entradas_validas.append(entry)
            
    total_entradas = len(entradas_validas)
    mapa_renomeio = {}
    contador_imagens = 1
    
    for i, entry in enumerate(entradas_validas):
        msg = entry.find('message')
        texto_msg = ""
        if msg is not None and msg.text:
            texto_msg = traduzir_mensagem(msg.text, tradutor, memoria_json)
            msg.text = texto_msg
            
        tag_time = entry.find('time_of_day')
        texto_hora = f"Evento_{i}"
        if tag_time is not None and tag_time.text:
            tag_time.text = converter_fuso_horario(tag_time.text)
            texto_hora = tag_time.text.replace(':', '-')
            
        tag_time_alt = entry.find('time')
        if tag_time_alt is not None and tag_time_alt.text:
            tag_time_alt.text = converter_fuso_horario(tag_time_alt.text)
            texto_hora = tag_time_alt.text.replace(':', '-')
            
        # Preparação do novo nome da foto (mas sem quebrar o XML ainda)
        file_node = entry.find('file')
        if file_node is not None and file_node.text:
            caminho_antigo = file_node.text.strip()
            if caminho_antigo.lower().endswith(('.png', '.jpg', '.jpeg')):
                nome_base = f"Inspecao_Local_{contador_imagens}"
                if "Capturada imagem com sucesso de" in texto_msg:
                    nome_base = texto_msg.split(" de ")[-1].strip()
                elif "Temperatura analisada com sucesso de" in texto_msg:
                    nome_base = "Termica_" + texto_msg.split(" de ")[-1].strip()
                elif "Inspecionando" in texto_msg:
                    nome_base = texto_msg.split("Inspecionando")[-1].split("daqui")[0].strip()
                    
                nome_seguro = sanitizar_nome(nome_base)
                extensao = os.path.splitext(caminho_antigo)[1]
                novo_nome = f"{nome_seguro}_{texto_hora}{extensao}"
                
                pasta_original = os.path.dirname(normalizar_caminho(caminho_antigo))
                novo_caminho_zip = f"{pasta_original}/{novo_nome}" if pasta_original else novo_nome
                
                mapa_renomeio[normalizar_caminho(caminho_antigo)] = novo_caminho_zip
                contador_imagens += 1
                
        atualizar_progresso(30 + int((i/total_entradas)*30), f"Processando evento {i+1}/{total_entradas}...")

    # --- ETAPA B: PREPARAÇÃO DO VISUAL E GERAÇÃO DO PDF (Idêntico ao original) ---
    atualizar_progresso(65, "Preparando o design e montando o PDF final...")
    xml_str = ET.tostring(root, encoding='utf-8').decode('utf-8')
    
    with open(caminho_xsl, 'r', encoding='utf-8') as file:
        xsl_str = file.read()
    
    dic_xsl = {
        "font-family: Impact, Charcoal, sans-serif;": "font-family: Arial, Helvetica, sans-serif;",
        "<title>Mission Report</title>": "<title>Relatório de Missão</title>",
        "MISSION REPORT": "RELATÓRIO DE MISSÃO",
        "<th>Level</th>": "<th>Nível</th>", "<th>Time</th>": "<th>Hora</th>",
        "<th>Event</th>": "<th>Evento</th>", "<th>Value</th>": "<th>Valor</th>",
        "<th>Status</th>": "<th>Situação</th>", "<th>File</th>": "<th>Arquivo</th>",
        "<th>Author</th>": "<th>Autor</th>", "<th>Message</th>": "<th>Mensagem</th>",
        "UTC Time": "Horário de Brasília", "Location:": "Local:", "Date:": "Data:", "Robot:": "Robô:"
    }
    for en, pt in dic_xsl.items(): xsl_str = xsl_str.replace(en, pt)
        
    # Transforma os textos em objetos LXML para fusão
    xml_lxml = lxml_ET.fromstring(xml_str.encode('utf-8'))
    xsl_lxml = lxml_ET.fromstring(xsl_str.encode('utf-8'))
    
    transform = lxml_ET.XSLT(xsl_lxml)
    html_result = transform(xml_lxml)
    html_content = str(html_result)
    
    # A base do Weasyprint é fundamental para as fotos carregarem no PDF!
    url_base = pathlib.Path(caminho_missao).absolute().as_uri() + "/"
    pdf_memoria = io.BytesIO()
    
    # CSS idêntico ao original, apenas com limite para a imagem não quebrar a tabela
    CSS_PAGINA = CSS(string='@page { size: A4 landscape; margin: 1cm; } img { max-width: 100%; height: auto; max-height: 300px; }')
    HTML(string=html_content, base_url=url_base).write_pdf(pdf_memoria, stylesheets=[CSS_PAGINA])

    # --- ETAPA C: ATUALIZA O XML COM OS NOVOS NOMES PARA O HTML INTERATIVO ---
    atualizar_progresso(85, "Empacotando relatório e fotografias finais...")
    for entry in root.findall('entry'):
        file_node = entry.find('file')
        if file_node is not None and file_node.text:
            caminho_norm = normalizar_caminho(file_node.text.strip())
            if caminho_norm in mapa_renomeio: file_node.text = mapa_renomeio[caminho_norm]

    xml_para_html = ET.tostring(root, encoding='utf-8').decode('utf-8')
    html_content_zip = str(lxml_ET.XSLT(xsl_lxml)(lxml_ET.fromstring(xml_para_html.encode('utf-8'))))
    
    # --- ETAPA D: CRIA O ZIP EM MEMÓRIA ---
    zip_memoria = io.BytesIO()
    with zipfile.ZipFile(zip_memoria, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.writestr("Relatorio_Traduzido_PT.pdf", pdf_memoria.getvalue())
        zipf.writestr("Relatorio_Interativo_PT.html", html_content_zip)
        zipf.writestr("stylesheet.xsl", xsl_str)
        
        for root_dir, dirs, files in os.walk(caminho_missao):
            for file in files:
                if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                    caminho_absoluto = os.path.join(root_dir, file)
                    caminho_relativo = normalizar_caminho(os.path.relpath(caminho_absoluto, caminho_missao))
                    zipf.write(caminho_absoluto, mapa_renomeio.get(caminho_relativo, caminho_relativo))

    atualizar_progresso(100, "Concluído! A enviar transferência...")
    zip_memoria.seek(0)
    return zip_memoria