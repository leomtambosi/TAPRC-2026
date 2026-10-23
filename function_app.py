from datetime import datetime
import json
import logging
import os

from azure.storage.blob import BlobServiceClient
import azure.functions as func
import pyodbc

app = func.FunctionApp()
logger = logging.getLogger(__name__)


def salvar_na_camada_bronze(
    tabela: str, registros: list, colunas: list
) -> None:
  """Salva os registros extraídos no container Bronze seguindo a estrutura de partições."""

  # Utiliza a variável de ambiente correta informada
  conn_str_storage = os.getenv("DEPLOYMENT_STORAGE_CONNECTION_STRING")

  if not conn_str_storage:
    logger.error(
        "A string de conexão do Blob Storage (DEPLOYMENT_STORAGE_CONNECTION_STRING)"
        " não está configurada."
    )
    return

  try:
    # Mapeia o nome da tabela (ex: 'itsm.chamado') para a entidade ('chamado')
    fonte, entidade = tabela.split(".")

    # Momento atual em UTC para estruturação das pastas e do arquivo
    agora = datetime.utcnow()
    ano = agora.strftime("%Y")
    mes = agora.strftime("%m")
    dia = agora.strftime("%d")
    timestamp_str = agora.strftime("%Y%m%dT%H%M%SZ")

    # Montagem do caminho (Path) no container 'bronze'
    # Ex: itsm/chamado/ano=2026/mes=10/dia=23/chamado_20261023T100100Z.json
    blob_path = f"{fonte}/{entidade}/ano={ano}/mes={mes}/dia={dia}/{entidade}_{timestamp_str}.json"

    # Converte os registros (tuplas do pyodbc) em uma lista de dicionários
    dados_json = []
    for reg in registros:
      dados_json.append(dict(zip(colunas, reg)))

    # Converte para string JSON formatada (com suporte a datas e caracteres especiais)
    conteudo_json = json.dumps(dados_json, ensure_ascii=False, default=str)

    # Conecta ao Blob Service e envia para o container 'bronze'
    blob_service_client = BlobServiceClient.from_connection_string(
        conn_str_storage
    )
    blob_client = blob_service_client.get_blob_client(
        container="bronze", blob=blob_path
    )

    blob_client.upload_blob(conteudo_json, overwrite=True)
    logger.info("Arquivo salvo com sucesso na camada Bronze: %s", blob_path)

  except Exception:
    logger.exception(
        "Erro ao salvar os dados da tabela %s no Data Lake.", tabela
    )


def extrair_dados(tabela: str) -> None:
  """Conecta ao SQL Server, captura os dados de uma tabela e envia para o Data Lake."""
  host_sql = os.getenv("HOST")
  database_sql = os.getenv("DATABASE")
  user_sql = os.getenv("USER")
  password_sql = os.getenv("PASSWORD")

  if not all((host_sql, database_sql, user_sql, password_sql)):
    logger.error("Uma ou mais variáveis de conexão com o banco estão ausentes.")
    return

  conn_string = (
      "DRIVER={ODBC Driver 18 for SQL Server};"
      f"SERVER={host_sql};"
      f"DATABASE={database_sql};"
      f"UID={user_sql};"
      f"PWD={password_sql};"
      "Encrypt=yes;"
      "TrustServerCertificate=no;"
      "Connection Timeout=30;"
  )

  try:
    with pyodbc.connect(conn_string) as conn:
      logger.info("Conexão com o banco realizada para a tabela %s.", tabela)

      cursor = conn.cursor()
      try:
        cursor.execute(f"SELECT * FROM {tabela}")
        registros = cursor.fetchall()

        # Captura os nomes das colunas retornadas pelo cursor
        colunas = [column[0] for column in cursor.description]

        logger.info(
            "Foram encontrados %s registros na tabela %s.",
            len(registros),
            tabela,
        )

        if registros:
          salvar_na_camada_bronze(tabela, registros, colunas)
        else:
          logger.warning(
              "A tabela %s está vazia. Nenhum arquivo foi gerado.", tabela
          )

      finally:
        cursor.close()

  except pyodbc.Error:
    logger.exception("Erro ao conectar ou consultar a tabela %s.", tabela)


# --- Funções de Trigger (Timer a cada 1 minuto) ---


@app.timer_trigger(
    schedule="0 * * * * *", arg_name="myTimer", run_on_startup=False, use_monitor=False
)
def extract_chamado(myTimer: func.TimerRequest) -> None:
  extrair_dados("itsm.chamado")


@app.timer_trigger(
    schedule="0 * * * * *", arg_name="myTimer", run_on_startup=False, use_monitor=False
)
def extract_fila(myTimer: func.TimerRequest) -> None:
  extrair_dados("itsm.fila")


@app.timer_trigger(
    schedule="0 * * * * *", arg_name="myTimer", run_on_startup=False, use_monitor=False
)
def extract_sla(myTimer: func.TimerRequest) -> None:
  extrair_dados("itsm.sla")


@app.timer_trigger(
    schedule="0 * * * * *", arg_name="myTimer", run_on_startup=False, use_monitor=False
)
def extract_solicitante(myTimer: func.TimerRequest) -> None:
  extrair_dados("itsm.solicitante")


@app.timer_trigger(
    schedule="0 * * * * *", arg_name="myTimer", run_on_startup=False, use_monitor=False
)
def extract_analista(myTimer: func.TimerRequest) -> None:
  extrair_dados("itsm.analista")


@app.timer_trigger(
    schedule="0 * * * * *", arg_name="myTimer", run_on_startup=False, use_monitor=False
)
def extract_categoria(myTimer: func.TimerRequest) -> None:
  extrair_dados("itsm.categoria")


@app.timer_trigger(
    schedule="0 * * * * *", arg_name="myTimer", run_on_startup=False, use_monitor=False
)
def extract_chamado_sla(myTimer: func.TimerRequest) -> None:
  extrair_dados("itsm.chamado_sla")


@app.timer_trigger(
    schedule="0 * * * * *", arg_name="myTimer", run_on_startup=False, use_monitor=False
)
def extract_chamado_status_historico(myTimer: func.TimerRequest) -> None:
  extrair_dados("itsm.chamado_status_historico")


@app.timer_trigger(
    schedule="0 * * * * *", arg_name="myTimer", run_on_startup=False, use_monitor=False
)
def extract_cliente_organizacao(myTimer: func.TimerRequest) -> None:
  extrair_dados("itsm.cliente_organizacao")


@app.timer_trigger(
    schedule="0 * * * * *", arg_name="myTimer", run_on_startup=False, use_monitor=False
)
def extract_csat_avaliacao(myTimer: func.TimerRequest) -> None:
  extrair_dados("itsm.csat_avaliacao")