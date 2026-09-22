import logging
import azure.functions as func
import requests

app = func.FunctionApp()


@app.route(route="http_trigger", auth_level=func.AuthLevel.ANONYMOUS)
def http_trigger(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('HTTP trigger recebeu uma requisição.')
    name = req.params.get('name') or req.params.get('nome')

    if name:
        return func.HttpResponse(
            f"Hello, {name}. This HTTP triggered function executed successfully.",
            status_code=200
        )
    return func.HttpResponse(
        "This HTTP triggered function executed successfully. Pass a name in the query string.",
        status_code=200
    )



@app.timer_trigger(schedule="0 */5 * * * *", arg_name="myTimer", run_on_startup=False, use_monitor=False)
def timer_trigger(myTimer: func.TimerRequest) -> None:
    logging.info('Timer trigger iniciado. Executando chamada HTTP...')


    url = "https://funcapp-leonardo0001-bkcchsg4gse9hqb0.canadacentral-01.azurewebsites.net/api/http_trigger?name=ChamadaDoTimer"

    try:
        resposta = requests.get(url)
        logging.info(f"Resposta recebida da HTTP Function: {resposta.text}")
    except Exception as e:
        logging.error(f"Erro ao chamar a HTTP Function: {e}")