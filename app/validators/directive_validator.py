from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


ALLOWED_DIRECTIVES = {
    "solar_reduction",
    "minimum_battery_reserve",
    "no_charge_window",
    "no_discharge_window",
    "max_grid_window",
    "no_op",
}


class StructuredAdjustment(BaseModel):
    hours: List[int] = Field(default_factory=list)
    factor: Optional[float] = None
    minimum_energy_kwh: Optional[float] = None
    max_grid_kwh: Optional[float] = None
    value: Optional[float] = None

    @field_validator("hours")
    @classmethod
    def validate_hours(cls, hours: List[int]) -> List[int]:
        cleaned: List[int] = []
        for hour in hours:
            if not isinstance(hour, int):
                continue
            if 0 <= int(hour) <= 23:
                cleaned.append(int(hour))
        return sorted(set(cleaned))


class DirectiveModel(BaseModel):
    note_index: int = Field(ge=0)
    applies: bool = True
    directive_type: str
    structured_adjustment: Optional[StructuredAdjustment] = None
    explanation: str = ""

    @field_validator("directive_type")
    @classmethod
    def validate_directive_type(cls, directive_type: str) -> str:
        cleaned = str(directive_type).strip()
        if cleaned not in ALLOWED_DIRECTIVES:
            raise ValueError(
                f"Unsupported directive type: {directive_type}. "
                f"Allowed: {sorted(ALLOWED_DIRECTIVES)}"
            )
        return cleaned

    @model_validator(mode="after")
    def validate_structured_payload(self) -> "DirectiveModel":
        if not self.applies:
            return self

        if self.directive_type == "no_op":
            return self

        if self.structured_adjustment is None:
            raise ValueError("structured_adjustment is required for active directives.")

        adjustment = self.structured_adjustment

        if self.directive_type == "solar_reduction":
            if adjustment.hours == []:
                raise ValueError("solar_reduction requires at least one hour.")
            if adjustment.factor is None or not (0 <= float(adjustment.factor) <= 1):
                raise ValueError("solar_reduction factor must be between 0 and 1.")
            return self

        if self.directive_type == "minimum_battery_reserve":
            if adjustment.minimum_energy_kwh is None:
                raise ValueError("minimum_battery_reserve requires minimum_energy_kwh.")
            if float(adjustment.minimum_energy_kwh) < 0:
                raise ValueError("minimum_battery_reserve must be non-negative.")
            return self

        if self.directive_type == "no_charge_window":
            if adjustment.hours == []:
                raise ValueError("no_charge_window requires at least one hour.")
            return self

        if self.directive_type == "no_discharge_window":
            if adjustment.hours == []:
                raise ValueError("no_discharge_window requires at least one hour.")
            return self

        if self.directive_type == "max_grid_window":
            if adjustment.max_grid_kwh is None:
                raise ValueError("max_grid_window requires max_grid_kwh.")
            if float(adjustment.max_grid_kwh) < 0:
                raise ValueError("max_grid_window must be non-negative.")
            return self

        return self


class DirectiveValidationResult(BaseModel):
    directives: List[DirectiveModel] = Field(default_factory=list)
    invalid_count: int = 0
    warnings: List[str] = Field(default_factory=list)


DEFAULT_DIRECTIVE_RESULT = DirectiveValidationResult(
    directives=[],
    invalid_count=0,
    warnings=["No valid directives produced by the LLM."],
)


class DirectiveValidator:
    @staticmethod
    def normalize_payload(payload: Any) -> Dict[str, Any]:
        if payload is None:
            return {"directives": []}

        if isinstance(payload, dict):
            if "directives" in payload and isinstance(payload["directives"], list):
                return payload
            if "directive" in payload and isinstance(payload["directive"], list):
                return {"directives": payload["directive"]}
            return {"directives": [payload]}

        if isinstance(payload, list):
            return {"directives": payload}

        return {"directives": []}

    @classmethod
    def validate(cls, payload: Any) -> DirectiveValidationResult:
        try:
            normalized = cls.normalize_payload(payload)
            raw_directives = normalized.get("directives", [])

            if not isinstance(raw_directives, list):
                return DirectiveValidationResult(
                    directives=[],
                    invalid_count=1,
                    warnings=["The LLM response did not contain a valid directives list."],
                )

            valid_directives: List[DirectiveModel] = []
            warnings: List[str] = []

            for idx, item in enumerate(raw_directives):
                if not isinstance(item, dict):
                    warnings.append(f"Directive at index {idx} is not an object and was ignored.")
                    continue

                try:
                    directive = DirectiveModel.model_validate(item)
                    if directive.applies:
                        valid_directives.append(directive)
                    else:
                        warnings.append(f"Directive at index {idx} was marked as not applicable.")
                except Exception as exc:
                    warnings.append(f"Directive at index {idx} rejected: {str(exc)}")

            return DirectiveValidationResult(
                directives=valid_directives,
                invalid_count=max(0, len(raw_directives) - len(valid_directives)),
                warnings=warnings,
            )

        except Exception as exc:
            return DirectiveValidationResult(
                directives=[],
                invalid_count=1,
                warnings=[f"Validator crash: {str(exc)}"],
            )


def validate_directives(payload: Any) -> DirectiveValidationResult:
    return DirectiveValidator.validate(payload)
