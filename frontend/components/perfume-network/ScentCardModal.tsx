"use client";

import { useEffect } from "react";

interface AccordInfo {
  name: string;
  description: string;
}

interface ScentCard {
  title: string;
  story: string;
  accords: AccordInfo[];
  created_at: string;
}

interface ScentCardModalProps {
  card: ScentCard;
  onClose: () => void;
  onSave?: () => void;
  onContinueExplore?: () => void;
}

export default function ScentCardModal({
  card,
  onClose,
  onSave,
  onContinueExplore,
}: ScentCardModalProps) {
  // ESC 키로 닫기
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleEscape);
    return () => window.removeEventListener("keydown", handleEscape);
  }, [onClose]);

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
