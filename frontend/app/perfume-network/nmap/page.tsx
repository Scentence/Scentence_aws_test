"use client";

import React, { useEffect, useState } from 'react';
import { useSession } from 'next-auth/react';
import NMapView from './NMapView';

/**
 * 향수 맵(NMap) 결과 페이지
 * 세션 정보를 관리하고 메인 뷰(NMapView)를 렌더링합니다.
 */
export default function NMapPage() {
  const { data: session } = useSession();
  const [sessionUserId, setSessionUserId] = useState<string | number | undefined>(undefined);

  useEffect(() => {
    // 1. Next-Auth 세션에서 ID 확인
    if (session?.user) {
      const id = (session.user as any).id;
      if (id) {
        setSessionUserId(id);
        return;
      }
    }

    // 2. 로컬 스토리지에서 인증 정보 확인
    const storedAuth = localStorage.getItem('localAuth');
    if (storedAuth) {
      try {
        const parsed = JSON.parse(storedAuth);
        if (parsed.memberId) {
          setSessionUserId(parsed.memberId);
        }
      } catch (e) {
        console.error('Failed to parse localAuth:', e);
      }
    }
  }, [session]);

  return (
    <main>
      <NMapView sessionUserId={sessionUserId} />
    </main>
  );
}
