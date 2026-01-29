"use client";

import { useEffect, useRef, useState } from "react";

const API_URL = "/api";

type SearchResult = {
  perfume_id: number;
  name: string;
  name_kr?: string;
  brand: string;
  brand_kr?: string;
  image_url: string | null;
};

type AutocompleteResult = {
  brands: string[];
  keywords: string[];
};

type LayeringPerfumeSearchModalProps = {
  open: boolean;
  onClose: () => void;
  onSelect: (name: string) => void;
};

export default function LayeringPerfumeSearchModal({
  open,
  onClose,
  onSelect,
}: LayeringPerfumeSearchModalProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [isKorean, setIsKorean] = useState(true);
  const [suggestions, setSuggestions] = useState<AutocompleteResult>({
    brands: [],
    keywords: [],
  });
  const [showSuggestions, setShowSuggestions] = useState(false);
  const searchTimeout = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (!open) {
      setQuery("");
      setResults([]);
      setSuggestions({ brands: [], keywords: [] });
      setShowSuggestions(false);
    }
  }, [open]);

  const executeSearch = async (searchTerm: string) => {
    if (!searchTerm.trim()) {
      setResults([]);
      return;
    }
    try {
      setLoading(true);
      setShowSuggestions(false);
      const res = await fetch(
        `${API_URL}/perfumes/search?q=${encodeURIComponent(searchTerm)}`,
      );
      if (res.ok) {
        const data = (await res.json()) as SearchResult[];
        setResults(data);
      }
    } catch (error) {
      console.error("Search failed:", error);
    } finally {
      setLoading(false);
    }
  };

  const fetchAutocomplete = async (input: string) => {
    if (!input.trim()) {
      setSuggestions({ brands: [], keywords: [] });
      return;
    }
    try {
      const res = await fetch(
        `${API_URL}/perfumes/autocomplete?q=${encodeURIComponent(input)}`,
      );
      if (res.ok) {
        const data = (await res.json()) as AutocompleteResult;
        setSuggestions(data);
        setShowSuggestions(true);
      }
    } catch (error) {
      console.error("Autocomplete failed:", error);
    }
  };

  const handleInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const value = event.target.value;
    setQuery(value);

    if (searchTimeout.current) {
      clearTimeout(searchTimeout.current);
    }

    searchTimeout.current = setTimeout(() => {
      if (value.length >= 1) {
        fetchAutocomplete(value);
        executeSearch(value);
      } else {
        setResults([]);
        setShowSuggestions(false);
      }
    }, 300);
  };

  const handleSuggestionClick = (keyword: string) => {
    setQuery(keyword);
    executeSearch(keyword);
    setShowSuggestions(false);
  };

  const handleSelect = (perfume: SearchResult) => {
    const name = isKorean ? (perfume.name_kr || perfume.name) : (perfume.name || perfume.name_kr);
    const brand = isKorean ? (perfume.brand_kr || perfume.brand) : (perfume.brand || perfume.brand_kr);
    const insertText = brand ? `${brand} ${name}` : name;
    if (insertText) {
      onSelect(insertText);
    }
    onClose();
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="bg-white w-full max-w-lg rounded-3xl shadow-2xl flex flex-col max-h-[85vh] overflow-hidden">
        <div className="p-4 border-b flex justify-between items-center sticky top-0 bg-white z-10">
          <div className="flex items-center gap-3">
            <h2 className="font-bold text-lg">향수 검색</h2>
            <button
              onClick={() => setIsKorean((prev) => !prev)}
              className="w-7 h-7 flex items-center justify-center rounded-full border border-gray-200 text-[10px] font-bold text-gray-500 hover:bg-black hover:text-white transition-all"
              title={isKorean ? "Switch to English" : "한글로 전환"}
            >
              {isKorean ? "KR" : "EN"}
            </button>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">✕</button>
        </div>

        <div className="p-6 bg-white relative z-20">
          <div className="flex gap-3">
            <input
              type="text"
              value={query}
              onChange={handleInputChange}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  if (searchTimeout.current) {
                    clearTimeout(searchTimeout.current);
                  }
                  setShowSuggestions(false);
                  executeSearch(query);
                }
              }}
              placeholder="브랜드 혹은 향수 이름 입력..."
              className="flex-1 bg-gray-50 text-[#333] px-4 py-4 rounded-xl border-none focus:ring-2 focus:ring-[#C5A55D]/50 focus:bg-white transition text-sm font-medium placeholder-gray-400"
              autoFocus
            />
          </div>

          {showSuggestions && (suggestions.brands.length > 0 || suggestions.keywords.length > 0) && (
            <div className="absolute left-6 right-6 top-[calc(100%-10px)] bg-white border border-gray-100 rounded-b-xl shadow-xl overflow-hidden">
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
                  {suggestions.keywords.map((keyword, idx) => (
                    <div
                      key={`k-${idx}`}
                      onClick={() => handleSuggestionClick(keyword)}
                      className="px-3 py-2 hover:bg-gray-50 cursor-pointer text-sm text-gray-600 flex items-center gap-2"
                    >
                      <svg className="w-3 h-3 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                      </svg>
                      {keyword}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-3 bg-white" onClick={() => setShowSuggestions(false)}>
          {results.length === 0 ? (
            <div className="text-center py-10 text-gray-400">
              {loading ? "검색 중..." : query ? "검색 결과가 없습니다." : "원하는 향수를 검색해보세요."}
            </div>
          ) : (
            results.map((perfume) => (
              <div
                key={perfume.perfume_id}
                className="group flex items-center gap-4 p-3 bg-white border border-gray-100 rounded-2xl hover:border-[#C5A55D]/30 hover:shadow-lg transition"
              >
                <div className="w-14 h-16 bg-[#f9f9f9] rounded-xl flex items-center justify-center overflow-hidden">
                  {perfume.image_url ? (
                    <img
                      src={perfume.image_url}
                      alt={perfume.name}
                      className="max-w-full max-h-full object-contain mix-blend-multiply scale-[1.3] -translate-y-1"
                    />
                  ) : (
                    <span className="text-gray-300 text-[10px]">No img</span>
                  )}
                </div>

                <div className="flex-1 min-w-0">
                  <p className="text-[#333] font-bold text-sm truncate">
                    {isKorean ? (perfume.name_kr || perfume.name) : (perfume.name || perfume.name_kr)}
                  </p>
                  <p className="text-[#999] text-xs font-medium uppercase tracking-wide truncate">
                    {isKorean ? (perfume.brand_kr || perfume.brand) : perfume.brand}
                  </p>
                </div>

                <button
                  onClick={() => handleSelect(perfume)}
                  className="px-3 py-1.5 rounded-lg bg-[#2E2B28] text-white border border-[#2E2B28] hover:bg-[#1E1C1A] transition text-[11px] font-bold whitespace-nowrap"
                >
                  입력
                </button>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
