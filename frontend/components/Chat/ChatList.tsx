"use client";

import MessageItem, { Message } from "./MessageItem";
import { RefObject } from "react";

// ✅ 뇌(Page)로부터 전달받을 데이터들의 명단입니다.
interface ChatListProps {
    messages: Message[];
    loading: boolean;
    messagesEndRef: RefObject<HTMLDivElement>;
    scrollToBottom: () => void;
    statusLog?: string; // [추가]
}

// useEffect 추가
import { useEffect } from "react"; // (맨 위에 import 확인해주세요, 없으면 추가)

const ChatList = ({ messages, loading, messagesEndRef, scrollToBottom, statusLog }: ChatListProps) => {
    // [New] 메시지나 상태가 변하면 바닥으로 스크롤!
    useEffect(() => {
        scrollToBottom();
    }, [messages, loading, statusLog, scrollToBottom]);
    // ✅ 메시지가 없을 때 (Empty State)
    if (messages.length === 0) {
        return (
            <section className="flex-1 h-full overflow-hidden relative flex flex-col items-center justify-center text-center">
                <div className="flex flex-col items-center gap-4 opacity-100">
                    <div className="w-24 h-24 mb-2">
                        <img
                            src="/perfumes/chatlist_icon1.png"
                            alt="Chat Icon"
                            className="w-full h-full object-contain drop-shadow-sm"
                        />
                    </div>
                    <p className="text-sm md:text-base font-medium text-[#393939]/80">
                        질문을 입력하면 AI가 분석 및 조사를 시작합니다.
                    </p>
                </div>
            </section>
        );
    }

    return (
        // [Seamless Design]: 박스 스타일(border, bg, shadow, rounded) 제거
        <section className="flex-1 overflow-y-auto no-scrollbar">
            <div className="space-y-6">
                {/* ✅ 메시지들을 순서대로 렌더링 */}
                {messages.map((msg, idx) => (
                    <MessageItem key={idx} message={msg} onScroll={scrollToBottom} />
                ))}
                {/* ✅ 로딩/로그 표시 */}
                {loading && (
                    <div className="flex flex-col gap-2">
                        {/* 1. 생각중 메시지 (statusLog가 있으면 그걸 보여주고, 없으면 기본) */}
                        {statusLog ? (
                            <div className="flex justify-start animate-pulse px-1">
                                <div className="flex items-center gap-2 rounded-2xl bg-white/50 border border-pink-500/20 px-4 py-2 text-xs text-pink-500 shadow-sm backdrop-blur-sm">
                                    <span className="animate-spin text-base">⏳</span> {statusLog}
                                </div>
                            </div>
                        ) : (
                            // 기존 심플 로딩 (statusLog가 아직 안 넘어왔을 때)
                            messages[messages.length - 1]?.role === "user" && (
                                <div className="flex justify-start"><div className="rounded-2xl bg-white/80 border border-[#E5E4DE] px-5 py-4 text-sm text-[#8E8E8E] animate-pulse shadow-sm">AI가 생각하고 있습니다... 💭</div></div>
                            )
                        )}
                    </div>
                )}
                {/* ✅ 스크롤 위치를 잡기 위한 깃발(Ref) */}
                <div ref={messagesEndRef} />
            </div>
        </section>
    );
};


export default ChatList;