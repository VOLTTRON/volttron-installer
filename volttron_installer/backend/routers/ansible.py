from fastapi import APIRouter, Depends
from ..services.inventory_service import InventoryService

# Make sure we're using a single instance of InventoryService
_inventory_service = None

def get_inventory_service():
    global _inventory_service
    if _inventory_service is None:
        _inventory_service = InventoryService()
    return _inventory_service

router = APIRouter()

@router.post("/inventory")
async def add_host_to_inventory(host: dict, inventory: InventoryService = Depends(get_inventory_service)):
    await inventory.add_host(host["id"], host)
    return {"status": "success"}
