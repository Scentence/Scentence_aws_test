/**
 * 시리즈 상세 페이지
 * 선택한 시리즈의 에피소드 목록을 페이지네이션과 함께 표시
 */
import Link from "next/link";
import { notFound } from "next/navigation";
import SeriesHeader from "../_components/SeriesHeader";
import EpisodeListItem from "../_components/EpisodeListItem";
import Pagination from "../_components/Pagination";
import perfumeWikiData from "../_data/perfumeWiki.json";
import type { PerfumeWikiData, Series } from "../types";

const data = perfumeWikiData as PerfumeWikiData;
const PAGE_SIZE = 4; // 페이지당 표시할 에피소드 수

type SeriesPageProps = {
  params: Promise<{ seriesId: string }>;
  searchParams?: Promise<{ page?: string }>;
};

/**
 * 시리즈 ID로 데이터 조회
 * 시리즈 ID 또는 시즌 ID로 검색 가능 (시즌 ID인 경우 첫 번째 시리즈 반환)
 */
function findSeries(seriesId: string): Series | undefined {
  for (const season of data.seasons) {
    const series = season.series.find((item) => item.id === seriesId);
    if (series) {
      return series;
    }
    // 시즌 ID로 검색한 경우 해당 시즌의 첫 번째 시리즈 반환
    if (season.id === seriesId) {
      return season.series[0];
    }
  }
  return undefined;
}

export default async function SeriesPage({ params, searchParams }: SeriesPageProps) {
  const { seriesId } = await params;
  const series = findSeries(seriesId);
  
  if (!series) {
    notFound();
  }

  // 페이지네이션 처리
  const searchParamsResolved = await searchParams;
  const currentPage = Math.max(
    1,
    Number.parseInt(searchParamsResolved?.page ?? "1", 10) || 1
  );
  const totalPages = Math.max(1, Math.ceil(series.episodes.length / PAGE_SIZE));
  const startIndex = (currentPage - 1) * PAGE_SIZE;
  const episodes = series.episodes.slice(startIndex, startIndex + PAGE_SIZE);

  return (
    <div className="min-h-screen bg-[#FDFBF8] text-[#2B2B2B] font-sans">
      <header className="fixed top-0 left-0 right-0 z-30 flex items-center justify-between px-6 md:px-10 py-5 bg-[#FDFBF8] border-b border-[#F0F0F0]">
        <Link
          href="/"
          className="text-xl font-bold tracking-tight text-[#333] hover:opacity-70 transition"
        >
          Scentence
        </Link>
        <Link
          href="/perfume-wiki"
          className="text-xs font-semibold text-[#8C6A1D] tracking-[0.3em] uppercase"
        >
          Perfume Wiki
        </Link>
      </header>

      <main className="pt-[120px] pb-24 px-6 md:px-10 max-w-6xl mx-auto space-y-10">
        <SeriesHeader series={series} />

        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-[#1F1F1F]">
              에피소드 리스트
            </h2>
            <span className="text-xs text-[#999]">{`총 ${series.episodes.length}개`}</span>
          </div>
          <div className="space-y-4">
            {episodes.map((episode) => (
              <EpisodeListItem
                key={episode.id}
                episode={episode}
                seriesId={series.id}
              />
            ))}
          </div>
        </section>

        <Pagination
          basePath={`/perfume-wiki/${series.id}`}
          currentPage={currentPage}
          totalPages={totalPages}
        />
      </main>
    </div>
  );
}
