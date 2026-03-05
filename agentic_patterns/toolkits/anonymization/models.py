"""Data models, enums, and default policy for PHI anonymization (i2b2/UTHealth 2014 taxonomy)."""

from enum import Enum
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field


class PhiLabel(str, Enum):
    """i2b2/UTHealth 2014 de-identification categories."""

    # Names
    NAME_PATIENT = "NAME_PATIENT"
    NAME_DOCTOR = "NAME_DOCTOR"
    NAME_USERNAME = "NAME_USERNAME"

    # Profession
    PROFESSION = "PROFESSION"

    # Location
    LOCATION_HOSPITAL = "LOCATION_HOSPITAL"
    LOCATION_ORGANIZATION = "LOCATION_ORGANIZATION"
    LOCATION_STREET = "LOCATION_STREET"
    LOCATION_CITY = "LOCATION_CITY"
    LOCATION_STATE = "LOCATION_STATE"
    LOCATION_COUNTRY = "LOCATION_COUNTRY"
    LOCATION_ZIP = "LOCATION_ZIP"
    LOCATION_OTHER = "LOCATION_OTHER"

    # Age
    AGE = "AGE"

    # Date
    DATE = "DATE"

    # Contact
    CONTACT_PHONE = "CONTACT_PHONE"
    CONTACT_FAX = "CONTACT_FAX"
    CONTACT_EMAIL = "CONTACT_EMAIL"
    CONTACT_URL = "CONTACT_URL"
    CONTACT_IPADDR = "CONTACT_IPADDR"

    # Identifiers
    ID_SSN = "ID_SSN"
    ID_MEDICALRECORD = "ID_MEDICALRECORD"
    ID_HEALTHPLAN = "ID_HEALTHPLAN"
    ID_ACCOUNT = "ID_ACCOUNT"
    ID_LICENSE = "ID_LICENSE"
    ID_VEHICLE = "ID_VEHICLE"
    ID_DEVICE = "ID_DEVICE"
    ID_BIOID = "ID_BIOID"
    ID_IDNUM = "ID_IDNUM"

    def __str__(self) -> str:
        return self.value


class Operator(str, Enum):
    """Redaction operators."""

    MASK = "MASK"
    TAG = "TAG"
    PSEUDONYM = "PSEUDONYM"
    DATE_SHIFT = "DATE_SHIFT"

    def __str__(self) -> str:
        return self.value


class EntitySpan(BaseModel):
    """A detected PHI span in text."""

    start: int
    end: int
    label: PhiLabel
    score: float = 1.0
    source: str = "unknown"

    def __str__(self) -> str:
        return f"{self.label.value}[{self.start}:{self.end}] score={self.score:.2f} src={self.source}"


class OperatorSpec(BaseModel):
    """How to redact a particular PHI label."""

    operator: Operator
    params: dict = Field(default_factory=dict)


class AnonymizationPolicy(BaseModel):
    """Maps each PHI label to a redaction operator, plus global thresholds."""

    operators: dict[PhiLabel, OperatorSpec] = Field(default_factory=dict)
    min_score: float = 0.5
    allowlist: set[str] = Field(default_factory=set)

    def get_operator(self, label: PhiLabel) -> OperatorSpec:
        return self.operators.get(label, OperatorSpec(operator=Operator.MASK))


class AnonymizationResult(BaseModel):
    """Output of anonymization: original text, redacted text, and detected spans."""

    original_text: str
    redacted_text: str
    detection_spans: list[EntitySpan] = Field(default_factory=list)
    audit_spans: list[EntitySpan] = Field(default_factory=list)

    def __str__(self) -> str:
        n_det = len(self.detection_spans)
        n_aud = len(self.audit_spans)
        return f"AnonymizationResult(detections={n_det}, audit_findings={n_aud}, len={len(self.redacted_text)})"


@runtime_checkable
class Detector(Protocol):
    """Protocol for PHI detectors."""

    def detect(self, text: str, meta: dict | None = None) -> list[EntitySpan]: ...


def default_phi_policy() -> AnonymizationPolicy:
    """HIPAA Safe Harbor default policy using i2b2 categories.

    All labels use PSEUDONYM (realistic fake data) except dates which use DATE_SHIFT
    to preserve temporal intervals.
    """
    pseudo = OperatorSpec(operator=Operator.PSEUDONYM)
    date_shift = OperatorSpec(operator=Operator.DATE_SHIFT, params={"max_days": 30})

    operators: dict[PhiLabel, OperatorSpec] = {label: pseudo for label in PhiLabel}
    operators[PhiLabel.DATE] = date_shift
    return AnonymizationPolicy(operators=operators)
