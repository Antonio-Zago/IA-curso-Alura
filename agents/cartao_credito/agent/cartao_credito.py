from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage
import os

load_dotenv()

_llm = init_chat_model(
    model="anthropic:claude-opus-5-5",
    api_key=os.getenv('ANTHROPIC_API_KEY'),
    max_tokens=16000,
)

agente_cartao_credito = create_agent(
    _llm,
    tools=[],
    system_prompt=(
        "Você é um especialista em cartão de crédito do banco MDBank. "
        "Ajude o cliente com dúvidas, solicitação e limites."
    ),
)

async def run_agent(mensagem: str):
    resultado = await agente_cartao_credito.ainvoke(
        {"messages":[HumanMessage(content=mensagem)]}
    )
    # O Claude devolve uma lista de blocos (raciocínio + texto); .text junta só o texto
    return resultado["messages"][-1].text
