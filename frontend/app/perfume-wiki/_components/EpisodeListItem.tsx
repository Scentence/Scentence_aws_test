/**
 * 에피소드 리스트 아이템 컴포넌트
 * 에피소드 목록에서 각 에피소드를 카드 형태로 표시
 */
import Link from "next/link";
import type { Episode } from "../types";

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
      <article className="flex items-center justify-between gap-6 rounded-2xl border border-[#EFEFEF] bg-white p-5 hover:shadow-md hover:border-[#C8A24D] transition-all cursor-pointer">
        <div className="space-y-3">
          <span className="inline-flex items-center px-3 py-1 rounded-full bg-[#FFF3D6] text-[#8C6A1D] text-[11px] font-semibold">
            {episode.tag}
          </span>
          <div>
            <h3 className="text-base font-bold text-[#2A2A2A]">
              {episode.title}
            </h3>
            <p className="text-sm text-[#777] mt-1">{episode.summary}</p>
          </div>
          <p className="text-xs text-[#A0A0A0]">{episode.date}</p>
        </div>
        <div className="w-[110px] h-[110px] rounded-2xl overflow-hidden bg-[#EFEFEF] shrink-0">
          <img
            src={episode.thumbnail}
            alt={episode.title}
            className="w-full h-full object-cover"
          />
        </div>
      </article>
    </Link>
  );
}
