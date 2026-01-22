"use client";

import { useState } from "react";
import Link from "next/link";
import Sidebar from "@/components/common/sidebar";

export default function ScentCardCreatePage() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [cardMode, setCardMode] = useState<"random" | "recommend">("random");
  const [selectedOccasion, setSelectedOccasion] = useState<string | null>(null);
  const [selectedSeason, setSelectedSeason] = useState<string | null>(null);
  const [selectedGender, setSelectedGender] = useState<string | null>(null);

  const occasions = [
    { value: "Daily", label: "데일리리" },
    { value: "Leisure", label: "휴식" },
    { value: "Evening", label: "저녁모임" },
    { value: "Night Out", label: "외출" },
    { value: "Business", label: "비즈니스" },
    { value: "Sport", label: "스포츠" }
  ];
  const seasons = ["봄", "여름", "가을", "겨울"];
  const genders = [
    { value: "Feminine", label: "여성" },
    { value: "Masculine", label: "남성" },
    { value: "Unisex", label: "유니섹스" }
  ];

  return (
    <div className="flex h-screen bg-white overflow-hidden text-black relative font-sans">
      <Sidebar
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
        context="home"
      />

      <main className="flex-1 flex flex-col relative w-full h-full overflow-y-auto no-scrollbar pb-8 pt-[72px]">
        {isSidebarOpen && (
          <div
            className="fixed inset-0 bg-black/50 z-40 md:hidden"
            onClick={() => setIsSidebarOpen(false)}
          />
        )}

        <header className="fixed top-0 left-0 right-0 flex items-center justify-between px-5 py-4 bg-[#E5E5E5] z-50">
          <div className="flex items-center gap-3">
            <Link href="/" className="text-xl font-bold text-black tracking-tight">
              Scentence
            </Link>
          </div>

          <button onClick={() => setIsSidebarOpen(true)} className="p-1">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={1.5}
              stroke="currentColor"
              className="w-8 h-8 text-[#555]"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5"
              />
            </svg>
          </button>
        </header>

        <div className="px-5 space-y-8 mt-6 w-full max-w-3xl mx-auto">
          <section className="rounded-2xl bg-[#F4F2EE] p-6 space-y-3 border border-[#E6DDCB]">
            <div className="flex items-center justify-between">
              <h1 className="text-xl font-bold text-[#2B2B2B]">
                나만의 향기 카드 만들기
              </h1>
            </div>
            <p className="text-sm text-[#666]">
              나만의 향에 맞춘 카드로 지금의 분위기를 기록해요.
            </p>
          </section>

          <section className="rounded-2xl bg-white border border-[#EAD7A1] p-5 space-y-4 shadow-[0_6px_18px_rgba(140,106,29,0.08)]">
            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={() => setCardMode("random")}
                className={`py-3 rounded-xl text-sm font-bold transition ${
                  cardMode === "random"
                    ? "bg-[#2B2B2B] text-white"
                    : "bg-[#F4F2EE] text-[#6B5A2B] hover:bg-[#EAE4D8]"
                }`}
              >
                랜덤 향기 카드
              </button>
              <button
                onClick={() => setCardMode("recommend")}
                className={`py-3 rounded-xl text-sm font-bold transition ${
                  cardMode === "recommend"
                    ? "bg-[#2B2B2B] text-white"
                    : "bg-[#F4F2EE] text-[#6B5A2B] hover:bg-[#EAE4D8]"
                }`}
              >
                회원 맞춤 향기 카드
              </button>
            </div>

            <div className="space-y-2">
              <h2 className="text-base font-bold text-[#2B2B2B]">
                {cardMode === "random" ? "랜덤 카드 생성" : "회원 맞춤 추천"}
              </h2>
              <p className="text-sm text-[#6B5A2B]">
                {cardMode === "random"
                  ? "간단한 분위기만 입력하면 21가지 향 캐릭터 중에서 바로 추천해요."
                  : "회원 데이터 기반으로 사용자와 가장 잘 맞는 향 카드를 완성해요."}
              </p>
              <p className="text-xs text-[#777]">
                {cardMode === "random"
                  ? "비회원도 참여할 수 있는 랜덤 카드 체험입니다."
                  : "회원 데이터 기반으로 향기 카드를 제공합니다."}
              </p>
            </div>
          </section>

          <section className="rounded-2xl bg-white border border-[#E6E6E6] p-5 space-y-4">
            <h3 className="text-base font-bold text-[#2B2B2B]">분위기 간단 입력</h3>
            <div className="space-y-3">
              <div className="space-y-1">
                <p className="text-xs text-[#666] font-semibold">이미지 입력(선택)</p>
                <input
                  type="file"
                  accept="image/*"
                  className="w-full rounded-xl border border-[#E0E0E0] px-4 py-3 text-xs text-[#666]"
                />
              </div>
              <div className="space-y-1">
                <p className="text-xs text-[#666] font-semibold">분위기 한 줄</p>
                <input
                  type="text"
                  placeholder="예: 비 오는 저녁, 따뜻한 홍차"
                  className="w-full rounded-xl border border-[#E0E0E0] px-4 py-3 text-sm outline-none focus:border-[#C8A24D]"
                />
              </div>
              <div className="space-y-2">
                <p className="text-xs text-[#666] font-semibold">상황 키워드</p>
                <div className="flex flex-wrap gap-2">
                {occasions.map((occasion) => (
                    <button
                    key={occasion.value}
                      type="button"
                      onClick={() =>
                        setSelectedOccasion((prev) =>
                        prev === occasion.value ? null : occasion.value
                        )
                      }
                      className={`px-3 py-2 rounded-full text-xs font-semibold transition ${
                      selectedOccasion === occasion.value
                          ? "bg-[#2B2B2B] text-white"
                          : "bg-[#F4F2EE] text-[#6B5A2B] hover:bg-[#EAE4D8]"
                      }`}
                    >
                    {occasion.label}
                    </button>
                  ))}
                </div>
              </div>
              <div className="space-y-2">
                <p className="text-xs text-[#666] font-semibold">계절 키워드</p>
                <div className="flex flex-wrap gap-2">
                  {seasons.map((season) => (
                    <button
                      key={season}
                      type="button"
                      onClick={() =>
                        setSelectedSeason((prev) =>
                          prev === season ? null : season
                        )
                      }
                      className={`px-3 py-2 rounded-full text-xs font-semibold transition ${
                        selectedSeason === season
                          ? "bg-[#2B2B2B] text-white"
                          : "bg-[#F4F2EE] text-[#6B5A2B] hover:bg-[#EAE4D8]"
                      }`}
                    >
                      {season}
                    </button>
                  ))}
                </div>
              </div>
              <div className="space-y-2">
                <p className="text-xs text-[#666] font-semibold">성별 키워드</p>
                <div className="flex flex-wrap gap-2">
                  {genders.map((gender) => (
                    <button
                      key={gender.value}
                      type="button"
                      onClick={() =>
                        setSelectedGender((prev) =>
                          prev === gender.value ? null : gender.value
                        )
                      }
                      className={`px-3 py-2 rounded-full text-xs font-semibold transition ${
                        selectedGender === gender.value
                          ? "bg-[#2B2B2B] text-white"
                          : "bg-[#F4F2EE] text-[#6B5A2B] hover:bg-[#EAE4D8]"
                      }`}
                    >
                      {gender.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </section>

          <button className="w-full py-3 rounded-xl bg-[#2B2B2B] text-white font-bold hover:bg-black transition">
            카드 생성하기
          </button>
        </div>
      </main>
    </div>
  );
}
