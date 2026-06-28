# Loja de Pesca — Controle de Estoque com MongoDB

Sistema de controle de estoque para uma loja de artigos de pesca, desenvolvido como trabalho da disciplina de **Banco de Dados Avançado** do **UniLaSalle**. O projeto demonstra o uso de um banco de dados **NoSQL orientado a documentos** (MongoDB) para modelar produtos com atributos que variam de acordo com a categoria, algo difícil de representar de forma elegante em bancos relacionais tradicionais.

O diferencial do modelo é o campo flexível `des_especificacoes`, que armazena atributos técnicos específicos de cada categoria de produto (linha, isca, carretilha, vara, acessório, anzol e rede) sem exigir alteração de esquema.

## Tecnologias utilizadas

- **MongoDB** — banco de dados NoSQL orientado a documentos
- **MongoDB Atlas** — hospedagem do banco na nuvem
- **Python** — linguagem do backend
- **PyMongo** — driver oficial para conexão entre Python e MongoDB
- **Flask** — framework web que expõe a rota GET de consulta dos produtos

## Estrutura do banco

- **Database:** `loja_pesca`
- **Coleção:** `produtos`
- **Volume:** 80 documentos distribuídos em 7 categorias (linha, isca, carretilha, vara, acessório, anzol e rede)

### Campos da coleção `produtos`

Cada documento possui um conjunto de campos fixos, comuns a todos os produtos, e um campo flexível com as especificações técnicas que variam por categoria.

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id_estoque` | Texto | Identificador do item em estoque (ex.: `PROD-001`) |
| `des_nome_item` | Texto | Nome/descrição do produto |
| `tp_categoria` | Texto | Categoria (linha, isca, carretilha, vara, acessório, anzol, rede) |
| `des_marca` | Texto | Marca do produto |
| `cod_sku` | Texto | Código SKU único do item |
| `vlr_preco` | Número | Preço de venda (aceita inteiro ou decimal) |
| `tp_moeda` | Texto | Moeda do preço (ex.: `BRL`) |
| `qtd_estoque` | Número | Quantidade disponível em estoque |
| `tp_unidade` | Texto | Unidade de medida do item (ex.: `rolo`, `unidade`) |
| `qtd_min_alerta` | Número | Quantidade mínima que dispara alerta de reposição |
| `tp_situacao` | Texto | Situação do item (ex.: ativo, inativo) |
| `data_cadastro` | Data | Data de cadastro do produto |
| `des_especificacoes` | Texto (flexível) | Campo **flexível** com os atributos técnicos que variam por categoria |

O campo `des_especificacoes` é o diferencial do modelo: ele guarda os atributos técnicos que mudam de uma categoria para outra (a bitola de uma linha, a relação de transmissão de uma carretilha, a malha de uma rede), sem exigir alteração de esquema nem tabelas auxiliares. Na implementação atual ele é armazenado como uma **string** com os pares atributo/valor; uma evolução prevista é convertê-lo em um subdocumento tipado, o que permitiria buscas por atributos técnicos específicos.

### Exemplo de documento

```json
{
  "id_estoque": "PROD-001",
  "des_nome_item": "Linha Monofilamento Crystal",
  "tp_categoria": "linha",
  "des_marca": "Maruri",
  "cod_sku": "LIN-MONO-0025",
  "vlr_preco": 29.90,
  "tp_moeda": "BRL",
  "qtd_estoque": 150,
  "tp_unidade": "rolo",
  "qtd_min_alerta": 20,
  "des_especificacoes": "bitola_mm: 0.25; resistencia_kg: 8.0; comprimento_m: 300",
  "tp_situacao": "ativo",
  "data_cadastro": "2024-01-10T08:00:00Z"
}
```

## Como rodar o backend localmente

> Pré-requisitos: Python 3.10+ instalado e uma string de conexão do MongoDB Atlas.

### 1. Clonar o repositório

```bash
git clone https://github.com/<seu-usuario>/Loja_pesca_MongoDB.git
cd Loja_pesca_MongoDB
```

### 2. Criar e ativar o ambiente virtual

```bash
# criar o venv
python -m venv venv

# ativar — Windows (PowerShell)
venv\Scripts\Activate.ps1

# ativar — Linux / macOS
source venv/bin/activate
```

### 3. Instalar as dependências

```bash
pip install -r requirements.txt
```

### 4. Configurar a string de conexão

A string de conexão do Atlas **nunca** deve ir para o repositório. Ela é lida de uma variável de ambiente.

Copie o arquivo de exemplo e preencha com a sua URI real:

```bash
# Windows
copy .env.example .env

# Linux / macOS
cp .env.example .env
```

Abra o `.env` e ajuste o valor de `MONGO_URI` com a string fornecida pelo Atlas (Database → Connect → Drivers).

### 5. Executar o backend

```bash
# a partir da pasta backend/
python app.py
```

O servidor Flask sobe localmente (por padrão em `http://127.0.0.1:5000`) e a rota `GET /produtos` retorna os documentos da coleção em formato JSON, prontos para o front-end consumir.

## CRUD com PyMongo

O sistema implementa as quatro operações básicas de manipulação de dados sobre a coleção `produtos`. Abaixo estão exemplos de como cada operação é feita com PyMongo.

### Conexão

```python
import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()  # carrega as variáveis do arquivo .env

client = MongoClient(os.environ["MONGO_URI"])
db = client["loja_pesca"]
colecao = db["produtos"]
```

### Create — `insert_one`

Insere um novo produto na coleção. O documento é passado como um dicionário e o próprio servidor gera o campo `_id`.

```python
colecao.insert_one({
    "id_estoque": "PROD-081",
    "des_nome_item": "Isca Soft Shad 9cm",
    "tp_categoria": "isca",
    "des_marca": "Yum",
    "vlr_preco": 24.90,
    "qtd_estoque": 60,
    "qtd_min_alerta": 15,
    "tp_situacao": "ativo",
})
```

### Read — `find`

Consulta produtos a partir de um padrão de busca. É essa operação que a rota GET do backend executa. Exemplo: todas as iscas ativas.

```python
colecao.find({"tp_categoria": "isca", "tp_situacao": "ativo"})
```

Consulta de reposição — produtos com estoque no mínimo ou abaixo do alerta:

```python
colecao.find({"$expr": {"$lte": ["$qtd_estoque", "$qtd_min_alerta"]}})
```

### Update — `update_one`

Localiza o documento por um critério e altera apenas os campos indicados pelo operador `$set`. Exemplo: baixa de estoque após uma venda.

```python
colecao.update_one(
    {"id_estoque": "PROD-001"},
    {"$set": {"qtd_estoque": 140}},
)
```

### Delete — `delete_one`

Remove o primeiro documento que atende ao critério informado.

```python
colecao.delete_one({"id_estoque": "PROD-081"})
```

## Estrutura do repositório

```
Loja_pesca_MongoDB/
├── backend/
│   └── app.py               # Flask: conexão ao Atlas, rota GET e funções de CRUD
├── docs/
│   └── roteiro_video.md     # roteiro do vídeo de apresentação (artigo vai aqui também)
├── produtos_pesca.json      # dump de exemplo da coleção
├── requirements.txt         # dependências do projeto
├── .env.example             # modelo da variável de conexão (sem senha)
├── .gitignore               # arquivos ignorados (inclui .env)
└── README.md
```

## Integrantes

- Matheus Santos Chaves de Almeida
- Leonardo Nunes
- Luan Vieira

---

Trabalho acadêmico — Banco de Dados Avançado — UniLaSalle.
