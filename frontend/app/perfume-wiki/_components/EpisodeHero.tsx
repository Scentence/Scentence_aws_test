/**
 * 에피소드 히어로 섹션 컴포넌트
 * 에피소드 상세 페이지 상단의 대형 이미지와 제목을 표시
 */
import type { Episode } from "../types";

type EpisodeHeroProps = {
  episode: Episode;
  seriesTitle: string;
  episodeNumber: number;
};

export default function EpisodeHero({
  episode,
  seriesTitle,
  episodeNumber,
}: EpisodeHeroProps) {
  // 히어로 이미지가 없으면 썸네일 사용
  const heroImage = episode.heroImage || episode.thumbnail;
  const readTime = episode.readTime || "3분";

  return (
    <section className="relative w-full h-[480px] md:h-[600px] overflow-hidden rounded-3xl">
      <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/30 to-transparent z-10" />
      <img
        src={heroImage}
        alt={episode.title}
        className="w-full h-full object-cover"
      />

      <div className="absolute bottom-0 left-0 right-0 z-20 p-8 md:p-12 space-y-4">
        <div className="flex items-center gap-3 text-white/90 text-sm">
          <span className="font-semibold">{seriesTitle}</span>
          <span className="w-1 h-1 rounded-full bg-white/50" />
          <span>EP {episodeNumber}</span>
          <span className="w-1 h-1 rounded-full bg-white/50" />
          <span>{readTime} 읽기</span>
        </div>

        <h1 className="text-3xl md:text-5xl font-bold text-white leading-tight max-w-3xl">
          {episode.title}
        </h1>

        <p className="text-base md:text-lg text-white/80 max-w-2xl">
          {episode.date}
        </p>
      </div>
    </section>
  );
}
