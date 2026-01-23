import logging
import os
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

try:  # pragma: no cover - fallback for script execution
    from .agent.database import LayeringDataError, PerfumeRepository, check_db_health
    from .agent.graph import analyze_user_input, analyze_user_query, suggest_perfume_options
    from .agent.schemas import (
        LayeringError,
        LayeringErrorResponse,
        LayeringRequest,
        LayeringResponse,
        UserQueryRequest,
        UserQueryResponse,
    )
    from .agent.tools import rank_recommendations
except ImportError:  # pragma: no cover
    from agent.database import LayeringDataError, PerfumeRepository, check_db_health
    from agent.graph import analyze_user_input, analyze_user_query, suggest_perfume_options
    from agent.schemas import (
        LayeringError,
        LayeringErrorResponse,
        LayeringRequest,
        LayeringResponse,
        UserQueryRequest,
        UserQueryResponse,
    )
    from agent.tools import rank_recommendations


app = FastAPI(title="Layering Service")
logger = logging.getLogger("layering")
DEBUG_ERROR_DETAILS = os.getenv("LAYERING_DEBUG_ERRORS", "").lower() in {
    "true",
    "1",
    "yes",
}

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

repository: Optional[PerfumeRepository] = None


def get_repository() -> PerfumeRepository:
    global repository
    if repository is not None:
        return repository
    repository = PerfumeRepository()
    return repository


def build_error_response(
    *,
    code: str,
    message: str,
    step: str,
    retriable: bool,
    details: Optional[str] = None,
) -> LayeringErrorResponse:
    return LayeringErrorResponse(
        error=LayeringError(
            code=code,
            message=message,
            step=step,
            retriable=retriable,
            details=details if DEBUG_ERROR_DETAILS else None,
        )
    )


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Layering service is running!"}


@app.get("/health")
def health() -> dict[str, str]:
    db_status = "ok" if check_db_health() else "degraded"
    if repository is None:
        repo_status = "uninitialized"
    else:
        repo_status = "ok" if repository.count > 0 else "degraded"
    status = "ok" if db_status == "ok" and repo_status == "ok" else "degraded"
    return {
        "status": status,
        "service": "layering",
        "db": db_status,
        "repository": repo_status,
    }


@app.post("/layering/recommend", response_model=LayeringResponse)
def layering_recommend(payload: LayeringRequest) -> LayeringResponse:
    try:
        repo = get_repository()
        recommendations, total_available = rank_recommendations(
            payload.base_perfume_id,
            payload.keywords,
            repo,
        )
    except LayeringDataError as exc:
        logger.exception("Layering data error during recommendation")
        error_payload = build_error_response(
            code=exc.code,
            message=exc.message,
            step=exc.step,
            retriable=exc.retriable,
            details=exc.details,
        )
        raise HTTPException(
            status_code=503,
            detail=error_payload.model_dump(exclude_none=True),
        ) from exc
    except KeyError as exc:
        error_payload = build_error_response(
            code="PERFUME_NOT_FOUND",
            message="요청한 향수를 찾지 못했습니다.",
            step="perfume_lookup",
            retriable=False,
            details=str(exc),
        )
        raise HTTPException(
            status_code=404,
            detail=error_payload.model_dump(exclude_none=True),
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error during recommendation")
        error_payload = build_error_response(
            code="RANKING_FAILED",
            message="추천 계산에 실패했습니다.",
            step="ranking",
            retriable=False,
            details=str(exc),
        )
        raise HTTPException(
            status_code=500,
            detail=error_payload.model_dump(exclude_none=True),
        ) from exc

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
    try:
        repo = get_repository()
        preferences = analyze_user_input(payload.user_text)
        keywords = preferences.keywords
        analysis = analyze_user_query(payload.user_text, repo, preferences)
        recommendation = None
        note = None
        base_perfume_id = None
        clarification_prompt = None
        clarification_options: list[str] = []

        if analysis.pairing_analysis:
            recommendation = analysis.pairing_analysis.result
            if analysis.detected_pair:
                base_perfume_id = analysis.detected_pair.base_perfume_id
        elif analysis.detected_perfumes:
            base_perfume_id = analysis.detected_perfumes[0].perfume_id
            recommendations, _ = rank_recommendations(base_perfume_id, keywords, repo)
            if recommendations:
                recommendation = recommendations[0]
            else:
                note = "No feasible layering options found for the detected base perfume."
        else:
            note = "No perfume names detected from the query."
            clarification_prompt = "레이어링할 향수 이름을 알려주세요. 예: CK One, Wood Sage & Sea Salt"
            clarification_options = suggest_perfume_options(payload.user_text, repo)
    except LayeringDataError as exc:
        logger.exception("Layering data error during analysis")
        error_payload = build_error_response(
            code=exc.code,
            message=exc.message,
            step=exc.step,
            retriable=exc.retriable,
            details=exc.details,
        )
        raise HTTPException(
            status_code=503,
            detail=error_payload.model_dump(exclude_none=True),
        ) from exc
    except KeyError as exc:
        error_payload = build_error_response(
            code="PERFUME_NOT_FOUND",
            message="요청한 향수를 찾지 못했습니다.",
            step="perfume_lookup",
            retriable=False,
            details=str(exc),
        )
        raise HTTPException(
            status_code=404,
            detail=error_payload.model_dump(exclude_none=True),
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error during analysis")
        error_payload = build_error_response(
            code="ANALYSIS_FAILED",
            message="자연어 분석에 실패했습니다.",
            step="analysis",
            retriable=False,
            details=str(exc),
        )
        raise HTTPException(
            status_code=500,
            detail=error_payload.model_dump(exclude_none=True),
        ) from exc

    return UserQueryResponse(
        raw_text=payload.user_text,
        keywords=keywords,
        base_perfume_id=base_perfume_id,
        detected_perfumes=analysis.detected_perfumes,
        detected_pair=analysis.detected_pair,
        recommendation=recommendation,
        clarification_prompt=clarification_prompt,
        clarification_options=clarification_options,
        note=note,
    )
