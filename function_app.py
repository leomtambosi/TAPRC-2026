import logging
import azure.functions as func
import os
import pyodbc

app = func.FunctionApp()


@app.timer_trigger(
    schedule="0 * * * * *",
    arg_name="myTimer",
    run_on_startup=False,
    use_monitor=False
)
def extract_chamado(myTimer: func.TimerRequest) -> None:

    # Variáveis de ambiente
    host_sql = os.getenv("HOST")
    database_sql = os.getenv("DATABASE")
    user_sql = os.getenv("USER")
    password_sql = os.getenv("PASSWORD")

    # String de conexão
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
        # Conectar ao banco
        with pyodbc.connect(conn_string) as conn:

            logging.info("Conexão com o banco realizada com sucesso.")

            cursor = conn.cursor()

            # Capturar os dados da tabela chamado
            cursor.execute("""
                SELECT *
                FROM itsm.chamado
            """)

            registros = cursor.fetchall()

            logging.info(
                f"Foram encontrados {len(registros)} registros "
                f"na tabela itsm.chamado."
            )

            # Exibir os dados capturados
            for registro in registros:
                logging.info(f"Registro: {registro}")

    except pyodbc.Error as error:
        logging.error(
            f"Erro ao conectar ou consultar o banco: {error}"
        )