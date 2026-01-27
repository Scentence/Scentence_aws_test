"use client";

import { useEffect, useState } from "react";

interface LoadingOverlayProps {
  message?: string;
}

const LOADING_STEPS = [
  { text: "취향을 분석하고 있어요...", icon: "🔍", color: "from-blue-400 to-blue-600" },
  { text: "향을 조합하고 있어요...", icon: "🌸", color: "from-pink-400 to-pink-600" },
  { text: "스토리를 만들고 있어요...", icon: "✍️", color: "from-purple-400 to-purple-600" },
  { text: "마지막 손질 중이에요...", icon: "✨", color: "from-amber-400 to-amber-600" },
];

export default function LoadingOverlay({ message }: LoadingOverlayProps) {
  const [step, setStep] = useState(0);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    // 단계별 전환 (1초마다)
    const stepInterval = setInterval(() => {
      setStep((prev) => (prev + 1) % LOADING_STEPS.length);
    }, 1200);

    // 프로그레스 바 증가 (전체 5초 가정)
    const progressInterval = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 95) return prev; // 95%에서 멈춤 (완료는 서버 응답 후)
        return prev + 1;
      });
    }, 50);

    return () => {
      clearInterval(stepInterval);
      clearInterval(progressInterval);
    };
  }, []);

  const currentStep = LOADING_STEPS[step];

  return (
    <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-md flex items-center justify-center animate-fade-in">
      <div className="bg-white rounded-3xl shadow-2xl p-10 max-w-md w-full mx-6 border border-[#E6DDCF]">
        <div className="text-center space-y-6">
          {/* 로딩 스피너 */}
          <div className="relative w-24 h-24 mx-auto">
            {/* 외곽 원 */}
            <div className="absolute inset-0 rounded-full border-4 border-[#E6DDCF]"></div>
            {/* 회전하는 그라데이션 원 */}
            <div className={`absolute inset-0 rounded-full border-4 border-transparent bg-gradient-to-tr ${currentStep.color} animate-spin`} 
                 style={{ 
                   borderTopColor: 'transparent',
                   clipPath: 'polygon(50% 50%, 50% 0%, 100% 0%, 100% 100%, 0% 100%, 0% 0%, 50% 0%)'
                 }}>
            </div>
            {/* 아이콘 */}
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-4xl animate-bounce" style={{ animationDuration: '1s' }}>
                {currentStep.icon}
              </span>
            </div>
          </div>

          {/* 메시지 */}
          <div className="space-y-2">
            <h3 className="text-xl font-bold text-[#2E2B28]">
              향기카드를 만들고 있어요
            </h3>
            <p className="text-base text-[#7A6B57] leading-relaxed font-medium animate-pulse">
              {message || currentStep.text}
            </p>
          </div>

          {/* 단계 인디케이터 */}
          <div className="flex justify-center gap-2">
            {LOADING_STEPS.map((_, idx) => (
              <div
                key={idx}
                className={`h-2 rounded-full transition-all duration-300 ${
                  idx === step
                    ? "w-8 bg-gradient-to-r from-[#6B4E71] to-[#9B7EAC]"
                    : "w-2 bg-[#E6DDCF]"
                }`}
              />
            ))}
          </div>

          {/* 프로그레스 바 */}
          <div className="w-full h-2 bg-[#E6DDCF] rounded-full overflow-hidden">
            <div 
              className="h-full bg-gradient-to-r from-[#6B4E71] to-[#9B7EAC] transition-all duration-300 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>

          {/* 추가 안내 */}
          <p className="text-xs text-[#9C8D7A]">
            잠시만 기다려주세요. 당신만의 특별한 향기 이야기를 완성하고 있어요 ✨
          </p>
        </div>
      </div>
    </div>
  );
}
