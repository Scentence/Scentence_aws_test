/**
 * 에피소드 콘텐츠 섹션 컴포넌트
 * 에피소드의 본문 내용을 섹션 단위로 표시
 */
import type { ContentSection } from "../types";

type EpisodeContentSectionProps = {
  content: ContentSection[];
};

export default function EpisodeContentSection({
  content,
}: EpisodeContentSectionProps) {
  if (!content || content.length === 0) {
    return null;
  }

  return (
    <section className="space-y-12 max-w-3xl mx-auto">
      {content.map((section, index) => (
        <div key={index} className="space-y-5">
          <h2 className="text-2xl font-bold text-[#1F1F1F]">
            {section.subtitle}
          </h2>
          <div className="space-y-4">
            {section.paragraphs.map((paragraph, pIndex) => (
              <p
                key={pIndex}
                className="text-base leading-relaxed text-[#444] whitespace-pre-line"
              >
                {paragraph}
              </p>
            ))}
          </div>
        </div>
      ))}
    </section>
  );
}
