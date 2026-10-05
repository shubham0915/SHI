"""GET /api/v1/ports — Port reference data endpoint."""

from fastapi import APIRouter, HTTPException
from src.config import PORT_CONSTRAINTS, VESSEL_SPECS

router = APIRouter()


@router.get("/ports")
async def get_ports():
    """Return all East Coast Indian port infrastructure constraints."""
    return {
        "ports": [
            {"port_name": name, **constraints}
            for name, constraints in PORT_CONSTRAINTS.items()
        ],
        "total": len(PORT_CONSTRAINTS),
    }


@router.get("/ports/{port_name}")
async def get_port(port_name: str):
    """Return constraints for a specific port."""
    port = PORT_CONSTRAINTS.get(port_name)
    if not port:
        raise HTTPException(status_code=404, detail=f"Port '{port_name}' not found")
    return {"port_name": port_name, **port}


@router.get("/vessels")
async def get_vessel_specs():
    """Return all vessel class specifications."""
    return {
        "vessel_classes": [
            {"vessel_class": vc, **specs}
            for vc, specs in VESSEL_SPECS.items()
        ]
    }
