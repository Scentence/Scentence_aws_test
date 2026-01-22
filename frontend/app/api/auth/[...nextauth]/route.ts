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
                    if (data?.withdraw_pending && data?.member_id) {
                        return `/recover?memberId=${data.member_id}`;
                    }
                    user.id = data.member_id; // DB의 진짜 회원번호(PK) 가져오기
                    return true;
                } catch (error) {
                    console.error('Sync Error:', error);
                    return true;
                }
            }
            return true;
        },
        async jwt({ token, user }) {
            if (user) {
                token.id = user.id; // 토큰에 회원번호 심기
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