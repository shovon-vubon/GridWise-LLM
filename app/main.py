from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse

from pydantic import BaseModel

from app.llm.interpreter import interpret_notes

from app.optimizer.energy_optimizer import EnergyOptimizer

from app.schemas import EnergyRequest

from app.validators.directive_validator import validate_directives


app = FastAPI(
    title="GridWise LLM Energy Optimizer",
    version="1.0.0",
)


class NotesRequest(BaseModel):
    notes: list[str]


@app.get("/", include_in_schema=False)
def docs_redirect():
    return RedirectResponse(url="/docs")


@app.get("/health")
def health_check():
    return {
        "status": "ok",
    }


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