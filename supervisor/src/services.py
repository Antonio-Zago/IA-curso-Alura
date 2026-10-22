import logging
import httpx

from langgraph.graph import StateGraph, START, END
from langgraph.types import Send
from typing import TypedDict, Annotated
from operator import add


from src.agents import classifique_intencao_do_usuario

logger = logging.getLogger(__name__)

# Nome do serviço de cada agente no docker-compose.yml (é o hostname na rede do Docker)
AGENTS = {
    "cartao_credito": "cartao_credito_agent",
    "abrir_conta": "abrir_conta_agent",
}

# Os agentes raciocinam antes de responder, então a resposta pode demorar
TIMEOUT_AGENTES = httpx.Timeout(120.0)

class State(TypedDict):
    query: str
    session_id: str
    client_id: str
    responses: Annotated[list[str], add]

async def request_agent(state: State, agent: str) -> str:
    # Dentro da rede do Docker os containers escutam na 8000;
    # 8081/8082 são as portas expostas só para a máquina host
    url = f"http://{agent}:8000/send"
    payload = {
        "message": state["query"],
        "session_id": state["session_id"],
        "client_id": state["client_id"],
    }

    try:
        logger.info(
            f"Enviando requisição para {agent} em {url} com payload: {payload}"
        )

        async with httpx.AsyncClient(timeout=TIMEOUT_AGENTES) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()

        data = response.json()

        logger.info(
            f"Resposta recebida do {agent}: {data}"
        )

        return data.get("resposta", "Resposta não encontrada")
    except httpx.HTTPError:
        logger.exception(f"Erro ao chamar o agente {agent}")
        return "Desculpe, não consegui obter resposta deste atendimento agora."


async def no_de_roteamento(state: State):
    query = state.get("query", "")
    classifications = await classifique_intencao_do_usuario(query)
    logger.info(f"Classificação: {classifications}")
    return [
        Send(c["agent"], {
            "query": c["query"],
            "session_id": state["session_id"],
            "client_id": state["client_id"],
        })
        for c in classifications
    ]

# -----------------------------
# NODE CARTAO
# -----------------------------


async def cartao_credito_node(state: State):
    logger.info("Executando agente CARTAO_CREDITO")
    resposta = await request_agent(state, AGENTS["cartao_credito"])
    return {"responses": [resposta]}

# -----------------------------
# NODE ABRIR CONTA
# -----------------------------


async def abrir_conta_node(state: State):
    logger.info("Executando agente ABRIR_CONTA")
    resposta = await request_agent(state, AGENTS["abrir_conta"])
    return {"responses": [resposta]}

# -----------------------------
# BUILD DO GRAFO
# -----------------------------
builder = StateGraph(State)
builder.add_node("cartao_credito", cartao_credito_node)
builder.add_node("abrir_conta", abrir_conta_node)
builder.add_conditional_edges(START, no_de_roteamento)
builder.add_edge("cartao_credito", END)
builder.add_edge("abrir_conta", END)
graph = builder.compile()

# -----------------------------
# EXECUTOR DO SUPERVISOR (NORMAL)
# -----------------------------


async def executar_supervisor(
    texto_usuario: str, session_id: str = "default", client_id: str = "default"
):
    input_state: State = {
        "query": texto_usuario,
        "session_id": session_id,
        "client_id": client_id,
        "responses": [],
    }
    result = await graph.ainvoke(input_state)

    if not result["responses"]:
        return (
            "Não consegui entender sua solicitação. Posso ajudar com abertura de "
            "contas e cartão de crédito."
        )
    return "\n\n".join(result["responses"])
