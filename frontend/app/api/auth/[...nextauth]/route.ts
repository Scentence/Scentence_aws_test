import NextAuth from "next-auth";
import KakaoProvider from "next-auth/providers/kakao";

const handler = NextAuth({
    providers: [
        KakaoProvider({
            clientId: process.env.KAKAO_CLIENT_ID!,
            clientSecret: process.env.KAKAO_CLIENT_SECRET!,
        }),
    ],
    callbacks: {
        async signIn({ user, account }) {
            if (account?.provider === 'kakao') {
                try {
                    const BACKEND_URL =
                        process.env.BACKEND_INTERNAL_URL ??
                        process.env.NEXT_PUBLIC_API_URL ??
                        "http://backend:8000";

                    const response = await fetch(`${BACKEND_URL}/users/login`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            kakao_id: account.providerAccountId,
                            nickname: user.name,
                            email: user.email,
                            profile_image: user.image
                        })
                    });

                    if (!response.ok) {
                        return true;
                    }

                    const data = await response.json();

                    // 탈퇴 대기 중인 계정인 경우
                    if (data?.withdraw_pending && data?.member_id) {
                        return `/recover?memberId=${data.member_id}`;
                    }

                    // 동일 이메일로 가입된 로컬 계정이 있는 경우 → 계정 연결 페이지로 이동
                    if (data?.link_available && data?.existing_member_id) {
                        const params = new URLSearchParams({
                            email: user.email || '',
                            kakao_id: account.providerAccountId,
                            kakao_nickname: user.name || '',
                            kakao_profile_image: user.image || '',
                            existing_member_id: String(data.existing_member_id)
                        });
                        return `/link-account?${params.toString()}`;
                    }

                    user.id = data.member_id; // DB의 진짜 회원번호(PK) 가져오기
                    console.log('[NextAuth signIn] member_id from backend:', data.member_id);
                    console.log('[NextAuth signIn] user.id set to:', user.id);
                    return true;
                } catch (error) {
                    console.error('Sync Error:', error);
                    return true;
                }
            }
            return true;
        },
        async jwt({ token, user }) {
            console.log('[NextAuth jwt] user:', user);
            console.log('[NextAuth jwt] user?.id:', user?.id);
            if (user) {
                token.id = user.id; // 토큰에 회원번호 심기
                console.log('[NextAuth jwt] token.id set to:', token.id);
            }
            return token;
        },
        async session({ session, token }) {
            if (session.user) {
                session.user.id = token.id as string; // 세션에서 회원번호 꺼낼 수 있게
            }
            return session;
        }
    }
});

export { handler as GET, handler as POST };