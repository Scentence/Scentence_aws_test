from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

try:  # pragma: no cover - fallback for script execution
    from .agent.database import PerfumeRepository
    from .agent.graph import analyze_user_input, analyze_user_query
    from .agent.schemas import LayeringRequest, LayeringResponse, UserQueryRequest, UserQueryResponse
    from .agent.tools import rank_recommendations
except ImportError:  # pragma: no cover
    from agent.database import PerfumeRepository
    from agent.graph import analyze_user_input, analyze_user_query
    from agent.schemas import LayeringRequest, LayeringResponse, UserQueryRequest, UserQueryResponse
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


@app.post("/layering/analyze", response_model=UserQueryResponse)
def layering_analyze(payload: UserQueryRequest) -> UserQueryResponse:
    preferences = analyze_user_input(payload.user_text)
    keywords = preferences.keywords
    analysis = analyze_user_query(payload.user_text, repository, preferences)
    recommendation = None
    note = None
    base_perfume_id = None

    if analysis.pairing_analysis:
        recommendation = analysis.pairing_analysis.result
        if analysis.detected_pair:
            base_perfume_id = analysis.detected_pair.base_perfume_id
    elif analysis.detected_perfumes:
        base_perfume_id = analysis.detected_perfumes[0].perfume_id
        recommendations, _ = rank_recommendations(base_perfume_id, keywords, repository)
        if recommendations:
            recommendation = recommendations[0]
        else:
            note = "No feasible layering options found for the detected base perfume."
    else:
        note = "No perfume names detected from the query."

    return UserQueryResponse(
        raw_text=payload.user_text,
        keywords=keywords,
        base_perfume_id=base_perfume_id,
        detected_perfumes=analysis.detected_perfumes,
        detected_pair=analysis.detected_pair,
        recommendation=recommendation,
        note=note,
    )
