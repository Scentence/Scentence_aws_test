/**
 * 에피소드 리스트 아이템 컴포넌트
 * 에피소드 목록에서 각 에피소드를 카드 형태로 표시
 */
import Link from "next/link";
import type { Episode } from "@/app/perfume-wiki/types";

type EpisodeListItemProps = {
  episode: Episode;
  seriesId: string;
};

export default function EpisodeListItem({
  episode,
  seriesId,
}: EpisodeListItemProps) {
  return (
    <Link href={`/perfume-wiki/${seriesId}/${episode.id}`}>
      <article className="flex items-center justify-between gap-6 md:gap-8 rounded-2xl border border-[#EFEFEF] bg-white p-6 md:p-7 hover:shadow-lg hover:border-[#C8A24D] hover:-translate-y-1 transition-all duration-300 cursor-pointer mb-6">
        <div className="flex-1 space-y-3">
          <span className="inline-flex items-center px-3 py-1.5 rounded-full bg-[#FFF3D6] text-[#8C6A1D] text-xs font-semibold tracking-wide">
            {episode.tag}
          </span>
          <div>
            <h3 className="text-lg font-bold text-[#2A2A2A] leading-snug mb-2">
              {episode.title}
            </h3>
            <p className="text-sm text-[#777] leading-relaxed">{episode.summary}</p>
          </div>
          <p className="text-xs text-[#A0A0A0] font-medium">{episode.date}</p>
        </div>
        <div className="w-[120px] h-[120px] md:w-[140px] md:h-[140px] rounded-2xl overflow-hidden bg-[#EFEFEF] shrink-0 shadow-sm">
          <img
            src={episode.thumbnail}
            alt={episode.title}
            className="w-full h-full object-cover hover:scale-105 transition-transform duration-300"
          />
        </div>
      </article>
    </Link>
  );
}
