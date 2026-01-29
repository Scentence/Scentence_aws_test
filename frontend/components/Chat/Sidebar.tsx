"use client";

import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";

// 백엔드 주소 (기존 설정과 동일하게 맞추세요)
const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface ChatRoom {
    thread_id: string;
    title: string;
    last_chat_dt: string;
}

interface SidebarProps {
    isOpen: boolean;
    activeThreadId?: string;       // ✅ 현재 활성화된 방 ID 추가
    onToggle: () => void;
    onNewChat: () => void;
    onSelectThread: (id: string) => void; // ✅ 방 선택 함수 추가
    loading: boolean;
    showToggleButton?: boolean;
}

const Sidebar = ({ isOpen, activeThreadId, onToggle, onNewChat, onSelectThread, loading, showToggleButton = false }: SidebarProps) => {
    const { data: session } = useSession(); // 카카오 로그인 세션
    const [chatRooms, setChatRooms] = useState<ChatRoom[]>([]);
    const [userNickname, setUserNickname] = useState("Guest");

    // [1] 사이드바가 열릴 때 목록 불러오기 (카카오 세션 또는 로컬 로그인)
    useEffect(() => {
        // 카카오 로그인 세션 확인
        console.log("[Sidebar] session:", session); // 디버깅
        console.log("[Sidebar] session.user.id:", session?.user?.id); // 디버깅
        if (session?.user) {
            setUserNickname(session.user.name || "User");
            if (isOpen && session.user.id) {
                console.log("[Sidebar] Fetching rooms for member_id:", session.user.id); // 디버깅
                fetch(`${BACKEND_URL}/chat/rooms/${session.user.id}`)
                    .then(res => res.json())
                    .then(data => setChatRooms(data.rooms || []))
                    .catch(err => console.error("History Load Error:", err));
            }
            return;
        }
        // 로컬 로그인 확인
        const localAuth = localStorage.getItem("localAuth");
        if (localAuth) {
            try {
                const auth = JSON.parse(localAuth);
                setUserNickname(auth.nickname || "User");

                if (isOpen && auth.memberId) {
                    fetch(`${BACKEND_URL}/chat/rooms/${auth.memberId}`)
                        .then(res => res.json())
                        .then(data => setChatRooms(data.rooms || []))
                        .catch(err => console.error("History Load Error:", err));
                }
            } catch (e) {
                console.error("Auth parsing failed", e);
            }
        }
    }, [isOpen, session]);

    return (
        <>
            {showToggleButton && (
                <button onClick={onToggle} className="fixed top-4 left-4 z-[60] p-2 hover:bg-[#F2F1EE] rounded-lg transition-colors bg-white/50 backdrop-blur-sm md:bg-transparent">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-6 h-6 text-[#393939]">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
                    </svg>
                </button>
            )}

            <div className={`fixed inset-y-0 right-0 z-50 w-64 bg-white border-l border-[#E5E4DE] transition-transform duration-300 transform ${isOpen ? "translate-x-0" : "translate-x-full"}`}>
                <div className="flex h-full flex-col p-4 pt-4">
                    <div className="flex justify-between items-center mb-6 px-2">
                        <span className="text-[10px] font-bold tracking-widest text-[#8E8E8E]">RECENT HISTORY</span>
                        <button onClick={onToggle} className="p-1 text-[#8E8E8E] hover:text-[#393939] transition-colors">
                            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5"><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
                        </button>
                    </div>

                    <button onClick={onNewChat} disabled={loading} className="group flex items-center justify-center gap-2 rounded-xl border border-[#E5E4DE] bg-[#FAF8F5] py-3 text-sm font-medium text-[#393939] transition-all hover:bg-[#F2F1EE] disabled:opacity-50">
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="h-5 w-5 transition-transform group-hover:rotate-180"><path strokeLinecap="round" strokeLinejoin="round" d="M16 9h5M3 19v-5m0 0h5m-5 0l3 3a8 8 0 0013-3M4 10a8 8 0 0113-3l3 3m0-5v5" /></svg>
                        새로운 대화 시작
                    </button>

                    {/* ✅ 실제 대화 목록 렌더링 영역 */}
                    <div className="mt-8 flex-1 overflow-y-auto no-scrollbar space-y-1">
                        {chatRooms.length > 0 ? (
                            chatRooms.map((room) => (
                                <button
                                    key={room.thread_id}
                                    onClick={() => onSelectThread(room.thread_id)}
                                    className={`w-full text-left px-3 py-3 rounded-xl transition-colors ${activeThreadId === room.thread_id ? "bg-[#F2F1EE] font-semibold" : "hover:bg-[#FAF8F5]"}`}
                                >
                                    <p className="text-sm text-[#393939] truncate">{room.title || "이전 대화"}</p>
                                    <p className="text-[10px] text-[#BCBCBC] mt-1">{new Date(room.last_chat_dt).toLocaleDateString()}</p>
                                </button>
                            ))
                        ) : (
                            <p className="px-2 text-xs text-[#BCBCBC]">이전 대화가 없습니다.</p>
                        )}
                    </div>

                    <div className="mt-auto border-t border-[#E5E4DE] pt-4 flex items-center gap-3 px-2">
                        <div className="h-8 w-8 rounded-full bg-gradient-to-tr from-pink-400 to-purple-400" />
                        <div className="text-sm font-medium text-[#393939]">{userNickname}</div>
                    </div>
                </div>
            </div>
        </>
    );
};

export default Sidebar;