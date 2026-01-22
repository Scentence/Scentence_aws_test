"use client";

import { useState } from "react";
import AccordWheel from "@/components/layering/AccordWheel";
import { BACKEND_ACCORDS } from "@/lib/accords";

type LayeringCandidate = {
  perfume_id: string;
  perfume_name: string;
  perfume_brand: string;
  total_score: number;
  spray_order: string[];
  analysis: string;
  layered_vector: number[];
};

type LayeringResponse = {
  base_perfume_id: string;
  keywords: string[];
  total_available: number;
  recommendations: LayeringCandidate[];
  note?: string | null;
};

type UserQueryResponse = {
  raw_text: string;
  keywords: string[];
  base_perfume_id?: string | null;
  detected_pair?: {
    base_perfume_id?: string | null;
    candidate_perfume_id?: string | null;
  } | null;
  recommendation?: LayeringCandidate | null;
  note?: string | null;
};

const apiBase =
  process.env.NEXT_PUBLIC_LAYERING_API_URL ?? "http://localhost:8002";

export default function LayeringPage() {
  const [queryText, setQueryText] = useState(
    "CK One이 있는데 이거랑 레이어링해서 좀 더 시트러스하고 시원한 느낌이 나게하는 향수를 추천해줘",
  );
  const [basePerfumeId, setBasePerfumeId] = useState("8701");
  const [keywordsInput, setKeywordsInput] = useState("fresh, citrus");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<LayeringResponse | null>(null);

  const handleAnalyze = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${apiBase}/layering/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_text: queryText }),
      });

      if (!response.ok) {
        throw new Error("자연어 분석 결과를 불러오지 못했어요.");
      }

      const payload = (await response.json()) as UserQueryResponse;
      const recommendation = payload.recommendation ?? null;
      const baseId =
        payload.base_perfume_id ?? payload.detected_pair?.base_perfume_id ?? basePerfumeId;
      const keywords = payload.keywords ?? [];

      if (recommendation) {
        setResult({
          base_perfume_id: baseId,
          keywords,
          total_available: 1,
          recommendations: [recommendation],
          note: payload.note ?? null,
        });
      } else {
        setResult({
          base_perfume_id: baseId,
          keywords,
          total_available: 0,
          recommendations: [],
          note: payload.note ?? "추천 결과가 없어요.",
        });
      }

      if (payload.keywords?.length) {
        setKeywordsInput(payload.keywords.join(", "));
      }
      if (payload.base_perfume_id || payload.detected_pair?.base_perfume_id) {
        setBasePerfumeId(
          payload.base_perfume_id ?? payload.detected_pair?.base_perfume_id ?? basePerfumeId,
        );
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "알 수 없는 오류가 발생했어요.");
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async () => {
    setLoading(true);
    setError(null);

    const keywords = keywordsInput
      .split(",")
      .map((item) => item.trim().toLowerCase())
      .filter(Boolean);

    try {
      const response = await fetch(`${apiBase}/layering/recommend`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ base_perfume_id: basePerfumeId, keywords }),
      });

      if (!response.ok) {
        throw new Error("레이어링 결과를 불러오지 못했어요.");
      }

      const payload = (await response.json()) as LayeringResponse;
      setResult(payload);
    } catch (err) {
      setError(err instanceof Error ? err.message : "알 수 없는 오류가 발생했어요.");
    } finally {
      setLoading(false);
    }
  };

  const candidate = result?.recommendations?.[0];
  const vector = candidate?.layered_vector ?? [];
  const vectorReady = vector.length === BACKEND_ACCORDS.length;

  return (
    <div className="min-h-screen bg-[#F5F2EA] text-[#1F1F1F]">
      <div className="max-w-5xl mx-auto px-6 py-12">
        <header className="space-y-3">
          <p className="text-xs uppercase tracking-[0.3em] text-[#7A6B57]">
            Layering Visualization
          </p>
          <h1 className="text-3xl font-semibold">레이어링 어코드 원판</h1>
          <p className="text-sm text-[#5C5448]">
            21개 어코드의 강도를 원형 그래픽으로 표현합니다.
          </p>
        </header>

        <section className="mt-8 grid gap-6 lg:grid-cols-[1fr_1.2fr]">
          <div className="rounded-3xl bg-white/80 border border-[#E2D7C5] p-6 shadow-sm">
            <h2 className="text-sm font-semibold text-[#7A6B57]">입력값</h2>
            <div className="mt-4 space-y-4">
              <div>
                <label className="text-xs font-semibold text-[#7A6B57]">자연어 질문</label>
                <textarea
                  value={queryText}
                  onChange={(event) => setQueryText(event.target.value)}
                  className="mt-2 w-full rounded-xl border border-[#E1D7C8] bg-white px-4 py-3 text-sm min-h-[110px]"
                  placeholder="예: CK One이 있는데, 시트러스하게 레이어링 추천해줘"
                />
                <button
                  onClick={handleAnalyze}
                  className="mt-3 w-full rounded-xl bg-[#2E2B28] px-4 py-3 text-sm font-semibold text-white shadow-md transition hover:bg-[#1E1C1A]"
                  disabled={loading}
                >
                  {loading ? "분석 중..." : "자연어로 추천받기"}
                </button>
              </div>
              <div>
                <label className="text-xs font-semibold text-[#7A6B57]">Base perfume ID</label>
                <input
                  value={basePerfumeId}
                  onChange={(event) => setBasePerfumeId(event.target.value)}
                  className="mt-2 w-full rounded-xl border border-[#E1D7C8] bg-white px-4 py-3 text-sm"
                  placeholder="예: 8701"
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-[#7A6B57]">Keywords</label>
                <input
                  value={keywordsInput}
                  onChange={(event) => setKeywordsInput(event.target.value)}
                  className="mt-2 w-full rounded-xl border border-[#E1D7C8] bg-white px-4 py-3 text-sm"
                  placeholder="fresh, citrus"
                />
              </div>
              <button
                onClick={handleSubmit}
                className="w-full rounded-xl bg-[#C8A24D] px-4 py-3 text-sm font-semibold text-white shadow-md transition hover:bg-[#B89138]"
                disabled={loading}
              >
                {loading ? "불러오는 중..." : "레이어링 결과 보기"}
              </button>
              {error && <p className="text-xs text-[#B13C2E]">{error}</p>}
              {result?.note && (
                <p className="text-xs text-[#7A6B57]">{result.note}</p>
              )}
            </div>
          </div>

          <div className="rounded-3xl bg-white/90 border border-[#E2D7C5] p-6 shadow-sm">
            <h2 className="text-sm font-semibold text-[#7A6B57]">레이어링 시각화</h2>
            <div className="mt-4 flex flex-col items-center gap-6">
              {vectorReady ? (
                <AccordWheel vector={vector} />
              ) : (
                <div className="h-[360px] w-[360px] flex items-center justify-center rounded-full border border-dashed border-[#D7CDBD] text-xs text-[#7A6B57]">
                  데이터를 불러오면 원판이 표시됩니다.
                </div>
              )}
              {candidate && (
                <div className="w-full rounded-2xl bg-[#F8F4EC] border border-[#E6DDCF] p-4 text-xs text-[#4D463A] space-y-2">
                  <div className="flex justify-between">
                    <span className="font-semibold">추천 향수</span>
                    <span>{candidate.total_score.toFixed(3)}</span>
                  </div>
                  <p className="text-sm font-semibold">
                    {candidate.perfume_name} · {candidate.perfume_brand}
                  </p>
                  <p className="text-[11px] text-[#7A6B57]">{candidate.analysis}</p>
                  <div className="text-[11px] text-[#7A6B57]">
                    분사 순서: {candidate.spray_order.join(" → ")}
                  </div>
                </div>
              )}
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
