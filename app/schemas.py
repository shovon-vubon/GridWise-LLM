from pydantic import BaseModel
from typing import List, Optional


# -----------------------------
# Input Models
# -----------------------------

class HourData(BaseModel):

    hour: int

    demand_kwh: float

    solar_kwh: float

    tariff_bdt_per_kwh: float



class Battery(BaseModel):

    capacity_kwh: float

    initial_energy_kwh: float

    minimum_energy_kwh: float

    max_charge_kwh_per_hour: float

    max_discharge_kwh_per_hour: float



class EnergyRequest(BaseModel):

    scenario_id: str

    operator_notes: List[str]

    hours: List[HourData]

    battery: Battery



# -----------------------------
# LLM Directive Output
# -----------------------------

class Directive(BaseModel):

    note_index: int

    applies: bool

    directive_type: str

    structured_adjustment: Optional[dict]

    explanation: str