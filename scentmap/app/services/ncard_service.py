import json
import random
import os
import asyncio
from typing import List, Dict, Any
from scentmap.app.schemas.ncard_schemas import ScentCard, MBTIComponent, AccordDetail

class NCardService:
    """
    향기카드 관련 비즈니스 로직 처리 서비스 클래스
    """
    def __init__(self):
        # 데이터 로드
        base_path = os.path.dirname(__file__)
        mbti_data_path = os.path.join(base_path, "../../data/perfume_mbti.json")
        mapping_data_path = os.path.join(base_path, "../../data/accord_mbti_mapping.json")
        
        with open(mbti_data_path, "r", encoding="utf-8") as f:
            self.mbti_data = {item["mbti"]: item for item in json.load(f)}
            
        with open(mapping_data_path, "r", encoding="utf-8") as f:
            self.mapping_data = json.load(f)

    async def generate_card(self, mbti: str, selected_accords: List[str]) -> ScentCard:
        """
        사용자 MBTI 및 선택 어코드 분석 기반 개인화 향기 카드 생성
        (현재 로직 기반 생성 수행, 향후 LLM API 연동)
        """
        # 1. MBTI 기본 데이터 추출
        persona_data = self.mbti_data.get(mbti)
        if not persona_data:
            # 기본값 처리 (예: INFJ)
            mbti = "INFJ"
            persona_data = self.mbti_data[mbti]

        # 2. 테마 결정 로직 (어코드 기반 또는 랜덤)
        # 선택 어코드 성격(Sensing vs Intuition 등)에 따른 결정 가능
        themes = ["space", "moment", "sensation"]
        selected_theme = random.choice(themes)
        
        persona_title = persona_data["persona"][selected_theme]
        image_url = persona_data["images"][selected_theme]
        keywords = persona_data["persona"]["keywords"]

        # 3. 4가지 축 분석 (MBTI 성격 기반 설명 생성)
        components = self._analyze_mbti_axes(mbti)

        # 4. 추천 어코드 상세 분석 (선택 어코드 + MBTI 적합도)
        recommends = self._get_recommended_accords(mbti, selected_accords)
        avoids = self._get_avoid_accords(mbti)

        # 5. 스토리텔링 생성 (제시 템플릿 기반)
        # LLM 연동 시 해당 영역 LLM 수행
        story = self._generate_story(persona_title, selected_accords, mbti)
        summary = f"{persona_data['impression']} 당신을 위한 향기 가이드입니다. {recommends[0].name} 어코드를 중심으로 탐색해보세요!"

        return ScentCard(
            id=random.randint(1000, 9999),
            mbti=mbti,
            persona_title=persona_title,
            image_url=image_url,
            keywords=keywords,
            components=components,
            recommends=recommends,
            avoids=avoids,
            story=story,
            summary=summary
        )

    def _analyze_mbti_axes(self, mbti: str) -> List[MBTIComponent]:
        """MBTI 4개 축에 대한 향기 관점 해석"""
        axis_map = {
            "E": ("존재방식", "공간을 채우는 압도적 존재감 및 화려한 오프닝"),
            "I": ("존재방식", "피부에 밀착되어 은은하게 남는 내밀한 여운"),
            "S": ("인식방식", "원료의 생동감이 느껴지는 직관적이고 사실적인 향"),
            "N": ("인식방식", "장면과 기억을 소환하는 추상적이고 서사적인 향"),
            "T": ("감정질감", "이성적이고 정돈된 드라이/메탈릭한 구조적 인상"),
            "F": ("감정질감", "감성을 자극하는 부드럽고 따뜻한 포근한 인상을 줍니다."),
            "J": ("취향안정성", "균형 잡힌 밸런스의 대중적이고 클래식한 조화"),
            "P": ("취향안정성", "독특한 킥(Kick)이 있는 실험적이고 개성 있는 감성")
        }
        
        components = []
        for char in mbti:
            if char in axis_map:
                axis_name, desc = axis_map[char]
                components.append(MBTIComponent(axis=axis_name, code=char, desc=desc))
        return components

    def _get_recommended_accords(self, mbti: str, selected_accords: List[str]) -> List[AccordDetail]:
        """사용자 선택 어코드 및 MBTI 데이터 조합 기반 추천 리스트 생성"""
        # accord_mbti_mapping.json 점수 계산 및 정렬 활용 가능
        # 선택 어코드 우선 배치
        res = []
        for acc in selected_accords[:2]:
            res.append(AccordDetail(
                name=acc,
                reason=f"당신이 선택한 {acc} 어코드는 {mbti}의 내면적 분위기를 가장 잘 대변합니다.",
                notes=[] # DB 연결 시 추출 가능
            ))
        
        # MBTI 기반 추천 어코드 추가
        mbti_likes = self.mbti_data[mbti]["scent_preferences"]["likes"]
        res.append(AccordDetail(
            name=mbti_likes[0],
            reason=f"{mbti} 성향의 사람들이 본능적으로 편안함을 느끼는 향조입니다.",
            notes=[]
        ))
        return res

    def _get_avoid_accords(self, mbti: str) -> List[AccordDetail]:
        """MBTI 기반 기피 어코드 추출"""
        mbti_avoids = self.mbti_data[mbti]["scent_preferences"]["avoids"]
        return [
            AccordDetail(
                name=acc,
                reason=f"이 향조는 당신의 {mbti} 특유의 섬세한 균형을 깨뜨릴 수 있습니다.",
                notes=[]
            ) for acc in mbti_avoids[:2]
        ]

    def _generate_story(self, persona_title: str, selected_accords: List[str], mbti: str) -> str:
        """스토리텔링 문구 생성"""
        accords_str = ", ".join([f"[{a}]" for a in selected_accords[:2]])
        return (f"당신의 내면은 [{persona_title}]처럼 깊고 고유한 색채를 품고 있습니다. "
                f"오늘 당신의 시선이 머문 {accords_str} 어코드는, "
                f"마치 당신의 {mbti}다운 면모를 투영하듯 감각적인 조화를 이룹니다.")

    def get_dummy_cards(self) -> List[ScentCard]:
        # 기존 더미 데이터 유지 (테스트용)
        data = self.mbti_data.get("INFJ")
        return [
            ScentCard(
                id=1,
                mbti="INFJ",
                persona_title=data["persona"]["space"],
                image_url=data["images"]["space"],
                keywords=data["persona"]["keywords"],
                components=self._analyze_mbti_axes("INFJ"),
                recommends=[AccordDetail(name="Woody", reason="신비로운 분위기", notes=[])],
                avoids=[AccordDetail(name="Citrus", reason="너무 밝음", notes=[])],
                story="더미 스토리",
                summary="더미 요약"
            )
        ]

ncard_service = NCardService()
