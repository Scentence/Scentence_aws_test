"use client";

import { useState } from "react";
import Link from "next/link";
// ✅ 방금 만든 아카이브 전용 사이드바 불러오기
import ArchiveSidebar from "@/components/archives/ArchiveSidebar";

export default function ArchivesPage() {
    // ✅ [에러 해결 원인] 이 줄이 없어서 에러가 났던 겁니다! (상태 선언)
    const [isSidebarOpen, setIsSidebarOpen] = useState(false);

    return (
        <div className="flex h-screen bg-[#F9F9F9] text-black relative font-sans w-full">

            {/* ✅ 0. 아카이브 전용 사이드바 */}
            <ArchiveSidebar
                isOpen={isSidebarOpen}
                onClose={() => setIsSidebarOpen(false)}
            />

            {/* 사이드바 배경 어둡게 처리 */}
            {isSidebarOpen && (
                <div className="fixed inset-0 bg-black/50 z-40" onClick={() => setIsSidebarOpen(false)} />
            )}

            {/* ✅ 1. 상단 공통 헤더 */}
            <header className="fixed top-0 left-0 right-0 flex items-center justify-between px-5 py-4 bg-white/80 backdrop-blur-md z-30 border-b border-gray-200">
                <Link href="/" className="text-xl font-bold text-black tracking-tight">
                    Scentence
                </Link>
                {/* 햄버거 버튼 (클릭 시 사이드바 열림) */}
                <button onClick={() => setIsSidebarOpen(true)} className="p-1">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-8 h-8 text-[#555]">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
                    </svg>
                </button>
            </header>


            {/* 본문 영역 (헤더 높이만큼 pt-[72px] 띄움) */}
            <main className="flex-1 overflow-y-auto w-full pt-[72px] pb-8 px-5">

                {/* 2. 상단 통계 바 */}
                <section className="w-full max-w-5xl mx-auto mb-10 mt-4">
                    <div className="flex justify-between items-center bg-white rounded-2xl shadow-sm px-10 py-6">
                        <StatItem label="위시" count={0} />
                        <StatItem label="추천" count={0} />
                        <StatItem label="보유" count={0} />
                        <StatItem label="과거" count={0} />
                    </div>
                </section>

                {/* 3. 향수 장식장 (GRID) */}
                <section className="w-full max-w-5xl mx-auto min-h-[600px] bg-white rounded-t-3xl shadow-sm p-8 pb-20">
                    <h2 className="text-xl font-bold mb-6 text-gray-800 px-2">나의 향수 컬렉션</h2>

                    <div className="grid grid-cols-4 md:grid-cols-5 lg:grid-cols-6 gap-x-6 gap-y-12">
                        {Array.from({ length: 12 }).map((_, i) => (
                            <div key={i} className="group flex flex-col gap-3 cursor-pointer">
                                {/* 이미지 자리 */}
                                <div className="aspect-[3/4] bg-gray-100 rounded-xl overflow-hidden transition-transform duration-300 group-hover:-translate-y-2 shadow-inner">
                                    {/* 추후 <img src="..." /> 추가 예정 */}
                                </div>
                                {/* 텍스트 정보 */}
                                <div className="text-center">
                                    <p className="text-xs font-bold text-gray-800 truncate">향수 이름 {i + 1}</p>
                                    <p className="text-[10px] text-gray-500 truncate">브랜드명</p>
                                </div>
                            </div>
                        ))}
                    </div>
                </section>

            </main>


            {/* 4. 우측 하단 플로팅 버튼 (향수 관계 맵 페이지 이동) */}
            <div className="fixed bottom-12 right-12 z-50">
                <Link
                    href="/perfume-network"
                    className="group flex items-center gap-2 bg-black text-white px-6 py-3 rounded-full shadow-xl hover:bg-gray-800 transition-all hover:pr-4"
                >
                    <span className="font-bold text-sm">향수 관계 맵</span>
                    <svg className="w-4 h-4 transition-transform group-hover:translate-x-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                    </svg>
                </Link>
            </div>

        </div>
    );
}

// 통계 아이템 컴포넌트
function StatItem({ label, count }: { label: string; count: number }) {
    return (
        <div className="flex flex-col items-center gap-1 min-w-[80px]">
            <span className="text-sm font-medium text-gray-400 tracking-wide">{label}</span>
            <span className="text-2xl font-bold text-gray-900">{count}</span>
        </div>
    );
}