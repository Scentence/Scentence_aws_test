import json
import random
import os
from typing import List, Dict
from scentmap.app.schemas.ncard_schemas import ScentCard, MBTIComponent, AccordDetail

class NCardService:
    """
    향기카드 관련 비즈니스 로직을 처리하는 서비스 클래스
    """
    def __init__(self):
        # 데이터 로드
        data_path = os.path.join(os.path.dirname(__file__), "../../data/perfume_mbti.json")
        with open(data_path, "r", encoding="utf-8") as f:
            self.mbti_data = {item["mbti"]: item for item in json.load(f)}

    def get_dummy_cards(self) -> List[ScentCard]:
        # 예시로 INFJ 데이터 반환
        mbti_type = "INFJ"
        data = self.mbti_data.get(mbti_type)
        
        # 테마 중 하나 랜덤 선택 (실제로는 추천 로직에 의해 결정)
        themes = ["space", "moment", "sensation"]
        selected_theme = random.choice(themes)
        
        persona_title = data["persona"][selected_theme]
        image_url = data["images"][selected_theme]
        keywords = data["persona"]["keywords"]

        return [
            ScentCard(
                id=1,
                mbti=mbti_type,
                persona_title=persona_title,
                image_url=image_url,
                keywords=keywords,
                components=[
                    MBTIComponent(axis="존재방식", code="I", desc="피부에 밀착되어 은은하게 남는 내밀한 여운을 선호합니다."),
                    MBTIComponent(axis="인식방식", code="N", desc="장면과 기억을 소환하는 추상적이고 서사적인 향에 끌립니다."),
                    MBTIComponent(axis="감정질감", code="F", desc="감성을 자극하는 부드럽고 따뜻한 포근한 인상을 줍니다."),
                    MBTIComponent(axis="취향안정성", code="J", desc="균형 잡힌 밸런스의 대중적이고 클래식한 조화를 추구합니다.")
                ],
                recommends=[
                    AccordDetail(name="Woody", reason="깊고 고요한 통찰력을 닮은 묵직한 안정감을 줍니다.", notes=["Sandalwood", "Cedarwood"]),
                    AccordDetail(name="Smoky", reason="신비로운 실루엣처럼 지적인 분위기를 완성해 줍니다.", notes=["Incense", "Patchouli"]),
                    AccordDetail(name="Floral", reason="내면의 다정함을 부드럽게 표현해 줍니다.", notes=["Iris", "Violet"])
                ],
                avoids=[
                    AccordDetail(name="Citrus", reason="너무 밝은 에너지는 당신의 깊은 사색을 방해할 수 있습니다."),
                    AccordDetail(name="Metallic", reason="차가운 금속의 느낌은 당신의 따뜻한 감성과 충돌할 수 있습니다."),
                ],
                story=f"당신의 내면은 [{persona_title}]처럼 깊고 고요한 통찰력을 품고 있습니다. 오늘 선택하신 어코드의 조화는, 안개 사이로 비치는 나무의 신비로운 실루엣처럼 당신의 지적인 분위기를 더욱 완성해 줍니다.",
                summary="신비롭고 깊이 있는 분위기가 당신을 빛나게 할 거예요. 우디와 스모키 어코드를 중심으로 향수를 찾아보는 걸 추천드려요!"
            )
        ]

ncard_service = NCardService()
