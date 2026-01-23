"use client";

import { useEffect, RefObject } from "react";
import MessageItem, { Message } from "./MessageItem";

interface ChatListProps {
    messages: Message[];
    loading: boolean;
    messagesEndRef: RefObject<HTMLDivElement>;
    scrollToBottom: () => void;
    statusLog?: string;
}

const ChatList = ({ messages, loading, messagesEndRef, scrollToBottom, statusLog }: ChatListProps) => {
    // 메시지나 로딩 상태, 로그 문구가 변할 때마다 바닥으로 자동 스크롤합니다.
    useEffect(() => {
        scrollToBottom();
    }, [messages, loading, statusLog, scrollToBottom]);

    // 대화 시작 전 초기 화면
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
        <section className="flex-1 overflow-y-auto no-scrollbar">
            <div className="space-y-6">
                {/* 기존 메시지 목록 렌더링 */}
                {messages.map((msg, idx) => (
                    <MessageItem key={idx} message={msg} onScroll={scrollToBottom} />
                ))}

                {/* ✅ 실시간 진행 상태(statusLog) 표시 영역 */}
                {loading && (
                    <div className="flex flex-col gap-2">
                        {/* 1. 백엔드에서 전달된 단계별 상태 로그 표시 */}
                        {statusLog ? (
                            <div className="flex justify-start animate-pulse px-1">
                                <div className="flex items-center gap-2 rounded-2xl bg-white/50 border border-pink-500/20 px-4 py-2 text-xs text-pink-500 shadow-sm backdrop-blur-sm">
                                    {/* 회전하는 모래시계 아이콘 */}
                                    <span className="animate-spin text-base">⏳</span>
                                    {statusLog}
                                </div>
                            </div>
                        ) : (
                            /* 2. 로그가 없고 답변 데이터도 아직 오지 않았을 때의 기본 로딩 */
                            messages[messages.length - 1]?.text === "" && (
                                <div className="flex justify-start">
                                    <div className="rounded-2xl bg-white/80 border border-[#E5E4DE] px-5 py-4 text-sm text-[#8E8E8E] animate-pulse shadow-sm">
                                        AI가 답변을 준비하고 있습니다... 💭
                                    </div>
                                </div>
                            )
                        )}
                    </div>
                )}

                {/* 하단 스크롤용 지점 */}
                <div ref={messagesEndRef} />
            </div>
        </section>
    );
};

export default ChatList;