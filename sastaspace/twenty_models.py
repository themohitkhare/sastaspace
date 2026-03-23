# sastaspace/twenty_models.py
"""Pydantic models for Twenty CRM API — typed schemas prevent field-name bugs."""

from __future__ import annotations

from pydantic import BaseModel

# ---- Twenty composite field types ----


class TwentyDomainName(BaseModel):
    primaryLinkUrl: str
    primaryLinkLabel: str = ""


class TwentyPersonName(BaseModel):
    firstName: str
    lastName: str = ""


class TwentyEmails(BaseModel):
    primaryEmail: str


class TwentyNoteBody(BaseModel):
    markdown: str


# ---- Request models ----


class CompanyCreateRequest(BaseModel):
    """Fields accepted by POST /rest/companies."""

    name: str
    domainName: TwentyDomainName


class CompanyUpdateRequest(BaseModel):
    """Fields accepted by PATCH /rest/companies/{id}. All optional."""

    name: str | None = None


class PersonCreateRequest(BaseModel):
    """Fields accepted by POST /rest/people."""

    name: TwentyPersonName
    emails: TwentyEmails
    companyId: str | None = None


class NoteCreateRequest(BaseModel):
    """Fields accepted by POST /rest/notes."""

    title: str
    bodyV2: TwentyNoteBody


class NoteTargetCreateRequest(BaseModel):
    """Fields accepted by POST /rest/noteTargets."""

    noteId: str
    targetObjectNameSingular: str
    targetObjectRecordId: str


# ---- SSE event models ----


class SSEProgressEvent(BaseModel):
    """Standard progress SSE event (crawling, redesigning, deploying)."""

    job_id: str
    message: str
    progress: int


class SSEDoneEvent(BaseModel):
    """Done SSE event — redesign complete."""

    job_id: str
    message: str = "Done!"
    progress: int = 100
    url: str
    subdomain: str


class SSEErrorEvent(BaseModel):
    """Error SSE event."""

    job_id: str
    error: str


class SSEDiscoveryItem(BaseModel):
    """Single discovery item shown during crawl."""

    label: str
    value: str


class SSEDiscoveryEvent(BaseModel):
    """Discovery SSE event — site facts found during crawl."""

    job_id: str
    items: list[SSEDiscoveryItem]


# ---- API response models ----


class JobIdResponse(BaseModel):
    """Response from POST /redesign when job is enqueued."""

    job_id: str


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str
    retry_after: int | None = None


class ContactFormRequest(BaseModel):
    """POST body for /twenty/person contact form."""

    name: str = ""
    email: str
    message: str = ""
    domain: str | None = None
