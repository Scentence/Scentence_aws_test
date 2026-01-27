"use client";

interface CardTriggerBannerProps {
  message: string;
  onAccept: () => void;
  onDismiss: () => void;
}

export default function CardTriggerBanner({
  message,
  onAccept,
  onDismiss,
}: CardTriggerBannerProps) {
  return (
    <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40 w-full max-w-lg px-6 animate-slide-up">
      <div className="relative bg-gradient-to-br from-white to-[#FFF9F0] rounded-2xl shadow-2xl border-2 border-[#C8A24D] p-6 overflow-hidden">
        {/* 배경 장식 */}
        <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-[#C8A24D]/10 to-transparent rounded-full blur-2xl"></div>
        <div className="absolute bottom-0 left-0 w-24 h-24 bg-gradient-to-tr from-[#9B7EAC]/10 to-transparent rounded-full blur-2xl"></div>
        
        <div className="relative">
          <div className="flex items-start gap-4">
            {/* 아이콘 */}
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-[#C8A24D] to-[#B89342] flex items-center justify-center flex-shrink-0 shadow-lg">
              <span className="text-3xl animate-bounce" style={{ animationDuration: '1.5s' }}>
                💫
              </span>
            </div>

            {/* 메시지 */}
            <div className="flex-1">
              <h3 className="text-xl font-bold text-[#2E2B28] mb-2 flex items-center gap-2">
                취향이 쌓였어요!
                <span className="text-base">✨</span>
              </h3>
              <p className="text-sm text-[#7A6B57] leading-relaxed">
                {message}
              </p>
            </div>

            {/* 닫기 버튼 */}
            <button
              onClick={onDismiss}
              className="w-8 h-8 rounded-full hover:bg-gray-100 flex items-center justify-center transition-colors flex-shrink-0"
              aria-label="닫기"
            >
              <svg
                className="w-5 h-5 text-gray-400"
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

          {/* 버튼 */}
          <div className="flex gap-3 mt-5">
            <button
              onClick={onAccept}
              className="flex-1 h-12 rounded-xl bg-gradient-to-r from-[#C8A24D] to-[#B89342] text-white text-sm font-bold hover:shadow-lg hover:scale-[1.02] active:scale-[0.98] transition-all flex items-center justify-center gap-2"
            >
              <span>👉</span>
              <span>지금 만들기</span>
            </button>
            <button
              onClick={onDismiss}
              className="px-6 h-12 rounded-xl border-2 border-[#E2D7C5] text-sm font-bold hover:bg-[#F8F4EC] hover:border-[#C8A24D] transition-all"
            >
              나중에
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
