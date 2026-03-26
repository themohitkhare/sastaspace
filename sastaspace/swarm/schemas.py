# sastaspace/swarm/schemas.py
from pydantic import BaseModel, Field


class ColorPalette(BaseModel):
    primary: str
    secondary: str
    accent: str
    background: str
    text: str
    headline_font: str = Field(description="Must include web-safe fallback stack")
    body_font: str = Field(description="Must include web-safe fallback stack")
    color_mode: str = Field(description="light|dark", pattern=r"^(light|dark)$")
    roundness: str
    rationale: str = ""


class SectionFragment(BaseModel):
    section_name: str
    html: str
    css: str = ""
    js: str = ""
