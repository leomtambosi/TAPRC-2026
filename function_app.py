import logging
import os

import azure.functions as func
import pyodbc

app = func.FunctionApp()
logger = logging.getLogger(__name__)


def extrair_dados(tabela: str) -> None:
    """Conecta ao SQL Server e captura os dados de uma tabela."""

    host_sql = os.getenv("HOST")
    database_sql = os.getenv("DATABASE")
    user_sql = os.getenv("USER")
    password_sql = os.getenv("PASSWORD")

    if not all((host_sql, database_sql, user_sql, password_sql)):
        logger.error("Uma ou mais variáveis de conexão estão ausentes.")
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
            logger.info("Conexão com o banco realizada com sucesso.")

            cursor = conn.cursor()
            try:
                cursor.execute(f"SELECT * FROM {tabela}")
                registros = cursor.fetchall()

                logger.info(
                    "Foram encontrados %s registros na tabela %s.",
                    len(registros),
                    tabela,
                )

                for registro in registros:
                    logger.info("Registro: %s", registro)
            finally:
                cursor.close()

    except pyodbc.Error:
        logger.exception(
            "Erro ao conectar ou consultar a tabela %s.",
            tabela,
        )


@app.timer_trigger(
    schedule="0 * * * * *",
    arg_name="myTimer",
    run_on_startup=False,
    use_monitor=False,
)
def extract_chamado(myTimer: func.TimerRequest) -> None:
    extrair_dados("itsm.chamado")


@app.timer_trigger(
    schedule="0 * * * * *",
    arg_name="myTimer",
    run_on_startup=False,
    use_monitor=False,
)
def extract_fila(myTimer: func.TimerRequest) -> None:
    extrair_dados("itsm.fila")


@app.timer_trigger(
    schedule="0 * * * * *",
    arg_name="myTimer",
    run_on_startup=False,
    use_monitor=False,
)
def extract_sla(myTimer: func.TimerRequest) -> None:
    extrair_dados("itsm.sla")


@app.timer_trigger(
    schedule="0 * * * * *",
    arg_name="myTimer",
    run_on_startup=False,
    use_monitor=False,
)
def extract_solicitante(myTimer: func.TimerRequest) -> None:
    extrair_dados("itsm.solicitante")


@app.timer_trigger(
    schedule="0 * * * * *",
    arg_name="myTimer",
    run_on_startup=False,
    use_monitor=False,
)
def extract_analista(myTimer: func.TimerRequest) -> None:
    extrair_dados("itsm.analista")


@app.timer_trigger(
    schedule="0 * * * * *",
    arg_name="myTimer",
    run_on_startup=False,
    use_monitor=False,
)
def extract_categoria(myTimer: func.TimerRequest) -> None:
    extrair_dados("itsm.categoria")


@app.timer_trigger(
    schedule="0 * * * * *",
    arg_name="myTimer",
    run_on_startup=False,
    use_monitor=False,
)
def extract_chamado_sla(myTimer: func.TimerRequest) -> None:
    extrair_dados("itsm.chamado_sla")


@app.timer_trigger(
    schedule="0 * * * * *",
    arg_name="myTimer",
    run_on_startup=False,
    use_monitor=False,
)
def extract_chamado_status_historico(
    myTimer: func.TimerRequest,
) -> None:
    extrair_dados("itsm.chamado_status_historico")


@app.timer_trigger(
    schedule="0 * * * * *",
    arg_name="myTimer",
    run_on_startup=False,
    use_monitor=False,
)
def extract_cliente_organizacao(
    myTimer: func.TimerRequest,
) -> None:
    extrair_dados("itsm.cliente_organizacao")


@app.timer_trigger(
    schedule="0 * * * * *",
    arg_name="myTimer",
    run_on_startup=False,
    use_monitor=False,
)
def extract_csat_avaliacao(myTimer: func.TimerRequest) -> None:
    extrair_dados("itsm.csat_avaliacao")
