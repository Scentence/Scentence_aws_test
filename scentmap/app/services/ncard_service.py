from typing import List
from scentmap.app.schemas.ncard_schemas import ScentCard, MBTIComponent, AccordDetail

class NCardService:
    """
    향기카드 관련 비즈니스 로직을 처리하는 서비스 클래스
    """
    def get_dummy_cards(self) -> List[ScentCard]:
        return [
            ScentCard(
                id=1,
                mbti="ENFP",
                components=[
                    MBTIComponent(axis="존재방식", code="E", desc="에너지를 밖으로 발산하는 당신은 시트러스처럼 주변을 밝게 만듭니다."),
                    MBTIComponent(axis="인식방식", code="N", desc="직관적인 당신의 사고방식은 우디 향처럼 깊고 신비롭습니다."),
                    MBTIComponent(axis="감정질감", code="F", desc="공감하는 따뜻한 마음은 바닐라와 머스크처럼 포근합니다."),
                    MBTIComponent(axis="취향안정성", code="P", desc="유연한 삶을 지향하는 당신은 와일드 플라워처럼 자유롭습니다.")
                ],
                recommends=[
                    AccordDetail(name="Citrus", reason="밝은 에너지와 가장 잘 어울리는 생동감 넘치는 향입니다.", notes=["Bergamot", "Lime"]),
                    AccordDetail(name="Floral", reason="자유로운 영혼에게 자연의 싱그러움을 더해줍니다.", notes=["Jasmine", "Green Tea"]),
                    AccordDetail(name="Floral", reason="자유로운 영혼에게 자연의 싱그러움을 더해줍니다.", notes=["Jasmine", "Green Tea"]),
                ],
                avoids=[
                    AccordDetail(name="Leather", reason="무거운 가죽 향은 당신의 밝은 에너지를 억누를 수 있습니다."),
                    AccordDetail(name="Powdery", reason="정적인 파우더리 향은 역동적인 매력과 거리가 있습니다."),
                ],
                story="해질녘 따스한 햇살 아래 피어나는 들꽃처럼, 당신은 존재만으로도 주변에 긍정적인 파동을 전달합니다.",
                summary="자유롭고 따뜻한 분위기가 당신을 빛나게 할 거예요. 시트러스와 플로럴 어코드를 찾아보세요! (API 데이터)"
            )
        ]

ncard_service = NCardService()
