/* PerfumeSearchModal.tsx (3-State Buttons: HAVE, HAD-Amber, WISH) */
"use client";

import { useState, useEffect, useRef } from 'react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface SearchResult {
    perfume_id: number;
    name: string;
    name_kr?: string;
    brand: string;
    brand_kr?: string;
    image_url: string | null;
}

interface AutocompleteResult {
    brands: string[];
    keywords: string[];
}

interface Props {
    memberId: string | null;
    onClose: () => void;
    onAdd: (perfume: SearchResult, status: string) => void;
}

export default function PerfumeSearchModal({ memberId, onClose, onAdd }: Props) {
    const [query, setQuery] = useState("");
    const [results, setResults] = useState<SearchResult[]>([]);
    const [loading, setLoading] = useState(false);

    // Autocomplete States
    const [suggestions, setSuggestions] = useState<AutocompleteResult>({ brands: [], keywords: [] });
    const [showSuggestions, setShowSuggestions] = useState(false);
    const searchTimeout = useRef<NodeJS.Timeout | null>(null);

    // [1] 통합 검색 함수 (Query로 검색)
    const executeSearch = async (searchTerm: string) => {
        if (!searchTerm.trim()) {
            setResults([]);
            return;
        }
        try {
            setLoading(true);
            setShowSuggestions(false); // 검색 시작하면 자동완성 닫기
            const res = await fetch(`${API_URL}/perfumes/search?q=${encodeURIComponent(searchTerm)}`);
            if (res.ok) {
                const data = await res.json();
                setResults(data);
            }
        } catch (error) {
            console.error("Search failed:", error);
        } finally {
            setLoading(false);
        }
    };

    // [2] 자동완성 데이터 가져오기
    const fetchAutocomplete = async (input: string) => {
        if (!input.trim()) {
            setSuggestions({ brands: [], keywords: [] });
            return;
        }
        try {
            const res = await fetch(`${API_URL}/perfumes/autocomplete?q=${encodeURIComponent(input)}`);
            if (res.ok) {
                const data = await res.json();
                setSuggestions(data);
                setShowSuggestions(true);
            }
        } catch (error) {
            console.error("Autocomplete failed:", error);
        }
    };

    // [3] 입력 핸들러 (Debounce 적용)
    const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const val = e.target.value;
        setQuery(val);

        if (searchTimeout.current) clearTimeout(searchTimeout.current);

        searchTimeout.current = setTimeout(() => {
            if (val.length >= 1) {
                fetchAutocomplete(val);  // 1. 자동완성 목록 호출
                executeSearch(val);      // 2. 실시간 검색 결과 호출 (동시 실행)
            } else {
                setResults([]);
                setShowSuggestions(false);
            }
        }, 300); // 300ms 딜레이
    };

    // [4] 추천 검색어 클릭 시
    const handleSuggestionClick = (keyword: string) => {
        setQuery(keyword);
        executeSearch(keyword);
        setShowSuggestions(false);
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
            <div className="bg-white w-full max-w-lg rounded-3xl shadow-2xl flex flex-col max-h-[85vh] overflow-hidden">

                {/* Header */}
                <div className="flex items-center justify-between p-6 border-b border-gray-50 bg-[#FDFBF8]">
                    <h2 className="text-[#333] font-bold text-lg">향수 검색</h2>
                    <button onClick={onClose} className="text-gray-400 hover:text-gray-800 text-2xl transition">&times;</button>
                </div>

                {/* Search Input Area */}
                <div className="p-6 bg-white relative z-20">
                    <div className="flex gap-3">
                        <input
                            type="text"
                            value={query}
                            onChange={handleInputChange}
                            placeholder="브랜드 혹은 향수 이름 입력..."
                            className="flex-1 bg-gray-50 text-[#333] px-4 py-4 rounded-xl border-none focus:ring-2 focus:ring-[#C5A55D]/50 focus:bg-white transition text-sm font-medium placeholder-gray-400"
                            autoFocus
                        />
                    </div>

                    {/* Autocomplete Dropdown */}
                    {showSuggestions && (suggestions.brands.length > 0 || suggestions.keywords.length > 0) && (
                        <div className="absolute left-6 right-6 top-[calc(100%-10px)] bg-white border border-gray-100 rounded-b-xl shadow-xl overflow-hidden animate-In">
                            {suggestions.brands.length > 0 && (
                                <div className="p-2">
                                    <div className="text-[10px] text-gray-400 font-bold px-3 py-1 uppercase">Brands</div>
                                    {suggestions.brands.map((brand, idx) => (
                                        <div
                                            key={`b-${idx}`}
                                            onClick={() => handleSuggestionClick(brand)}
                                            className="px-3 py-2 hover:bg-gray-50 cursor-pointer text-sm font-medium text-gray-700 flex items-center gap-2"
                                        >
                                            <span className="w-1.5 h-1.5 rounded-full bg-indigo-400"></span>
                                            {brand}
                                        </div>
                                    ))}
                                </div>
                            )}
                            {suggestions.keywords.length > 0 && (
                                <div className="p-2 border-t border-gray-50">
                                    <div className="text-[10px] text-gray-400 font-bold px-3 py-1 uppercase">Perfumes</div>
                                    {suggestions.keywords.map((kw, idx) => (
                                        <div
                                            key={`k-${idx}`}
                                            onClick={() => handleSuggestionClick(kw)}
                                            className="px-3 py-2 hover:bg-gray-50 cursor-pointer text-sm text-gray-600 flex items-center gap-2"
                                        >
                                            <svg className="w-3 h-3 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                                            </svg>
                                            {kw}
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}
                </div>

                {/* Results List */}
                <div className="flex-1 overflow-y-auto p-6 space-y-3 bg-white custom-scrollbar z-10" onClick={() => setShowSuggestions(false)}>
                    {results.length === 0 ? (
                        <div className="text-center py-10 text-gray-400">
                            {loading ? "검색 중..." : query ? "검색 결과가 없습니다." : "원하는 향수를 검색해보세요."}
                        </div>
                    ) : (
                        results.map((perfume) => (
                            <div key={perfume.perfume_id} className="group flex items-center gap-4 p-3 bg-white border border-gray-100 rounded-2xl hover:border-[#C5A55D]/30 hover:shadow-lg transition">
                                <div className="w-14 h-16 bg-[#f9f9f9] rounded-xl flex items-center justify-center overflow-hidden">
                                    {perfume.image_url ? (
                                        <img src={perfume.image_url} alt={perfume.name} className="max-w-full max-h-full object-contain mix-blend-multiply scale-[1.3] -translate-y-1" />
                                    ) : <span className="text-gray-300 text-[10px]">No img</span>}
                                </div>

                                <div className="flex-1 min-w-0">
                                    <p className="text-[#333] font-bold text-sm truncate">{perfume.name_kr || perfume.name}</p>
                                    <p className="text-[#999] text-xs font-medium uppercase tracking-wide truncate">
                                        {perfume.brand_kr || perfume.brand}
                                    </p>
                                </div>

                                <div className="flex gap-2">
                                    {/* 보유 (HAVE) */}
                                    <button
                                        onClick={() => onAdd(perfume, 'HAVE')}
                                        className="px-3 py-1.5 rounded-lg bg-indigo-50 text-indigo-600 border border-indigo-100 hover:bg-indigo-600 hover:text-white transition text-[11px] font-bold whitespace-nowrap"
                                    >
                                        보유
                                    </button>
                                    {/* 위시 (RECOMMENDED) -> Rose */}
                                    <button
                                        onClick={() => onAdd(perfume, 'RECOMMENDED')}
                                        className="px-3 py-1.5 rounded-lg bg-rose-50 text-rose-500 border border-rose-100 hover:bg-rose-500 hover:text-white transition text-[11px] font-bold whitespace-nowrap"
                                    >
                                        위시
                                    </button>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </div>
        </div>
    );
}