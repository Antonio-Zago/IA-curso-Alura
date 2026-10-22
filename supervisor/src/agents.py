import asyncio
import logging
import os
from typing import List, Dict, Any

import httpx
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import JsonOutputParser
from langgraph.checkpoint.memory import InMemorySaver

logger = logging.getLogger(__name__)
load_dotenv()

# Claude Opus 5.5 não aceita "temperature" (retorna erro 400); o modelo
# sempre raciocina antes de responder, e max_tokens inclui esse raciocínio.
_llm = init_chat_model(
    model="anthropic:claude-opus-5-5",
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    max_tokens=16000,
)


class RouterOutput(BaseModel):
    agents: List[str] = Field(
        description="Lista de agentes que devem responder a pergunta"
    )


parser = JsonOutputParser(pydantic_object=RouterOutput)

AGENTES_DISPONIVEIS = ["cartao_credito", "abrir_conta"]

async def classifique_intencao_do_usuario(
    query: str
) -> List[Dict]:

    prompt = f"""
    Você é o roteador de atendimento do banco MDBank.
    Escolha quais agentes devem responder à pergunta do usuário.
    Pode escolher mais de um, se a pergunta tratar de mais de um assunto,
    ou nenhum, se não tiver relação com os agentes disponíveis.

    Agentes disponiveis:
    cartao_credito
    abrir_conta

    Pergunta: {query}

    {parser.get_format_instructions()}
    """
    
    resposta = await _llm.ainvoke(prompt)

    # O Claude devolve uma lista de blocos (raciocínio + texto); .text junta só o texto
    saida = parser.parse(resposta.text)

    # Descarta nomes que não existem no grafo, senão o Send aponta para um nó inexistente
    agentes_escolhidos = [
        agente for agente in saida.get("agents", [])
        if agente in AGENTES_DISPONIVEIS
    ]

    logger.info(f"Agentes escolhidos pelo roteador: {agentes_escolhidos}")

    return [
        {
            "query" : query,
            "agent" : agente
        }for agente in agentes_escolhidos
    ]

