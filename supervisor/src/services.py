import logging
import httpx
import uuid

from langgraph.graph import StateGraph, START, END
from langgraph.types import Send
from typing import TypedDict, Annotated
from operator import add

from a2a.client import A2ACardResolver, ClientFactory, ClientConfig
from a2a.types import Message, Part, Role, TextPart


from src.agents import classifique_intencao_do_usuario

logger = logging.getLogger(__name__)

HTTPX_CLIENT = httpx.AsyncClient(timeout=30)

AGENTS = {
    "cartao_credito": "http://cartao_credito_agent:8000",
    "abrir_conta": "http://abrir_conta_agent:8000"
}

CLIENT_CACHE = {}


class State(TypedDict):
    query: str
    session_id: str
    client_id: str
    responses: Annotated[list[str], add]

async def request_agent(message: str, agent_url: str) -> str:
    if agent_url not in CLIENT_CACHE:
        logger.info(f"Descobrindo AgentCard em {agent_url}")

        resolver = A2ACardResolver(
            http_client=HTTPX_CLIENT,
            base_url=agent_url,
        )

        agent_card = await resolver.get_agent_card()
        logger.info(f"Agent encontrado: {agent_card.name}")

        config = ClientConfig(
            http_client=HTTPX_CLIENT,
            streaming=False
        )
        factory = ClientFactory(config)
        CLIENT_CACHE[agent_url] = factory.create(agent_card)

    client = CLIENT_CACHE[agent_url]

    msg = Message(
        role=Role.user,
        message_id=str(uuid.uuid4()),
        parts=[Part(root=TextPart(text=message))],
    )

    logger.info(f"Enviando mensagem para agente: {message}")

    async for event in client.send_message(msg):
        if isinstance(event, Message):
            for part in event.parts:
                if part.root.kind == "text":
                    return part.root.text
                
    return "Sem resposta do agente."


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
    
    query = state.get("query","")

    logger.info("Executando agente CARTAO_CREDITO")

    resposta = await request_agent(
        query, 
        AGENTS["cartao_credito"]
    )
    return {"responses": [resposta]}

# -----------------------------
# NODE ABRIR CONTA
# -----------------------------


async def abrir_conta_node(state: State):
    query = state.get("query","")

    logger.info("Executando agente ABRIR_CONTA")

    resposta = await request_agent(query, AGENTS["abrir_conta"])
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
