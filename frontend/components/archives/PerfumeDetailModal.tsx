/* PerfumeDetailModal.tsx (Color Updated) */
"use client";

import { useState } from "react";

interface MyPerfume {
    my_perfume_id: number;
    perfume_id: number;
    name: string;
    brand: string;
    image_url: string | null;
    status: string;
}

interface Props {
    perfume: MyPerfume;
    onClose: () => void;
    onUpdateStatus: (id: number, status: string) => void;
    onDelete: (id: number, rating: number) => void;
}

export default function PerfumeDetailModal({ perfume, onClose, onUpdateStatus, onDelete }: Props) {
    const [isDeleting, setIsDeleting] = useState(false);

    const handleDeleteWithRating = (rating: number) => {
        onDelete(perfume.my_perfume_id, rating);
        onClose();
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-fade-in" onClick={onClose}>
            <div
                className="bg-white w-full max-w-3xl rounded-3xl overflow-hidden shadow-2xl relative flex flex-col md:flex-row min-h-[400px]"
                onClick={(e) => e.stopPropagation()}
            >
                <button
                    onClick={onClose}
                    className="absolute top-4 right-4 z-10 w-8 h-8 flex items-center justify-center rounded-full bg-gray-100 text-gray-500 hover:bg-gray-200 transition"
                >
                    &times;
                </button>

                <div className={`w-full md:w-1/2 aspect-square bg-[#Fdfcf8] flex items-center justify-center p-10 relative transition-all ${isDeleting ? 'brightness-50 grayscale' : ''}`}>
                    <div className="absolute w-[80%] h-[80%] rounded-full bg-[#f5f1e6] blur-3xl opacity-60"></div>
                    {perfume.image_url ? (
                        <img
                            src={perfume.image_url}
                            alt={perfume.name}
                            className="max-w-full max-h-full object-contain relative z-10 drop-shadow-xl"
                        />
                    ) : (
                        <span className="text-gray-300 font-medium">No Image</span>
                    )}
                </div>

                <div className="w-full md:w-1/2 p-10 flex flex-col justify-center relative">

                    {!isDeleting ? (
                        <>
                            <div className="mb-8">
                                <p className="text-[#C5A55D] text-xs font-bold tracking-widest uppercase mb-2">{perfume.brand}</p>
                                <h2 className="text-3xl font-bold text-[#222] leading-tight mb-4">{perfume.name}</h2>
                                <div className="h-1 w-12 bg-[#C5A55D]/30 rounded-full"></div>
                            </div>

                            <div className="space-y-6">
                                <div className="space-y-3">
                                    <label className="text-gray-400 text-xs font-bold uppercase tracking-wider">Current Status</label>
                                    <div className="flex gap-2">
                                        {/* 상태 버튼 (Color Updated) */}
                                        <button
                                            onClick={() => onUpdateStatus(perfume.my_perfume_id, 'HAVE')}
                                            className={`
                        flex-1 py-4 text-lg font-bold rounded-xl border transition-all
                        ${perfume.status === 'HAVE'
                                                    ? 'bg-indigo-600 text-white border-indigo-600 shadow-lg shadow-indigo-200'
                                                    : 'bg-white text-gray-400 border-gray-100 hover:bg-indigo-50 hover:text-indigo-600'}
                      `}
                                        >
                                            보유 (HAVE)
                                        </button>
                                        <button
                                            onClick={() => onUpdateStatus(perfume.my_perfume_id, 'WANT')}
                                            className={`
                        flex-1 py-4 text-lg font-bold rounded-xl border transition-all
                        ${perfume.status === 'WANT'
                                                    ? 'bg-rose-500 text-white border-rose-500 shadow-lg shadow-rose-200'
                                                    : 'bg-white text-gray-400 border-gray-100 hover:bg-rose-50 hover:text-rose-500'}
                      `}
                                        >
                                            위시 (WANT)
                                        </button>
                                    </div>
                                </div>

                                <div className="pt-6 border-t border-gray-100">
                                    <button
                                        onClick={() => setIsDeleting(true)}
                                        className="w-full py-3 text-sm font-medium text-red-400 hover:text-red-600 hover:bg-red-50 rounded-xl transition flex items-center justify-center gap-2"
                                    >
                                        이 향수 삭제하기
                                    </button>
                                </div>
                            </div>
                        </>
                    ) : (
                        /* 삭제 평가 모드 */
                        <div className="absolute inset-0 p-10 flex flex-col justify-center bg-white/95 backdrop-blur-sm z-20 animate-slide-up">
                            <h3 className="text-xl font-bold text-[#333] mb-2">이 향수는 어땠나요?</h3>
                            <p className="text-gray-500 text-sm mb-6">평가를 남기면 취향 분석이 더 정확해집니다.</p>

                            <div className="space-y-3">
                                <button
                                    onClick={() => handleDeleteWithRating(1)}
                                    className="w-full py-3 px-4 bg-green-50 hover:bg-green-100/80 border border-green-100 rounded-xl flex items-center gap-3 transition group"
                                >
                                    <span className="text-2xl group-hover:scale-110 transition">👍</span>
                                    <div className="text-left">
                                        <p className="font-bold text-green-700 text-sm">좋았어요</p>
                                        <p className="text-[10px] text-green-600/70">내 취향에 잘 맞음 (+1)</p>
                                    </div>
                                </button>

                                <button
                                    onClick={() => handleDeleteWithRating(0)}
                                    className="w-full py-3 px-4 bg-gray-50 hover:bg-gray-100 border border-gray-200 rounded-xl flex items-center gap-3 transition group"
                                >
                                    <span className="text-2xl group-hover:scale-110 transition">😐</span>
                                    <div className="text-left">
                                        <p className="font-bold text-gray-700 text-sm">무난했어요</p>
                                        <p className="text-[10px] text-gray-500">쏘쏘 (0)</p>
                                    </div>
                                </button>

                                <button
                                    onClick={() => handleDeleteWithRating(-1)}
                                    className="w-full py-3 px-4 bg-red-50 hover:bg-red-100/80 border border-red-100 rounded-xl flex items-center gap-3 transition group"
                                >
                                    <span className="text-2xl group-hover:scale-110 transition">👎</span>
                                    <div className="text-left">
                                        <p className="font-bold text-red-700 text-sm">별로였어요</p>
                                        <p className="text-[10px] text-red-600/70">내 취향 아님 (-1)</p>
                                    </div>
                                </button>
                            </div>

                            <button
                                onClick={() => setIsDeleting(false)}
                                className="mt-4 text-xs text-gray-400 hover:text-gray-600 underline"
                            >
                                취소 (돌아가기)
                            </button>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
