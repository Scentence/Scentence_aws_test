"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export type Message = {
    role: "user" | "assistant";
    text: string;
    isStreaming?: boolean;
};

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ✅ 1. 저장 버튼 컴포넌트
const SaveButton = ({ id, name }: { id: string; name: string }) => {
    const [isSaved, setIsSaved] = useState(false);
    const [loading, setLoading] = useState(false);

    const handleSave = async () => {
        let memberId = 0;
        try {
            // localStorage에서 'localAuth'를 꺼내서 memberId 확인
            const localAuth = localStorage.getItem("localAuth");
            if (localAuth) {
                const parsed = JSON.parse(localAuth);
                if (parsed && parsed.memberId) {
                    memberId = parseInt(parsed.memberId, 10);
                }
            }
        } catch (e) {
            console.error("로그인 정보 파싱 실패:", e);
        }

        if (memberId === 0) {
            alert("로그인이 필요한 서비스입니다.");
            return;
        }

        setLoading(true);
        try {
            const res = await fetch(`${BACKEND_URL}/users/me/perfumes`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    member_id: memberId,
                    perfume_id: parseInt(id),
                    perfume_name: name,
                }),
            });

            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || "저장 실패");

            if (data.status === "already_exists") {
                alert("이미 내 향수에 저장되어 있어요! 😉");
                setIsSaved(true);
            } else {
                alert(`'${name}'이(가) 내 향수로 저장되었습니다! 💖`);
                setIsSaved(true);
            }
        } catch (e: any) {
            console.error(e);
            alert(`저장 중 오류가 발생했습니다: ${e.message}`);
        } finally {
            setLoading(false);
        }
    };

    return (
        <button
            onClick={handleSave}
            disabled={isSaved || loading}
            className={`mt-3 mb-1 flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all shadow-sm
                ${isSaved
                    ? "bg-gray-100 text-gray-400 cursor-default border border-gray-200"
                    : "bg-white text-pink-600 hover:bg-pink-50 border border-pink-200 hover:border-pink-300"
                }`}
        >
            {loading ? <span>⏳ 저장 중...</span> : isSaved ? <>✅ 저장됨</> : (
                <>
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4">
                        <path d="M11.645 20.91l-.007-.003-.022-.012a15.247 15.247 0 01-.383-.218 25.18 25.18 0 01-4.244-3.17C4.688 15.36 2.25 12.174 2.25 8.25 2.25 5.322 4.714 3 7.688 3A5.5 5.5 0 0112 5.052 5.5 5.5 0 0116.313 3c2.973 0 5.437 2.322 5.437 5.25 0 3.925-2.438 7.111-4.739 9.256a25.175 25.175 0 01-4.244 3.17 15.247 15.247 0 01-.383.219l-.022.012-.007.004-.003.001a.752.752 0 01-.704 0l-.003-.001z" />
                    </svg>
                    내 향수로 저장
                </>
            )}
        </button>
    );
};

// ✅ 2. 텍스트 파서 및 이미지 렌더링 최적화
const parseMessageContent = (text: string) => {
    if (!text) return null;

    const regex = /(\[\[SAVE:\d+:[^\]]+\]\])/g;
    const parts = text.split(regex);

    return parts.map((part, index) => {
        const match = part.match(/^\[\[SAVE:(\d+):([^\]]+)\]\]$/);

        if (match) {
            return <SaveButton key={index} id={match[1]} name={match[2]} />;
        }

        if (!part.trim()) return null;

        return (
            <ReactMarkdown
                key={index}
                remarkPlugins={[remarkGfm]}
                components={{
                    a: ({ node, ...props }: any) => (
                        <a {...props} target="_blank" rel="noopener noreferrer" className="text-pink-600 hover:underline" />
                    ),
                    img: ({ node, ...props }: any) => {
                        // [★수정] URL 패턴에 따른 이미지 스타일 분기 로직
                        const imageUrl = props.src || "";
                        const isSquare = imageUrl.includes("aspect_ratio=1:1");

                        return (
                            <span className="mx-auto my-6 block h-40 w-40 md:h-[250px] md:w-[250px] overflow-hidden rounded-2xl shadow-lg border border-slate-200 relative bg-white">
                                <img
                                    {...props}
                                    className={`h-full w-full transition-all duration-300 ${isSquare
                                            ? "object-contain p-2"  // 1:1 이미지는 여백을 주고 전체 표시
                                            : "object-cover object-center scale-125" // 일반 이미지는 기존처럼 크롭 강조
                                        }`}
                                    alt={props.alt || "Perfume Image"}
                                />
                            </span>
                        );
                    },
                    h2: ({ node, ...props }: any) => (
                        <h2 {...props} className="text-xl font-bold mt-8 mb-3 text-[#393939] border-l-4 border-pink-500 pl-3" />
                    ),
                    hr: ({ node, ...props }: any) => <hr {...props} className="my-10 border-[#E5E4DE]" />,
                    em: ({ node, ...props }: any) => (
                        <em {...props} className="not-italic text-violet-600 font-bold mr-1" />
                    ),
                    strong: ({ node, ...props }: any) => <strong {...props} className="text-pink-600 font-extrabold" />,
                    p: ({ node, ...props }: any) => <p {...props} className="mb-4 last:mb-0" />,
                }}
            >
                {part}
            </ReactMarkdown>
        );
    });
};

// ✅ 3. 최종 조립
const MessageItem = ({ message }: { message: Message }) => {
    if (message.role === "assistant" && !message.text) return null;

    return (
        <div className={`flex w-full ${message.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-[85%] rounded-2xl px-5 py-4 text-sm leading-relaxed shadow-sm ${message.role === "user" ? "bg-[#E5E4DE] text-[#393939]" : "bg-white text-[#393939] border border-[#E5E4DE]"
                }`}>
                <div className="mb-1 font-semibold uppercase tracking-[0.2em] text-[0.6rem] text-[#8E8E8E]">
                    {message.role === "user" ? "나" : "AI"}
                </div>
                {message.role === "assistant" ? (
                    <div className="prose prose-stone prose-sm max-w-none">
                        {parseMessageContent(message.text)}
                    </div>
                ) : (
                    <div className="whitespace-pre-wrap">{message.text}</div>
                )}
            </div>
        </div>
    );
};

export default MessageItem;