"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import MbtiInputSection from "./MbtiInputSection";

// API 설정
const API_BASE =
  process.env.NEXT_PUBLIC_SCENTMAP_API_URL ?? "http://localhost:8001";

interface AccordInfo {
  name: string;
  description: string;
}

interface NextAction {
  type: string;
  title: string;
  description: string;
  button_text: string;
  link: string;
}

interface MbtiPrompt {
  message: string;
  options: string[];
}

interface ScentCard {
  title: string;
  story: string;
  accords: AccordInfo[];
  created_at: string;
  mbti?: string;
  mbti_code?: string;
  mbti_headline?: string;
  next_actions?: NextAction[];
  mbti_prompt?: MbtiPrompt;
  image_url?: string;
}

interface ScentCardModalProps {
  card: ScentCard;
  onClose: () => void;
  onSave?: () => void;
  onContinueExplore?: () => void;
  sessionId?: string;
  cardId?: string;
  isLoggedIn?: boolean;
}

export default function ScentCardModal({
  card,
  onClose,
  onSave,
  onContinueExplore,
  sessionId,
  cardId,
  isLoggedIn = false,
}: ScentCardModalProps) {
  const router = useRouter();
  const [feedbackGiven, setFeedbackGiven] = useState(false);
  const [feedbackType, setFeedbackType] = useState<"positive" | "negative" | null>(null);
  const [feedbackError, setFeedbackError] = useState<string | null>(null);
  const [isSubmittingFeedback, setIsSubmittingFeedback] = useState(false);
  const [mbtiApplied, setMbtiApplied] = useState(false);

  // Props 로깅 (디버깅용)
  useEffect(() => {
    console.log("👉 ScentCardModal Props:");
    console.log("  - sessionId:", sessionId);
    console.log("  - cardId:", cardId);
    console.log("  - cardId type:", typeof cardId);
    console.log("  - isLoggedIn:", isLoggedIn);
  }, [sessionId, cardId, isLoggedIn]);

  // ESC 키로 닫기
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleEscape);
    return () => window.removeEventListener("keydown", handleEscape);
  }, [onClose]);

  // 피드백 제출
  const handleFeedback = async (type: "positive" | "negative") => {
    console.log("🔍 피드백 제출 시작:");
    console.log("  - sessionId:", sessionId, "(type:", typeof sessionId, ")");
    console.log("  - cardId:", cardId, "(type:", typeof cardId, ")");
    console.log("  - type:", type);
    
    // 유효성 검사 강화
    if (!sessionId || !cardId) {
      const errorMsg = !sessionId 
        ? "세션 정보가 만료되었습니다. 페이지를 새로고침해주세요." 
        : "카드 정보가 올바르지 않습니다. 카드를 다시 생성해주세요.";
      
      console.error("❌ 피드백 제출 실패:", errorMsg, { sessionId, cardId });
      setFeedbackError(errorMsg);
      return;
    }
    
    setIsSubmittingFeedback(true);
    setFeedbackError(null);
    
    try {
      const url = `${API_BASE}/session/${sessionId}/feedback?card_id=${cardId}&feedback=${type}`;
      console.log("📡 API 호출:", url);
      
      const response = await fetch(url, { 
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      });
      
      console.log("📥 API 응답 상태:", response.status);
      
      if (response.ok) {
        const data = await response.json();
        console.log("✅ 피드백 저장 성공:", data);
        setFeedbackGiven(true);
        setFeedbackType(type);
      } else {
        const errorData = await response.json().catch(() => ({ detail: "알 수 없는 오류" }));
        const errorMsg = errorData.detail || `서버 오류: ${response.status}`;
        console.error("❌ 피드백 저장 실패:", errorMsg);
        setFeedbackError(errorMsg);
      }
    } catch (error) {
      console.error("❌ 피드백 전송 에러:", error);
      setFeedbackError("네트워크 오류가 발생했습니다. 다시 시도해주세요.");
    } finally {
      setIsSubmittingFeedback(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-6 animate-fade-in"
      onClick={onClose} // 배경 클릭으로 닫기
    >
      <div
        onClick={(e) => e.stopPropagation()} // 모달 내부 클릭은 닫히지 않음
        className="bg-white rounded-3xl shadow-2xl w-full max-w-2xl max-h-[85vh] overflow-y-auto animate-scale-in"
      >
          {/* 헤더 */}
          <div className="sticky top-0 bg-white border-b border-[#E6DDCF] px-8 py-6 flex items-center justify-between rounded-t-3xl z-10">
            <h2 className="text-xl font-semibold text-[#2E2B28]">당신의 향</h2>
            <button
              onClick={onClose}
              className="w-8 h-8 rounded-full hover:bg-[#F8F4EC] flex items-center justify-center transition-colors"
              aria-label="닫기"
            >
              <svg
                className="w-5 h-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>

          {/* 카드 내용 */}
          <div className="px-8 py-8 space-y-8">
            {/* [NEW] 카드 이미지 */}
            {card.image_url && (
              <div className="w-full h-48 rounded-2xl overflow-hidden">
                <img
                  src={card.image_url}
                  alt={card.title}
                  className="w-full h-full object-cover"
                />
              </div>
            )}

            {/* [NEW] MBTI 배지 */}
            {card.mbti_code && (
              <div className="text-center">
                <span className="inline-block px-4 py-2 bg-gradient-to-r from-[#6B4E71] to-[#9B7EAC] text-white rounded-full font-semibold text-sm">
                  💎 {card.mbti_code}
                </span>
              </div>
            )}

            {/* 제목 */}
            <div className="text-center space-y-2">
              <div className="text-4xl mb-2">💫</div>
              <h3 className="text-2xl font-bold text-[#C8A24D]">
                {card.title}
              </h3>
            </div>

            {/* 스토리 */}
            <div className="bg-[#F8F4EC] rounded-2xl p-6">
              <p className="text-base text-[#2E2B28] leading-relaxed">
                {card.story}
              </p>
            </div>

            {/* 어코드 정보 */}
            <div className="space-y-4">
              <h4 className="text-sm font-semibold text-[#7A6B57] uppercase tracking-wider">
                선택하신 향
              </h4>
              <div className="grid gap-3">
                {card.accords.map((accord, index) => (
                  <div
                    key={index}
                    className="bg-white border border-[#E6DDCF] rounded-xl p-4 hover:border-[#C8A24D] transition-colors"
                  >
                    <div className="flex items-start gap-3">
                      <div className="w-8 h-8 rounded-full bg-[#C8A24D]/10 flex items-center justify-center flex-shrink-0">
                        <span className="text-lg">✨</span>
                      </div>
                      <div className="flex-1">
                        <h5 className="font-semibold text-[#2E2B28] mb-1">
                          {accord.name}
                        </h5>
                        <p className="text-sm text-[#7A6B57] leading-relaxed">
                          {accord.description}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* [NEW] MBTI 입력 안내 (회원이지만 MBTI 없는 경우) */}
            {card.mbti_prompt && isLoggedIn && sessionId && !mbtiApplied && (
              <MbtiInputSection
                mbtiPrompt={card.mbti_prompt}
                sessionId={sessionId}
                onSuccess={() => setMbtiApplied(true)}
              />
            )}

            {/* [NEW] 비회원 로그인 유도 */}
            {!isLoggedIn && (
              <div className="bg-gradient-to-br from-gray-50 to-gray-100 border-2 border-dashed border-gray-300 rounded-2xl p-6 text-center space-y-4">
                <div className="text-4xl">🔒</div>
                <div>
                  <p className="text-lg font-bold text-[#2E2B28] mb-2">
                    회원 전용 기능
                  </p>
                  <p className="text-sm text-[#7A6B57] leading-relaxed">
                    MBTI 기반 개인화 카드는 회원만 이용할 수 있어요.<br />
                    로그인하고 나만의 향기 이야기를 만들어보세요.
                  </p>
                </div>
                <button
                  onClick={() => router.push("/login")}
                  className="w-full py-3 bg-gradient-to-r from-[#6B4E71] to-[#9B7EAC] text-white rounded-xl font-bold hover:shadow-lg hover:scale-[1.02] active:scale-[0.98] transition-all"
                >
                  로그인하러 가기
                </button>
              </div>
            )}

            {/* [NEW] 피드백 섹션 */}
            {!feedbackGiven && (
              <div className="text-center bg-gradient-to-br from-gray-50 to-white rounded-2xl p-6 space-y-4 border border-gray-200">
                <div>
                  <span className="text-2xl mb-2 block">💭</span>
                  <p className="font-bold text-[#2E2B28] text-base">
                    이 카드가 도움이 되었나요?
                  </p>
                  <p className="text-xs text-[#7A6B57] mt-1">
                    여러분의 피드백으로 더 나은 추천을 만들어갑니다
                  </p>
                </div>
                <div className="flex gap-3 justify-center">
                  <button
                    onClick={() => handleFeedback("positive")}
                    disabled={isSubmittingFeedback}
                    className="flex-1 max-w-[140px] py-3 border-2 border-[#E6DDCF] bg-white rounded-xl hover:border-[#4CAF50] hover:bg-green-50 hover:scale-105 active:scale-95 transition-all text-base font-semibold disabled:opacity-50 disabled:cursor-not-allowed shadow-sm hover:shadow-md"
                  >
                    {isSubmittingFeedback ? (
                      <span className="flex items-center justify-center gap-2">
                        <svg
                          className="animate-spin h-4 w-4"
                          xmlns="http://www.w3.org/2000/svg"
                          fill="none"
                          viewBox="0 0 24 24"
                        >
                          <circle
                            className="opacity-25"
                            cx="12"
                            cy="12"
                            r="10"
                            stroke="currentColor"
                            strokeWidth="4"
                          ></circle>
                          <path
                            className="opacity-75"
                            fill="currentColor"
                            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                          ></path>
                        </svg>
                      </span>
                    ) : (
                      <span className="flex items-center justify-center gap-1">
                        <span className="text-xl">👍</span>
                        <span className="text-sm">좋아요</span>
                      </span>
                    )}
                  </button>
                  <button
                    onClick={() => handleFeedback("negative")}
                    disabled={isSubmittingFeedback}
                    className="flex-1 max-w-[140px] py-3 border-2 border-[#E6DDCF] bg-white rounded-xl hover:border-[#FF6B6B] hover:bg-red-50 hover:scale-105 active:scale-95 transition-all text-base font-semibold disabled:opacity-50 disabled:cursor-not-allowed shadow-sm hover:shadow-md"
                  >
                    {isSubmittingFeedback ? (
                      <span className="flex items-center justify-center gap-2">
                        <svg
                          className="animate-spin h-4 w-4"
                          xmlns="http://www.w3.org/2000/svg"
                          fill="none"
                          viewBox="0 0 24 24"
                        >
                          <circle
                            className="opacity-25"
                            cx="12"
                            cy="12"
                            r="10"
                            stroke="currentColor"
                            strokeWidth="4"
                          ></circle>
                          <path
                            className="opacity-75"
                            fill="currentColor"
                            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                          ></path>
                        </svg>
                      </span>
                    ) : (
                      <span className="flex items-center justify-center gap-1">
                        <span className="text-xl">👎</span>
                        <span className="text-sm">아쉬워요</span>
                      </span>
                    )}
                  </button>
                </div>
                
                {/* 에러 메시지 표시 */}
                {feedbackError && (
                  <div className="mt-3 p-4 bg-red-50 border-2 border-red-200 rounded-xl animate-fade-in">
                    <div className="flex items-start gap-3">
                      <span className="text-xl">⚠️</span>
                      <div className="flex-1">
                        <p className="text-sm text-red-700 font-medium">
                          {feedbackError}
                        </p>
                        <button
                          onClick={() => setFeedbackError(null)}
                          className="mt-2 text-xs text-red-600 underline hover:text-red-800 transition-colors"
                        >
                          닫기
                        </button>
                      </div>
                    </div>
                  </div>
                )}
                
                {/* 디버그 정보 (개발 중에만 표시) */}
                {process.env.NODE_ENV === 'development' && (
                  <p className="text-xs text-gray-400 mt-2">
                    Debug: sessionId={sessionId ? "✓" : "✗"} / cardId={cardId ? "✓" : "✗"}
                  </p>
                )}
              </div>
            )}

            {feedbackGiven && (
              <div className={`text-center rounded-2xl p-6 border-2 animate-fade-in ${
                feedbackType === "positive" 
                  ? "bg-gradient-to-br from-green-50 to-emerald-50 border-green-200" 
                  : "bg-gradient-to-br from-orange-50 to-amber-50 border-orange-200"
              }`}>
                <span className="text-4xl mb-3 block">
                  {feedbackType === "positive" ? "🎉" : "💡"}
                </span>
                <p className={`font-bold text-lg mb-2 ${
                  feedbackType === "positive" ? "text-green-700" : "text-orange-700"
                }`}>
                  {feedbackType === "positive" 
                    ? "피드백 감사합니다!" 
                    : "소중한 의견 감사합니다!"}
                </p>
                <p className="text-sm text-[#7A6B57] leading-relaxed">
                  {feedbackType === "positive"
                    ? "앞으로도 취향에 꼭 맞는 향기를 추천해드릴게요."
                    : "더 나은 향기 추천을 위해 피드백을 반영하겠습니다."}
                </p>
              </div>
            )}

            {/* [NEW] 다음 단계 CTA */}
            {card.next_actions && card.next_actions.length > 0 && (
              <div className="pt-6 border-t-2 border-gray-200 space-y-4">
                <h3 className="text-lg font-bold text-gray-800 text-center">
                  다음 단계
                </h3>
                {card.next_actions.map((action) => (
                  <div
                    key={action.type}
                    className="bg-gray-50 rounded-2xl p-5 space-y-3"
                  >
                    <h4 className="font-semibold text-[#6B4E71]">
                      {action.title}
                    </h4>
                    <p className="text-sm text-gray-600">{action.description}</p>
                    <button
                      onClick={() => router.push(action.link)}
                      className="w-full py-3 bg-gradient-to-r from-[#6B4E71] to-[#9B7EAC] text-white rounded-lg font-semibold hover:shadow-lg transition-all"
                    >
                      {action.button_text}
                    </button>
                  </div>
                ))}
              </div>
            )}

            {/* 생성 시간 */}
            <div className="text-center">
              <p className="text-xs text-[#9C8D7A]">
                {new Date(card.created_at).toLocaleString("ko-KR", {
                  year: "numeric",
                  month: "long",
                  day: "numeric",
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </p>
            </div>
          </div>

          {/* 푸터 버튼 */}
          <div className="sticky bottom-0 bg-white border-t border-[#E6DDCF] px-8 py-6 flex gap-3 rounded-b-3xl">
            {onSave && (
              <button
                onClick={onSave}
                className="flex-1 h-12 rounded-full bg-[#C8A24D] text-white font-semibold hover:bg-[#B89342] transition-colors flex items-center justify-center gap-2"
              >
                <svg
                  className="w-5 h-5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M5 13l4 4L19 7"
                  />
                </svg>
                카드 저장
              </button>
            )}
            {onContinueExplore && (
              <button
                onClick={onContinueExplore}
                className="flex-1 h-12 rounded-full border border-[#E2D7C5] font-semibold hover:bg-[#F8F4EC] transition-colors flex items-center justify-center gap-2"
              >
                <svg
                  className="w-5 h-5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                  />
                </svg>
                계속 탐색
              </button>
            )}
          </div>
        </div>
      </div>
  );
}
