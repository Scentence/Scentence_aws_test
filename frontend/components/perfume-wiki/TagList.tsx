/**
 * 태그 리스트 컴포넌트
 * 에피소드 관련 키워드 태그들을 표시
 */
type TagListProps = {
  tags: string[];
};

export default function TagList({ tags }: TagListProps) {
  if (!tags || tags.length === 0) {
    return null;
  }

  return (
    <div className="flex flex-wrap gap-3">
      {tags.map((tag) => (
        <span
          key={tag}
          className="px-4 py-2 rounded-full bg-[#F7F7F7] text-[#555] text-xs font-medium hover:bg-[#EFEFEF] hover:text-[#333] transition-all cursor-pointer border border-transparent hover:border-[#E0E0E0]"
        >
          #{tag}
        </span>
      ))}
    </div>
  );
}
