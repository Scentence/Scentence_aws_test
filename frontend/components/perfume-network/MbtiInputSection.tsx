"use client";

import { useState } from "react";

// API 설정
const API_BASE =
  process.env.NEXT_PUBLIC_SCENTMAP_API_URL ?? "http://localhost:8001";

interface MbtiPrompt {
  message: string;
  options: string[];
}

interface MbtiInputSectionProps {
  mbtiPrompt: MbtiPrompt;
  sessionId: string;
  onSuccess?: () => void;
}

export default function MbtiInputSection({
  mbtiPrompt,
  sessionId,
  onSuccess,
}: MbtiInputSectionProps) {
  const [selectedMbti, setSelectedMbti] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitStatus, setSubmitStatus] = useState<"idle" | "success" | "error">("idle");
  const [errorMessage, setErrorMessage] = useState("");

  const handleSubmit = async () => {
    if (!selectedMbti) return;

    setIsSubmitting(true);
    setSubmitStatus("idle");
    setErrorMessage("");

    try {
      const response = await fetch(
        `${API_BASE}/session/${sessionId}/update-mbti?member_id=1&mbti=${selectedMbti}`,
        { 
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
        }
      );

      if (response.ok) {
        setSubmitStatus("success");
        onSuccess?.();

        // 3초 후 성공 메시지 초기화
        setTimeout(() => {
          setSubmitStatus("idle");
        }, 3000);
      } else {
        const errorText = await response.text().catch(() => "");
        setSubmitStatus("error");
        setErrorMessage(
          errorText
            ? `MBTI 저장에 실패했습니다: ${errorText}`
            : "MBTI 저장에 실패했습니다."
        );
        return;
      }
    } catch (error) {
      console.error("MBTI 저장 실패:", error);
      setSubmitStatus("error");
      setErrorMessage("MBTI 저장 중 오류가 발생했습니다. 다시 시도해주세요.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="bg-gradient-to-br from-[#FFF9E6] to-[#FFF4DB] border-2 border-[#FFD700] rounded-2xl p-6 space-y-4 shadow-sm">
      {/* 헤더 */}
      <div className="text-center">
        <span className="text-2xl mb-2 block">💡</span>
        <p className="font-bold text-[#6B4E71] text-base">
          {mbtiPrompt.message}
        </p>
        <p className="text-xs text-[#7A6B57] mt-2">
          MBTI를 알려주시면 더 정확한 향기 추천을 받으실 수 있어요.
        </p>
      </div>

      {/* 입력 영역 */}
      {submitStatus !== "success" && (
        <div className="flex flex-col gap-3">
          <select
            value={selectedMbti}
            onChange={(e) => setSelectedMbti(e.target.value)}
            disabled={isSubmitting}
            className="w-full px-4 py-3 border-2 border-[#E6DDCF] rounded-xl text-sm font-medium focus:border-[#C8A24D] focus:outline-none focus:ring-2 focus:ring-[#C8A24D]/20 transition-all disabled:opacity-50 disabled:cursor-not-allowed bg-white"
          >
            <option value="">MBTI를 선택해주세요</option>
            {mbtiPrompt.options.map((mbti) => (
              <option key={mbti} value={mbti}>
                {mbti}
              </option>
            ))}
          </select>

          <button
            onClick={handleSubmit}
            disabled={!selectedMbti || isSubmitting}
            className="w-full py-3 bg-gradient-to-r from-[#6B4E71] to-[#9B7EAC] text-white rounded-xl font-bold text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:shadow-lg hover:scale-[1.02] active:scale-[0.98] transition-all"
          >
            {isSubmitting ? (
              <span className="flex items-center justify-center gap-2">
                <svg
                  className="animate-spin h-4 w-4 text-white"
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
                적용 중...
              </span>
            ) : (
              "적용하기"
            )}
          </button>
        </div>
      )}

      {/* 성공 메시지 */}
      {submitStatus === "success" && (
        <div className="text-center bg-white rounded-xl p-4 border-2 border-[#4CAF50] animate-fade-in">
          <span className="text-3xl mb-2 block">✅</span>
          <p className="font-bold text-[#4CAF50] text-base">
            MBTI가 적용되었습니다!
          </p>
          <p className="text-xs text-[#7A6B57] mt-1">
            다음 카드부터 개인화된 추천을 받으실 수 있어요.
          </p>
        </div>
      )}

      {/* 에러 메시지 */}
      {submitStatus === "error" && (
        <div className="bg-red-50 border-2 border-red-300 rounded-xl p-4 text-center animate-fade-in">
          <span className="text-2xl mb-2 block">❌</span>
          <p className="text-sm text-red-700 font-medium">{errorMessage}</p>
          <button
            onClick={() => setSubmitStatus("idle")}
            className="mt-3 text-xs text-red-600 underline hover:text-red-800 transition-colors"
          >
            다시 시도하기
          </button>
        </div>
      )}
    </div>
  );
}
