import os
import sqlite3
import urllib.request
import json
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__, static_folder='.', static_url_path='')

DB_FILE = os.environ.get("DB_FILE", "estoque_hotel.db")
EMAIL_DESTINO = os.environ.get("EMAIL_DESTINO", "mwfreitas@gmail.com")
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")

HOTEIS_DISPONIVEIS = ["Hit Hotel", "Porto Salvador", "Ancoras"]

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

# Lista oficial enviada pelo cliente
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

# --- DISPARO DE EMAIL VIA RESEND OU WEBHOOK GRÁTIS ---
def enviar_email_conferencia(hotel, conferente, agora, itens_conferidos, itens_alerta):
    """Envia o e-mail completo com a contagem do hotel específico para mwfreitas@gmail.com"""
    try:
        linhas_alerta_html = ""
        if itens_alerta:
            linhas_alerta_html = f"""
            <h3 style="color:#d93025;margin-top:20px;">⚠️ ITENS QUE ATINGIRAM ESTOQUE MÍNIMO - {hotel} (COMPRA SUGERIDA)</h3>
            <table style="width:100%;border-collapse:collapse;margin-bottom:25px;font-family:sans-serif;font-size:13px;">
                <thead>
                    <tr style="background:#d93025;color:white;">
                        <th style="padding:8px;border:1px solid #ccc;text-align:left;">Freezer</th>
                        <th style="padding:8px;border:1px solid #ccc;text-align:left;">Item</th>
                        <th style="padding:8px;border:1px solid #ccc;text-align:center;">Estoque Atual</th>
                        <th style="padding:8px;border:1px solid #ccc;text-align:center;">Mínimo</th>
                        <th style="padding:8px;border:1px solid #ccc;text-align:center;background:#b31412;">Comprar</th>
                    </tr>
                </thead>
                <tbody>
            """
            for it in itens_alerta:
                linhas_alerta_html += f"""
                    <tr>
                        <td style="padding:6px;border:1px solid #ccc;">{it['categoria']}</td>
                        <td style="padding:6px;border:1px solid #ccc;"><strong>{it['nome']}</strong></td>
                        <td style="padding:6px;border:1px solid #ccc;text-align:center;color:#d93025;font-weight:bold;">{it['atual']} {it['unidade']}</td>
                        <td style="padding:6px;border:1px solid #ccc;text-align:center;">{it['minimo']} {it['unidade']}</td>
                        <td style="padding:6px;border:1px solid #ccc;text-align:center;color:#1a73e8;font-weight:bold;">+{it['sugestao']} {it['unidade']}</td>
                    </tr>
                """
            linhas_alerta_html += "</tbody></table>"

        # Tabela completa de todos os itens contados
        tabela_geral_html = f"""
        <h3 style="color:#1a73e8;margin-top:15px;">📋 CONTAGEM COMPLETA - {hotel}</h3>
        <table style="width:100%;border-collapse:collapse;font-family:sans-serif;font-size:13px;">
            <thead>
                <tr style="background:#334155;color:white;">
                    <th style="padding:8px;border:1px solid #ccc;text-align:left;">Freezer</th>
                    <th style="padding:8px;border:1px solid #ccc;text-align:left;">Item</th>
                    <th style="padding:8px;border:1px solid #ccc;text-align:center;">Contado</th>
                    <th style="padding:8px;border:1px solid #ccc;text-align:center;">Mínimo</th>
                    <th style="padding:8px;border:1px solid #ccc;text-align:center;">Status</th>
                </tr>
            </thead>
            <tbody>
        """
        for it in itens_conferidos:
            cor_status = "#d93025" if it['precisa_comprar'] else "#0f9d58"
            tabela_geral_html += f"""
                <tr>
                    <td style="padding:6px;border:1px solid #ccc;">{it['categoria']}</td>
                    <td style="padding:6px;border:1px solid #ccc;">{it['nome']}</td>
                    <td style="padding:6px;border:1px solid #ccc;text-align:center;font-weight:bold;">{it['atual']} {it['unidade']}</td>
                    <td style="padding:6px;border:1px solid #ccc;text-align:center;">{it['minimo']} {it['unidade']}</td>
                    <td style="padding:6px;border:1px solid #ccc;text-align:center;color:{cor_status};font-weight:bold;">{it['status']}</td>
                </tr>
            """
        tabela_geral_html += "</tbody></table>"

        html_body = f"""
        <div style="font-family:Arial,sans-serif;max-width:700px;margin:0 auto;padding:20px;border:1px solid #e2e8f0;border-radius:10px;">
            <div style="background:#1a73e8;color:white;padding:12px;border-radius:8px;margin-bottom:15px;">
                <h2 style="margin:0;font-size:1.3rem;">🏨 {hotel} - Conferência de Freezers</h2>
            </div>
            <p style="font-size:15px;color:#475569;">
                Data/Hora: <strong>{agora}</strong><br>
                Conferente responsável: <strong>{conferente}</strong>
            </p>
            {linhas_alerta_html}
            {tabela_geral_html}
            <p style="font-size:12px;color:#94a3b8;margin-top:25px;text-align:center;">
                Sistema Multi-Hotel Automatizado de Estoque
            </p>
        </div>
        """

        subject = f"🏨 [{hotel}] Conferência de Freezers ({agora}) {'[ALERTA DE COMPRAS]' if itens_alerta else ''}"

        if RESEND_API_KEY:
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
            urllib.request.urlopen(req, timeout=10)
        else:
            req_data = json.dumps({
                "to": EMAIL_DESTINO,
                "subject": subject,
                "html": html_body
            }).encode('utf-8')
            req = urllib.request.Request(
                "https://formspree.io/f/mwkgyyqk",
                data=req_data,
                headers={"Content-Type": "application/json"}
            )
            try:
                urllib.request.urlopen(req, timeout=5)
            except Exception:
                pass
    except Exception as e:
        print(f"Erro ao disparar e-mail: {e}")

# --- ROTAS PRINCIPAIS ---

@app.route("/")
def index():
    return send_from_directory('.', 'app.html')

@app.route("/api/hoteis")
def listar_hoteis():
    return jsonify(HOTEIS_DISPONIVEIS)

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
    
    enviar_email_conferencia(hotel, conferente, agora, itens_conferidos, itens_alerta)
    
    return jsonify({
        "sucesso": True,
        "mensagem": f"Conferência do {hotel} registrada com sucesso!",
        "itensAlerta": len(itens_alerta)
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
