from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

try:  # pragma: no cover - fallback for script execution
    from .agent.database import PerfumeRepository
    from .agent.schemas import LayeringRequest, LayeringResponse
    from .agent.tools import rank_recommendations
except ImportError:  # pragma: no cover
    from agent.database import PerfumeRepository
    from agent.schemas import LayeringRequest, LayeringResponse
    from agent.tools import rank_recommendations


app = FastAPI(title="Layering Service")

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

repository = PerfumeRepository()


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Layering service is running!"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "layering"}


@app.post("/layering/recommend", response_model=LayeringResponse)
def layering_recommend(payload: LayeringRequest) -> LayeringResponse:
    try:
        recommendations, total_available = rank_recommendations(
            payload.base_perfume_id,
            payload.keywords,
            repository,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    note = None
    if total_available < 3:
        note = (
            f"Only {total_available} layering option(s) available after feasibility checks."
        )

    return LayeringResponse(
        base_perfume_id=payload.base_perfume_id,
        keywords=payload.keywords,
        total_available=total_available,
        recommendations=recommendations,
        note=note,
    )
