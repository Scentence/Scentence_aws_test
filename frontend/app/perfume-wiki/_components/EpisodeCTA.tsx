/**
 * 에피소드 CTA(Call To Action) 컴포넌트
 * 에피소드 하단에 다음 액션으로 유도하는 링크 카드들을 표시
 */
import Link from "next/link";

export default function EpisodeCTA() {
  // 사용자에게 제안할 다음 액션 목록
  const actions = [
    {
      title: "일반 향수 추천",
      description: "나에게 딱 맞는 향수를 찾아보세요",
      href: "/recommendation",
      bgColor: "bg-[#FFF8E7]",
      hoverColor: "hover:bg-[#FFF0D0]",
    },
    {
      title: "레이어링 추천",
      description: "향을 조합하여 나만의 무드를 만들어보세요",
      href: "/layering",
      bgColor: "bg-[#F0F4FF]",
      hoverColor: "hover:bg-[#E5EEFF]",
    },
    {
      title: "향수맵 바로가기",
      description: "향수의 세계를 시각적으로 탐색해보세요",
      href: "/map",
      bgColor: "bg-[#F0FFF4]",
      hoverColor: "hover:bg-[#E0FFE9]",
    },
  ];

  return (
    <section className="py-12 px-6 rounded-3xl bg-gradient-to-br from-[#FDFBF8] to-[#F8F6F1] border border-[#F0F0F0]">
      <div className="text-center mb-8">
        <h3 className="text-2xl font-bold text-[#1F1F1F] mb-2">
          다음 단계를 시작해보세요
        </h3>
        <p className="text-sm text-[#777]">
          이제 배운 내용을 바탕으로 실제 향수를 탐색해보는 건 어떨까요?
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-5 max-w-5xl mx-auto">
        {actions.map((action) => (
          <Link
            key={action.href}
            href={action.href}
            className={`group flex flex-col p-6 rounded-2xl ${action.bgColor} ${action.hoverColor} transition-all border border-transparent hover:border-[#C8A24D] hover:shadow-md`}
          >
            <h4 className="text-lg font-bold text-[#2B2B2B] mb-2">
              {action.title}
            </h4>
            <p className="text-sm text-[#666] leading-relaxed">
              {action.description}
            </p>
            <span className="mt-4 text-[#C8A24D] text-sm font-semibold group-hover:translate-x-1 transition-transform inline-block">
              바로가기 →
            </span>
          </Link>
        ))}
      </div>
    </section>
  );
}
