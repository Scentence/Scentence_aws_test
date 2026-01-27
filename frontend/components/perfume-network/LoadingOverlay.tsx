"use client";

interface LoadingOverlayProps {
  message: string;
}

export default function LoadingOverlay({ message }: LoadingOverlayProps) {
  return (
    <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-center justify-center animate-fade-in">
      <div className="bg-white rounded-2xl shadow-2xl p-8 max-w-sm w-full mx-6">
        <div className="text-center space-y-6">
          {/* 로딩 스피너 */}
          <div className="relative w-20 h-20 mx-auto">
            <div className="absolute inset-0 rounded-full border-4 border-[#E6DDCF]"></div>
            <div className="absolute inset-0 rounded-full border-4 border-[#C8A24D] border-t-transparent animate-spin"></div>
            <div className="absolute inset-0 flex items-center justify-center text-3xl">
              ✨
            </div>
          </div>

          {/* 메시지 */}
          <div>
            <h3 className="text-lg font-semibold text-[#2E2B28] mb-2">
              향기카드를 만들고 있어요
            </h3>
            <p className="text-sm text-[#7A6B57] leading-relaxed">
              {message}
            </p>
          </div>

          {/* 프로그레스 바 (선택적) */}
          <div className="w-full h-1 bg-[#E6DDCF] rounded-full overflow-hidden">
            <div className="h-full bg-[#C8A24D] animate-progress" />
          </div>
        </div>
      </div>
    </div>
  );
}
