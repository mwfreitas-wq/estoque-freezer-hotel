import os
import sqlite3
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from flask import Flask, request, jsonify, render_to_string, send_from_directory

app = Flask(__name__, static_folder='.', static_url_path='')

DB_FILE = os.environ.get("DB_FILE", "estoque_hotel.db")
EMAIL_DESTINO = os.environ.get("EMAIL_DESTINO", "mwfreitas@gmail.com")

# Credenciais opcionais de envio de e-mail (caso queira configurar variáveis no painel da nuvem)
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def inicializar_banco():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS produtos (
            id TEXT PRIMARY KEY,
            categoria TEXT,
            nome TEXT,
            estoque_minimo INTEGER,
            estoque_atual INTEGER,
            unidade TEXT,
            ultima_atualizacao TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS historico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_hora TEXT,
            conferente TEXT,
            produto_id TEXT,
            produto_nome TEXT,
            categoria TEXT,
            quantidade INTEGER,
            minimo INTEGER,
            status TEXT
        )
    """)
    cursor.execute("SELECT COUNT(*) FROM produtos")
    if cursor.fetchone()[0] == 0:
        itens_iniciais = [
            ("BEB-01", "Freezer Bebidas", "Água Mineral sem Gás 500ml", 30, 0, "un"),
            ("BEB-02", "Freezer Bebidas", "Água Mineral com Gás 500ml", 20, 0, "un"),
            ("BEB-03", "Freezer Bebidas", "Coca-Cola Lata 350ml", 24, 0, "lata"),
            ("BEB-04", "Freezer Bebidas", "Coca-Cola Zero Lata 350ml", 18, 0, "lata"),
            ("BEB-05", "Freezer Bebidas", "Guaraná Antarctica 350ml", 18, 0, "lata"),
            ("BEB-06", "Freezer Bebidas", "Cerveja Heineken Long Neck 330ml", 24, 0, "garrafa"),
            ("BEB-07", "Freezer Bebidas", "Cerveja Amstel Lata 350ml", 20, 0, "lata"),
            ("BEB-08", "Freezer Bebidas", "Suco Del Valle Uva 290ml", 12, 0, "lata"),
            ("SOR-01", "Freezer Picolés e Sorvetes", "Picolé Frutas (Limão/Uva/Maracujá)", 25, 0, "un"),
            ("SOR-02", "Freezer Picolés e Sorvetes", "Picolé Cremoso (Chocolate/Morango)", 25, 0, "un"),
            ("SOR-03", "Freezer Picolés e Sorvetes", "Paleta Mexicana Recheada", 15, 0, "un"),
            ("SOR-04", "Freezer Picolés e Sorvetes", "Pote de Sorvete Individual 150ml", 10, 0, "pote"),
            ("SOR-05", "Freezer Picolés e Sorvetes", "Cone Trufado", 12, 0, "un")
        ]
        agora = datetime.now().strftime("%d/%m/%Y %H:%M")
        cursor.executemany("""
            INSERT INTO produtos (id, categoria, nome, estoque_minimo, estoque_atual, unidade, ultima_atualizacao)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [(it[0], it[1], it[2], it[3], it[4], it[5], agora) for it in itens_iniciais])
    conn.commit()
    conn.close()

# Inicializa ao carregar o app
inicializar_banco()

@app.route("/")
def index():
    return send_from_directory('.', 'app.html')

@app.route("/api/produtos")
def listar_produtos():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, categoria, nome, estoque_minimo, estoque_atual, unidade, ultima_atualizacao FROM produtos")
    linhas = cursor.fetchall()
    conn.close()
    
    produtos = [{
        "id": l["id"],
        "categoria": l["categoria"],
        "nome": l["nome"],
        "estoqueMinimo": l["estoque_minimo"],
        "estoqueAtual": l["estoque_atual"],
        "unidade": l["unidade"],
        "ultimaAtualizacao": l["ultima_atualizacao"]
    } for l in linhas]
    
    return jsonify(produtos)

@app.route("/api/salvar", methods=["POST"])
def salvar_conferencia():
    dados = request.get_json(force=True)
    conferente = dados.get("conferente", "Não identificado")
    itens = dados.get("itens", [])
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
    
    conn = get_db()
    cursor = conn.cursor()
    itens_alerta = []
    
    for it in itens:
        p_id = it.get("id")
        qtd = int(it.get("quantidade", 0))
        
        cursor.execute("SELECT categoria, nome, estoque_minimo, unidade FROM produtos WHERE id = ?", (p_id,))
        row = cursor.fetchone()
        if row:
            cat = row["categoria"]
            nome = row["nome"]
            min_estq = row["estoque_minimo"]
            unidade = row["unidade"]
            
            cursor.execute("UPDATE produtos SET estoque_atual = ?, ultima_atualizacao = ? WHERE id = ?", (qtd, agora, p_id))
            
            precisa_comprar = qtd < min_estq
            status = "OK"
            if precisa_comprar:
                faltante = min_estq - qtd
                status = f"COMPRAR (Faltam {faltante} {unidade})"
                itens_alerta.append({
                    "categoria": cat,
                    "nome": nome,
                    "atual": qtd,
                    "minimo": min_estq,
                    "sugestao": faltante,
                    "unidade": unidade
                })
            
            cursor.execute("""
                INSERT INTO historico (data_hora, conferente, produto_id, produto_nome, categoria, quantidade, minimo, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (agora, conferente, p_id, nome, cat, qtd, min_estq, status))
    
    conn.commit()
    conn.close()
    
    # Envio de e-mail (se configurado SMTP)
    if itens_alerta and SMTP_USER and SMTP_PASS:
        enviar_email_smtp(conferente, agora, itens_alerta)
    
    return jsonify({
        "sucesso": True,
        "mensagem": "Conferência registrada com sucesso na nuvem!",
        "itensAlerta": len(itens_alerta)
    })

def enviar_email_smtp(conferente, agora, itens):
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"🛒 [COMPRA NECESSÁRIA] Alerta de Estoque - Freezers ({agora})"
        msg["From"] = SMTP_USER
        msg["To"] = EMAIL_DESTINO
        
        html = f"""
        <h2>Alerta de Estoque: Reposição de Freezers</h2>
        <p>Conferência realizada em {agora} por: <b>{conferente}</b></p>
        <table border='1' cellpadding='8' style='border-collapse:collapse;'>
            <tr style='background:#d93025;color:white;'>
                <th>Freezer</th><th>Item</th><th>Atual</th><th>Mínimo</th><th>Comprar</th>
            </tr>
        """
        for it in itens:
            html += f"<tr><td>{it['categoria']}</td><td>{it['nome']}</td><td>{it['atual']} {it['unidade']}</td><td>{it['minimo']} {it['unidade']}</td><td><b>+{it['sugestao']} {it['unidade']}</b></td></tr>"
        html += "</table>"
        
        msg.attach(MIMEText(html, "html"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, EMAIL_DESTINO, msg.as_string())
    except Exception as e:
        print(f"Erro ao enviar email SMTP: {e}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
