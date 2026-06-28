"""
app.py — Backend do sistema de controle de estoque (Loja de Pesca).

Conecta-se ao MongoDB Atlas (database "loja_pesca", coleção "produtos") via
PyMongo e expõe os dados ao front-end por meio de uma rota de leitura (GET).
Também concentra as quatro operações de escrita/leitura (CRUD) descritas no
artigo, implementadas com insert_one, find, update_one e delete_one.

A string de conexão NUNCA é escrita no código: ela é lida da variável de
ambiente MONGO_URI (arquivo .env, ignorado pelo Git).

Como executar (a partir da pasta backend/):
    python app.py
"""

import os

from bson import json_util
from dotenv import load_dotenv
from flask import Flask, Response, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient

# ---------------------------------------------------------------------------
# Configuração e conexão
# ---------------------------------------------------------------------------

# Carrega as variáveis definidas no arquivo .env (MONGO_URI, DB_NAME, ...).
load_dotenv()

MONGO_URI = os.environ.get("MONGO_URI")
if not MONGO_URI:
    raise RuntimeError(
        "A variável de ambiente MONGO_URI não está definida. "
        "Copie o arquivo .env.example para .env e preencha com a string "
        "de conexão do MongoDB Atlas."
    )

DB_NAME = os.environ.get("DB_NAME", "loja_pesca")
COLLECTION_NAME = os.environ.get("COLLECTION_NAME", "produtos")

# Cliente do MongoDB. O objeto "colecao" representa a coleção produtos e é
# usado por todas as operações de CRUD abaixo.
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
colecao = db[COLLECTION_NAME]

app = Flask(__name__)
CORS(app)  # libera o front-end para consumir a API


def _json(dados):
    """Serializa documentos do MongoDB (incluindo ObjectId) para JSON."""
    return Response(json_util.dumps(dados, ensure_ascii=False),
                    mimetype="application/json")


# ---------------------------------------------------------------------------
# READ — rota GET consumida pelo front-end
# ---------------------------------------------------------------------------

@app.route("/produtos", methods=["GET"])
def listar_produtos():
    """Retorna os produtos da coleção em JSON.

    Aceita filtros opcionais via query string, por exemplo:
        GET /produtos                      -> todos os produtos
        GET /produtos?categoria=isca       -> apenas a categoria informada
        GET /produtos?situacao=ativo       -> apenas itens ativos
    """
    filtro = {}
    categoria = request.args.get("categoria")
    situacao = request.args.get("situacao")
    if categoria:
        filtro["tp_categoria"] = categoria
    if situacao:
        filtro["tp_situacao"] = situacao

    produtos = list(colecao.find(filtro))
    return _json(produtos)


@app.route("/produtos/reposicao", methods=["GET"])
def listar_reposicao():
    """Consulta de reposição: itens cujo estoque está no mínimo ou abaixo."""
    filtro = {"$expr": {"$lte": ["$qtd_estoque", "$qtd_min_alerta"]}}
    return _json(list(colecao.find(filtro)))


# ---------------------------------------------------------------------------
# CREATE / UPDATE / DELETE — exemplos de funções de escrita
# --------------------------------------------------------------------------

def criar_produto(documento: dict):
    """CREATE — insere um novo produto (insert_one).

    O documento é um dicionário; o próprio servidor gera o campo _id.
    Exemplo de uso, conforme o artigo:

        criar_produto({
            "id_estoque": "PROD-081",
            "des_nome_item": "Isca Soft Shad 9cm",
            "tp_categoria": "isca",
            "des_marca": "Yum",
            "vlr_preco": 24.90,
            "qtd_estoque": 60,
            "qtd_min_alerta": 15,
            "tp_situacao": "ativo",
        })
    """
    resultado = colecao.insert_one(documento)
    return resultado.inserted_id


def buscar_produtos(filtro: dict):
    """READ — busca documentos que correspondem ao padrão (find).

    Exemplo: iscas ativas -> {"tp_categoria": "isca", "tp_situacao": "ativo"}
    """
    return list(colecao.find(filtro))


def atualizar_estoque(id_estoque: str, nova_quantidade: int):
    """UPDATE — altera apenas os campos indicados com $set (update_one).

    Exemplo: baixa de estoque após uma venda.
    """
    resultado = colecao.update_one(
        {"id_estoque": id_estoque},
        {"$set": {"qtd_estoque": nova_quantidade}},
    )
    return resultado.modified_count


def remover_produto(id_estoque: str):
    """DELETE — remove o primeiro documento que atende ao critério (delete_one)."""
    resultado = colecao.delete_one({"id_estoque": id_estoque})
    return resultado.deleted_count


# ---------------------------------------------------------------------------
# Rotas de escrita (opcionais — evolução prevista no artigo)
# ---------------------------------------------------------------------------

@app.route("/produtos", methods=["POST"])
def rota_criar_produto():
    documento = request.get_json(force=True)
    novo_id = criar_produto(documento)
    return jsonify({"inserted_id": str(novo_id)}), 201


@app.route("/produtos/<id_estoque>", methods=["PUT"])
def rota_atualizar_produto(id_estoque):
    dados = request.get_json(force=True)
    nova_qtd = dados.get("qtd_estoque")
    alterados = atualizar_estoque(id_estoque, nova_qtd)
    return jsonify({"modified_count": alterados})


@app.route("/produtos/<id_estoque>", methods=["DELETE"])
def rota_remover_produto(id_estoque):
    removidos = remover_produto(id_estoque)
    return jsonify({"deleted_count": removidos})


@app.route("/", methods=["GET"])
def index():
    """Mensagem simples para confirmar que o backend está no ar."""
    return jsonify({
        "servico": "API Loja de Pesca",
        "rotas": ["/produtos", "/produtos?categoria=isca", "/produtos/reposicao"],
    })


if __name__ == "__main__":
    # debug=True facilita o desenvolvimento; desative em produção.
    app.run(host="127.0.0.1", port=5000, debug=True)
