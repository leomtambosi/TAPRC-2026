import logging
import azure.functions as func

app = func.FunctionApp()


# =========================================================
# 1. TIMER TRIGGER ORIGINAL
# =========================================================
@app.timer_trigger(
    schedule="0 * * * * *",
    arg_name="myTimer",
    run_on_startup=False,
    use_monitor=False
)
def timer_trigger_taprc(myTimer: func.TimerRequest) -> None:
    if myTimer.past_due:
        logging.info("The timer is past due!")

    logging.info("Python timer trigger function executed.")


# =========================================================
# 2. HTTP TRIGGER ORIGINAL
# =========================================================
@app.route(
    route="http_trigger",
    auth_level=func.AuthLevel.ANONYMOUS
)
def http_trigger(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Python HTTP trigger function processed a request.")

    name = req.params.get("name")

    if name:
        return func.HttpResponse(
            f"Hello, {name}. This HTTP triggered function executed successfully."
        )

    return func.HttpResponse(
        "This HTTP triggered function executed successfully. "
        "Pass a name in the query string or in the request body for a personalized response.",
        status_code=200
    )


# =========================================================
# 3. TIMER TRIGGER 2 (Chama o http_trigger2 diretamente)
# =========================================================
@app.timer_trigger(
    schedule="0 * * * * *",
    arg_name="myTimer",
    run_on_startup=False,
    use_monitor=False
)
def timer_trigger2(myTimer: func.TimerRequest) -> None:
    if myTimer.past_due:
        logging.info("Timer 2 is past due!")

    logging.info("Timer trigger 2 executed, chamando http_trigger2...")

    try:
        # Cria uma requisição simulada enviando o parâmetro 'name'
        req = func.HttpRequest(
            method="GET",
            url="/api/http_trigger2",
            body=b"",
            params={"name": "TimerTrigger2"}
        )

        # Chama a função http_trigger2 diretamente no código
        response = http_trigger2(req)

        logging.info(f"Status da chamada: {response.status_code}")
        logging.info(f"Resposta: {response.get_body().decode('utf-8')}")

    except Exception as e:
        logging.error(f"Erro ao executar http_trigger2: {type(e).__name__}: {e}")


# =========================================================
# 4. HTTP TRIGGER 2
# =========================================================
@app.route(
    route="http_trigger2",
    auth_level=func.AuthLevel.ANONYMOUS
)
def http_trigger2(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Python HTTP trigger 2 function processed a request.")

    name = req.params.get("name")

    if not name:
        try:
            req_body = req.get_json()
            name = req_body.get("name")
        except ValueError:
            pass

    if name:
        response_text = (
            f"Olá, {name}! Esta resposta veio do HTTP Trigger 2 "
            f"processada com sucesso."
        )
        return func.HttpResponse(response_text, status_code=200)

    return func.HttpResponse(
        "HTTP Trigger 2 executado. "
        "Passe um nome na query string ou no corpo da requisição.",
        status_code=200
    )