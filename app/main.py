"""
FastAPI application entrypoint.

CP2 adds the Case/Observation HTTP surface (Phase 4.4, 7.1) over the CP1
Patient State Store, plus a uniform error-response mapping so the frontend
gets predictable status codes rather than 500s for expected domain
conditions (missing case/observation, re-superseding, invalid arrival).
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.db import init_db
from app.api.alerts import router as alerts_router
from app.api.audit import router as audit_router
from app.api.auth import router as auth_router
from app.api.cases import router as cases_router
from app.api.conflicts import router as conflicts_router
from app.api.control_tower import router as control_tower_router
from app.api.demo import router as demo_router
from app.api.diagnostics import router as diagnostics_router
from app.api.observations import router as observations_router
from app.api.ops import router as ops_router
from app.api.queue import router as queue_router
from app.api.resources import router as resources_router
from app.store.event_store import (
    CapacityConflictError,
    InvalidArrivalError,
    NotFoundError,
    ObservationAlreadySupersededError,
    UnknownEventTypeError,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="PatientTriage.ai Backend", version="0.1.0", lifespan=lifespan)

app.include_router(auth_router)
app.include_router(audit_router)
app.include_router(alerts_router)
app.include_router(cases_router)
app.include_router(conflicts_router)
app.include_router(control_tower_router)
app.include_router(demo_router)
app.include_router(observations_router)
app.include_router(queue_router)
app.include_router(resources_router)
app.include_router(diagnostics_router)
app.include_router(ops_router)


@app.get("/health")
def health():
    return {"status": "ok"}


# ----------------------------------------------------------------------
# Error contract: domain exceptions from EventStore map to specific HTTP
# statuses rather than bubbling up as 500s. Each handler is registered
# against its exact exception type; Starlette resolves the most specific
# registered ancestor in the exception's MRO, so subclasses of ValueError
# below (InvalidArrivalError, ObservationAlreadySupersededError,
# UnknownEventTypeError) are matched before the generic ValueError handler.
# ----------------------------------------------------------------------
@app.exception_handler(NotFoundError)
def handle_not_found(request: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(ObservationAlreadySupersededError)
def handle_already_superseded(request: Request, exc: ObservationAlreadySupersededError) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(InvalidArrivalError)
def handle_invalid_arrival(request: Request, exc: InvalidArrivalError) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(CapacityConflictError)
def handle_capacity_conflict(request: Request, exc: CapacityConflictError) -> JSONResponse:
    # Phase 6.2: surfaced to the human as a conflict, never as a silently
    # downgraded acuity -- the response body carries exactly what the
    # charge nurse needs to act (what was needed, why, and candidate actions).
    return JSONResponse(
        status_code=409,
        content={
            "detail": str(exc),
            "resource_type": exc.resource_type.value,
            "candidate_actions": exc.candidate_actions,
        },
    )


@app.exception_handler(UnknownEventTypeError)
def handle_unknown_event_type(request: Request, exc: UnknownEventTypeError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(ValueError)
def handle_value_error(request: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})
