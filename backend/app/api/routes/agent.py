from app.agents.fitness_agent import FitnessAgent
from app.api.deps import get_fitness_agent
from app.schemas.agent import AgentRequest, AgentResponse
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/messages", response_model=AgentResponse)
async def handle_agent_message(
    request: AgentRequest,
    agent: FitnessAgent = Depends(get_fitness_agent),
) -> AgentResponse:
    return await agent.run(request)
