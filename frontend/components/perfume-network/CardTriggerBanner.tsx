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
        <div className="bg-white rounded-2xl shadow-xl border-2 border-[#C8A24D] p-6">
          <div className="flex items-start gap-4">
            {/* 아이콘 */}
            <div className="w-12 h-12 rounded-full bg-[#C8A24D]/10 flex items-center justify-center flex-shrink-0">
              <span className="text-2xl">💫</span>
            </div>

            {/* 메시지 */}
            <div className="flex-1">
              <h3 className="text-lg font-semibold text-[#2E2B28] mb-2">
                취향이 쌓였어요!
              </h3>
              <p className="text-sm text-[#7A6B57] leading-relaxed">
                {message}
              </p>
            </div>
          </div>

          {/* 버튼 */}
          <div className="flex gap-3 mt-4">
            <button
              onClick={onAccept}
              className="flex-1 h-11 rounded-full bg-[#C8A24D] text-white text-sm font-semibold hover:bg-[#B89342] transition-colors"
            >
              지금 만들기
            </button>
            <button
              onClick={onDismiss}
              className="flex-1 h-11 rounded-full border border-[#E2D7C5] text-sm font-semibold hover:bg-[#F8F4EC] transition-colors"
            >
              더 둘러보기
            </button>
          </div>
        </div>
      </div>
  );
}
