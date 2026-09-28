import os
import sqlite3
import smtplib
import urllib.request
import json
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__, static_folder='.', static_url_path='')

DB_FILE = os.environ.get("DB_FILE", "estoque_hotel.db")
EMAIL_DESTINO = os.environ.get("EMAIL_DESTINO", "mwfreitas@gmail.com")

# Credenciais SMTP opcionais (ex: Gmail App Password ou Brevo / SendGrid / Mailgun)
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")

HOTEIS_DISPONIVEIS = ["Hit Hotel", "Porto Salvador", "Ancoras"]

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

# Lista oficial de produtos
NOVOS_PRODUTOS = [
    # Bebidas
    ("BEB-01", "Freezer Bebidas", "Cerveja Amstel 350ml", 24, 0, "lata"),
    ("BEB-02", "Freezer Bebidas", "Cerveja Heineken 350ml", 24, 0, "lata"),
    ("BEB-03", "Freezer Bebidas", "Cerveja Heineken zero 350ml", 12, 0, "lata"),
    ("BEB-04", "Freezer Bebidas", "Cerveja Corona Extra 350ml", 18, 0, "lata"),
    ("BEB-05", "Freezer Bebidas", "Energético Red Bull Energy", 16, 0, "lata"),
    ("BEB-06", "Freezer Bebidas", "Proteína Emana Protein cacau", 10, 0, "un"),
    ("BEB-07", "Freezer Bebidas", "Refrigerante Guaraná Antártica 350ml", 20, 0, "lata"),
    ("BEB-08", "Freezer Bebidas", "Refrigerante Guaraná Antártica Zero 350ml", 16, 0, "lata"),
    ("BEB-09", "Freezer Bebidas", "Água Tônica 350ml", 12, 0, "lata"),
    ("BEB-10", "Freezer Bebidas", "Schewpps 350ml", 12, 0, "lata"),
    ("BEB-11", "Freezer Bebidas", "Refrigerante Coca-Cola Original 350ml", 30, 0, "lata"),
    ("BEB-12", "Freezer Bebidas", "Refrigerante Coca-Cola Zero 350ml", 24, 0, "lata"),
    ("BEB-13", "Freezer Bebidas", "Refrigerante Sprite Zero 350ml", 12, 0, "lata"),
    ("BEB-14", "Freezer Bebidas", "Refrigerante Sprite Normal 350ml", 12, 0, "lata"),
    ("BEB-15", "Freezer Bebidas", "Agua sem gás 500ml", 36, 0, "garrafa"),
    ("BEB-16", "Freezer Bebidas", "Agua com gás 500 ml", 24, 0, "garrafa"),
    ("BEB-17", "Freezer Bebidas", "Agua de coco 500ml", 15, 0, "garrafa"),
    ("BEB-18", "Freezer Bebidas", "Suco de Laranja 500ml", 10, 0, "garrafa"),
    ("BEB-19", "Freezer Bebidas", "Suco de Laranja 200ml", 12, 0, "un"),
    ("BEB-20", "Freezer Bebidas", "Achocolatado Betânia Kids", 15, 0, "un"),
    ("BEB-21", "Freezer Bebidas", "Agua de 1.5L", 12, 0, "garrafa"),
    # Picolés e Sorvetes
    ("SOR-01", "Freezer Picolés e Sorvetes", "Sorvete Cheesecake de Morango 150ml", 10, 0, "pote"),
    ("SOR-02", "Freezer Picolés e Sorvetes", "Sorvete pistache 150ml", 10, 0, "pote"),
    ("SOR-03", "Freezer Picolés e Sorvetes", "Sorvete doce de leite 150ml", 10, 0, "pote"),
    ("SOR-04", "Freezer Picolés e Sorvetes", "Picole pistache", 15, 0, "un"),
    ("SOR-05", "Freezer Picolés e Sorvetes", "Picole leite com creme de avelã", 15, 0, "un"),
    ("SOR-06", "Freezer Picolés e Sorvetes", "Picole Clássico", 20, 0, "un"),
    ("SOR-07", "Freezer Picolés e Sorvetes", "Picole chocomaltine", 15, 0, "un"),
    ("SOR-08", "Freezer Picolés e Sorvetes", "Picole doce de leite", 15, 0, "un"),
    ("SOR-09", "Freezer Picolés e Sorvetes", "Picole morango com leite condensado", 18, 0, "un"),
    ("SOR-10", "Freezer Picolés e Sorvetes", "Picole Mousse de Maracujá", 15, 0, "un"),
    ("SOR-11", "Freezer Picolés e Sorvetes", "Picole morango", 20, 0, "un"),
    ("SOR-12", "Freezer Picolés e Sorvetes", "Picole Paçoca", 15, 0, "un"),
    ("SOR-13", "Freezer Picolés e Sorvetes", "Picole Torta de limão", 15, 0, "un"),
    ("SOR-14", "Freezer Picolés e Sorvetes", "Picole coco", 20, 0, "un"),
    ("SOR-15", "Freezer Picolés e Sorvetes", "Picole Açaí", 15, 0, "un"),
    ("SOR-16", "Freezer Picolés e Sorvetes", "Picole Cookies'n Cream", 15, 0, "un"),
    ("SOR-17", "Freezer Picolés e Sorvetes", "Picole chocolate belga", 15, 0, "un"),
    ("SOR-18", "Freezer Picolés e Sorvetes", "Picole chocolate zero açúcar", 15, 0, "un")
]

def inicializar_banco():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS produtos (
            id TEXT,
            hotel TEXT,
            categoria TEXT,
            nome TEXT,
            estoque_minimo INTEGER,
            estoque_atual INTEGER,
            unidade TEXT,
            ultima_atualizacao TEXT,
            PRIMARY KEY (id, hotel)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conferencias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hotel TEXT,
            data_hora TEXT,
            data_dia TEXT,
            conferente TEXT,
            total_itens INTEGER,
            total_alertas INTEGER
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS historico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conferencia_id INTEGER,
            hotel TEXT,
            data_hora TEXT,
            data_dia TEXT,
            conferente TEXT,
            produto_id TEXT,
            produto_nome TEXT,
            categoria TEXT,
            quantidade INTEGER,
            quantidade_anterior INTEGER,
            minimo INTEGER,
            status TEXT
        )
    """)

    # Popula o catálogo de cada hotel de forma isolada
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
    for hotel in HOTEIS_DISPONIVEIS:
        cursor.execute("SELECT COUNT(*) FROM produtos WHERE hotel = ?", (hotel,))
        qtd = cursor.fetchone()[0]
        if qtd == 0:
            for it in NOVOS_PRODUTOS:
                cursor.execute("""
                    INSERT OR REPLACE INTO produtos (id, hotel, categoria, nome, estoque_minimo, estoque_atual, unidade, ultima_atualizacao)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (it[0], hotel, it[1], it[2], it[3], it[4], it[5], agora))

    conn.commit()
    conn.close()

inicializar_banco()

# --- DISPARO DE EMAIL ROBUSTO ---
def gerar_html_email(hotel, conferente, agora, itens_conferidos, itens_alerta):
    linhas_alerta_html = ""
    if itens_alerta:
        linhas_alerta_html = f"""
        <div style="background:#fff1f2;border:1px solid #fecdd3;border-radius:8px;padding:14px;margin-bottom:20px;">
            <h3 style="color:#b91c1c;margin:0 0 10px 0;">⚠️ ITENS QUE ATINGIRAM ESTOQUE MÍNIMO - COMPRA SUGERIDA</h3>
            <table style="width:100%;border-collapse:collapse;font-family:sans-serif;font-size:13px;background:white;">
                <thead>
                    <tr style="background:#dc2626;color:white;">
                        <th style="padding:8px;border:1px solid #e5e7eb;text-align:left;">Freezer</th>
                        <th style="padding:8px;border:1px solid #e5e7eb;text-align:left;">Item</th>
                        <th style="padding:8px;border:1px solid #e5e7eb;text-align:center;">Estoque Atual</th>
                        <th style="padding:8px;border:1px solid #e5e7eb;text-align:center;">Mínimo</th>
                        <th style="padding:8px;border:1px solid #e5e7eb;text-align:center;background:#991b1b;">Comprar</th>
                    </tr>
                </thead>
                <tbody>
        """
        for it in itens_alerta:
            linhas_alerta_html += f"""
                <tr>
                    <td style="padding:6px 8px;border:1px solid #e5e7eb;">{it['categoria']}</td>
                    <td style="padding:6px 8px;border:1px solid #e5e7eb;"><strong>{it['nome']}</strong></td>
                    <td style="padding:6px 8px;border:1px solid #e5e7eb;text-align:center;color:#dc2626;font-weight:bold;">{it['atual']} {it['unidade']}</td>
                    <td style="padding:6px 8px;border:1px solid #e5e7eb;text-align:center;">{it['minimo']} {it['unidade']}</td>
                    <td style="padding:6px 8px;border:1px solid #e5e7eb;text-align:center;color:#2563eb;font-weight:bold;">+{it['sugestao']} {it['unidade']}</td>
                </tr>
            """
        linhas_alerta_html += "</tbody></table></div>"

    tabela_geral_html = f"""
    <h3 style="color:#1e293b;margin:15px 0 8px 0;">📋 CONTAGEM COMPLETA - {hotel}</h3>
    <table style="width:100%;border-collapse:collapse;font-family:sans-serif;font-size:13px;background:white;">
        <thead>
            <tr style="background:#334155;color:white;">
                <th style="padding:8px;border:1px solid #cbd5e1;text-align:left;">Freezer</th>
                <th style="padding:8px;border:1px solid #cbd5e1;text-align:left;">Item</th>
                <th style="padding:8px;border:1px solid #cbd5e1;text-align:center;">Contado</th>
                <th style="padding:8px;border:1px solid #cbd5e1;text-align:center;">Mínimo</th>
                <th style="padding:8px;border:1px solid #cbd5e1;text-align:center;">Status</th>
            </tr>
        </thead>
        <tbody>
    """
    for it in itens_conferidos:
        cor_status = "#dc2626" if it['precisa_comprar'] else "#16a34a"
        tabela_geral_html += f"""
            <tr>
                <td style="padding:6px 8px;border:1px solid #cbd5e1;">{it['categoria']}</td>
                <td style="padding:6px 8px;border:1px solid #cbd5e1;">{it['nome']}</td>
                <td style="padding:6px 8px;border:1px solid #cbd5e1;text-align:center;font-weight:bold;">{it['atual']} {it['unidade']}</td>
                <td style="padding:6px 8px;border:1px solid #cbd5e1;text-align:center;">{it['minimo']} {it['unidade']}</td>
                <td style="padding:6px 8px;border:1px solid #cbd5e1;text-align:center;color:{cor_status};font-weight:bold;">{it['status']}</td>
            </tr>
        """
    tabela_geral_html += "</tbody></table>"

    return f"""
    <div style="font-family:Arial,sans-serif;max-width:720px;margin:0 auto;padding:20px;border:1px solid #e2e8f0;border-radius:10px;background:#f8fafc;">
        <div style="background:#1a73e8;color:white;padding:14px;border-radius:8px;margin-bottom:15px;">
            <h2 style="margin:0;font-size:1.3rem;">🏨 {hotel} - Relatório de Conferência de Estoque</h2>
        </div>
        <p style="font-size:14px;color:#475569;margin-bottom:15px;">
            Data/Hora: <strong>{agora}</strong><br>
            Conferente responsável: <strong>{conferente}</strong><br>
            Unidade: <strong>{hotel}</strong>
        </p>
        {linhas_alerta_html}
        {tabela_geral_html}
        <p style="font-size:12px;color:#94a3b8;margin-top:25px;text-align:center;">
            Sistema de Gestão de Estoque dos Freezers do Hotel
        </p>
    </div>
    """

def enviar_email_conferencia(hotel, conferente, agora, itens_conferidos, itens_alerta):
    """Envia o e-mail via múltiplos métodos resilientes (SMTP, Resend ou Formspree)"""
    subject = f"🏨 [{hotel}] Conferência de Freezers ({agora}) {'[ALERTA DE COMPRAS]' if itens_alerta else ''}"
    html_body = gerar_html_email(hotel, conferente, agora, itens_conferidos, itens_alerta)
    email_enviado = False
    detalhes_erro = ""

    # Método 1: Se SMTP configurado (Gmail, Brevo, SendGrid, etc.)
    if SMTP_USER and SMTP_PASS:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"Hotel Estoque <{SMTP_USER}>"
            msg["To"] = EMAIL_DESTINO
            msg.attach(MIMEText(html_body, "html"))

            if SMTP_PORT == 465:
                server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=10)
            else:
                server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10)
                server.starttls()
            
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, [EMAIL_DESTINO], msg.as_string())
            server.quit()
            email_enviado = True
            print("E-mail enviado com sucesso via SMTP!")
        except Exception as e:
            detalhes_erro = f"SMTP falhou: {e}"
            print(detalhes_erro)

    # Método 2: Resend API
    if not email_enviado and RESEND_API_KEY:
        try:
            req_data = json.dumps({
                "from": f"{hotel} <onboarding@resend.dev>",
                "to": [EMAIL_DESTINO],
                "subject": subject,
                "html": html_body
            }).encode('utf-8')
            req = urllib.request.Request(
                "https://api.resend.com/emails",
                data=req_data,
                headers={"Authorization": f"Bearer {RESEND_API_KEY}", "Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status in (200, 201):
                    email_enviado = True
                    print("E-mail enviado via Resend!")
        except Exception as e:
            detalhes_erro += f" | Resend falhou: {e}"
            print(f"Erro Resend: {e}")

    # Método 3: Webhook Formspree com e-mail direto do cliente
    if not email_enviado:
        try:
            req_data = json.dumps({
                "email": EMAIL_DESTINO,
                "_replyto": EMAIL_DESTINO,
                "subject": subject,
                "hotel": hotel,
                "conferente": conferente,
                "data_hora": agora,
                "total_itens": len(itens_conferidos),
                "total_alertas": len(itens_alerta),
                "resumo_alertas": ", ".join([f"{it['nome']} (Faltam {it['sugestao']} {it['unidade']})" for it in itens_alerta]) if itens_alerta else "Nenhum item abaixo do mínimo",
                "relatorio_html": html_body
            }).encode('utf-8')
            
            # Usando endpoint com o e-mail direto
            req = urllib.request.Request(
                f"https://formspree.io/{EMAIL_DESTINO}",
                data=req_data,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                email_enviado = True
                print("E-mail despachado via Formspree direto!")
        except Exception as e:
            detalhes_erro += f" | Formspree falhou: {e}"
            print(f"Erro Formspree: {e}")

    return email_enviado, detalhes_erro

# --- ROTAS PRINCIPAIS ---

@app.route("/")
def index():
    return send_from_directory('.', 'app.html')

@app.route("/api/hoteis")
def listar_hoteis():
    return jsonify(HOTEIS_DISPONIVEIS)

@app.route("/api/config-email")
def obter_config_email():
    """Retorna o status do e-mail para exibir na interface"""
    tem_smtp = bool(SMTP_USER and SMTP_PASS)
    tem_resend = bool(RESEND_API_KEY)
    return jsonify({
        "emailDestino": EMAIL_DESTINO,
        "temSmtp": tem_smtp,
        "temResend": tem_resend,
        "smtpUser": SMTP_USER if tem_smtp else ""
    })

@app.route("/api/produtos")
def listar_produtos():
    hotel = request.args.get("hotel", "Hit Hotel")
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, hotel, categoria, nome, estoque_minimo, estoque_atual, unidade, ultima_atualizacao FROM produtos WHERE hotel = ? ORDER BY categoria, nome", (hotel,))
    linhas = cursor.fetchall()
    conn.close()
    
    produtos = [{
        "id": l["id"],
        "hotel": l["hotel"],
        "categoria": l["categoria"],
        "nome": l["nome"],
        "estoqueMinimo": l["estoque_minimo"],
        "estoqueAtual": l["estoque_atual"],
        "unidade": l["unidade"],
        "ultimaAtualizacao": l["ultima_atualizacao"]
    } for l in linhas]
    
    return jsonify(produtos)

@app.route("/api/produtos/adicionar", methods=["POST"])
def adicionar_produto():
    dados = request.get_json(force=True)
    hotel = dados.get("hotel", "Hit Hotel")
    nome = dados.get("nome", "").strip()
    categoria = dados.get("categoria", "Freezer Bebidas")
    minimo = int(dados.get("estoqueMinimo", 10))
    unidade = dados.get("unidade", "un").strip()
    
    if not nome:
        return jsonify({"sucesso": False, "mensagem": "Nome do item é obrigatório"}), 400

    conn = get_db()
    cursor = conn.cursor()
    
    prefix = "BEB" if "Bebidas" in categoria else "SOR"
    cursor.execute("SELECT COUNT(*) FROM produtos WHERE hotel = ? AND categoria = ?", (hotel, categoria))
    prox_num = cursor.fetchone()[0] + 1
    novo_id = f"{prefix}-{prox_num:02d}-{int(datetime.now().timestamp())%10000}"
    
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
    cursor.execute("""
        INSERT INTO produtos (id, hotel, categoria, nome, estoque_minimo, estoque_atual, unidade, ultima_atualizacao)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (novo_id, hotel, categoria, nome, minimo, 0, unidade, agora))
    conn.commit()
    conn.close()
    
    return jsonify({"sucesso": True, "mensagem": f"Produto adicionado ao {hotel} com sucesso!", "id": novo_id})

@app.route("/api/produtos/editar", methods=["POST"])
def editar_produto():
    dados = request.get_json(force=True)
    hotel = dados.get("hotel", "Hit Hotel")
    p_id = dados.get("id")
    nome = dados.get("nome", "").strip()
    minimo = int(dados.get("estoqueMinimo", 10))
    unidade = dados.get("unidade", "un").strip()
    
    if not p_id or not nome:
        return jsonify({"sucesso": False, "mensagem": "Dados inválidos"}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE produtos SET nome = ?, estoque_minimo = ?, unidade = ? WHERE id = ? AND hotel = ?
    """, (nome, minimo, unidade, p_id, hotel))
    conn.commit()
    conn.close()
    
    return jsonify({"sucesso": True, "mensagem": f"Produto atualizado no {hotel} com sucesso!"})

@app.route("/api/produtos/excluir", methods=["POST"])
def excluir_produto():
    dados = request.get_json(force=True)
    hotel = dados.get("hotel", "Hit Hotel")
    p_id = dados.get("id")
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM historico WHERE produto_id = ? AND hotel = ?", (p_id, hotel))
    total_movimentacoes = cursor.fetchone()[0]
    
    if total_movimentacoes > 0:
        conn.close()
        return jsonify({
            "sucesso": False, 
            "mensagem": f"Este produto já possui {total_movimentacoes} movimentação(ões) no {hotel} e não pode ser excluído por segurança contábil."
        }), 400
        
    cursor.execute("DELETE FROM produtos WHERE id = ? AND hotel = ?", (p_id, hotel))
    conn.commit()
    conn.close()
    
    return jsonify({"sucesso": True, "mensagem": f"Produto excluído do {hotel} com sucesso!"})

@app.route("/api/salvar", methods=["POST"])
def salvar_conferencia():
    dados = request.get_json(force=True)
    hotel = dados.get("hotel", "Hit Hotel")
    conferente = dados.get("conferente", "Não identificado").strip()
    itens = dados.get("itens", [])
    agora_dt = datetime.now()
    agora = agora_dt.strftime("%d/%m/%Y %H:%M")
    data_dia = agora_dt.strftime("%Y-%m-%d")
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO conferencias (hotel, data_hora, data_dia, conferente, total_itens, total_alertas)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (hotel, agora, data_dia, conferente, len(itens), 0))
    conf_id = cursor.lastrowid
    
    itens_alerta = []
    itens_conferidos = []
    
    for it in itens:
        p_id = it.get("id")
        qtd = int(it.get("quantidade", 0))
        
        cursor.execute("SELECT categoria, nome, estoque_minimo, estoque_atual, unidade FROM produtos WHERE id = ? AND hotel = ?", (p_id, hotel))
        row = cursor.fetchone()
        if row:
            cat = row["categoria"]
            nome = row["nome"]
            min_estq = row["estoque_minimo"]
            qtd_anterior = row["estoque_atual"]
            unidade = row["unidade"]
            
            cursor.execute("UPDATE produtos SET estoque_atual = ?, ultima_atualizacao = ? WHERE id = ? AND hotel = ?", (qtd, agora, p_id, hotel))
            
            precisa_comprar = qtd <= min_estq
            status = f"ALERTA: Repor (+{min_estq - qtd} {unidade})" if precisa_comprar else "OK"
            
            item_info = {
                "id": p_id,
                "categoria": cat,
                "nome": nome,
                "atual": qtd,
                "anterior": qtd_anterior,
                "minimo": min_estq,
                "unidade": unidade,
                "precisa_comprar": precisa_comprar,
                "status": status
            }
            itens_conferidos.append(item_info)
            
            if precisa_comprar:
                faltante = min_estq - qtd
                item_info["sugestao"] = faltante if faltante > 0 else 0
                itens_alerta.append(item_info)
            
            cursor.execute("""
                INSERT INTO historico (conferencia_id, hotel, data_hora, data_dia, conferente, produto_id, produto_nome, categoria, quantidade, quantidade_anterior, minimo, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (conf_id, hotel, agora, data_dia, conferente, p_id, nome, cat, qtd, qtd_anterior, min_estq, status))
    
    cursor.execute("UPDATE conferencias SET total_alertas = ? WHERE id = ?", (len(itens_alerta), conf_id))
    conn.commit()
    conn.close()
    
    # Enviar e-mail
    email_enviado, erro_msg = enviar_email_conferencia(hotel, conferente, agora, itens_conferidos, itens_alerta)
    
    # Gerar também os dados prontos para visualização e PDF imediato
    return jsonify({
        "sucesso": True,
        "mensagem": f"Conferência do {hotel} registrada com sucesso!",
        "itensAlerta": len(itens_alerta),
        "emailEnviado": email_enviado,
        "emailDestino": EMAIL_DESTINO,
        "detalhesEmail": erro_msg,
        "dadosPdf": {
            "hotel": hotel,
            "conferente": conferente,
            "dataHora": agora,
            "totalItens": len(itens_conferidos),
            "totalAlertas": len(itens_alerta),
            "itensAlerta": itens_alerta,
            "itens": itens_conferidos
        }
    })

# --- RELATÓRIOS DO HOTEL ---

@app.route("/api/relatorios/estoque-atual")
def relatorio_estoque_atual():
    hotel = request.args.get("hotel", "Hit Hotel")
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, hotel, categoria, nome, estoque_minimo, estoque_atual, unidade, ultima_atualizacao,
        CASE WHEN estoque_atual <= estoque_minimo THEN 1 ELSE 0 END as precisa_comprar,
        CASE WHEN estoque_minimo > estoque_atual THEN estoque_minimo - estoque_atual ELSE 0 END as sugestao_compra
        FROM produtos
        WHERE hotel = ?
        ORDER BY categoria, nome
    """, (hotel,))
    rows = cursor.fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/relatorios/conferencias-dia")
def relatorio_conferencias():
    hotel = request.args.get("hotel", "Hit Hotel")
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, hotel, data_hora, data_dia, conferente, total_itens, total_alertas FROM conferencias WHERE hotel = ? ORDER BY id DESC LIMIT 60", (hotel,))
    rows = cursor.fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/relatorios/comparativo-dias")
def relatorio_comparativo_dias():
    hotel = request.args.get("hotel", "Hit Hotel")
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT data_dia FROM historico WHERE hotel = ? ORDER BY data_dia DESC LIMIT 2", (hotel,))
    dias = [r[0] for r in cursor.fetchall()]
    
    if len(dias) < 2:
        conn.close()
        return jsonify({
            "disponivel": False, 
            "mensagem": f"O {hotel} precisa ter pelo menos 2 conferências em dias distintos para gerar o comparativo de vendas diárias."
        })
        
    dia_recente, dia_anterior = dias[0], dias[1]
    
    query = """
        SELECT 
            h1.produto_nome, h1.categoria,
            h2.quantidade as qtd_anterior,
            h1.quantidade as qtd_atual,
            (h2.quantidade - h1.quantidade) as consumo_estimado,
            h1.minimo
        FROM historico h1
        JOIN historico h2 ON h1.produto_id = h2.produto_id AND h2.data_dia = ? AND h2.hotel = ?
        WHERE h1.data_dia = ? AND h1.hotel = ?
        GROUP BY h1.produto_id
        ORDER BY h1.categoria, h1.produto_nome
    """
    cursor.execute(query, (dia_anterior, hotel, dia_recente, hotel))
    rows = cursor.fetchall()
    conn.close()
    
    comparativo = []
    total_saidas = 0
    for r in rows:
        consumo = r["consumo_estimado"] if r["consumo_estimado"] > 0 else 0
        total_saidas += consumo
        comparativo.append({
            "produto": r["produto_nome"],
            "categoria": r["categoria"],
            "qtdAnterior": r["qtd_anterior"],
            "qtdAtual": r["qtd_atual"],
            "consumoVendas": consumo,
            "minimo": r["minimo"]
        })
        
    return jsonify({
        "disponivel": True,
        "hotel": hotel,
        "diaRecente": dia_recente,
        "diaAnterior": dia_anterior,
        "totalSaidas": total_saidas,
        "itens": comparativo
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
