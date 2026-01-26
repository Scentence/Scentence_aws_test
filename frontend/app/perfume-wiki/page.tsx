/**
 * 향수 백과 메인 페이지
 * 각 시즌의 대표 시리즈를 카드 형태로 렌더링
 */
import Link from "next/link";
import SeriesGrid from "./_components/SeriesGrid";
import perfumeWikiData from "./_data/perfumeWiki.json";
import type { PerfumeWikiData } from "./types";

const data = perfumeWikiData as PerfumeWikiData;

/**
 * 시즌 데이터에서 각 시즌의 첫 번째 시리즈를 추출하여
 * 메인 페이지에 표시할 카드 목록 데이터 생성
 */
const seriesList = data.seasons.flatMap((season, index) => {
  const [primarySeries] = season.series;
  if (!primarySeries) {
    return [];
  }

  return [
    {
      ...primarySeries,
      seriesLabel: `Series ${index + 1}`,
      seasonTitle: season.title,
    },
  ];
});

export default function PerfumeWikiPage() {
  return (
    <div className="min-h-screen bg-[#FDFBF8] text-[#2B2B2B] font-sans">
      <header className="fixed top-0 left-0 right-0 z-30 flex items-center justify-between px-6 md:px-10 py-5 bg-[#FDFBF8] border-b border-[#F0F0F0]">
        <Link
          href="/"
          className="text-xl font-bold tracking-tight text-[#333] hover:opacity-70 transition"
        >
          Scentence
        </Link>
        <span className="text-xs font-semibold text-[#8C6A1D] tracking-[0.3em] uppercase">
          Perfume Wiki
        </span>
      </header>

      <main className="pt-[120px] pb-24 px-6 md:px-10 max-w-6xl mx-auto space-y-16">
        <section className="space-y-3">
          <h1 className="text-3xl md:text-4xl font-bold text-[#1F1F1F]">
            향수 백과
          </h1>
          <p className="text-sm md:text-base text-[#777]">
            향수에 대해 더 알아보고 싶다면 시리즈를 따라 향의 흐름을 배워보세요.
          </p>
        </section>

        <SeriesGrid series={seriesList} />
      </main>
    </div>
  );
}
