"use client";

import { useState, useMemo, useRef, useEffect } from "react";
import { useSession } from "next-auth/react"; // 카카오 로그인 세션
import Link from "next/link";
import AccordWheel from "@/components/layering/AccordWheel";
import { BACKEND_ACCORDS, ACCORD_LABELS } from "@/lib/accords";
import LayeringPerfumePicker from "@/components/layering/LayeringPerfumePicker"; // 내 향수 불러오기
import PerfumeInfoModal from "@/components/layering/PerfumeInfoModal";
import Sidebar from "@/components/common/sidebar";
import LayeringPerfumeSearchModal from "@/components/layering/LayeringPerfumeSearchModal";

// ==================== 타입 정의 ====================

/**
 * 레이어링 추천 후보 향수 정보
 */
type LayeringCandidate = {
  perfume_id: string;        // 향수 고유 ID
  perfume_name: string;       // 향수 이름
  perfume_brand: string;      // 브랜드명
  image_url?: string | null;  // 이미지 URL
  concentration?: string | null; // 농도
  total_score: number;        // 추천 점수
  spray_order: string[];      // 분사 순서 (향수 이름 배열)
  analysis: string;           // 추천 이유 분석
  layered_vector: number[];   // 레이어링 결과 어코드 벡터 (21개)
};

/**
 * 레이어링 추천 응답 (다중 추천)
 */
type LayeringResponse = {
  base_perfume?: PerfumeSummary | null;
  base_perfume_id: string;              // 베이스 향수 ID
  keywords: string[];                    // 추출된 키워드
  total_available: number;               // 사용 가능한 추천 개수
  recommendations: LayeringCandidate[];  // 추천 향수 목록
  note?: string | null;                  // 추가 노트
};

type PerfumeSummary = {
  perfume_id: string;
  perfume_name: string;
  perfume_brand: string;
  image_url?: string | null;
  concentration?: string | null;
};

type PerfumeInfo = {
  perfume_id: string;
  perfume_name: string;
  perfume_brand: string;
  image_url?: string | null;
  concentration?: string | null;
  gender?: string | null;
  accords: string[];
  seasons: string[];
  occasions: string[];
  top_notes: string[];
  middle_notes: string[];
  base_notes: string[];
};

/**
 * 자연어 질문 분석 응답
 */
type UserQueryResponse = {
  raw_text: string;                      // 원본 질문 텍스트
  keywords: string[];                    // 추출된 키워드
  base_perfume_id?: string | null;       // 베이스 향수 ID
  base_perfume?: PerfumeSummary | null;
  detected_pair?: {                      // 감지된 향수 쌍
    base_perfume_id?: string | null;
    candidate_perfume_id?: string | null;
  } | null;
  recommendation?: LayeringCandidate | null;  // 추천 결과 (단일)
  recommended_perfume_info?: PerfumeInfo | null;
  brand_name?: string | null;
  brand_best_perfume?: PerfumeSummary | null;
  brand_best_score?: number | null;
  brand_best_reason?: string | null;
  similar_perfumes?: PerfumeSummary[];
  clarification_prompt?: string | null;       // 명확화 요청 메시지
  clarification_options?: string[];           // 명확화 옵션 목록
  note?: string | null;                       // 추가 노트
  save_results?: {                            // 저장 결과
    target: string;
    saved: boolean;
    saved_count: number;
    message?: string | null;
  }[];
};

/**
 * 피드백 저장 응답
 */
type FeedbackResponse = {
  save_result: {
    target: string;           // 저장 대상
    saved: boolean;           // 저장 성공 여부
    saved_count: number;      // 저장된 개수
    message?: string | null;  // 추가 메시지
  };
};

/**
 * 레이어링 API 오류 정보
 */
type LayeringError = {
  code: string;           // 오류 코드
  message: string;        // 오류 메시지
  step: string;           // 오류 발생 단계
  retriable?: boolean;    // 재시도 가능 여부
  details?: string | null; // 상세 정보
};

/**
 * 레이어링 API 오류 응답
 */
type LayeringErrorResponse = {
  error?: LayeringError;
  detail?: { error?: LayeringError };
};

// ==================== API 설정 ====================

/**
 * 환경변수에서 레이어링 API URL 추출 및 정규화
 * - 후행 슬래시 제거
 * - "/layering" 경로 중복 제거
 * - 기본값으로 "/api/layering" 사용
 */
const getApiBase = () => {
  const apiHost = process.env.NEXT_PUBLIC_LAYERING_API_URL;
  if (!apiHost) return "/api/layering";

  const normalized = apiHost.replace(/\/+$/, "");
  const withoutLayering = normalized.endsWith("/layering")
    ? normalized.slice(0, -9)
    : normalized;

  return `${withoutLayering}/layering`;
};

const apiBase = getApiBase();

// ==================== 유틸리티 함수 ====================

/**
 * 로컬 스토리지에서 현재 회원 ID 추출
 * @param sessionUserId - 카카오 세션의 user.id (있으면 우선 사용)
 * @returns 회원 ID (로그인하지 않은 경우 0)
 */
const getMemberId = (sessionUserId?: string | number | null): number => {
  // 카카오 로그인 세션 우선
  if (sessionUserId) {
    return typeof sessionUserId === 'number' ? sessionUserId : parseInt(sessionUserId, 10);
  }
  if (typeof window === "undefined") {
    return 0;
  }
  // 로컬 로그인 확인
  try {
    const localAuth = localStorage.getItem("localAuth");
    if (!localAuth) return 0;

    const parsed = JSON.parse(localAuth);
    return parsed?.memberId ? parseInt(parsed.memberId, 10) : 0;
  } catch (error) {
    console.error("Member ID Parsing Error:", error);
    return 0;
  }
};

/**
 * 점수에 따른 평가 정보 계산
 */
const getScoreEvaluation = (score: number) => {
  if (score >= 0.85) {
    return { scoreEval: "매우 높은 매칭도", scoreEmoji: "⭐" };
  } else if (score >= 0.8) {
    return { scoreEval: "높은 매칭도", scoreEmoji: "✨" };
  } else if (score >= 0.75) {
    return { scoreEval: "좋은 매칭도", scoreEmoji: "👍" };
  } else if (score >= 0.65) {
    return { scoreEval: "적절한 매칭도", scoreEmoji: "💡" };
  } else {
    return { scoreEval: "기본 매칭도", scoreEmoji: "📝" };
  }
};

/**
 * 피드백 상태에 따른 스타일 클래스 반환
 */
const getFeedbackStatusClass = (status: string) => {
  if (status.includes('완료')) {
    return 'bg-green-50 text-green-800 border border-green-200';
  } else if (status.includes('실패') || status.includes('필요')) {
    return 'bg-red-50 text-red-800 border border-red-200';
  } else {
    return 'bg-blue-50 text-blue-800 border border-blue-200';
  }
};

// ==================== 상수 정의 ====================

/**
 * 기본 텍스트 메시지
 */
const TEXT_MESSAGES = {
  NO_DATA: "정보 없음",
  NO_SPRAY_ORDER: "분사 순서 정보가 제공되지 않았습니다.",
  SPRAY_ORDER_SUFFIX: "순서로 분사하시면 최적의 향을 즐기실 수 있습니다.",
  LOADING: "분석 중...",
  SUBMIT_BUTTON: "자연어로 추천받기",
  EMPTY_QUERY_ERROR: "질문을 입력해주세요.",
  FEEDBACK_CONFIRM: "선택한 만족도를 저장할까요? 저장 후에는 변경할 수 없습니다.",
  FEEDBACK_LOGIN_REQUIRED: "로그인이 필요합니다.",
  FEEDBACK_SAVING: "저장 중...",
  FEEDBACK_SAVED: "만족도 저장 완료",
  FEEDBACK_FAILED: "저장 실패",
  ARCHIVE_LOGIN_REQUIRED: "로그인이 필요합니다.",
  ARCHIVE_SAVING: "아카이브 저장 중...",
  ARCHIVE_SAVED: "아카이브에 저장되었습니다.",
  ARCHIVE_FAILED: "아카이브 저장 실패",
  ARCHIVE_ID_ERROR: "향수 정보를 확인할 수 없어요.",
} as const;

// ==================== 오류 처리 설정 ====================

/**
 * 오류 발생 단계별 한글 라벨
 */
const errorStepLabels: Record<string, string> = {
  db_connect: "DB 연결 실패",
  data_load: "데이터 로딩 실패",
  analysis: "자연어 분석 실패",
  perfume_lookup: "향수 식별 실패",
  ranking: "추천 계산 실패",
  response: "응답 처리 실패",
};

/**
 * 오류 발생 단계별 사용자 안내 메시지
 */
const errorStepHints: Record<string, string> = {
  db_connect: "레이어링 서버와 DB 연결 상태를 확인해주세요.",
  data_load: "DB 데이터 적재 상태를 확인해주세요.",
  analysis: "질문을 조금 더 구체적으로 입력해보세요.",
  perfume_lookup: "향수 이름을 정확히 입력했는지 확인해주세요.",
  ranking: "잠시 후 다시 시도해주세요.",
  response: "잠시 후 다시 시도해주세요.",
};

/** 기본 오류 메시지 */
const defaultErrorMessage = "자연어 분석 결과를 불러오지 못했어요.";

/** 
 * 상세 오류 정보 표시 여부
 * - 개발 환경이거나 디버그 플래그가 설정된 경우 상세 정보 표시
 */
const showErrorDetails =
  process.env.NODE_ENV !== "production" ||
  process.env.NEXT_PUBLIC_LAYERING_DEBUG_ERRORS === "true";

/**
 * 오류 객체를 사용자 친화적인 메시지로 변환
 * @param error - 레이어링 API 오류 객체
 * @returns 포맷팅된 오류 메시지
 */
const buildErrorMessage = (error?: LayeringError) => {
  if (!error) {
    return defaultErrorMessage;
  }
  const label = errorStepLabels[error.step] ?? "처리 실패";
  const message = error.message || defaultErrorMessage;
  const hint = errorStepHints[error.step];
  const codeSuffix = error.code ? ` (${error.code})` : "";
  const hintSuffix = hint ? ` ${hint}` : "";
  const detailsSuffix =
    showErrorDetails && error.details ? ` (${error.details})` : "";
  return `${label}: ${message}${codeSuffix}${hintSuffix}${detailsSuffix}`;
};

/**
 * API 응답에서 오류 메시지 추출 및 파싱
 * @param response - Fetch API Response 객체
 * @returns 사용자에게 표시할 오류 메시지
 */
const parseErrorResponse = async (response: Response) => {
  // Content-Type 확인
  const contentType = response.headers.get("content-type") ?? "";

  // JSON이 아닌 경우 텍스트로 처리
  if (!contentType.includes("application/json")) {
    const text = await response.text().catch(() => "");
    return text || defaultErrorMessage;
  }

  // JSON 파싱
  const payload = (await response.json().catch(() => null)) as
    | LayeringErrorResponse
    | null;

  // 단순 문자열 detail
  if (typeof payload?.detail === "string") {
    return payload.detail;
  }

  // 유효성 검사 오류 (배열 형태)
  if (Array.isArray(payload?.detail)) {
    return "입력값을 확인해주세요.";
  }

  // 구조화된 오류 객체
  const error = payload?.error ?? payload?.detail?.error;
  return buildErrorMessage(error);
};

/**
 * 채팅 메시지 타입 정의
 */
type ChatMessage = {
  id: string;                    // 메시지 고유 ID
  type: "user" | "assistant";    // 메시지 타입 (사용자/어시스턴트)
  content: string;               // 메시지 내용
  timestamp: Date;               // 전송 시간
  isRecommendation?: boolean;    // 추천 결과 메시지 여부
  similarPerfumes?: PerfumeSummary[]; // 비슷한 향수 카드 목록
};

export default function LayeringPage() {
  const { data: session } = useSession(); // 카카오 로그인 세션

  const createWelcomeMessages = () => ([
    {
      id: `welcome-${Date.now()}`,
      type: "assistant" as const,
      content: "안녕하세요! 레이어링 추천을 도와드릴게요. 어떤 향수를 가지고 계신가요? 어떤 느낌의 향을 원하시나요?",
      timestamp: new Date(),
    },
  ]);

  // ==================== 상태 관리 ====================

  /** 사용자가 입력한 자연어 질문 텍스트 */
  const [queryText, setQueryText] = useState("");

  /** 채팅 메시지 기록 */
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>(createWelcomeMessages());

  /** API 호출 중 로딩 상태 */
  const [loading, setLoading] = useState(false);

  /** API 호출 오류 메시지 */
  const [error, setError] = useState<string | null>(null);

  /** API로부터 받은 추천 결과 */
  const [result, setResult] = useState<UserQueryResponse | null>(null);

  /** 피드백 저장 상태 메시지 */
  const [feedbackStatus, setFeedbackStatus] = useState<string | null>(null);

  /** 피드백 저장 중 여부 */
  const [feedbackSaving, setFeedbackSaving] = useState(false);

  /** 피드백 저장 완료 후 잠금 상태 (수정 불가) */
  const [feedbackLocked, setFeedbackLocked] = useState(false);

  /** 향수 정보 모달 상태 */
  const [infoModalOpen, setInfoModalOpen] = useState(false);
  const [infoModalLoading, setInfoModalLoading] = useState(false);
  const [infoModalError, setInfoModalError] = useState<string | null>(null);
  const [infoModalData, setInfoModalData] = useState<PerfumeInfo | null>(null);
  const [infoModalLabel, setInfoModalLabel] = useState<string | null>(null);
  const [archiveFeedbackStatus, setArchiveFeedbackStatus] = useState<string | null>(null);
  const [archiveFeedbackSaving, setArchiveFeedbackSaving] = useState(false);
  const [archiveFeedbackLocked, setArchiveFeedbackLocked] = useState(false);

  /** 향수 검색 모달 상태 */
  const [searchModalOpen, setSearchModalOpen] = useState(false);

  /** 렌더 시 안전한 memberId 상태 */
  const [memberId, setMemberId] = useState(0);

  /** 마지막 추천 향수 ID (대화 맥락 유지용) */
  const [lastRecommendationId, setLastRecommendationId] = useState<string | null>(null);

  /** 채팅 메시지 영역 자동 스크롤을 위한 ref */
  const chatEndRef = useRef<HTMLDivElement>(null);

  /** 채팅 입력 입력창 포커스를 위한 ref */
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // [Fix] Hydration mismatch 해결을 위한 mounted 상태
  const [isMounted, setIsMounted] = useState(false);
  useEffect(() => {
    setIsMounted(true);
  }, []);

  // ==================== [NEW] 전역 헤더 및 프로필 상태 ====================
  const [isNavOpen, setIsNavOpen] = useState(false);
  const [localUser, setLocalUser] = useState<any>(null);
  const [profileImageUrl, setProfileImageUrl] = useState<string | null>(null);

  // API 호출 경로 설정
  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  useEffect(() => {
    // 1. 로컬 스토리지 데이터 확인
    const authData = localStorage.getItem("localAuth");
    if (authData) {
      try {
        const parsed = JSON.parse(authData);
        setLocalUser(parsed);
      } catch (e) {
        console.error("Local auth parse error", e);
      }
    }

    // 2. 세션(카카오) 기반 프로필 이미지 가져오기
    if (session?.user?.id) {
      fetch(`${API_URL}/users/profile/${session.user.id}`)
        .then((res) => res.json())
        .then((data) => {
          if (data.profile_image_url) {
            setProfileImageUrl(data.profile_image_url);
          }
        })
        .catch((err) => console.error("Profile image fetch error", err));
    }
    // 3. 로컬 사용자 기반 프로필 이미지 가져오기
    else if (localUser?.memberId) {
      fetch(`${API_URL}/users/profile/${localUser.memberId}`)
        .then((res) => res.json())
        .then((data) => {
          if (data.profile_image_url) {
            setProfileImageUrl(data.profile_image_url);
          }
        })
        .catch((err) => console.error("Local profile image fetch error", err));
    }
  }, [session, localUser?.memberId]);

  const displayName = session?.user?.name || localUser?.userName || "사용자";
  const isLoggedIn = !!(session || localUser);

  /**
   * 채팅 메시지가 업데이트될 때마다 자동으로 스크롤
   */
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages, loading]);

  useEffect(() => {
    setMemberId(getMemberId(session?.user?.id));
  }, [session?.user?.id]);

  /**
   * 자연어 질문 분석 및 레이어링 추천 요청
   * - 사용자 입력 검증
   * - 채팅 메시지 추가
   * - 로컬 스토리지에서 회원 ID 추출
   * - API 호출 및 결과 처리
   * - 에러 핸들링
   */
  const handleAnalyze = async () => {
    // 입력값 검증
    const trimmedQuery = queryText.trim();
    if (!trimmedQuery) {
      // 빈 입력 오류 메시지를 채팅에 추가
      setChatMessages((prev) => [
        ...prev,
        {
          id: `error-${Date.now()}`,
          type: "assistant",
          content: TEXT_MESSAGES.EMPTY_QUERY_ERROR,
          timestamp: new Date(),
        },
      ]);
      return;
    }

    const contextRecommendedId = lastRecommendationId ?? result?.recommendation?.perfume_id ?? null;

    // 사용자 메시지 추가
    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      type: "user",
      content: trimmedQuery,
      timestamp: new Date(),
    };
    setChatMessages((prev) => [...prev, userMessage]);

    // 입력창 초기화 및 상태 초기화
    setQueryText("");
    setLoading(true);
    setError(null);
    setResult(null);
    setFeedbackStatus(null);
    setFeedbackSaving(false);
    setFeedbackLocked(false);

    try {
      // 로컬 스토리지에서 회원 ID 추출
      const currentMemberId = getMemberId(session?.user?.id);

      // 레이어링 분석 API 호출
      const response = await fetch(`${apiBase}/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_text: trimmedQuery,
          member_id: currentMemberId,
          context_recommended_perfume_id: contextRecommendedId,
          save_recommendations: true,  // 추천 결과 저장 여부
          save_my_perfume: false,      // 내 향수로 저장 여부
        }),
      });

      // 응답 오류 처리
      if (!response.ok) {
        const errorMessage = await parseErrorResponse(response);
        throw new Error(errorMessage);
      }

      // 응답 데이터 파싱
      let payload: UserQueryResponse;
      try {
        payload = (await response.json()) as UserQueryResponse;
      } catch (parseError) {
        throw new Error(defaultErrorMessage);
      }

      // 추천 결과 상태 업데이트
      const recommendation = payload.recommendation ?? null;
      setResult({
        ...payload,
        recommendation,
      });

      if (recommendation) {
        setLastRecommendationId(recommendation.perfume_id);
      } else if (payload.brand_best_perfume) {
        setLastRecommendationId(payload.brand_best_perfume.perfume_id);
      } else if (
        (payload.similar_perfumes && payload.similar_perfumes.length > 0)
        || payload.recommended_perfume_info
      ) {
        setLastRecommendationId(null);
      }

      // 추천 성공 메시지 추가
      if (recommendation) {
        setChatMessages((prev) => [
          ...prev,
          {
            id: `rec-${Date.now()}`,
            type: "assistant",
            content: `추천 결과가 나왔어요! 👈 왼쪽에서 "${recommendation.perfume_name}" 향수를 확인해보세요.`,
            timestamp: new Date(),
            isRecommendation: true,
          },
          {
            id: `feedback-${Date.now()}`,
            type: "assistant",
            content: "추천 결과가 마음에 드시나요? 아래에서 만족도를 알려주세요!",
            timestamp: new Date(),
          },
        ]);
      } else if (payload.similar_perfumes && payload.similar_perfumes.length > 0) {
        const similarList = payload.similar_perfumes
          .map((item) => `${item.perfume_name} (${item.perfume_brand})`)
          .join("\n");
        setChatMessages((prev) => [
          ...prev,
          {
            id: `similar-${Date.now()}`,
            type: "assistant",
            content: `비슷한 느낌의 향수 후보를 골라봤어요.\n\n${similarList}`,
            timestamp: new Date(),
            similarPerfumes: payload.similar_perfumes,
          },
        ]);
      } else if (payload.brand_best_perfume) {
        const brandName = payload.brand_name ?? payload.brand_best_perfume.perfume_brand;
        setChatMessages((prev) => [
          ...prev,
          {
            id: `brand-${Date.now()}`,
            type: "assistant",
            content: `${brandName} 브랜드에서 어디에나 레이어링하기 좋은 향수를 골라드렸어요. 👈 왼쪽 카드에서 "${payload.brand_best_perfume.perfume_name}"을 확인해보세요.`,
            timestamp: new Date(),
          },
        ]);
      } else if (payload.clarification_prompt) {
        // 명확화 요청 메시지 (옵션 포함)
        let clarificationText = payload.clarification_prompt;
        if (payload.clarification_options && payload.clarification_options.length > 0) {
          clarificationText += "\n\n추천 옵션:\n" + payload.clarification_options.map(opt => `• ${opt}`).join("\n");
        }
        setChatMessages((prev) => [
          ...prev,
          {
            id: `clarify-${Date.now()}`,
            type: "assistant",
            content: clarificationText,
            timestamp: new Date(),
          },
        ]);
      } else if (payload.note) {
        // 일반 노트 메시지
        setChatMessages((prev) => [
          ...prev,
          {
            id: `note-${Date.now()}`,
            type: "assistant",
            content: payload.note ?? "",
            timestamp: new Date(),
          },
        ]);
      }
    } catch (err) {
      // 에러 메시지를 채팅에 추가
      const errorMessage = err instanceof Error ? err.message : "알 수 없는 오류가 발생했어요.";
      setError(errorMessage);
      setChatMessages((prev) => [
        ...prev,
        {
          id: `error-${Date.now()}`,
          type: "assistant",
          content: errorMessage,
          timestamp: new Date(),
        },
      ]);
    } finally {
      // 로딩 상태 해제
      setLoading(false);
    }
  };

  /**
   * 추천 결과에 대한 만족도 피드백 전송
   * @param preference - 만족도 (GOOD, BAD)
   * 
   * 처리 흐름:
   * 1. 추천 결과 및 상태 검증
   * 2. 회원 ID 검증
   * 3. 피드백 API 호출
   * 4. 결과 저장 및 채팅 메시지 업데이트
   */
  const sendFeedback = async (preference: "GOOD" | "BAD") => {
    // 추천 결과 존재 확인
    const candidate = result?.recommendation;
    if (!candidate) {
      return;
    }

    // 중복 저장 방지
    if (feedbackLocked || feedbackSaving) {
      return;
    }

    // 로컬 스토리지에서 회원 ID 추출 및 로그인 상태 확인
    const currentMemberId = getMemberId(session?.user?.id);
    if (!currentMemberId) {
      const loginMessage = TEXT_MESSAGES.FEEDBACK_LOGIN_REQUIRED;
      setFeedbackStatus(loginMessage);
      setChatMessages((prev) => [
        ...prev,
        {
          id: `feedback-error-${Date.now()}`,
          type: "assistant",
          content: loginMessage,
          timestamp: new Date(),
        },
      ]);
      return;
    }

    try {
      // 저장 중 상태 표시
      setFeedbackSaving(true);
      setFeedbackStatus(TEXT_MESSAGES.FEEDBACK_SAVING);

      // 피드백 API 호출
      const response = await fetch(`${apiBase}/recommendation/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          member_id: currentMemberId,
          perfume_id: candidate.perfume_id,
          perfume_name: candidate.perfume_name,
          preference,
        }),
      });

      // 응답 오류 처리
      if (!response.ok) {
        const errorMessage = await parseErrorResponse(response);
        throw new Error(errorMessage);
      }

      // 응답 데이터 파싱 및 결과 처리
      const payload = (await response.json()) as FeedbackResponse;
      if (payload.save_result?.saved) {
        const successMessage = "만족도가 저장되었습니다. 소중한 의견 감사합니다! 😊";
        setFeedbackStatus(TEXT_MESSAGES.FEEDBACK_SAVED);
        setFeedbackLocked(true);  // 저장 완료 후 잠금 처리

        // 성공 메시지를 채팅에 추가
        setChatMessages((prev) => [
          ...prev,
          {
            id: `feedback-success-${Date.now()}`,
            type: "assistant",
            content: successMessage,
            timestamp: new Date(),
          },
        ]);
      } else if (preference === "BAD") {
        const ackMessage = "불만족 의견을 남겨주셔서 감사합니다. 다음 추천에 반영할게요.";
        setFeedbackStatus(ackMessage);
        setFeedbackLocked(true);
        setChatMessages((prev) => [
          ...prev,
          {
            id: `feedback-bad-${Date.now()}`,
            type: "assistant",
            content: ackMessage,
            timestamp: new Date(),
          },
        ]);
      } else {
        const failMessage = payload.save_result?.message ?? TEXT_MESSAGES.FEEDBACK_FAILED;
        setFeedbackStatus(failMessage);
        setChatMessages((prev) => [
          ...prev,
          {
            id: `feedback-fail-${Date.now()}`,
            type: "assistant",
            content: failMessage,
            timestamp: new Date(),
          },
        ]);
      }
    } catch (err) {
      // 에러 메시지 설정 및 채팅에 추가
      const errorMessage = err instanceof Error ? err.message : TEXT_MESSAGES.FEEDBACK_FAILED;
      setFeedbackStatus(errorMessage);
      setChatMessages((prev) => [
        ...prev,
        {
          id: `feedback-error-${Date.now()}`,
          type: "assistant",
          content: errorMessage,
          timestamp: new Date(),
        },
      ]);
    } finally {
      // 저장 중 상태 해제
      setFeedbackSaving(false);
    }
  };

  /**
   * 향수 정보 모달에서 아카이브 저장 (만족/불만족)
   */
  const handleArchiveFeedback = async (preference: "GOOD" | "BAD") => {
    const perfume = infoModalData;
    if (!perfume) {
      return;
    }

    if (archiveFeedbackLocked || archiveFeedbackSaving) {
      return;
    }

    if (!memberId) {
      setArchiveFeedbackStatus(TEXT_MESSAGES.ARCHIVE_LOGIN_REQUIRED);
      return;
    }

    const perfumeId = Number(perfume.perfume_id);
    if (!Number.isFinite(perfumeId)) {
      setArchiveFeedbackStatus(TEXT_MESSAGES.ARCHIVE_ID_ERROR);
      return;
    }

    try {
      setArchiveFeedbackSaving(true);
      setArchiveFeedbackStatus(TEXT_MESSAGES.ARCHIVE_SAVING);

      const response = await fetch(`/api/users/${memberId}/perfumes`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          perfume_id: perfumeId,
          perfume_name: perfume.perfume_name,
          register_status: "RECOMMENDED",
          preference,
        }),
      });

      if (!response.ok) {
        const errorText = await response.text().catch(() => "");
        throw new Error(errorText || TEXT_MESSAGES.ARCHIVE_FAILED);
      }

      setArchiveFeedbackLocked(true);
      setArchiveFeedbackStatus(TEXT_MESSAGES.ARCHIVE_SAVED);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : TEXT_MESSAGES.ARCHIVE_FAILED;
      setArchiveFeedbackStatus(errorMessage);
    } finally {
      setArchiveFeedbackSaving(false);
    }
  };

  const resetChat = () => {
    setChatMessages(createWelcomeMessages());
    setQueryText("");
    setResult(null);
    setError(null);
    setFeedbackStatus(null);
    setFeedbackSaving(false);
    setFeedbackLocked(false);
    setLastRecommendationId(null);
    setLoading(false);
  };

  // ==================== 렌더링 데이터 준비 ====================

  /** 추천된 향수 후보 */
  const candidate = result?.recommendation ?? null;
  const basePerfume = result?.base_perfume ?? null;
  const perfumeInfo = result?.recommended_perfume_info ?? null;
  const brandBestPerfume = result?.brand_best_perfume ?? null;
  const brandBestScore = result?.brand_best_score ?? null;
  const brandBestReason = result?.brand_best_reason ?? null;

  /** 
   * 레이어링 결과의 어코드 벡터 및 유효성 검증
   * 메모이제이션을 통해 불필요한 재계산 방지
   */
  const { vector, vectorReady } = useMemo(() => {
    const vec = candidate?.layered_vector ?? [];
    const ready =
      vec.length === BACKEND_ACCORDS.length &&
      vec.every((value) => Number.isFinite(value));

    return { vector: vec, vectorReady: ready };
  }, [candidate]);

  /** 
   * 분사 순서 배열 유효성 검증
   */
  const hasSprayOrder = useMemo(() =>
    candidate?.spray_order &&
    Array.isArray(candidate.spray_order) &&
    candidate.spray_order.length > 0,
    [candidate]
  );

  /** 
   * 추천 점수 포맷팅 (소수점 3자리)
   * 유효하지 않은 경우 "-" 표시
   */
  const totalScore = useMemo(() =>
    Number.isFinite(candidate?.total_score)
      ? candidate?.total_score.toFixed(3)
      : "-",
    [candidate]
  );

  /**
   * 점수 평가 정보 메모이제이션
   * JSX 내부에서 반복 계산되는 것을 방지
   */
  const scoreEvaluation = useMemo(() => {
    if (!candidate) return null;
    return getScoreEvaluation(candidate.total_score);
  }, [candidate]);

  const infoSections = useMemo(() => {
    if (!perfumeInfo) return [];
    return [
      { label: "어코드", items: perfumeInfo.accords },
      { label: "탑 노트", items: perfumeInfo.top_notes },
      { label: "미들 노트", items: perfumeInfo.middle_notes },
      { label: "베이스 노트", items: perfumeInfo.base_notes },
      { label: "계절", items: perfumeInfo.seasons },
      { label: "상황", items: perfumeInfo.occasions },
    ].filter((section) => section.items && section.items.length > 0);
  }, [perfumeInfo]);

  const handleOpenPerfumeInfo = async (perfumeId?: string | null, label?: string) => {
    if (!perfumeId) return;
    setInfoModalOpen(true);
    setInfoModalLoading(true);
    setInfoModalError(null);
    setInfoModalData(null);
    setInfoModalLabel(label ?? "향수");
    setArchiveFeedbackStatus(null);
    setArchiveFeedbackSaving(false);
    setArchiveFeedbackLocked(false);

    try {
      const currentMemberId = getMemberId(session?.user?.id);
      const response = await fetch(`${apiBase}/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_text: "향수 정보",
          member_id: currentMemberId,
          context_recommended_perfume_id: perfumeId,
          save_recommendations: false,
          save_my_perfume: false,
        }),
      });

      if (!response.ok) {
        const errorMessage = await parseErrorResponse(response);
        throw new Error(errorMessage);
      }

      const payload = (await response.json()) as UserQueryResponse;
      if (!payload.recommended_perfume_info) {
        throw new Error("향수 정보를 불러오지 못했어요.");
      }
      setInfoModalData(payload.recommended_perfume_info);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "향수 정보를 불러오지 못했어요.";
      setInfoModalError(errorMessage);
    } finally {
      setInfoModalLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#FDFBF8] text-black relative font-sans">
      {/* ==================== [NEW] Sidebar & Overlay ==================== */}
      <Sidebar
        isOpen={isNavOpen}
        onClose={() => setIsNavOpen(false)}
        context="home"
      />
      {isNavOpen && (
        <div
          className="fixed inset-0 bg-transparent z-40"
          onClick={() => setIsNavOpen(false)}
        />
      )}

      {/* [STANDARD HEADER] 메인 페이지(app/page.tsx)와 100% 동일한 구조 및 디자인 적용 */}
      <header className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-5 py-4 bg-[#FDFBF8] border-b border-[#F0F0F0]">
        {/* 로고 영역: font-bold, text-black, tracking-tight (표준) */}
        <Link href="/" className="text-xl font-bold tracking-tight text-black">
          Scentence
        </Link>

        {/* 우측 상단 UI: 로그인 상태 및 사이드바 토글 버튼 (표준) */}
        <div className="flex items-center gap-4">
          {!isLoggedIn ? (
            // 비로그인 상태 UI
            <div className="flex items-center gap-2 text-sm font-medium text-gray-400">
              <Link href="/login" className="hover:text-black transition-colors">Sign in</Link>
              <span className="text-gray-300">|</span>
              <Link href="/signup" className="hover:text-black transition-colors">Sign up</Link>
            </div>
          ) : (
            // 로그인 상태 UI: 이름과 프로필 이미지
            <div className="flex items-center gap-3">
              <span className="text-sm font-bold text-gray-800 hidden sm:block">
                {displayName}님 반가워요!
              </span>
              <Link href="/mypage" className="block w-9 h-9 rounded-full overflow-hidden border border-gray-100 shadow-sm hover:opacity-80 transition-opacity">
                <img
                  src={profileImageUrl || "/default_profile.png"}
                  alt="Profile"
                  className="w-full h-full object-cover"
                  onError={(e) => { e.currentTarget.src = "/default_profile.png"; }}
                />
              </Link>
            </div>
          )}

          {/* 글로벌 내비게이션 토글 버튼 (px-5 py-4 패딩 및 w-8 h-8 규격 준수) */}
          {/* 글로벌 내비게이션 토글 버튼 (px-5 py-4 패딩 및 w-8 h-8 규격 준수) */}
          <button
            id="global-menu-toggle"
            onClick={() => setIsNavOpen(!isNavOpen)}
            className="p-1 rounded-md hover:bg-gray-100 transition-colors"
          >
            {isNavOpen ? (
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-8 h-8 text-[#555]">
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            ) : (
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-8 h-8 text-[#555]">
                <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 9h16.5m-16.5 6.75h16.5" />
              </svg>
            )}
          </button>
        </div>
      </header>

      <div className="max-w-5xl mx-auto px-6 pt-[120px] pb-12">
        {/* ==================== 페이지 헤더 (본문 타이틀) ==================== */}
        <div className="flex items-center justify-between mb-8">
          <div className="space-y-3">
            {/* 영문 서브 타이틀 */}
            <p className="text-xs uppercase tracking-[0.3em] text-[#7A6B57] font-medium">
              Layering Visualization
            </p>

            {/* 메인 타이틀 */}
            <h1 className="text-3xl font-semibold text-[#2E2B28]">
              레이어링 어코드 원판
            </h1>

            {/* 설명 텍스트 */}
            <p className="text-sm text-[#5C5448] leading-relaxed">
              자연어 질문으로 향수 레이어링을 추천받고,<br />
              21개 어코드의 강도를 원형 그래픽으로 확인하세요.
            </p>
          </div>

          {/* 홈 버튼 */}
          <Link
            href="/"
            className="p-3 bg-white/70 hover:bg-white rounded-full transition-all shadow-sm hover:shadow-md text-[#7A6B57] hover:text-[#5C5448]"
            aria-label="홈으로 이동"
          >
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-6 h-6">
              <path strokeLinecap="round" strokeLinejoin="round" d="m2.25 12 8.954-8.955c.44-.439 1.152-.439 1.591 0L21.75 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125H9.75v-4.875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21h4.125c.621 0 1.125-.504 1.125-1.125V9.75M8.25 21h8.25" />
            </svg>
          </Link>
        </div>

        {/* ==================== 메인 콘텐츠 그리드 ==================== */}
        <section className="grid gap-6 lg:grid-cols-[1fr_1.2fr]">
          <div className="rounded-3xl bg-white/90 border border-[#E2D7C5] p-6 shadow-sm">
            {/* 시각화 섹션 헤더 */}
            <h2 className="text-sm font-semibold text-[#7A6B57]">레이어링 시각화</h2>

            <div className="mt-4 flex flex-col items-center gap-6">
              {basePerfume && (
                <div className="w-full rounded-2xl border border-[#E6DDCF] bg-white/80 p-4 shadow-sm">
                  <div className="flex items-center gap-4">
                    {basePerfume.image_url ? (
                      <button
                        type="button"
                        onClick={() => handleOpenPerfumeInfo(basePerfume.perfume_id, "기존 향수")}
                        className="h-16 w-16 rounded-xl overflow-hidden border border-[#E6DDCF] bg-white/80 shadow-sm hover:shadow-md transition"
                        aria-label="기존 향수 상세 정보 보기"
                      >
                        <img
                          src={basePerfume.image_url}
                          alt={`${basePerfume.perfume_name} 이미지`}
                          className="h-full w-full object-cover transition-transform duration-200 hover:scale-105"
                          loading="lazy"
                        />
                      </button>
                    ) : (
                      <button
                        type="button"
                        onClick={() => handleOpenPerfumeInfo(basePerfume.perfume_id, "기존 향수")}
                        className="h-16 w-16 rounded-xl bg-gradient-to-br from-[#F4EBDD] to-[#E8D9C4] flex items-center justify-center text-[10px] text-[#7A6B57] border border-[#E6DDCF] hover:shadow-md transition"
                        aria-label="기존 향수 상세 정보 보기"
                      >
                        No Image
                      </button>
                    )}
                    <div>
                      <p className="text-[11px] font-semibold text-[#7A6B57]">기존 향수</p>
                      <p className="text-sm font-bold text-[#2E2B28]">
                        {basePerfume.perfume_name}
                      </p>
                      <p className="text-xs text-[#7A6B57]">
                        {basePerfume.perfume_brand}
                      </p>
                      {basePerfume.concentration && (
                        <p className="text-[11px] text-[#8A7F73]">
                          농도: {basePerfume.concentration}
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              )}
              {brandBestPerfume && (
                <div className="w-full rounded-2xl border border-[#E6DDCF] bg-white/80 p-4 shadow-sm">
                  <div className="flex items-center gap-4">
                    {brandBestPerfume.image_url ? (
                      <img
                        src={brandBestPerfume.image_url}
                        alt={`${brandBestPerfume.perfume_name} 이미지`}
                        className="h-16 w-16 rounded-xl object-cover border border-[#E6DDCF]"
                        loading="lazy"
                      />
                    ) : (
                      <div className="h-16 w-16 rounded-xl bg-gradient-to-br from-[#F4EBDD] to-[#E8D9C4] flex items-center justify-center text-[10px] text-[#7A6B57] border border-[#E6DDCF]">
                        No Image
                      </div>
                    )}
                    <div className="flex-1">
                      <p className="text-[11px] font-semibold text-[#7A6B57]">브랜드 추천</p>
                      <p className="text-sm font-bold text-[#2E2B28]">
                        {brandBestPerfume.perfume_name}
                      </p>
                      <p className="text-xs text-[#7A6B57]">
                        {brandBestPerfume.perfume_brand}
                      </p>
                      {brandBestReason && (
                        <p className="text-[11px] text-[#5C5448] mt-2 leading-relaxed">
                          {brandBestReason}
                        </p>
                      )}
                    </div>
                    {Number.isFinite(brandBestScore) && (
                      <div className="rounded-full border border-[#C8A24D]/30 bg-[#C8A24D]/10 px-3 py-1.5">
                        <p className="text-[10px] font-semibold text-[#7A6B57]">평균 점수</p>
                        <p className="text-sm font-bold text-[#C8A24D]">
                          {brandBestScore?.toFixed(3)}
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              )}
              {/* 어코드 원판 표시 영역 */}
              {vectorReady ? (
                <AccordWheel vector={vector} />
              ) : (
                <div className="h-[360px] w-[360px] flex flex-col items-center justify-center rounded-full border-2 border-dashed border-[#D7CDBD] text-xs text-[#7A6B57] gap-2 bg-[#FDFBF9]">
                  <svg className="w-12 h-12 text-[#D7CDBD]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                  <p className="text-center px-6">
                    데이터를 불러오면<br />원판이 표시됩니다.
                  </p>
                </div>
              )}

              {/* 추천 향수 정보 카드 */}
              {candidate && (
                <div className="w-full rounded-2xl bg-white border-2 border-[#E6DDCF] overflow-hidden shadow-md hover:shadow-xl transition-all">
                  {/* 헤더: 추천 라벨과 점수 뱃지 */}
                  <div className="bg-gradient-to-r from-[#F8F4EC] to-[#F0EAE0] px-5 py-3 flex items-center justify-between border-b border-[#E6DDCF]">
                    <div className="flex items-center gap-2">
                      <svg className="w-4 h-4 text-[#C8A24D]" fill="currentColor" viewBox="0 0 20 20">
                        <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                      </svg>
                      <span className="text-xs font-bold text-[#C8A24D] uppercase tracking-wide">
                        추천 향수
                      </span>
                    </div>
                    <div className="flex items-center gap-1.5 bg-[#C8A24D]/10 px-3 py-1.5 rounded-full border border-[#C8A24D]/30">
                      <span className="text-[10px] font-medium text-[#7A6B57]">매칭도</span>
                      <span className="text-sm font-bold text-[#C8A24D]">{totalScore}</span>
                    </div>
                  </div>

                  {/* 메인 콘텐츠 */}
                  <div className="p-5 space-y-4 max-h-[360px] overflow-y-auto">
                    {/* 향수 이름과 브랜드 */}
                    <div className="flex items-center gap-4">
                      <button
                        type="button"
                        onClick={() => handleOpenPerfumeInfo(candidate.perfume_id, "추천 향수")}
                        className="group h-16 w-16 rounded-xl border border-[#E6DDCF] bg-white/80 overflow-hidden shadow-sm hover:shadow-md transition"
                        aria-label="추천 향수 상세 정보 보기"
                      >
                        {candidate.image_url ? (
                          <img
                            src={candidate.image_url}
                            alt={`${candidate.perfume_name} 이미지`}
                            className="h-full w-full object-cover transition-transform duration-200 group-hover:scale-105"
                            loading="lazy"
                          />
                        ) : (
                          <div className="h-full w-full bg-gradient-to-br from-[#F4EBDD] to-[#E8D9C4] flex items-center justify-center text-[10px] text-[#7A6B57]">
                            No Image
                          </div>
                        )}
                      </button>
                      <div>
                        <h3 className="text-lg font-bold text-[#2E2B28] leading-tight mb-1">
                          {candidate.perfume_name}
                        </h3>
                        <p className="text-sm font-medium text-[#7A6B57]">
                          {candidate.perfume_brand}
                        </p>
                        {candidate.concentration && (
                          <p className="text-xs text-[#8A7F73]">
                            농도: {candidate.concentration}
                          </p>
                        )}
                      </div>
                    </div>

                    {/* 추천 이유 */}
                    {candidate.analysis && (
                      <div className="space-y-2">
                        <div className="flex items-center gap-1.5">
                          <svg className="w-3.5 h-3.5 text-[#C8A24D]" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                          </svg>
                          <p className="text-xs font-semibold text-[#5C5448]">추천 이유</p>
                        </div>
                        <p className="text-sm text-[#2E2B28] leading-relaxed pl-5">
                          {scoreEvaluation && (
                            <>
                              {scoreEvaluation.scoreEmoji} <span className="font-bold text-[#C8A24D]">{candidate.perfume_name}</span>
                              은(는) 매칭도 {totalScore}로{" "}
                              <span className="font-semibold text-[#5C5448]">{scoreEvaluation.scoreEval}</span>입니다. {candidate.analysis}
                            </>
                          )}
                        </p>
                      </div>
                    )}

                    {/* 분사 순서 */}
                    <div className="pt-3 border-t border-[#E6DDCF]">
                      <div className="space-y-2">
                        <div className="flex items-center gap-1.5">
                          <svg className="w-3.5 h-3.5 text-[#C8A24D]" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 011.12-.38z" clipRule="evenodd" />
                          </svg>
                          <p className="text-xs font-semibold text-[#5C5448]">분사 순서</p>
                        </div>
                        <p className="text-sm text-[#2E2B28] leading-relaxed pl-5">
                          {hasSprayOrder ? (
                            <>
                              {candidate.spray_order.map((perfume, idx) => (
                                <span key={idx}>
                                  <span className="font-semibold text-[#5C5448]">{perfume}</span>
                                  {idx < candidate.spray_order.length - 1 && (
                                    <span className="text-[#C8A24D] mx-1">→</span>
                                  )}
                                </span>
                              ))}
                              {" "}{TEXT_MESSAGES.SPRAY_ORDER_SUFFIX}
                            </>
                          ) : (
                            <span className="text-[#7A6B57] italic">{TEXT_MESSAGES.NO_SPRAY_ORDER}</span>
                          )}
                        </p>
                      </div>
                    </div>

                    {perfumeInfo && (
                      <div className="pt-3 border-t border-[#E6DDCF]">
                        <div className="space-y-2">
                          <div className="flex items-center gap-1.5">
                            <svg className="w-3.5 h-3.5 text-[#C8A24D]" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm-1-11a1 1 0 112 0v3a1 1 0 01-2 0V7zm1 6a1.25 1.25 0 100 2.5A1.25 1.25 0 0010 13z" clipRule="evenodd" />
                            </svg>
                            <p className="text-xs font-semibold text-[#5C5448]">향수 정보</p>
                          </div>
                          {perfumeInfo.gender && (
                            <p className="text-xs text-[#7A6B57] pl-5">성별: {perfumeInfo.gender}</p>
                          )}
                          <div className="pl-5 space-y-2">
                            {infoSections.map((section) => (
                              <div key={section.label}>
                                <p className="text-[11px] font-semibold text-[#7A6B57]">
                                  {section.label}
                                </p>
                                <div className="flex flex-wrap gap-1 mt-1">
                                  {section.items.map((item) => (
                                    <span
                                      key={`${section.label}-${item}`}
                                      className="text-[11px] px-2 py-0.5 rounded-full bg-[#F8F4EC] text-[#5C5448] border border-[#E6DDCF]"
                                    >
                                      {item}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}
              {!candidate && perfumeInfo && (
                <div className="w-full rounded-2xl bg-white border-2 border-[#E6DDCF] overflow-hidden shadow-md">
                  <div className="bg-gradient-to-r from-[#F8F4EC] to-[#F0EAE0] px-5 py-3 flex items-center justify-between border-b border-[#E6DDCF]">
                    <div className="flex items-center gap-2">
                      <svg className="w-4 h-4 text-[#C8A24D]" fill="currentColor" viewBox="0 0 20 20">
                        <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                      </svg>
                      <span className="text-xs font-bold text-[#C8A24D] uppercase tracking-wide">
                        추천 향수 정보
                      </span>
                    </div>
                  </div>
                  <div className="p-5 space-y-4 max-h-[360px] overflow-y-auto">
                    <div className="flex items-center gap-4">
                      {perfumeInfo.image_url ? (
                        <img
                          src={perfumeInfo.image_url}
                          alt={`${perfumeInfo.perfume_name} 이미지`}
                          className="h-16 w-16 rounded-xl object-cover border border-[#E6DDCF]"
                          loading="lazy"
                        />
                      ) : (
                        <div className="h-16 w-16 rounded-xl bg-gradient-to-br from-[#F4EBDD] to-[#E8D9C4] flex items-center justify-center text-[10px] text-[#7A6B57] border border-[#E6DDCF]">
                          No Image
                        </div>
                      )}
                      <div>
                        <h3 className="text-lg font-bold text-[#2E2B28] leading-tight mb-1">
                          {perfumeInfo.perfume_name}
                        </h3>
                        <p className="text-sm font-medium text-[#7A6B57]">
                          {perfumeInfo.perfume_brand}
                        </p>
                        {perfumeInfo.concentration && (
                          <p className="text-xs text-[#8A7F73]">
                            농도: {perfumeInfo.concentration}
                          </p>
                        )}
                      </div>
                    </div>
                    {perfumeInfo.gender && (
                      <p className="text-xs text-[#7A6B57]">성별: {perfumeInfo.gender}</p>
                    )}
                    <div className="space-y-2">
                      {infoSections.map((section) => (
                        <div key={`solo-${section.label}`}>
                          <p className="text-[11px] font-semibold text-[#7A6B57]">
                            {section.label}
                          </p>
                          <div className="flex flex-wrap gap-1 mt-1">
                            {section.items.map((item) => (
                              <span
                                key={`solo-${section.label}-${item}`}
                                className="text-[11px] px-2 py-0.5 rounded-full bg-[#F8F4EC] text-[#5C5448] border border-[#E6DDCF]"
                              >
                                {item}
                              </span>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* ==================== 채팅 영역 ==================== */}
          <div className="min-h-[700px] h-full rounded-3xl bg-white/80 border border-[#E2D7C5] shadow-sm flex flex-col overflow-hidden">
            {/* 채팅 헤더 */}
            <div className="bg-gradient-to-r from-[#F8F4EC] to-[#F0EAE0] px-6 py-4 border-b border-[#E2D7C5]">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h2 className="text-sm font-semibold text-[#7A6B57]">레이어링 어시스턴트</h2>
                  <p className="text-xs text-[#8A7F73] mt-1">원하는 향수 레이어링을 설명해주세요</p>
                </div>
                <button
                  type="button"
                  onClick={resetChat}
                  className="text-[11px] font-semibold text-[#7A6B57] border border-[#E2D7C5] rounded-full px-3 py-1.5 bg-white/80 hover:bg-white transition"
                >
                  대화 초기화
                </button>
              </div>
            </div>

            {/* 채팅 메시지 영역 - 스크롤 가능 */}
            <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
              {chatMessages.map((message) => (
                <div
                  key={message.id}
                  className={`flex ${message.type === "user" ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-[85%] rounded-2xl px-4 py-3 ${message.type === "user"
                      ? "bg-[#2E2B28] text-white rounded-br-sm"
                      : message.isRecommendation
                        ? "bg-gradient-to-r from-[#C8A24D]/20 to-[#D4B570]/20 text-[#2E2B28] border-2 border-[#C8A24D]/40 rounded-bl-sm"
                        : "bg-[#F8F4EC] text-[#2E2B28] border border-[#E6DDCF] rounded-bl-sm"
                      }`}
                  >
                    <p className="text-sm leading-relaxed whitespace-pre-wrap break-words">
                      {message.content}
                    </p>
                    {message.similarPerfumes && message.similarPerfumes.length > 0 && (
                      <div className="mt-3 grid gap-3 sm:grid-cols-2">
                        {message.similarPerfumes.map((perfume) => (
                          <button
                            key={`similar-${message.id}-${perfume.perfume_id}`}
                            type="button"
                            onClick={() => handleOpenPerfumeInfo(perfume.perfume_id, "비슷한 향수")}
                            className="flex items-center gap-3 rounded-xl border border-[#E6DDCF] bg-white/80 px-3 py-2 text-left shadow-sm hover:shadow-md transition"
                          >
                            {perfume.image_url ? (
                              <img
                                src={perfume.image_url}
                                alt={`${perfume.perfume_name} 이미지`}
                                className="h-12 w-12 rounded-lg object-cover border border-[#E6DDCF]"
                                loading="lazy"
                              />
                            ) : (
                              <div className="h-12 w-12 rounded-lg bg-gradient-to-br from-[#F4EBDD] to-[#E8D9C4] flex items-center justify-center text-[10px] text-[#7A6B57] border border-[#E6DDCF]">
                                No Image
                              </div>
                            )}
                            <div className="flex-1">
                              <p className="text-sm font-semibold text-[#2E2B28] leading-tight">
                                {perfume.perfume_name}
                              </p>
                              <p className="text-[11px] text-[#7A6B57]">
                                {perfume.perfume_brand}
                              </p>
                            </div>
                          </button>
                        ))}
                      </div>
                    )}
                    <p className={`text-[10px] mt-1.5 ${message.type === "user" ? "text-white/60" : "text-[#8A7F73]"
                      }`}>
                      {isMounted ? message.timestamp.toLocaleTimeString("ko-KR", {
                        hour: "2-digit",
                        minute: "2-digit",
                      }) : ""}
                    </p>
                  </div>
                </div>
              ))}

              {/* 로딩 중 표시 */}
              {loading && (
                <div className="flex justify-start">
                  <div className="bg-[#F8F4EC] text-[#2E2B28] border border-[#E6DDCF] rounded-2xl rounded-bl-sm px-4 py-3">
                    <div className="flex items-center gap-2">
                      <svg className="animate-spin h-4 w-4 text-[#7A6B57]" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      <span className="text-sm text-[#7A6B57]">분석 중...</span>
                    </div>
                  </div>
                </div>
              )}

              {/* 자동 스크롤을 위한 더미 요소 */}
              <div ref={chatEndRef} />
            </div>

            {/* 만족도 피드백 영역 - 추천 결과가 있을 때만 표시 */}
            {candidate && !feedbackLocked && (
              <div className="px-6 py-3 bg-[#FDFBF7] border-t border-[#E6DDCF]">
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => sendFeedback("GOOD")}
                    className="flex-1 rounded-lg border-2 border-[#D4E5D4] bg-[#F0F8F0] px-3 py-2 text-xs font-semibold text-[#3D5A3D] transition-all hover:bg-[#E1F3E1] hover:border-[#B8D4B8] disabled:cursor-not-allowed disabled:opacity-50"
                    disabled={feedbackSaving}
                    aria-label="만족스러운 추천"
                  >
                    <span className="flex items-center justify-center gap-1">
                      <span className="text-sm">😊</span>
                      만족
                    </span>
                  </button>
                  <button
                    type="button"
                    onClick={() => sendFeedback("BAD")}
                    className="flex-1 rounded-lg border-2 border-[#F5D4D4] bg-[#FDF0F0] px-3 py-2 text-xs font-semibold text-[#6B3D3D] transition-all hover:bg-[#FCE1E1] hover:border-[#EBB8B8] disabled:cursor-not-allowed disabled:opacity-50"
                    disabled={feedbackSaving}
                    aria-label="불만족스러운 추천"
                  >
                    <span className="flex items-center justify-center gap-1">
                      <span className="text-sm">😞</span>
                      불만족
                    </span>
                  </button>
                </div>
              </div>
            )}

            {/* 입력창 영역 - 하단 고정 */}
            <div className="px-6 py-4 bg-white border-t border-[#E2D7C5]">
              <div className="flex flex-col gap-2">
                <div className="flex gap-2 items-center w-full">
                  {/* [추가] 내 향수 선택 팝오버 */}
                  <LayeringPerfumePicker
                    memberId={memberId}
                    onSelect={(name) => {
                      const newText = queryText + (queryText ? " " : "") + name;
                      setQueryText(newText);
                      // 향수 선택 후 입력창에 자동 포커스 및 커서를 맨 뒤로 이동
                      setTimeout(() => {
                        if (textareaRef.current) {
                          textareaRef.current.focus();
                          textareaRef.current.setSelectionRange(newText.length, newText.length);
                        }
                      }, 0);
                    }}
                  />

                  <button
                    type="button"
                    onClick={() => setSearchModalOpen(true)}
                    className="w-[72px] h-[72px] flex items-center justify-center rounded-xl text-gray-400 hover:text-[#C5A55D] hover:bg-[#F5F2EA] transition-all"
                    title="향수 검색"
                    aria-label="향수 검색"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-7 h-7">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-4.35-4.35m1.1-4.4a7.5 7.5 0 11-15 0 7.5 7.5 0 0115 0z" />
                    </svg>
                  </button>

                  <textarea
                    ref={textareaRef}
                    value={queryText}
                    onChange={(event) => setQueryText(event.target.value)}
                    onKeyDown={(event) => {
                      // Enter 키로 전송 (Shift+Enter는 줄바꿈)
                      if (event.key === "Enter" && !event.shiftKey) {
                        event.preventDefault();
                        handleAnalyze();
                      }
                    }}
                    spellCheck={false}
                    className="flex-1 rounded-xl border border-[#E1D7C8] bg-white px-4 py-3 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-[#7A6B57]/30 focus:border-[#7A6B57] transition-all h-[72px]"
                    placeholder="예: CK One이 있는데 더 시트러스하고 시원한 느낌이 나게 하려면?"
                    disabled={loading}
                    aria-label="레이어링 질문 입력"
                  />
                  <button
                    onClick={handleAnalyze}
                    className="rounded-xl bg-[#2E2B28] px-3 text-sm font-semibold text-white transition-all hover:bg-[#1E1C1A] disabled:opacity-50 disabled:cursor-not-allowed h-[72px] w-[72px] flex items-center justify-center flex-shrink-0"
                    disabled={loading || !queryText.trim()}
                    aria-label="메시지 전송"
                  >
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 11.5L21 3l-6.8 18-3.6-7.2L3 11.5z" />
                    </svg>
                  </button>
                </div>
                <p className="text-[10px] text-[#8A7F73]">
                  Enter로 전송, Shift+Enter로 줄바꿈
                </p>
              </div>
            </div>
          </div>
        </section>
      </div>
      <PerfumeInfoModal
        open={infoModalOpen}
        loading={infoModalLoading}
        errorMessage={infoModalError}
        perfume={infoModalData}
        label={infoModalLabel ?? undefined}
        archiveFeedbackStatus={archiveFeedbackStatus}
        archiveFeedbackSaving={archiveFeedbackSaving}
        archiveFeedbackLocked={archiveFeedbackLocked}
        onArchiveFeedback={handleArchiveFeedback}
        onClose={() => setInfoModalOpen(false)}
      />
      <LayeringPerfumeSearchModal
        open={searchModalOpen}
        onClose={() => setSearchModalOpen(false)}
        onSelect={(name) => {
          const newText = queryText + (queryText ? " " : "") + name;
          setQueryText(newText);
          setTimeout(() => {
            if (textareaRef.current) {
              textareaRef.current.focus();
              textareaRef.current.setSelectionRange(newText.length, newText.length);
            }
          }, 0);
        }}
      />
    </div>
  );
}
