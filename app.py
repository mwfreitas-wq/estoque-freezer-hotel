import os
import sqlite3
import smtplib
import urllib.request
import json
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory

# Suporte ao PostgreSQL do Neon
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    TEM_POSTGRES = True
except ImportError:
    TEM_POSTGRES = False

app = Flask(__name__, static_folder='.', static_url_path='')

# Banco de dados: Se DATABASE_URL estiver configurada (Neon), usa Postgres na nuvem!
DATABASE_URL = os.environ.get("DATABASE_URL", "")
DB_FILE = os.environ.get("DB_FILE", "estoque_hotel.db")
EMAIL_DESTINO = os.environ.get("EMAIL_DESTINO", "mwfreitas@gmail.com")

SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")

HOTEIS_DISPONIVEIS = ["Hit Hotel", "Porto Salvador", "Ancoras", "La Vista"]

class DBConnWrapper:
    """Wrapper para unificar SQLite e PostgreSQL do Neon com a mesma interface amigável"""
    def __init__(self):
        self.is_pg = False
        self.conn = None
        self.erro = None
        
        # Conexão com PostgreSQL (Neon)
        if TEM_POSTGRES and DATABASE_URL and (DATABASE_URL.startswith("postgres://") or DATABASE_URL.startswith("postgresql://")):
            try:
                db_url = DATABASE_URL
                # O psycopg2 prefere postgresql://
                if db_url.startswith("postgres://"):
                    db_url = db_url.replace("postgres://", "postgresql://", 1)
                if "channel_binding" in db_url:
                    db_url = db_url.split("&channel_binding")[0]
                self.conn = psycopg2.connect(db_url)
                self.is_pg = True
            except Exception as e:
                self.erro = str(e)
                print(f"Aviso: Falha ao conectar no Postgres ({e}), usando fallback SQLite temporário.")
                self.conn = sqlite3.connect(DB_FILE)
                self.conn.row_factory = sqlite3.Row
        else:
            self.conn = sqlite3.connect(DB_FILE)
            self.conn.row_factory = sqlite3.Row

    def cursor(self):
        if self.is_pg:
            return self.conn.cursor(cursor_factory=RealDictCursor)
        return self.conn.cursor()

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()

def get_db():
    return DBConnWrapper()

# Lista oficial de produtos
PRODUTOS_PADRAO = [
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
    ("SOR-18", "Freezer Picolés e Sorvetes", "Picole chocolate zero açúcar", 15, 0, "un"),
    # Utensílios Padrão
    ("UT-01", "Utensílios", "Abridor de Garrafas", 5, 0, "un"),
    ("UT-02", "Utensílios", "Copos de Vidro", 30, 0, "un"),
    ("UT-03", "Utensílios", "Taças", 20, 0, "un"),
    ("UT-04", "Utensílios", "Colher para Sorvete / Pás", 50, 0, "un"),
    ("UT-05", "Utensílios", "Guardanapos (Pacote)", 10, 0, "pct")
]

def inicializar_banco():
    db = get_db()
    cursor = db.cursor()

    id_auto_col = "SERIAL PRIMARY KEY" if db.is_pg else "INTEGER PRIMARY KEY AUTOINCREMENT"
    
    cursor.execute(f"""
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
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS conferencias (
            id {id_auto_col},
            hotel TEXT,
            data_hora TEXT,
            data_dia TEXT,
            conferente TEXT,
            total_itens INTEGER,
            total_alertas INTEGER
        )
    """)
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS historico (
            id {id_auto_col},
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

    # Popula produtos nos 4 hotéis se ainda não existirem
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
    param_char = "%s" if db.is_pg else "?"

    for hotel in HOTEIS_DISPONIVEIS:
        cursor.execute(f"SELECT COUNT(*) FROM produtos WHERE hotel = {param_char}", (hotel,))
        qtd = list(cursor.fetchone().values())[0] if db.is_pg else cursor.fetchone()[0]
        if qtd == 0:
            for it in PRODUTOS_PADRAO:
                if db.is_pg:
                    cursor.execute("""
                        INSERT INTO produtos (id, hotel, categoria, nome, estoque_minimo, estoque_atual, unidade, ultima_atualizacao)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id, hotel) DO NOTHING
                    """, (it[0], hotel, it[1], it[2], it[3], it[4], it[5], agora))
                else:
                    cursor.execute("""
                        INSERT OR REPLACE INTO produtos (id, hotel, categoria, nome, estoque_minimo, estoque_atual, unidade, ultima_atualizacao)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (it[0], hotel, it[1], it[2], it[3], it[4], it[5], agora))
        else:
            # Garante que Utensílios estejam presentes
            cursor.execute(f"SELECT COUNT(*) FROM produtos WHERE hotel = {param_char} AND categoria = 'Utensílios'", (hotel,))
            qtd_ut = list(cursor.fetchone().values())[0] if db.is_pg else cursor.fetchone()[0]
            if qtd_ut == 0:
                for it in [p for p in PRODUTOS_PADRAO if p[1] == "Utensílios"]:
                    if db.is_pg:
                        cursor.execute("""
                            INSERT INTO produtos (id, hotel, categoria, nome, estoque_minimo, estoque_atual, unidade, ultima_atualizacao)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (id, hotel) DO NOTHING
                        """, (it[0], hotel, it[1], it[2], it[3], it[4], it[5], agora))
                    else:
                        cursor.execute("""
                            INSERT OR REPLACE INTO produtos (id, hotel, categoria, nome, estoque_minimo, estoque_atual, unidade, ultima_atualizacao)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (it[0], hotel, it[1], it[2], it[3], it[4], it[5], agora))

    db.commit()
    db.close()

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
                        <th style="padding:8px;border:1px solid #e5e7eb;text-align:left;">Setor / Categoria</th>
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
                <th style="padding:8px;border:1px solid #cbd5e1;text-align:left;">Setor / Categoria</th>
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
            <h2 style="margin:0;font-size:1.3rem;">🏨 {hotel} - Relatório de Estoque (Freezers e Utensílios)</h2>
        </div>
        <p style="font-size:14px;color:#475569;margin-bottom:15px;">
            Data/Hora: <strong>{agora}</strong><br>
            Conferente responsável: <strong>{conferente}</strong><br>
            Unidade: <strong>{hotel}</strong>
        </p>
        {linhas_alerta_html}
        {tabela_geral_html}
        <p style="font-size:12px;color:#94a3b8;margin-top:25px;text-align:center;">
            Sistema de Gestão de Estoque Permanente (Neon Cloud DB)
        </p>
    </div>
    """

def enviar_email_conferencia(hotel, conferente, agora, itens_conferidos, itens_alerta):
    subject = f"🏨 [{hotel}] Conferência de Estoque ({agora}) {'[ALERTA DE COMPRAS]' if itens_alerta else ''}"
    html_body = gerar_html_email(hotel, conferente, agora, itens_conferidos, itens_alerta)
    email_enviado = False
    detalhes_erro = ""

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
        except Exception as e:
            detalhes_erro = f"SMTP falhou: {e}"

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
        except Exception as e:
            detalhes_erro += f" | Resend falhou: {e}"

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
            
            req = urllib.request.Request(
                f"https://formspree.io/{EMAIL_DESTINO}",
                data=req_data,
                headers={"Content-Type": "application/json", "Accept": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                email_enviado = True
        except Exception as e:
            detalhes_erro += f" | Formspree falhou: {e}"

    return email_enviado, detalhes_erro

# --- ROTAS PRINCIPAIS ---

@app.route("/")
def index():
    return send_from_directory('.', 'app.html')

@app.route("/api/hoteis")
def listar_hoteis():
    return jsonify(HOTEIS_DISPONIVEIS)

@app.route("/api/status-banco")
def status_banco():
    db = get_db()
    tipo = "Neon PostgreSQL (Permanente)" if db.is_pg else "SQLite Local (Temporário)"
    permanente = db.is_pg
    erro = getattr(db, 'erro', None)
    db.close()
    return jsonify({
        "tipo": tipo,
        "permanente": permanente,
        "databaseUrlConfigurada": bool(DATABASE_URL),
        "erro": erro
    })

@app.route("/api/produtos")
def listar_produtos():
    hotel = request.args.get("hotel", "Hit Hotel")
    db = get_db()
    cursor = db.cursor()
    param = "%s" if db.is_pg else "?"
    cursor.execute(f"SELECT id, hotel, categoria, nome, estoque_minimo, estoque_atual, unidade, ultima_atualizacao FROM produtos WHERE hotel = {param} ORDER BY categoria, nome", (hotel,))
    linhas = cursor.fetchall()
    db.close()
    
    produtos = []
    for l in linhas:
        d = dict(l)
        produtos.append({
            "id": d["id"],
            "hotel": d["hotel"],
            "categoria": d["categoria"],
            "nome": d["nome"],
            "estoqueMinimo": d["estoque_minimo"],
            "estoqueAtual": d["estoque_atual"],
            "unidade": d["unidade"],
            "ultimaAtualizacao": d["ultima_atualizacao"]
        })
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

    db = get_db()
    cursor = db.cursor()
    param = "%s" if db.is_pg else "?"
    
    if "Bebidas" in categoria:
        prefix = "BEB"
    elif "Sorvetes" in categoria or "Picolé" in categoria:
        prefix = "SOR"
    else:
        prefix = "UT"
        
    cursor.execute(f"SELECT COUNT(*) FROM produtos WHERE hotel = {param} AND categoria = {param}", (hotel, categoria))
    row = cursor.fetchone()
    total = list(row.values())[0] if db.is_pg else row[0]
    novo_id = f"{prefix}-{total+1:02d}-{int(datetime.now().timestamp())%10000}"
    
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
    if db.is_pg:
        cursor.execute("""
            INSERT INTO produtos (id, hotel, categoria, nome, estoque_minimo, estoque_atual, unidade, ultima_atualizacao)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (novo_id, hotel, categoria, nome, minimo, 0, unidade, agora))
    else:
        cursor.execute("""
            INSERT INTO produtos (id, hotel, categoria, nome, estoque_minimo, estoque_atual, unidade, ultima_atualizacao)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (novo_id, hotel, categoria, nome, minimo, 0, unidade, agora))
        
    db.commit()
    db.close()
    
    return jsonify({"sucesso": True, "mensagem": f"Item adicionado ao {hotel} com sucesso!", "id": novo_id})

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

    db = get_db()
    cursor = db.cursor()
    if db.is_pg:
        cursor.execute("""
            UPDATE produtos SET nome = %s, estoque_minimo = %s, unidade = %s WHERE id = %s AND hotel = %s
        """, (nome, minimo, unidade, p_id, hotel))
    else:
        cursor.execute("""
            UPDATE produtos SET nome = ?, estoque_minimo = ?, unidade = ? WHERE id = ? AND hotel = ?
        """, (nome, minimo, unidade, p_id, hotel))
        
    db.commit()
    db.close()
    
    return jsonify({"sucesso": True, "mensagem": f"Item atualizado no {hotel} com sucesso!"})

@app.route("/api/produtos/excluir", methods=["POST"])
def excluir_produto():
    dados = request.get_json(force=True)
    hotel = dados.get("hotel", "Hit Hotel")
    p_id = dados.get("id")
    
    db = get_db()
    cursor = db.cursor()
    param = "%s" if db.is_pg else "?"
    
    cursor.execute(f"SELECT COUNT(*) FROM historico WHERE produto_id = {param} AND hotel = {param}", (p_id, hotel))
    row = cursor.fetchone()
    total_movimentacoes = list(row.values())[0] if db.is_pg else row[0]
    
    if total_movimentacoes > 0:
        db.close()
        return jsonify({
            "sucesso": False, 
            "mensagem": f"Este item possui movimentações no {hotel} e não pode ser excluído por segurança contábil."
        }), 400
        
    cursor.execute(f"DELETE FROM produtos WHERE id = {param} AND hotel = {param}", (p_id, hotel))
    db.commit()
    db.close()
    
    return jsonify({"sucesso": True, "mensagem": f"Item excluído do {hotel} com sucesso!"})

@app.route("/api/salvar", methods=["POST"])
def salvar_conferencia():
    dados = request.get_json(force=True)
    hotel = dados.get("hotel", "Hit Hotel")
    conferente = dados.get("conferente", "Não identificado").strip()
    itens = dados.get("itens", [])
    agora_dt = datetime.now()
    agora = agora_dt.strftime("%d/%m/%Y %H:%M")
    data_dia = agora_dt.strftime("%Y-%m-%d")
    
    db = get_db()
    cursor = db.cursor()
    
    if db.is_pg:
        cursor.execute("""
            INSERT INTO conferencias (hotel, data_hora, data_dia, conferente, total_itens, total_alertas)
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
        """, (hotel, agora, data_dia, conferente, len(itens), 0))
        conf_id = list(cursor.fetchone().values())[0]
    else:
        cursor.execute("""
            INSERT INTO conferencias (hotel, data_hora, data_dia, conferente, total_itens, total_alertas)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (hotel, agora, data_dia, conferente, len(itens), 0))
        conf_id = cursor.lastrowid
    
    itens_alerta = []
    itens_conferidos = []
    param = "%s" if db.is_pg else "?"
    
    for it in itens:
        p_id = it.get("id")
        qtd = int(it.get("quantidade", 0))
        
        cursor.execute(f"SELECT categoria, nome, estoque_minimo, estoque_atual, unidade FROM produtos WHERE id = {param} AND hotel = {param}", (p_id, hotel))
        row = cursor.fetchone()
        if row:
            d = dict(row)
            cat = d["categoria"]
            nome = d["nome"]
            min_estq = d["estoque_minimo"]
            qtd_anterior = d["estoque_atual"]
            unidade = d["unidade"]
            
            if db.is_pg:
                cursor.execute("""
                    UPDATE produtos SET estoque_atual = %s, ultima_atualizacao = %s WHERE id = %s AND hotel = %s
                """, (qtd, agora, p_id, hotel))
            else:
                cursor.execute("""
                    UPDATE produtos SET estoque_atual = ?, ultima_atualizacao = ? WHERE id = ? AND hotel = ?
                """, (qtd, agora, p_id, hotel))
            
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
            
            if db.is_pg:
                cursor.execute("""
                    INSERT INTO historico (conferencia_id, hotel, data_hora, data_dia, conferente, produto_id, produto_nome, categoria, quantidade, quantidade_anterior, minimo, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (conf_id, hotel, agora, data_dia, conferente, p_id, nome, cat, qtd, qtd_anterior, min_estq, status))
            else:
                cursor.execute("""
                    INSERT INTO historico (conferencia_id, hotel, data_hora, data_dia, conferente, produto_id, produto_nome, categoria, quantidade, quantidade_anterior, minimo, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (conf_id, hotel, agora, data_dia, conferente, p_id, nome, cat, qtd, qtd_anterior, min_estq, status))
    
    if db.is_pg:
        cursor.execute("UPDATE conferencias SET total_alertas = %s WHERE id = %s", (len(itens_alerta), conf_id))
    else:
        cursor.execute("UPDATE conferencias SET total_alertas = ? WHERE id = ?", (len(itens_alerta), conf_id))
        
    db.commit()
    db.close()
    
    email_enviado, erro_msg = enviar_email_conferencia(hotel, conferente, agora, itens_conferidos, itens_alerta)
    
    return jsonify({
        "sucesso": True,
        "mensagem": f"Conferência do {hotel} gravada permanentemente na nuvem!",
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
    db = get_db()
    cursor = db.cursor()
    param = "%s" if db.is_pg else "?"
    cursor.execute(f"""
        SELECT id, hotel, categoria, nome, estoque_minimo, estoque_atual, unidade, ultima_atualizacao,
        CASE WHEN estoque_atual <= estoque_minimo THEN 1 ELSE 0 END as precisa_comprar,
        CASE WHEN estoque_minimo > estoque_atual THEN estoque_minimo - estoque_atual ELSE 0 END as sugestao_compra
        FROM produtos
        WHERE hotel = {param}
        ORDER BY categoria, nome
    """, (hotel,))
    rows = cursor.fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/relatorios/conferencias-dia")
def relatorio_conferencias():
    hotel = request.args.get("hotel", "Hit Hotel")
    db = get_db()
    cursor = db.cursor()
    param = "%s" if db.is_pg else "?"
    cursor.execute(f"SELECT id, hotel, data_hora, data_dia, conferente, total_itens, total_alertas FROM conferencias WHERE hotel = {param} ORDER BY id DESC LIMIT 60", (hotel,))
    rows = cursor.fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/relatorios/comparativo-dias")
def relatorio_comparativo_dias():
    hotel = request.args.get("hotel", "Hit Hotel")
    db = get_db()
    cursor = db.cursor()
    param = "%s" if db.is_pg else "?"
    cursor.execute(f"SELECT DISTINCT data_dia FROM historico WHERE hotel = {param} ORDER BY data_dia DESC LIMIT 2", (hotel,))
    dias_raw = cursor.fetchall()
    dias = [list(dict(r).values())[0] for r in dias_raw]
    
    if len(dias) < 2:
        db.close()
        return jsonify({
            "disponivel": False, 
            "mensagem": f"O {hotel} precisa ter pelo menos 2 conferências em dias distintos para gerar o comparativo de consumo."
        })
        
    dia_recente, dia_anterior = dias[0], dias[1]
    
    query = f"""
        SELECT 
            h1.produto_nome, h1.categoria,
            h2.quantidade as qtd_anterior,
            h1.quantidade as qtd_atual,
            (h2.quantidade - h1.quantidade) as consumo_estimado,
            h1.minimo
        FROM historico h1
        JOIN historico h2 ON h1.produto_id = h2.produto_id AND h2.data_dia = {param} AND h2.hotel = {param}
        WHERE h1.data_dia = {param} AND h1.hotel = {param}
        GROUP BY h1.produto_id, h1.produto_nome, h1.categoria, h2.quantidade, h1.quantidade, h1.minimo
        ORDER BY h1.categoria, h1.produto_nome
    """
    cursor.execute(query, (dia_anterior, hotel, dia_recente, hotel))
    rows = cursor.fetchall()
    db.close()
    
    comparativo = []
    total_saidas = 0
    for r in rows:
        d = dict(r)
        consumo = d["consumo_estimado"] if d["consumo_estimado"] and d["consumo_estimado"] > 0 else 0
        total_saidas += consumo
        comparativo.append({
            "produto": d["produto_nome"],
            "categoria": d["categoria"],
            "qtdAnterior": d["qtd_anterior"],
            "qtdAtual": d["qtd_atual"],
            "consumoVendas": consumo,
            "minimo": d["minimo"]
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
