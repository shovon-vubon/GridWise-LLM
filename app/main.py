from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from pydantic import BaseModel

from app.llm.interpreter import interpret_notes

from app.optimizer.energy_optimizer import EnergyOptimizer

from app.schemas import EnergyRequest

from app.validators.directive_validator import validate_directives


app = FastAPI(
    title="GridWise LLM Energy Optimizer",
    version="1.0.0",
)

BASE_DIR = Path(__file__).resolve().parent


class NotesRequest(BaseModel):
    notes: list[str]


@app.get("/health")
def health_check():
    return {
        "status": "ok",
    }


@app.get("/dashboard", include_in_schema=False)
def dashboard():
    return FileResponse(BASE_DIR / "dashboard.html")


@app.post("/test-llm")
def test_llm(request: NotesRequest):
    result = interpret_notes(request.notes)
    return result


@app.post("/optimize-energy")
def optimize_energy(request: EnergyRequest):
    try:
        llm_response = interpret_notes(request.operator_notes)
        validated = validate_directives(llm_response)

        directives_payload = [
            directive.model_dump(mode="json")
            for directive in validated.directives
        ]

        optimizer = EnergyOptimizer(
            hourly_data=[hour.model_dump() for hour in request.hours],
            battery=request.battery.model_dump(),
            directives=directives_payload,
        )

        optimization_result = optimizer.solve()

        return {
            "scenario_id": request.scenario_id,
            "validation_warnings": validated.warnings,
            "directives": directives_payload,
            "optimization": optimization_result,
        }

    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))