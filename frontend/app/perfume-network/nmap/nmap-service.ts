import axios from 'axios';
import { API_CONFIG } from '@/app/perfume-network/config';
import { NMapResponse } from './types';

// 향수 맵 API
export const nmapService = {
  /**
   * 향수 맵 분석 결과 및 시각화 데이터 조회
   * @param params 조회 옵션 (memberId, maxPerfumes, minSimilarity, topAccords)
   */
  async getNMapResult(params: {
    memberId?: number;
    maxPerfumes?: number;
    minSimilarity?: number;
    topAccords?: number;
  } = {}): Promise<NMapResponse> {
    try {
      const response = await axios.get<NMapResponse>(`${API_CONFIG.BASE_URL}/nmap/result`, {
        params: {
          member_id: params.memberId,
          max_perfumes: params.maxPerfumes,
          min_similarity: params.minSimilarity,
          top_accords: params.topAccords,
        },
      });
      return response.data;
    } catch (error) {
      console.error('Failed to fetch NMap result:', error);
      throw error;
    }
  },

  /**
   * (선택 사항) 향수 맵 분석 결과를 향기 카드로 변환하여 저장하는 로직이 필요할 경우 여기에 추가
   */
};
