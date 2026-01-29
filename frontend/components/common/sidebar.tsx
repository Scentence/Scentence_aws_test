'use client';

import { useEffect, useState } from "react";
import { useSession, signOut } from "next-auth/react";
import Link from "next/link";

interface SidebarProps {
    isOpen: boolean;
    onClose: () => void;
    context: "home" | "chat";
}

// [MENU ITEM COMPONENT] 아이콘 + 제목 + 설명 구조
function MenuItem({ href, icon, title, desc, onClick, colorClass = "bg-gray-100 text-gray-600" }: any) {
    return (
        <Link
            href={href}
            onClick={onClick}
            className="flex items-start gap-4 p-3 rounded-xl hover:bg-gray-50 transition-colors group"
        >
            <div className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 ${colorClass} group-hover:scale-105 transition-transform`}>
                {icon}
            </div>
            <div className="flex-1">
                <p className="text-sm font-bold text-gray-900 leading-tight mb-0.5">{title}</p>
                <p className="text-[11px] text-gray-400 leading-snug">{desc}</p>
            </div>
        </Link>
    );
}

export default function Sidebar({ isOpen, onClose, context }: SidebarProps) {
    const { data: session } = useSession();
    const [localUser, setLocalUser] = useState<{ memberId?: string | null; email?: string | null; nickname?: string | null; roleType?: string | null; isAdmin?: boolean } | null>(null);
    const [profileRoleType, setProfileRoleType] = useState<string | null>(null);

    // [AUTH CHECK LOGIC] 기존 로직 유지
    useEffect(() => {
        if (!isOpen) return;
        if (typeof window === "undefined") return;
        const stored = localStorage.getItem("localAuth");
        if (!stored) {
            setLocalUser(null);
            return;
        }
        try {
            setLocalUser(JSON.parse(stored));
        } catch {
            setLocalUser(null);
        }
    }, [isOpen]);

    useEffect(() => {
        if (!isOpen) return;
        if (typeof window === "undefined") return;
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
    const resolvedRoleType = (
        localUser?.roleType ||
        (localUser?.isAdmin ? "ADMIN" : "") ||
        profileRoleType ||
        ""
    ).toUpperCase();
    const isAdmin = resolvedRoleType === "ADMIN";

    // [CLICK OUTSIDE LOGIC] overlay 제거 후 ref로 외부 클릭 감지
    const sidebarRef = useState<HTMLDivElement | null>(null);
    const [ref, setRef] = useState<HTMLDivElement | null>(null);

    useEffect(() => {
        function handleClickOutside(event: MouseEvent) {
            if (ref && !ref.contains(event.target as Node)) {
                onClose();
            }
        }
        if (isOpen) {
            document.addEventListener("mousedown", handleClickOutside);
        }
        return () => {
            document.removeEventListener("mousedown", handleClickOutside);
        };
    }, [isOpen, ref, onClose]);

    if (!isOpen) return null;

    return (
        <>
            {/* [POPOVER MENU] fixed 적용으로 스크롤 시에도 위치 고정, 세련된 애니메이션 적용 */}
            <div ref={setRef} className="fixed top-[72px] right-5 z-50 w-[320px] max-h-[calc(100vh-100px)] bg-white rounded-2xl shadow-2xl border border-gray-100 overflow-y-auto custom-scrollbar animate-in fade-in zoom-in-95 slide-in-from-top-2 duration-300 ease-out">
                <div className="p-2 space-y-1">

                    {/* --- HOME CONTEXT --- */}
                    {context === "home" && (
                        <>
                            {!isLoggedIn ? (
                                // [LOGGED OUT]
                                <div className="p-2 space-y-2">
                                    <MenuItem
                                        href="/login"
                                        onClick={onClose}
                                        icon={<span className="text-lg">🔐</span>}
                                        title="로그인 / 회원가입"
                                        desc="센텐스의 모든 기능을 이용해보세요"
                                        colorClass="bg-black text-white"
                                    />

                                    <div className="h-px bg-gray-100 my-1 mx-2" />

                                    <MenuItem
                                        href="/chat"
                                        onClick={onClose}
                                        icon={<span className="text-lg">✨</span>}
                                        title="AI 향수 추천"
                                        desc="챗봇과 대화하며 취향 찾기"
                                        colorClass="bg-yellow-50 text-yellow-600"
                                    />

                                    <MenuItem
                                        href="/about"
                                        onClick={onClose}
                                        icon={<span className="text-lg">ℹ️</span>}
                                        title="서비스 소개"
                                        desc="센텐스가 추구하는 가치"
                                    />
                                    <MenuItem
                                        href="/contact"
                                        onClick={onClose}
                                        icon={<span className="text-lg">📞</span>}
                                        title="문의하기"
                                        desc="궁금한 점을 물어보세요"
                                    />
                                </div>
                            ) : (
                                // [LOGGED IN]
                                <div className="p-1 space-y-1">
                                    {!isAdmin && (
                                        <MenuItem
                                            href="/mypage"
                                            onClick={onClose}
                                            icon={<span className="text-lg">👤</span>}
                                            title="마이페이지"
                                            desc="내 정보 및 프로필 관리"
                                        />
                                    )}
                                    {isAdmin && (
                                        <MenuItem
                                            href="/admin"
                                            onClick={onClose}
                                            icon={<span className="text-lg">🛠️</span>}
                                            title="관리자 페이지"
                                            desc="시스템 관리 및 모니터링"
                                            colorClass="bg-blue-100 text-blue-600"
                                        />
                                    )}

                                    <div className="h-px bg-gray-100 my-1 mx-2" />

                                    <MenuItem
                                        href="/chat"
                                        onClick={onClose}
                                        icon={<span className="text-lg">✨</span>}
                                        title="AI 향수 추천"
                                        desc="챗봇과 대화하며 취향 찾기"
                                        colorClass="bg-yellow-50 text-yellow-600"
                                    />
                                    <MenuItem
                                        href="/archives"
                                        onClick={onClose}
                                        icon={<span className="text-lg">📂</span>}
                                        title="나만의 아카이브"
                                        desc="저장한 향수 카드 모음집"
                                        colorClass="bg-orange-50 text-orange-600"
                                    />
                                    <MenuItem
                                        href="/layering"
                                        onClick={onClose}
                                        icon={<span className="text-lg">🧪</span>}
                                        title="향수 레이어링"
                                        desc="나만의 향수 조합 실험실"
                                        colorClass="bg-purple-50 text-purple-600"
                                    />
                                    <MenuItem
                                        href="/perfume-network/nmap"
                                        onClick={onClose}
                                        icon={<span className="text-lg">🗺️</span>}
                                        title="향수 관계맵"
                                        desc="향수의 연결고리 탐험하기"
                                        colorClass="bg-blue-50 text-blue-600"
                                    />

                                    <div className="h-px bg-gray-100 my-1 mx-2" />

                                    <MenuItem
                                        href="/about"
                                        onClick={onClose}
                                        icon={<span className="text-lg">ℹ️</span>}
                                        title="서비스 소개"
                                        desc="센텐스가 추구하는 가치"
                                    />
                                    <MenuItem
                                        href="/contact"
                                        onClick={onClose}
                                        icon={<span className="text-lg">📞</span>}
                                        title="문의하기"
                                        desc="불편사항 및 제안 접수"
                                    />

                                    {/* LOGOUT BUTTON */}
                                    <button
                                        onClick={() => {
                                            if (session) signOut({ callbackUrl: "/login" });
                                            else {
                                                if (typeof window !== "undefined") {
                                                    localStorage.removeItem("localAuth");
                                                    window.location.href = "/login";
                                                }
                                                setLocalUser(null);
                                                onClose();
                                            }
                                        }}
                                        className="w-full text-left flex items-center gap-4 p-3 rounded-xl hover:bg-red-50 group transition-colors mt-2"
                                    >
                                        <div className="w-10 h-10 rounded-full flex items-center justify-center shrink-0 bg-gray-100 text-gray-400 group-hover:bg-red-100 group-hover:text-red-500 transition-colors">
                                            <span className="text-lg">🚪</span>
                                        </div>
                                        <div>
                                            <p className="text-sm font-bold text-gray-500 group-hover:text-red-600 transition-colors">로그아웃</p>
                                        </div>
                                    </button>
                                </div>
                            )}
                        </>
                    )}

                    {/* --- CHAT CONTEXT --- */}
                    {context === "chat" && (
                        <div className="p-2 space-y-2">
                            <MenuItem
                                href="/chat"
                                onClick={onClose}
                                icon={<span className="text-lg">✨</span>}
                                title="새 채팅 시작하기"
                                desc="새로운 주제로 대화하기"
                                colorClass="bg-black text-white"
                            />

                            <div className="h-px bg-gray-100 my-2 mx-2" />

                            <div className="px-3 py-2">
                                <p className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">History</p>
                                <ul className="space-y-1">
                                    <li className="text-xs text-gray-600 p-2 hover:bg-gray-50 rounded-lg cursor-pointer truncate">
                                        24.01.19 데이트 향수 추천...
                                    </li>
                                    <li className="text-xs text-gray-600 p-2 hover:bg-gray-50 rounded-lg cursor-pointer truncate">
                                        24.01.15 우디 계열 문의...
                                    </li>
                                </ul>
                            </div>

                            <div className="h-px bg-gray-100 my-2 mx-2" />

                            <MenuItem
                                href="/"
                                onClick={onClose}
                                icon={<span className="text-lg">🏠</span>}
                                title="홈으로 나가기"
                                desc="메인 화면으로 이동"
                            />
                        </div>
                    )}
                </div>
            </div>
        </>
    );
}