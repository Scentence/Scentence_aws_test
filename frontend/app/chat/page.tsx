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

function useTypewriter(text: string, speed = 10) {
    const [displayedText, setDisplayedText] = useState("");

    useEffect(() => {
        // 텍스트가 줄어들었거나(새 메시지), 초기 상태면 리셋
        if (!text || text.length < displayedText.length) {
            setDisplayedText("");
            return;
        }

        // 다 썼으면 멈춤
        if (displayedText.length >= text.length) {
            return;
        }

        const timeout = setTimeout(() => {
            setDisplayedText((prev) => {
                const nextCharIndex = prev.length;
                if (nextCharIndex >= text.length) return prev;
                // [스마트 이미지 감지 로직] by ksu
                // '!'로 시작하고 바로 뒤가 '[' 라면 (이미지 태그 시작 지점)
                if (text[nextCharIndex] === "!" && text[nextCharIndex + 1] === "[") {
                    const remaining = text.slice(nextCharIndex);
                    // 이미지 태그 전체 패턴 검사: ![...](...)
                    const match = remaining.match(/^!\[.*?\]\(.*?\)/);

                    if (match) {
                        // 태그가 완성된 상태라면 -> 통째로 한 번에 출력 (URL 타이핑 생략)
                        return prev + match[0];
                    } else {
                        // 태그가 아직 덜 넘어왔다면(스트리밍 중) -> 멈춰서 기다림 (마 뜨는 효과)
                        // 다음 청크가 들어와서 text가 길어지면 useEffect가 다시 실행되어 결국 완성됨
                        return prev;
                    }
                }
                // 일반 텍스트는 한 글자씩 타이핑
                return prev + text.charAt(nextCharIndex);
            });
        }, speed);
        return () => clearTimeout(timeout);
    }, [text, displayedText, speed]);
    return displayedText;
}

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

    const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        const trimmed = inputValue.trim();
        if (!trimmed || !threadId) return;

        setMessages((prev) => prev.map(m => ({ ...m, isStreaming: false })));
        setMessages((prev) => [...prev, { role: "user", text: trimmed, isStreaming: false }]);
        setInputValue("");
        setError("");
        setLoading(true);
        setStatusLog("AI가 요청을 분석 중입니다..."); // 초기 로그

        try {
            const response = await fetch(API_URL, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ user_query: trimmed, thread_id: threadId }),
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
                            console.log("Stream Data:", data); // [Debug] 데이터 수신 확인
                            if (data.type === "answer") {
                                setStatusLog(""); // 답변 시작되면 로그 지움
                                setMessages((prev) => {
                                    const updated = [...prev];
                                    const lastIndex = updated.length - 1;
                                    const lastMsg = updated[lastIndex];

                                    // [Fix] 덮어쓰기(=)가 아니라 이어붙이기(+)
                                    if (lastMsg.role === "assistant") {
                                        updated[lastIndex] = {
                                            ...lastMsg,
                                            text: lastMsg.text + data.content
                                        };
                                    }
                                    return updated;
                                });
                            } else if (data.type === "log") {
                                setStatusLog(data.content);
                            } else if (data.type === "error") {
                                setStatusLog(`오류: ${data.content}`);
                            }
                        } catch (e: any) { // ✅ catch 에러 타입 any로 지정
                            console.error(e);
                        }
                    }
                }
            }
        } catch (e: any) { // ✅ catch 에러 타입 any로 지정
            setError("오류가 발생했습니다.");
        } finally {
            setLoading(false);
            setStatusLog(""); // 종료 시 로그 초기화
        }
    };

    return (
        <div className="flex h-[100dvh] bg-[#FAF8F5] overflow-hidden text-[#393939]">
            {/* ✅ 사이드바에 스위치 상태와 끄기 기능을 전달합니다. */}
            <Sidebar
                isOpen={isSidebarOpen}
                onToggle={() => setIsSidebarOpen(!isSidebarOpen)}
                onNewChat={handleNewChat}
                loading={loading}
            />
            <main className="flex-1 flex flex-col relative h-full bg-[#FAF8F5] overflow-hidden">
                {/* 1. HEADER (Gray Background - Matches Landing Page) */}
                <header className="flex items-center justify-between px-5 py-4 bg-[#E5E5E5] shrink-0">
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
                {/* [Layout Fix]: absolute로 하단 네비게이션(70px) 바로 위에 고정 */}
                {/* <div className="absolute bottom-[70px] left-0 right-0 p-4 bg-[#FAF8F5] border-t border-[#E5E4DE] z-30"> */}
                <div className="shrink-0 p-4 bg-[#FAF8F5] border-t border-[#E5E4DE] z-30 mb-[70px]">
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

            {/* 6. BOTTOM NAVIGATION (Fixed Gray Box) */}
            < nav className="fixed bottom-0 left-0 right-0 bg-[#E5E5E5] border-t border-[#CCC] px-6 h-[70px] flex justify-between items-center z-50" >
                <button onClick={() => router.push('/')} className="flex flex-col items-center gap-1 text-[#555] p-2 hover:text-black transition-colors">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-6 h-6"><path strokeLinecap="round" strokeLinejoin="round" d="m2.25 12 8.954-8.955c.44-.439 1.152-.439 1.591 0L21.75 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125H9.75v-4.875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21h4.125c.621 0 1.125-.504 1.125-1.125V9.75M8.25 21h8.25" /></svg>
                </button>
                <button className="flex flex-col items-center gap-1 text-[#555] p-2">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-6 h-6"><path strokeLinecap="round" strokeLinejoin="round" d="M21 8.25c0-2.485-2.099-4.5-4.688-4.5-1.935 0-3.597 1.126-4.312 2.733-.715-1.607-2.377-2.733-4.313-2.733C5.1 3.75 3 5.765 3 8.25c0 7.22 9 12 9 12s9-4.78 9-12Z" /></svg>
                </button>
                <button className="flex flex-col items-center gap-1 text-black p-2">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-7 h-7"><path strokeLinecap="round" strokeLinejoin="round" d="M8.625 12a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H8.25m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H12m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 0 1-2.555-.337A5.972 5.972 0 0 1 5.41 20.97a5.969 5.969 0 0 1-.474-.065 4.48 4.48 0 0 0 .978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25Z" /></svg>
                </button>
                <button className="flex flex-col items-center gap-1 text-[#555] p-2">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-6 h-6"><path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0ZM4.501 20.118a7.5 7.5 0 0 1 14.998 0A17.933 17.933 0 0 1 12 21.75c-2.676 0-5.216-.584-7.499-1.632Z" /></svg>
                </button>
            </nav >
        </div >
    );
}
