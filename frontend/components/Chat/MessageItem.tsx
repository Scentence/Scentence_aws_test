"use client";

import { useState, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

// ✅ 1. 부품 조립을 위한 설계도 (다른 곳에서도 쓸 수 있게 export 붙임)

export type Message = {
    role: "user" | "assistant";
    text: string;
    isStreaming?: boolean;
};

// ✅ 2. 글자 타이핑 효과 조각
function useTypewriter(text: string, speed = 10) {
    const [displayedText, setDisplayedText] = useState("");
    useEffect(() => {
        if (!text || text.length < displayedText.length) {
            setDisplayedText("");
            return;
        }
        if (displayedText.length >= text.length) return;
        const timeout = setTimeout(() => {
            setDisplayedText((prev) => {
                const nextCharIndex = prev.length;
                if (nextCharIndex >= text.length) return prev;

                // [스마트 이미지 감지]
                // '!'로 시작하고 바로 뒤가 '[' 라면 (이미지 태그 시작 지점)
                if (text[nextCharIndex] === "!" && text[nextCharIndex + 1] === "[") {
                    const remaining = text.slice(nextCharIndex);
                    // 이미지 태그 전체 패턴 검사: ![...](...)
                    const match = remaining.match(/^!\[.*?\]\(.*?\)/);

                    // 태그가 완성된 상태라면 -> 통째로 한 번에 출력 (URL 타이핑 생략)
                    if (match) return prev + match[0];

                    // 태그가 아직 덜 넘어왔다면(스트리밍 중) -> 멈춰서 기다림 (마 뜨는 효과)
                    // 다음 청크가 들어와서 text가 길어지면 useEffect가 다시 실행되어 결국 완성됨
                    else return prev;
                }
                // 일반 텍스트는 한 글자씩 타이핑
                return prev + text.charAt(nextCharIndex);
            });
        }, speed);
        return () => clearTimeout(timeout);
    }, [text, displayedText, speed]);
    return displayedText;
}

// ✅ 3. 말풍선 조각 MessageItem
const MessageItem = ({ message, onScroll }: { message: Message, onScroll?: () => void }) => {
    const shouldAnimate = message.role === "assistant" && message.isStreaming;
    const typedText = useTypewriter(message.text, 15);
    const content = shouldAnimate ? typedText : message.text;

    useEffect(() => {
        if (shouldAnimate && onScroll) {
            onScroll();
        }
    }, [typedText, shouldAnimate, onScroll]);
    // [수정] 내용이 없으면 말풍선 자체를 숨김 (이미 ChatList에 로딩바가 있으므로 중복 방지)
    if (message.role === "assistant" && !content) {
        return null;
    }
    return (
        <div className={`flex w-full ${message.role === "user" ? "justify-end" : "justify-start"}`}>
            <div
                // [Claude Theme] Message Bubbles: User=Beige(#E5E4DE), AI=White(#FFFFFF) with border
                className={`max-w-[85%] rounded-2xl px-5 py-4 text-sm leading-relaxed shadow-sm ${message.role === "user"
                    ? "bg-[#E5E4DE] text-[#393939]"
                    : "bg-white text-[#393939] border border-[#E5E4DE]"
                    }`}
            >
                <div className="mb-1 font-semibold uppercase tracking-[0.2em] text-[0.6rem] text-[#8E8E8E]">
                    {message.role === "user" ? "나" : "AI"}
                </div>

                {message.role === "assistant" ? (
                    // [Claude Theme] Markdown Styling: prose-stone for warmer gray text
                    <div className="prose prose-stone prose-sm max-w-none">
                        <ReactMarkdown
                            remarkPlugins={[remarkGfm]}
                            components={{
                                // ✅ any로 타입 에러 방지
                                a: ({ node, ...props }: any) => (
                                    <a {...props} target="_blank" rel="noopener noreferrer" className="text-pink-600 hover:underline" />
                                ),
                                img: ({ node, ...props }: any) => (
                                    <span className="mx-auto my-6 block h-40 w-40 md:h-[250px] md:w-[250px] overflow-hidden rounded-2xl shadow-lg border border-slate-200 relative">
                                        <img
                                            {...props}
                                            className="h-full w-full object-cover object-center scale-125"
                                            alt={props.alt || "Perfume Image"}
                                        />
                                    </span>
                                ),
                                h2: ({ node, ...props }: any) => (
                                    <h2 {...props} className="text-xl font-bold mt-8 mb-3 text-[#393939] border-l-4 border-pink-500 pl-3" />
                                ),
                                hr: ({ node, ...props }: any) => (
                                    <hr {...props} className="my-10 border-[#E5E4DE]" />
                                ),
                                em: ({ node, ...props }: any) => (
                                    <em {...props} className="not-italic text-violet-600 font-bold mr-1" />
                                ),
                                strong: ({ node, ...props }: any) => (
                                    <strong {...props} className="text-pink-600 font-extrabold" />
                                ),
                            }}
                        >
                            {content || "..."}
                        </ReactMarkdown>
                    </div>
                ) : (
                    <div>{content}</div>
                )}
            </div>
        </div>
    );
};

export default MessageItem;