"use client";

import React from 'react';

/**
 * 향수 맵 및 카드 생성 시 사용되는 공통 로딩 오버레이
 */
const LoadingOverlay = () => {
  return (
    <div className="fixed inset-0 z-[200] flex flex-col items-center justify-center bg-white/80 backdrop-blur-md animate-in fade-in duration-500">
      <div className="relative w-24 h-24 mb-8">
        {/* 중앙 아이콘 */}
        <div className="absolute inset-0 flex items-center justify-center text-4xl animate-pulse">
          🫧
        </div>
        
        {/* 회전하는 링 */}
        <div className="absolute inset-0 border-4 border-[#C8A24D]/20 rounded-full"></div>
        <div className="absolute inset-0 border-4 border-[#C8A24D] border-t-transparent rounded-full animate-spin"></div>
      </div>

      <div className="text-center space-y-3">
        <h3 className="text-xl font-bold text-[#1F1F1F] tracking-tight">
          당신의 향기를 분석 중입니다
        </h3>
        <p className="text-sm text-[#7A6B57] max-w-[240px] leading-relaxed">
          탐색하신 데이터를 바탕으로<br />
          세상에 하나뿐인 향기 카드를 만들고 있어요.
        </p>
      </div>

      {/* 하단 진행 상태 바 시뮬레이션 */}
      <div className="mt-12 w-48 h-1 bg-[#E6DDCF] rounded-full overflow-hidden">
        <div className="h-full bg-[#C8A24D] rounded-full animate-progress-shimmer w-full origin-left"></div>
      </div>

      <style jsx>{`
        @keyframes progress-shimmer {
          0% { transform: scaleX(0); opacity: 0.5; }
          50% { transform: scaleX(0.7); opacity: 1; }
          100% { transform: scaleX(1); opacity: 0; }
        }
        .animate-progress-shimmer {
          animation: progress-shimmer 2s infinite ease-in-out;
        }
      `}</style>
    </div>
  );
};

export default LoadingOverlay;
