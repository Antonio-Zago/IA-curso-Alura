import logging
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langchain.chat_models import init_chat_model
from dotenv import load_dotenv
import os

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Claude Opus 5.5 não aceita "temperature" (retorna erro 400); o modelo
# sempre raciocina antes de responder, e max_tokens inclui esse raciocínio.
_llm = init_chat_model(
    model="anthropic:claude-opus-5-5",
    api_key=os.getenv('ANTHROPIC_API_KEY'),
    max_tokens=16000,
)


agente_abertura_conta = create_agent(
    _llm,
    tools=[],
    system_prompt=(
        "Você é um especialista em abertura de contas do banco MDBank. "
        "Ajude o cliente a abrir uma conta e explique os tipos disponíveis."
    ),
)


class ChatRequest(BaseModel):
    message: str
    session_id: str
    client_id: str


app = FastAPI()

@app.post("/send")
async def chat_endpoint(payload: ChatRequest):
    if not payload.message:
        return JSONResponse(status_code=400, content={"error": "Campo 'message' é obrigatório"})

    try:
        logger.info(f"Mensagem recebida no agente abrir_conta: {payload.message}")
        resultado = await agente_abertura_conta.ainvoke(
            {"messages": [HumanMessage(content=payload.message)]}
        )
        # O Claude devolve uma lista de blocos (raciocínio + texto); .text junta só o texto
        resposta = resultado["messages"][-1].text
        logger.info(f"Resposta gerada: {resposta}")
        return {"resposta": resposta}
    except Exception as e:
        logger.exception("Erro ao processar requisição no agente abrir_conta")
        return JSONResponse(status_code=500, content={"error": str(e)})
