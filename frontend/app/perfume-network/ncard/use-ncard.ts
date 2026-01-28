/** **************************************************************
 * 비즈니스 로직 
 ************************************************************** */
import { useState, useEffect } from 'react';
import { ScentCard, ncardService } from './ncard-service';

// 향기 분석 카드 데이터를 관리하는 커스텀 훅
export const useNCard = () => {
  
  // 향기 분석 카드 데이터 상태 관리
  const [cards, setCards] = useState<ScentCard[]>([]);
  // 로딩 상태 관리
  const [loading, setLoading] = useState(true);
  // 에러 상태 관리
  const [error, setError] = useState<string | null>(null);

  // 향기 분석 카드 데이터 가져오기 함수
  const fetchCards = async () => {
    try {
      setLoading(true);
      const data = await ncardService.getScentCards();
      setCards(data);
    } catch (err) {
      setError('Failed to fetch scent cards');
    } finally {
      setLoading(false);
    }
  };

  // 카드 생성 함수 추가
  const generateCard = async (mbti: string, selectedAccords: string[]) => {
    try {
      setLoading(true);
      const newCard = await ncardService.generateAndSaveCard(mbti, selectedAccords);
      setCards(prev => [newCard, ...prev]);
      return newCard;
    } catch (err) {
      setError('Failed to generate scent card');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  // 컴포넌트 마운트 시 최초 1회 실행
  useEffect(() => {
    fetchCards();
  }, []);

  return { cards, loading, error, refresh: fetchCards, generateCard };
};
