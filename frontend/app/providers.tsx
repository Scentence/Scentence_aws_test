'use client';

/**
 * Providers
 * -----------------------------
 * NextAuth의 SessionProvider를 감싸는 전역 Provider 컴포넌트
 *
 * 역할:
 * - 로그인 세션(Session)을 React Context로 앱 전체에 공유
 * - useSession(), signIn(), signOut() 같은 NextAuth 훅을
 *   모든 하위 컴포넌트에서 사용할 수 있게 해줌
 *
 * 사용 위치:
 * - app/layout.tsx 최상단에서 children을 감싸는 용도
 *
 * 주의:
 * - 반드시 'use client'가 필요함 (브라우저 전용)
 * - 이 파일 없으면 로그인 상태 UI 연동 불가
 */

import { SessionProvider } from "next-auth/react";

export function Providers({ children }: { children: React.ReactNode }) {
    return (
        <SessionProvider>
            {children}
        </SessionProvider>
    );
}