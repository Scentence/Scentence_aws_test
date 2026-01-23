'use client';

import { useEffect, useState } from "react";
import { useSession, signOut } from "next-auth/react";
import Link from "next/link";

interface SidebarProps {
    isOpen: boolean;
    onClose: () => void;
    context: "home" | "chat"; // 페이지 성격 (홈 vs 채팅)
}

export default function Sidebar({ isOpen, onClose, context }: SidebarProps) {
    const { data: session } = useSession(); // 로그인 상태 확인
    const [localUser, setLocalUser] = useState<{ memberId?: string | null; email?: string | null; nickname?: string | null; roleType?: string | null; isAdmin?: boolean } | null>(null);
    const [profileImageUrl, setProfileImageUrl] = useState<string | null>(null);
    const [profileRoleType, setProfileRoleType] = useState<string | null>(null);

    useEffect(() => {
        if (!isOpen) return;
        if (typeof window === "undefined") return;
        const stored = localStorage.getItem("localAuth");
        if (!stored) {
            setLocalUser(null);
            return;
        }
        try {
            const parsed = JSON.parse(stored);
            setLocalUser(parsed);
        } catch (error) {
            setLocalUser(null);
        }
    }, [isOpen]);

    useEffect(() => {
        if (!isOpen) return;
        if (typeof window === "undefined") return;
        const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || "";
        const memberId = session?.user?.id || localUser?.memberId;
        if (!memberId) {
            setProfileImageUrl(null);
            return;
        }
        fetch(`${apiBaseUrl}/users/profile/${memberId}`)
            .then((res) => (res.ok ? res.json() : null))
            .then((data) => {
                if (data?.profile_image_url) {
                    const url = data.profile_image_url.startsWith("http")
                        ? data.profile_image_url
                        : `${apiBaseUrl}${data.profile_image_url}`;
                    setProfileImageUrl(url);
                } else {
                    setProfileImageUrl(null);
                }
                if (data?.role_type) {
                    setProfileRoleType(data.role_type);
                }
            })
            .catch(() => setProfileImageUrl(null));
    }, [isOpen, localUser, session]);

    const isLoggedIn = Boolean(session || localUser);
    const displayName = session?.user?.name || localUser?.nickname || localUser?.email || "회원";
    const resolvedRoleType = (
        localUser?.roleType ||
        (localUser?.isAdmin ? "ADMIN" : "") ||
        profileRoleType ||
        ""
    ).toUpperCase();
    const isAdmin = resolvedRoleType === "ADMIN";

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-[9999] flex justify-end">
            {/* 반투명 배경 (클릭 시 닫힘) */}
            <div className="fixed inset-0 bg-black/50" onClick={onClose} />

            {/* 사이드바 본체 */}
            <div className="relative w-64 h-full bg-white shadow-xl flex flex-col p-6 z-10">
                <button onClick={onClose} className="self-end mb-8 text-2xl">&times;</button>

                <nav className="flex-1 space-y-4">

                    {/* 1. 홈(Main) 컨텍스트일 때 */}
                    {context === "home" && (
                        <>
                            {!isLoggedIn ? (
                                // 로그인 전
                                <div className="space-y-4">
                                    <Link
                                        href="/login"
                                        onClick={onClose}
                                        className="w-full bg-black text-white py-3 rounded-xl font-bold flex items-center justify-center gap-2 hover:opacity-90 transition"
                                    >
                                        로그인
                                    </Link>
                                    <Link href="/about" className="block text-gray-700 hover:text-black">ℹ️ 서비스 소개</Link>
                                    <Link href="/contact" className="block text-gray-700 hover:text-black">📞 문의하기</Link>
                                </div>
                            ) : (
                                // 로그인 후
                                <div className="space-y-4">
                                    <div className="mb-6 pb-4 border-b flex items-center gap-3">
                                        <div className="w-10 h-10 rounded-full overflow-hidden bg-[#F2F2F2]">
                                            <img
                                                src={profileImageUrl || "/default_profile.png"}
                                                alt="프로필"
                                                className="w-full h-full object-cover"
                                                onError={(event) => {
                                                    event.currentTarget.src = "/default_profile.png";
                                                }}
                                            />
                                        </div>
                                        <div>
                                            <p className="font-bold text-lg">{displayName}님</p>
                                            <p className="text-sm text-gray-500">환영합니다!</p>
                                        </div>
                                    </div>
                                    {!isAdmin && (
                                        <Link href="/mypage" className="flex items-center gap-2 text-lg font-medium hover:text-blue-600">
                                            <img src="/profile.svg" alt="마이페이지" className="w-5 h-5" />
                                            마이페이지
                                        </Link>
                                    )}
                                    {isAdmin && (
                                        <Link href="/admin" className="block text-lg font-medium hover:text-blue-600">🛠️ 관리자 페이지</Link>
                                    )}
                                    <Link href="/archives" className="block text-lg font-medium hover:text-blue-600">📂 나만의 아카이브</Link>
                                    <Link href="/layering" className="block text-lg font-medium hover:text-blue-600">🧪 향수 레이어링</Link>
                                    <Link href="/perfume-network" className="block text-lg font-medium hover:text-blue-600">🗺️ 향수 관계맵</Link>
                                    <Link href="/contact" className="block text-gray-600">📞 문의하기</Link>
                                    <button
                                        onClick={() => {
                                            if (session) {
                                                signOut({ callbackUrl: "/login" });
                                                return;
                                            }
                                            if (typeof window !== "undefined") {
                                                localStorage.removeItem("localAuth");
                                                window.location.href = "/login";
                                            }
                                            setLocalUser(null);
                                            onClose();
                                        }}
                                        className="text-gray-500 hover:text-red-500 text-sm mt-4"
                                    >
                                        로그아웃
                                    </button>
                                </div>
                            )}
                        </>
                    )}

                    {/* 2. 채팅(Chat) 컨텍스트일 때 */}
                    {context === "chat" && (
                        <div className="space-y-4">
                            <Link href="/chat" onClick={onClose} className="block w-full text-center bg-black text-white py-3 rounded-xl font-bold">
                                ✨ 새 채팅 시작하기
                            </Link>

                            <div className="mt-6">
                                <p className="text-xs text-gray-400 mb-2 font-bold uppercase">History</p>
                                <ul className="space-y-2 text-sm text-gray-600">
                                    <li className="p-2 hover:bg-gray-100 rounded cursor-pointer">24.01.19 데이트 향수</li>
                                    <li className="p-2 hover:bg-gray-100 rounded cursor-pointer">24.01.15 우디 계열 문의</li>
                                </ul>
                            </div>

                            <div className="mt-auto pt-8 border-t">
                                <Link href="/" className="flex items-center gap-2 text-gray-600 hover:text-black">
                                    🏠 홈으로 나가기
                                </Link>
                            </div>
                        </div>
                    )}

                </nav>
            </div>
        </div>
    );
}