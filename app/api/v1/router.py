from fastapi import APIRouter

from app.api.v1 import properties
from app.api.v1 import admin_properties

router = APIRouter()


@router.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}


router.include_router(properties.router)
router.include_router(admin_properties.router)

api_router = router
