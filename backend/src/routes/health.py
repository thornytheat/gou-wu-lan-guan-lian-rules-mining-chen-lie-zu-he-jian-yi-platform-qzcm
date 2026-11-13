from fastapi import APIRouter

from src.controllers import health_controller

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    return health_controller.health()
