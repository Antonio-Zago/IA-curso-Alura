from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from executor import CartaoCreditoExecutor

# Definição do skill
skill = AgentSkill(
    id="cartao_credito",
    name="Cartão de Crédito MDBank",
    description="Ajuda clientes com dúvidas, solicitação e limites de cartão de crédito.",
    tags=[
        "cartão",
        "cartão de crédito",
        "solicitar cartão",
        "limite",
        "aumento de limite",
        "fatura",
        "anuidade",
    ],
    examples=[
        "quero um cartão de crédito",
        "como aumento o limite do meu cartão?",
        "qual a anuidade do cartão?",
        "como pago a fatura?",
        "quais cartões vocês oferecem?",
    ],
)

# Agent Card
agent_card = AgentCard(
    name="Agente de Cartão de Crédito MDBank",
    description="Especialista em cartões de crédito do MDBank.",
    url="http://cartao_credito_agent:8000/",
    default_input_modes=["text"],
    default_output_modes=["text"],
    skills=[skill],
    version="1.0.0",
    capabilities=AgentCapabilities(),
)

# Request Handler
handler = DefaultRequestHandler(
    agent_executor=CartaoCreditoExecutor(),
    task_store=InMemoryTaskStore(),
)

# A2A Application
server = A2AStarletteApplication(
    http_handler=handler,
    agent_card=agent_card,
)

# EXPOSIÇÃO DO APP PARA O UVICORN
app = server.build()
