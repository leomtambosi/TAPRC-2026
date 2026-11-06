import json
import logging
import os
from datetime import datetime
from typing import Any

import azure.functions as func
import pyodbc
from azure.storage.blob import BlobServiceClient, ContainerClient

app = func.FunctionApp()
logger = logging.getLogger(__name__)

# Ordem de carga pensada para respeitar chaves estrangeiras (Foreign Keys)
ORDEM_ENTIDADES = [
    "cliente_organizacao",
    "solicitante",
    "analista",
    "categoria",
    "fila",
    "sla",
    "chamado",
    "chamado_sla",
    "chamado_status_historico",
    "csat_avaliacao",
]


def _odbc_value(value: str) -> str:
    """Escapa um valor para uso em uma string de conexão ODBC."""
    return "{" + value.replace("}", "}}") + "}"


def _nome_tabela_qualificado(schema: str, tabela: str) -> str:
    """Protege identificadores SQL Server."""
    schema_escapado = schema.replace("]", "]]")
    tabela_escapada = tabela.replace("]", "]]")
    return f"[{schema_escapado}].[{tabela_escapada}]"


def _nome_coluna_qualificado(coluna: str) -> str:
    """Protege nomes de colunas no SQL Server."""
    return f"[{coluna.replace(']', ']]')}]"


def _obter_string_conexao_sql() -> str:
    host_sql = os.getenv("HOST")
    database_sql = os.getenv("DATABASE")
    user_sql = os.getenv("USER")
    password_sql = os.getenv("PASSWORD")

    if not all((host_sql, database_sql, user_sql, password_sql)):
        raise RuntimeError(
            "Uma ou mais variáveis de conexão com o banco (HOST, DATABASE, USER, PASSWORD) estão ausentes."
        )

    return (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        f"SERVER={_odbc_value(host_sql)};"
        f"DATABASE={_odbc_value(database_sql)};"
        f"UID={_odbc_value(user_sql)};"
        f"PWD={_odbc_value(password_sql)};"
        "Encrypt=yes;"
        "TrustServerCertificate=no;"
        "Connection Timeout=30;"
    )


def _listar_ultimos_blobs_por_entidade(
    container_client: ContainerClient, fonte: str
) -> dict[str, str]:
    """
    Percorre a pasta da fonte (ex: 'itsm/') no container bronze e retorna
    o caminho do arquivo .json mais recente de cada subpasta (entidade).
    """
    prefixo = f"{fonte.rstrip('/')}/"
    ultimos_blobs: dict[str, tuple[datetime, str]] = {}

    for blob in container_client.list_blobs(name_starts_with=prefixo):
        if not blob.name.endswith(".json"):
            continue

        partes = blob.name.split("/")
        if len(partes) < 2:
            continue

        entidade = partes[1]
        data_modificacao = blob.last_modified or datetime.min

        if (
            entidade not in ultimos_blobs
            or data_modificacao >= ultimos_blobs[entidade][0]
        ):
            ultimos_blobs[entidade] = (data_modificacao, blob.name)

    return {entidade: caminho for entidade, (_, caminho) in ultimos_blobs.items()}


def _inferir_tipo_sql(valores: list[Any]) -> str:
    """Infere o tipo de dado no SQL Server caso a tabela precise ser criada."""
    nao_nulos = [v for v in valores if v is not None]
    if not nao_nulos:
        return "NVARCHAR(4000) NULL"

    if all(isinstance(v, bool) for v in nao_nulos):
        return "BIT NULL"
    if all(isinstance(v, int) and not isinstance(v, bool) for v in nao_nulos):
        return "BIGINT NULL"
    if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in nao_nulos):
        return "FLOAT NULL"

    maior_texto = max((len(str(v)) for v in nao_nulos), default=0)
    if maior_texto > 4000:
        return "NVARCHAR(MAX) NULL"
    return "NVARCHAR(4000) NULL"


def _garantir_tabela_existe(
    cursor: pyodbc.Cursor, schema: str, tabela: str, registros: list[dict[str, Any]]
) -> None:
    """Cria a tabela automaticamente no banco caso ela ainda não exista."""
    cursor.execute(
        """
        SELECT 1
        FROM sys.tables AS t
        INNER JOIN sys.schemas AS s ON s.schema_id = t.schema_id
        WHERE s.name = ? AND t.name = ?
        """,
        (schema, tabela),
    )
    if cursor.fetchone():
        return

    colunas = list(registros[0].keys())
    definicoes_colunas = []
    for col in colunas:
        amostra = [linha.get(col) for linha in registros]
        tipo_sql = _inferir_tipo_sql(amostra)
        definicoes_colunas.append(f"{_nome_coluna_qualificado(col)} {tipo_sql}")

    nome_qualificado = _nome_tabela_qualificado(schema, tabela)
    sql_create = f"CREATE TABLE {nome_qualificado} ({', '.join(definicoes_colunas)})"
    cursor.execute(sql_create)
    logger.info("Tabela %s criada automaticamente.", nome_qualificado)


def _possui_coluna_identity(cursor: pyodbc.Cursor, schema: str, tabela: str) -> bool:
    """Verifica se a tabela possui coluna IDENTITY para liberar a inserção de IDs."""
    cursor.execute(
        """
        SELECT COUNT(1)
        FROM sys.identity_columns AS ic
        INNER JOIN sys.tables AS t ON t.object_id = ic.object_id
        INNER JOIN sys.schemas AS s ON s.schema_id = t.schema_id
        WHERE s.name = ? AND t.name = ?
        """,
        (schema, tabela),
    )
    resultado = cursor.fetchone()
    return bool(resultado and resultado[0] > 0)


def carregar_dados_na_tabela(
    cursor: pyodbc.Cursor,
    entidade: str,
    registros: list[dict[str, Any]],
) -> None:
    """Garante a existência da tabela, limpa dados antigos e insere os registros."""
    if not registros:
        logger.info("Nenhum registro para carregar na entidade '%s'.", entidade)
        return

    if "." in entidade:
        schema, tabela = entidade.split(".", 1)
    else:
        schema, tabela = "dbo", entidade

    nome_qualificado = _nome_tabela_qualificado(schema, tabela)
    _garantir_tabela_existe(cursor, schema, tabela, registros)

    colunas = list(registros[0].keys())
    colunas_sql = ", ".join(_nome_coluna_qualificado(c) for c in colunas)
    placeholders = ", ".join("?" for _ in colunas)

    # Limpa os dados anteriores da tabela para evitar duplicidade
    cursor.execute(f"DELETE FROM {nome_qualificado}")

    tem_identity = _possui_coluna_identity(cursor, schema, tabela)
    if tem_identity:
        cursor.execute(f"SET IDENTITY_INSERT {nome_qualificado} ON")

    try:
        sql_insert = (
            f"INSERT INTO {nome_qualificado} ({colunas_sql}) VALUES ({placeholders})"
        )
        cursor.fast_executemany = True

        # Prepara as linhas convertendo eventuais dicts/listas aninhados em string JSON
        linhas = [
            tuple(
                json.dumps(linha.get(c), ensure_ascii=False)
                if isinstance(linha.get(c), (dict, list))
                else linha.get(c)
                for c in colunas
            )
            for linha in registros
        ]

        tamanho_lote = 1000
        for i in range(0, len(linhas), tamanho_lote):
            cursor.executemany(sql_insert, linhas[i : i + tamanho_lote])

        logger.info(
            "Tabela %s carregada com sucesso (%s linhas).",
            nome_qualificado,
            len(linhas),
        )
    finally:
        if tem_identity:
            cursor.execute(f"SET IDENTITY_INSERT {nome_qualificado} OFF")


def importar_todas_as_tabelas_da_bronze() -> None:
    """Puxa os arquivos JSON mais recentes de bronze/itsm e carrega no banco SQL."""
    conn_str_storage = os.getenv("DEPLOYMENT_STORAGE_CONNECTION_STRING")
    if not conn_str_storage:
        raise RuntimeError(
            "A variável DEPLOYMENT_STORAGE_CONNECTION_STRING não está configurada."
        )

    # Por padrão busca da pasta 'itsm' caso SOURCE_NAME não esteja definida
    fonte = (os.getenv("SOURCE_NAME") or "itsm").strip().lower()

    blob_service_client = BlobServiceClient.from_connection_string(conn_str_storage)
    container_client = blob_service_client.get_container_client("bronze")

    mapa_blobs = _listar_ultimos_blobs_por_entidade(container_client, fonte)
    if not mapa_blobs:
        logger.warning(
            "Nenhum arquivo .json encontrado no container 'bronze/%s'.", fonte
        )
        return

    # Ordena as entidades para carregar tabelas pai antes das tabelas filhas
    entidades_ordenadas = [e for e in ORDEM_ENTIDADES if e in mapa_blobs] + [
        e for e in sorted(mapa_blobs.keys()) if e not in ORDEM_ENTIDADES
    ]

    tabelas_com_erro = []

    with pyodbc.connect(_obter_string_conexao_sql()) as conn:
        cursor = conn.cursor()
        try:
            for entidade in entidades_ordenadas:
                blob_path = mapa_blobs[entidade]
                logger.info("Baixando blob '%s' para a tabela '%s'...", blob_path, entidade)

                try:
                    blob_client = container_client.get_blob_client(blob_path)
                    conteudo = blob_client.download_blob().readall()
                    registros = json.loads(conteudo.decode("utf-8"))

                    carregar_dados_na_tabela(cursor, entidade, registros)
                    conn.commit()
                except Exception:
                    conn.rollback()
                    tabelas_com_erro.append(entidade)
                    logger.exception(
                        "Erro ao carregar a entidade '%s' a partir de '%s'.",
                        entidade,
                        blob_path,
                    )
        finally:
            cursor.close()

    if tabelas_com_erro:
        raise RuntimeError(
            "Falha ao importar as seguintes tabelas: " + ", ".join(tabelas_com_erro)
        )


@app.timer_trigger(
    schedule="0 30 23 * * *", arg_name="myTimer", run_on_startup=False, use_monitor=False
)
def load_bronze_to_sql(myTimer: func.TimerRequest) -> None:
    importar_todas_as_tabelas_da_bronze()