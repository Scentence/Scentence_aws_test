/** **************************************************************
 * API 통신 
 ************************************************************** */
// MBTI 축별 분석
export interface MBTIComponent {
  axis: string;
  code: string;
  desc: string;
}

// 향기 어코드 상세
export interface AccordDetail {
  name: string;
  reason: string;
  notes?: string[];
}

// 향기 분석 카드 (메인)
export interface ScentCard {
  id: number;
  mbti: string;
  components: MBTIComponent[];
  recommends: AccordDetail[];
  avoids: AccordDetail[];
  story: string;
  summary: string;
}

import { API_CONFIG } from '@/app/perfume-network/config';
import axios from 'axios';

// 향기 분석 카드 관련 API 통신 서비스
export const ncardService = {

  // 조회
  // 백엔드로부터 향기카드 리스트를 가져옴
  getScentCards: async (): Promise<ScentCard[]> => {
    try {
      const response = await fetch(`${API_CONFIG.BASE_URL}/ncard/`);
      if (!response.ok) throw new Error('Network response was not ok');
      return await response.json();
    } catch (error) {
      console.warn('Backend not reachable, using frontend dummy data');
      return [
        {
          id: 1,
          mbti: "ENFP",
          components: [
            { axis: "존재방식", code: "E", desc: "에너지를 밖으로 발산하는 당신은 시트러스처럼 주변을 밝게 만듭니다." },
            { axis: "인식방식", code: "N", desc: "직관적인 당신의 사고방식은 우디 향처럼 깊고 신비롭습니다." },
            { axis: "감정질감", code: "F", desc: "공감하는 따뜻한 마음은 바닐라와 머스크처럼 포근합니다." },
            { axis: "취향안정성", code: "P", desc: "유연한 삶을 지향하는 당신은 와일드 플라워처럼 자유롭습니다." }
          ],
          recommends: [
            { name: "Citrus", reason: "밝은 에너지와 가장 잘 어울리는 생동감 넘치는 향입니다.", notes: ["Bergamot", "Lime"] },
            { name: "Floral", reason: "자유로운 영혼에게 자연의 싱그러움을 더해줍니다.", notes: ["Jasmine", "Green Tea"] }
          ],
          avoids: [
            { name: "Leather", reason: "무거운 가죽 향은 당신의 밝은 에너지를 억누를 수 있습니다." },
            { name: "Powdery", reason: "정적인 파우더리 향은 역동적인 매력과 거리가 있습니다." }
          ],
          story: "해질녘 따스한 햇살 아래 피어나는 들꽃처럼, 당신은 존재만으로도 주변에 긍정적인 파동을 전달합니다.",
          summary: "자유롭고 따뜻한 분위기가 당신을 빛나게 할 거예요. 시트러스와 플로럴 어코드를 찾아보세요!"
        }
      ];
    }
  },

  // 추가
  // 향수 맵 분석 데이터를 기반으로 실제 향기 카드를 생성하고 저장
  generateAndSaveCard: async (analysisData: any): Promise<ScentCard> => {
    try {
      const response = await axios.post(`${API_CONFIG.BASE_URL}/ncard/generate`, analysisData);
      return response.data;
    } catch (error) {
      console.error('Failed to generate card:', error);
      throw error;
    }
  }
};
