from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langchain.chat_models import init_chat_model
from dotenv import load_dotenv
import os

load_dotenv()

# Claude Opus 5.5 não aceita "temperature" (retorna erro 400); o modelo
# sempre raciocina antes de responder, e max_tokens inclui esse raciocínio.
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
    )
)

agente_abertura_conta = create_agent(
    _llm,
    tools=[],
    system_prompt=(
        "Você é um especialista em abertura de contas do banco MDBank. "
        "Ajude o cliente a abrir uma conta e explique os tipos disponíveis."
    ),
)

def classificar_pergunta(pergunta: str) -> str:
    prompt = f"""
    Classifique a intenção do usuário.

    Possíveis agentes:
    cartao_credito
    abrir_conta

    Pergunta: {pergunta}

    Responda apenas com o nome do agente.
    """
    resposta = _llm.invoke(prompt)
    # O Claude devolve uma lista de blocos (raciocínio + texto); .text junta só o texto
    return resposta.text.strip().lower()


async def executar_supervisor(texto_usuario: str) -> str:
    agente = classificar_pergunta(texto_usuario)

    if agente == "cartao_credito":
        resultado = agente_cartao_credito.invoke(
            {"messages": [HumanMessage(content=texto_usuario)]}
        )
    elif agente == "abrir_conta":
        resultado = agente_abertura_conta.invoke(
            {"messages": [HumanMessage(content=texto_usuario)]}
        )
    else:
        return "Não consegui entender sua solicitação"

    mensagem_ia = resultado["messages"][-1]
    return mensagem_ia.text
