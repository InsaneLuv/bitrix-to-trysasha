from dishka.integrations.fastapi import (
    DishkaRoute
)
from fastapi import APIRouter

router = APIRouter(route_class=DishkaRoute)


@router.get("/")
async def _():
    return "I'm alive!"
