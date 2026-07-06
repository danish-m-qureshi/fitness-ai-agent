from app.api.routes import (
    agent,
    ai,
    body_weight_logs,
    daily_summaries,
    debug,
    goals,
    health,
    meals,
    memory,
    nutrition,
    status,
    summaries,
    users,
    whatsapp,
    workouts,
)
from fastapi import APIRouter

api_router = APIRouter()

api_router.include_router(agent.router)
api_router.include_router(ai.router)
api_router.include_router(users.router)
api_router.include_router(health.router)
api_router.include_router(meals.router)
api_router.include_router(memory.router)
api_router.include_router(nutrition.router)
api_router.include_router(whatsapp.router)
api_router.include_router(workouts.router)
api_router.include_router(goals.router)
api_router.include_router(daily_summaries.router)
api_router.include_router(summaries.router)
api_router.include_router(body_weight_logs.router)
api_router.include_router(debug.router)
api_router.include_router(status.router)
