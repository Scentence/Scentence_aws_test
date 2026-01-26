/**
 * 에피소드 상세 페이지
 * 에피소드의 전체 콘텐츠와 관련 정보를 표시
 */
import Link from "next/link";
import { notFound } from "next/navigation";
import EpisodeHero from "../../_components/EpisodeHero";
import EpisodeContentSection from "../../_components/EpisodeContentSection";
import EpisodeCTA from "../../_components/EpisodeCTA";
import SeriesRelatedCard from "../../_components/SeriesRelatedCard";
import TagList from "../../_components/TagList";
import LikeButton from "../../_components/LikeButton";
import ShareButton from "../../_components/ShareButton";
import perfumeWikiData from "../../_data/perfumeWiki.json";
import type { PerfumeWikiData, Series, Episode, ContentSection } from "../../types";

const data = perfumeWikiData as PerfumeWikiData;

type EpisodePageProps = {
  params: Promise<{ seriesId: string; episodeId: string }>;
};

/**
 * 시리즈와 에피소드를 ID로 검색
 * @returns 시리즈, 에피소드, 에피소드 번호를 포함한 객체 또는 null
 */
function findSeriesAndEpisode(
  seriesId: string,
  episodeId: string
): { series: Series; episode: Episode; episodeNumber: number } | null {
  for (const season of data.seasons) {
    for (const series of season.series) {
      if (series.id === seriesId) {
        const episodeIndex = series.episodes.findIndex(
          (ep) => ep.id === episodeId
        );
        if (episodeIndex !== -1) {
          return {
            series,
            episode: series.episodes[episodeIndex],
            episodeNumber: episodeIndex + 1,
          };
        }
      }
    }
  }
  return null;
}

/**
 * 에피소드 콘텐츠가 없을 경우 사용할 기본 콘텐츠
 * (향후 실제 데이터로 대체 예정)
 */
function getDefaultContent(): ContentSection[] {
  return [
    {
      subtitle: "향수의 기본 이해",
      paragraphs: [
        "향수는 시간이 지나면서 향이 변화하는 특성을 가지고 있습니다. 탑 노트, 미들 노트, 베이스 노트로 구성되며, 각 단계마다 다른 향을 경험할 수 있습니다.",
        "향수를 선택할 때는 자신의 피부 타입과 취향을 고려하여 선택하는 것이 중요합니다. 같은 향수라도 사람마다 다르게 표현될 수 있습니다.",
      ],
    },
    {
      subtitle: "향수 사용 팁",
      paragraphs: [
        "향수는 체온이 높은 부위에 뿌리면 더 오래 지속되고 향이 잘 퍼집니다. 손목, 목, 귀 뒤가 대표적인 포인트입니다.",
      ],
    },
  ];
}

export default async function EpisodePage({ params }: EpisodePageProps) {
  const { seriesId, episodeId } = await params;
  const result = findSeriesAndEpisode(seriesId, episodeId);

  if (!result) {
    notFound();
  }

  const { series, episode, episodeNumber } = result;

  // 콘텐츠와 태그 설정 (없을 경우 기본값 사용)
  const content = episode.content || getDefaultContent();
  const tags = episode.tags || ["향수입문", "향의변화", "탑노트", "미들노트"];

  return (
    <div className="min-h-screen bg-[#FDFBF8] text-[#2B2B2B] font-sans">
      {/* Header */}
      <header className="fixed top-0 left-0 right-0 z-30 flex items-center justify-between px-6 md:px-10 py-5 bg-[#FDFBF8]/95 backdrop-blur-sm border-b border-[#F0F0F0]">
        <Link
          href="/"
          className="text-xl font-bold tracking-tight text-[#333] hover:opacity-70 transition"
        >
          Scentence
        </Link>
        <Link
          href="/perfume-wiki"
          className="text-xs font-semibold text-[#8C6A1D] tracking-[0.3em] uppercase hover:opacity-70 transition"
        >
          Perfume Wiki
        </Link>
      </header>

      <main className="pt-[80px] pb-24">
        {/* Hero Section */}
        <div className="px-6 md:px-10 max-w-7xl mx-auto mb-12">
          <EpisodeHero
            episode={episode}
            seriesTitle={series.title}
            episodeNumber={episodeNumber}
          />
        </div>

        {/* Like & Share Buttons */}
        <div className="px-6 md:px-10 max-w-3xl mx-auto mb-12">
          <div className="flex items-center gap-3">
            <LikeButton />
            <ShareButton />
          </div>
        </div>

        {/* Content Section */}
        <div className="px-6 md:px-10 mb-20">
          <EpisodeContentSection content={content} />
        </div>

        {/* CTA Section */}
        <div className="px-6 md:px-10 max-w-7xl mx-auto mb-20">
          <EpisodeCTA />
        </div>

        {/* Series Related Section */}
        <div className="px-6 md:px-10 max-w-5xl mx-auto mb-16">
          <SeriesRelatedCard series={series} currentEpisodeId={episode.id} />
        </div>

        {/* Tags Section */}
        <div className="px-6 md:px-10 max-w-3xl mx-auto">
          <div className="space-y-4">
            <h3 className="text-sm font-bold text-[#555]">관련 키워드</h3>
            <TagList tags={tags} />
          </div>
        </div>
      </main>
    </div>
  );
}
