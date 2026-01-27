"use client";

import { FormEvent, useState, useEffect, useRef, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import ChatList from "../../components/Chat/ChatList";
import { Message } from "../../components/Chat/MessageItem";
import Sidebar from "../../components/Chat/Sidebar";

// [수정] AWS와 로컬 모두 대응하기 위한 환경 변수 처리
// .env에 NEXT_PUBLIC_API_URL이 있으면 그걸 쓰고, 없으면 로컬(localhost:8000)을 씁니다.
const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_URL = `${BACKEND_URL}/chat`;

export default function ChatPage() {
    const router = useRouter();
    const [isSidebarOpen, setIsSidebarOpen] = useState(false); // 온오프 토글 (기본은 닫힘 상태)
    const [messages, setMessages] = useState<Message[]>([]);
    const [inputValue, setInputValue] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    // [추가] 진행 상태 로그 (예: "🔎 조사 완료: ...")
    const [statusLog, setStatusLog] = useState("");
    const [isMounted, setIsMounted] = useState(false);
    const [threadId, setThreadId] = useState("");
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = useCallback(() => {
        if (messagesEndRef.current) {
            messagesEndRef.current.scrollIntoView({ behavior: "smooth", block: "end" });
        }
    }, []);

    useEffect(() => {
        // DOM 렌더링 딜레이를 고려해 약간 지연
        setTimeout(() => scrollToBottom(), 50);
    }, [messages, scrollToBottom]);

    useEffect(() => {
        setIsMounted(true);
        const savedId = localStorage.getItem("chat_thread_id");
        if (savedId) {
            setThreadId(savedId);
        } else {
            const newId = crypto.randomUUID();
            localStorage.setItem("chat_thread_id", newId);
            setThreadId(newId);
        }
    }, []);

    if (!isMounted) return <div className="min-h-screen bg-[#FAF8F5]" />;

    const handleNewChat = () => {
        if (loading) return;
        const newId = crypto.randomUUID();
        localStorage.setItem("chat_thread_id", newId);
        setThreadId(newId);
        setMessages([]);
        setInputValue("");
        setError("");
    };

    const handleSelectThread = async (id: string) => {
        if (loading) return;
        
        setLoading(true);
        setThreadId(id);
        localStorage.setItem("chat_thread_id", id); // 로컬 스토리지 갱신
        
        try {
            const response = await fetch(`${BACKEND_URL}/chat/history/${id}`);
            if (!response.ok) throw new Error("내역 로드 실패");
            
            const data = await response.json();
            // 백엔드 필드명(text)을 프론트엔드 필드명(text)에 맞춰 매핑
            const formattedMessages = data.messages.map((m: any) => ({
                role: m.role,
                text: m.text,
                isStreaming: false
            }));
            
            setMessages(formattedMessages);
            setIsSidebarOpen(false); // 모바일 편의를 위해 선택 후 사이드바 닫기
        } catch (err) {
            console.error(err);
            setError("대화 내역을 불러오는데 실패했습니다.");
        } finally {
            setLoading(false);
        }
    };

    const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        const trimmed = inputValue.trim();
        if (!trimmed || !threadId) return;

        // [★추가] 로그인 정보(MemberID) 가져오기
        let currentMemberId = 0;
        try {
            const localAuth = localStorage.getItem("localAuth");
            if (localAuth) {
                const parsed = JSON.parse(localAuth);
                if (parsed && parsed.memberId) {
                    currentMemberId = parseInt(parsed.memberId, 10);
                }
            }
        } catch (e) {
            console.error("Member ID Parsing Error:", e);
        }

        setMessages((prev) => prev.map(m => ({ ...m, isStreaming: false })));
        setMessages((prev) => [...prev, { role: "user", text: trimmed, isStreaming: false }]);
        setInputValue("");
        setError("");
        setLoading(true);
        setStatusLog("AI가 요청을 분석 중입니다...");

        try {
            const response = await fetch(API_URL, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    user_query: trimmed,
                    thread_id: threadId,
                    member_id: currentMemberId  // [★추가] 백엔드로 내 ID 전송!
                }),
            });

            if (!response.ok || !response.body) throw new Error("서버 연결 실패");

            setMessages((prev) => [...prev, { role: "assistant", text: "", isStreaming: true }]);
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let done = false;
            let buffer = "";

            while (!done) {
                const { value, done: readerDone } = await reader.read();
                done = readerDone;
                if (value) {
                    const chunk = decoder.decode(value, { stream: true });
                    buffer += chunk;
                    const lines = buffer.split("\n\n");
                    buffer = lines.pop() || "";
                    for (const line of lines) {
                        const trimmedLine = line.trim();
                        if (!trimmedLine.startsWith("data: ")) continue;
                        try {
                            const data = JSON.parse(trimmedLine.replace("data: ", ""));
                            console.log("Stream Data:", data);
                            if (data.type === "answer") {
                                setStatusLog("");
                                setMessages((prev) => {
                                    const updated = [...prev];
                                    const lastIndex = updated.length - 1;
                                    const lastMsg = updated[lastIndex];

                                    if (lastMsg.role === "assistant") {
                                        let nextChunk = data.content;
                                        const prevText = lastMsg.text;
                                        const prevTrimmed = prevText.trimEnd();
                                        if (
                                            prevTrimmed.endsWith("---") &&
                                            !prevText.endsWith("\n") &&
                                            typeof nextChunk === "string" &&
                                            nextChunk.startsWith("##")
                                        ) {
                                            nextChunk = `\n${nextChunk}`;
                                        }
                                        updated[lastIndex] = {
                                            ...lastMsg,
                                            text: prevText + nextChunk
                                        };
                                    }
                                    return updated;
                                });
                            } else if (data.type === "log") {
                                setStatusLog(data.content);
                            } else if (data.type === "error") {
                                setStatusLog(`오류: ${data.content}`);
                            }
                        } catch (e: any) {
                            console.error(e);
                        }
                    }
                }
            }
        } catch (e: any) {
            setError("오류가 발생했습니다.");
        } finally {
            setLoading(false);
            setStatusLog("");
        }
    };

    return (
        <div className="flex h-[100dvh] bg-[#FDFBF8] overflow-hidden text-[#393939]">
            {/* ✅ 사이드바에 스위치 상태와 끄기 기능을 전달합니다. */}
            <Sidebar
                isOpen={isSidebarOpen}
                activeThreadId={threadId}           // ✅ 추가
                onToggle={() => setIsSidebarOpen(!isSidebarOpen)}
                onNewChat={handleNewChat}
                onSelectThread={handleSelectThread} // ✅ 추가
                loading={loading}
            />
            <main className="flex-1 flex flex-col relative h-full bg-[#FDFBF8] overflow-hidden">
                {/* 1. HEADER (Unified Style) */}
                <header className="flex items-center justify-between px-5 py-4 bg-[#FDFBF8] border-b border-[#F0F0F0] shrink-0">
                    <h1 className="text-xl font-bold text-black tracking-tight cursor-pointer" onClick={() => router.push('/')}>Scentence</h1>
                    <button onClick={() => setIsSidebarOpen(true)} className="p-1">
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-8 h-8 text-[#555]">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
                        </svg>
                    </button>
                </header>

                <div className="flex-1 flex flex-col min-h-0 overflow-hidden relative">
                    {/* ✅ 모바일용 뒷배경 (사이드바 열렸을 때 화면 어두워지는 효과) */}
                    {isSidebarOpen && (
                        <div className="fixed inset-0 bg-black/20 z-40 md:hidden" onClick={() => setIsSidebarOpen(false)} />
                    )}

                    {/* ✅ 대화 목록 (Scrollable) */}
                    {/* [Spacing Fix]: 상단 p-6, 하단은 고정된 입력창(약 80px) + 네비게이션(70px) + 여백(20px) = 170px 정도 확보 */}
                    <div className="flex-1 overflow-y-auto no-scrollbar pt-6 px-6 pb-6">
                        <ChatList
                            messages={messages}
                            loading={loading}
                            statusLog={statusLog} // [추가] 전달
                            messagesEndRef={messagesEndRef}
                            scrollToBottom={scrollToBottom}
                        />
                    </div>
                </div>

                {/* ✅ 채팅 입력창 (Fixed at bottom) */}
                <div className="shrink-0 p-4 bg-[#FDFBF8] border-t border-[#F0F0F0] z-30">
                    <form onSubmit={handleSubmit} className="space-y-3">
                        <div className="flex gap-3">
                            <input
                                className="flex-1 rounded-2xl border border-[#E5E4DE] bg-white px-3 py-3 text-base md:text-sm text-[#393939] outline-none focus:border-pink-500/50 transition-colors shadow-sm"
                                placeholder="예) 겨울에 어울리는 포근한 향수를 추천해줘"
                                value={inputValue}
                                onChange={(e) => setInputValue(e.target.value)}
                                disabled={loading}
                            />
                            <button
                                className="rounded-2xl bg-gradient-to-r from-pink-500 to-purple-500 px-6 py-3 font-semibold text-white hover:opacity-90 disabled:opacity-50 shadow-sm"
                                type="submit"
                                disabled={loading}
                            >
                                {loading ? "..." : "전송"}
                            </button>
                        </div>
                        {error && <div className="text-sm text-rose-500">{error}</div>}
                    </form>
                </div>
            </main >

        </div >
    );
}
