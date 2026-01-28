import json
import random
import os
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any
import psycopg2.extras
from scentmap.db import get_recom_db_connection, get_db_connection
from scentmap.app.schemas.ncard_schemas import ScentCard, MBTIComponent, AccordDetail, ScentCardBase
from .scent_analysis_service import (
    analyze_scent_type, 
    get_accord_descriptions, 
    load_mbti_data,
    load_accord_mbti_mapping,
    load_accord_type_mapping
)

"""
NCardService: 향기 분석 카드 생성, 저장 및 결과 관리 서비스
"""

logger = logging.getLogger(__name__)

class NCardService:
    def __init__(self):
        """서비스 초기화 및 데이터 로드"""
        self.mbti_data = {item["mbti"]: item for item in load_mbti_data()}

    async def generate_card(self, session_id: str, mbti: Optional[str] = None, selected_accords: List[str] = []) -> Dict:
        """세션 데이터를 기반으로 향기 분석 카드 생성 및 DB 저장"""
        try:
            # 세션 ID가 adhoc이 아닌 경우 DB에서 최신 데이터 조회
            if session_id != "adhoc":
                with get_recom_db_connection() as conn:
                    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                        cur.execute("SELECT member_id, selected_accords, device_type FROM TB_SCENT_CARD_SESSION_T WHERE session_id = %s", (session_id,))
                        session = cur.fetchone()
                        if session:
                            selected_accords = session['selected_accords'] or selected_accords
                            try:
                                context = json.loads(session['device_type']) if session['device_type'] else {}
                                mbti = context.get('mbti') or mbti
                            except: pass
            # 1. 어코드 설명 조회
            descriptions = get_accord_descriptions(selected_accords)
            if not descriptions:
                descriptions = [{"accord": acc, "desc1": acc, "desc2": "향"} for acc in selected_accords]

            # 2. 향 타입 분석
            analysis = analyze_scent_type(selected_accords, descriptions, user_mbti=mbti)
            derived_mbti = analysis.get('derived_mbti') or mbti or "INFJ"
            scent_code = analysis.get('scent_code', 'ISFJ') # 기본값 최신화
            
            # 3. 컴포넌트 및 추천 어코드 구성
            components = self._generate_mbti_components(analysis.get('axis_scores', {}), scent_code)
            recommends, avoids = self._get_accord_details(analysis, derived_mbti, selected_accords)

            # 4. 스토리텔링 및 페르소나 설정
            main_desc = analysis['main_accord_desc']
            persona_data = self.mbti_data.get(derived_mbti, self.mbti_data.get("INFJ"))
            persona_title = f"{main_desc['desc1']}를 사랑하는 {analysis['type_name']}"
            
            # 기획 의도에 따른 스토리 생성 (2-3문장)
            story = f"당신은 {main_desc['desc1']}의 {main_desc['desc2']}를 좋아하는 {analysis['type_name']} 타입이에요. "
            story += f"{persona_data['impression']} 당신의 내면은 {persona_title}처럼 깊고 고유한 색채를 품고 있습니다. "
            story += f"오늘 선택하신 향기들은 당신의 {derived_mbti}다운 면모를 투영하듯 감각적인 조화를 이룹니다."

            # 5. 추천 향수 및 다음 탐색 제안 (기획 반영)
            recommended_perfume = self._get_representative_perfume(selected_accords)
            suggested_accords = analysis.get('type_info', {}).get('harmonious_accords', [])[:3]

            # 6. 카드 데이터 조립
            card_data = {
                "mbti": derived_mbti,
                "components": components,
                "recommends": recommends,
                "avoids": avoids,
                "story": story,
                "summary": f"{analysis['type_name']}인 당신에게 어울리는 향기 리포트입니다.",
                "persona_title": persona_title,
                "image_url": persona_data["images"]["space"],
                "keywords": analysis.get('axis_keywords', persona_data["persona"]["keywords"]),
                "recommended_perfume": recommended_perfume,
                "suggested_accords": suggested_accords,
                "scent_type": analysis,
                "created_at": datetime.now().isoformat()
            }

            # 7. DB 저장
            card_id = self._save_card_to_db(session_id, card_data)
            
            return {
                "card": card_data,
                "session_id": session_id,
                "card_id": str(card_id),
                "generation_method": "template"
            }
        except Exception as e:
            logger.error(f"카드 생성 실패: {e}", exc_info=True)
            raise

    def _generate_mbti_components(self, axis_scores: Dict, scent_code: str) -> List[Dict]:
        """4축 점수 기반 MBTI 컴포넌트 생성 (E/I, S/N, T/F, J/P)"""
        if not scent_code or len(scent_code) != 4: return []
        mapping = load_accord_mbti_mapping()
        axis_desc = mapping.get('axis_descriptions', {})
        
        # improve_plan_v1 기반 축 명칭 정의
        axes = [
            ("존재방식", scent_code[0]), # E/I
            ("인식방식", scent_code[1]), # S/N
            ("감정질감", scent_code[2]), # T/F
            ("취향안정성", scent_code[3]) # J/P
        ]
        return [{"axis": name, "code": code, "desc": axis_desc.get(code, {}).get("description", "")} for name, code in axes]

    def _get_accord_details(self, analysis: Dict, mbti: str, selected: List[str]) -> tuple:
        """추천 및 기피 어코드 상세 정보 생성"""
        recommends = [
            {"name": acc, "reason": f"{mbti} 성향과 조화를 이루는 추천 향입니다."} 
            for acc in analysis.get('type_info', {}).get('harmonious_accords', [])[:2]
        ]
        avoids = [
            {"name": acc, "reason": "현재의 분위기와 상충될 수 있는 향입니다."} 
            for acc in analysis.get('type_info', {}).get('avoid_accords', [])[:2]
        ]
        return recommends, avoids

    def _get_representative_perfume(self, selected_accords: List[str]) -> Optional[Dict]:
        """선택된 어코드 비중이 가장 높은 대표 향수 1개 조회"""
        if not selected_accords: return None
        try:
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    # 가장 많이 선택된 어코드 기준 (첫 번째 어코드)
                    main_accord = selected_accords[0]
                    cur.execute("""
                        SELECT b.perfume_id, b.perfume_name, b.perfume_brand, b.img_link, a.vote
                        FROM TB_PERFUME_BASIC_M b
                        JOIN TB_PERFUME_ACCORD_M a ON b.perfume_id = a.perfume_id
                        WHERE a.accord = %s
                        ORDER BY a.vote DESC LIMIT 1
                    """, (main_accord,))
                    row = cur.fetchone()
                    if row:
                        return {
                            "id": row["perfume_id"],
                            "name": row["perfume_name"],
                            "brand": row["perfume_brand"],
                            "image": row["img_link"]
                        }
        except Exception as e:
            logger.error(f"대표 향수 조회 실패: {e}")
        return None

    def _save_card_to_db(self, session_id: str, card_data: Dict) -> Any:
        """생성된 카드 데이터를 DB에 저장"""
        with get_recom_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO TB_SCENT_CARD_RESULT_T (session_id, card_data, generation_method)
                    VALUES (%s, %s, %s) RETURNING card_id
                """, (session_id, psycopg2.extras.Json(card_data), 'template'))
                card_id = cur.fetchone()[0]
                conn.commit()
                return card_id

    def save_member_card(self, card_id: str, member_id: int) -> Dict:
        """회원 계정에 카드 저장"""
        with get_recom_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE TB_SCENT_CARD_RESULT_T SET saved = TRUE, member_id = %s WHERE card_id = %s", (member_id, card_id))
                conn.commit()
                return {"success": True, "card_id": card_id}

    def get_member_cards(self, member_id: int, limit: int = 20, offset: int = 0) -> Dict:
        """회원의 저장된 카드 목록 조회"""
        with get_recom_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("SELECT card_id, card_data, created_dt FROM TB_SCENT_CARD_RESULT_T WHERE member_id = %s AND saved = TRUE ORDER BY created_dt DESC LIMIT %s OFFSET %s", (member_id, limit, offset))
                rows = cur.fetchall()
                cards = [{"card_id": str(r['card_id']), "card_data": r['card_data'], "created_at": r['created_dt'].isoformat()} for r in rows]
                return {"cards": cards, "total_count": len(cards)}

ncard_service = NCardService()
