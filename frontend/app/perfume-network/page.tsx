"use client";

import "./vis-network.css";
import Link from "next/link";
import Script from "next/script";
import { useEffect, useMemo, useRef, useState } from "react";

type NetworkNode = {
  id: string;
  type: "perfume" | "accord";
  label: string;
  brand?: string;
  image?: string;
  primary_accord?: string;
};

type NetworkEdge = {
  from: string;
  to: string;
  type: "HAS_ACCORD" | "SIMILAR_TO";
  weight?: number;
};

type NetworkMeta = {
  perfume_count: number;
  accord_count: number;
  edge_count: number;
  accord_edges: number;
  similarity_edges: number;
  similarity_edges_high: number;
  min_similarity: number;
  top_accords: number;
  candidate_pairs: number;
  built_at: string;
  build_seconds: number;
  max_perfumes?: number | null;
};

type NetworkPayload = {
  nodes: NetworkNode[];
  edges: NetworkEdge[];
  meta: NetworkMeta;
};

const API_BASE =
  process.env.NEXT_PUBLIC_SCENTMAP_API_URL ?? "http://127.0.0.1:8001";

export default function PerfumeNetworkPage() {
  const [minSimilarity, setMinSimilarity] = useState(0.45);
  const [topAccords, setTopAccords] = useState(2);
  const [maxPerfumes, setMaxPerfumes] = useState<string>("");
  const [payload, setPayload] = useState<NetworkPayload | null>(null);
  const [status, setStatus] = useState("대기 중");
  const [error, setError] = useState("");
  const [scriptReady, setScriptReady] = useState(false);
  const [lastRequest, setLastRequest] = useState("");

  const containerRef = useRef<HTMLDivElement>(null);
  const networkRef = useRef<any>(null);

  const requestUrl = useMemo(() => {
    const params = new URLSearchParams();
    params.set("min_similarity", String(minSimilarity));
    params.set("top_accords", String(topAccords));
    if (maxPerfumes.trim()) {
      params.set("max_perfumes", maxPerfumes.trim());
    }
    return `${API_BASE}/network/perfumes?${params.toString()}`;
  }, [minSimilarity, topAccords, maxPerfumes]);

  useEffect(() => {
    const fetchData = async () => {
      setStatus("데이터 요청 중...");
      setError("");
      setLastRequest(requestUrl);
      try {
        const res = await fetch(requestUrl);
        if (!res.ok) {
          throw new Error(`서버 오류: ${res.status}`);
        }
        const data = (await res.json()) as NetworkPayload;
        setPayload(data);
        setStatus("데이터 수신 완료");
      } catch (err) {
        setError(err instanceof Error ? err.message : "알 수 없는 오류");
        setStatus("요청 실패");
      }
    };

    fetchData();
  }, [requestUrl]);

  useEffect(() => {
    if (!scriptReady || !payload || !containerRef.current) return;
    const vis = (window as any).vis;
    if (!vis) return;

    if (networkRef.current) {
      networkRef.current.destroy();
      networkRef.current = null;
    }

    const nodes = payload.nodes.map((node) => {
      if (node.type === "perfume") {
        return {
          id: node.id,
          label: node.label,
          shape: "circularImage",
          image: node.image || undefined,
          title: `${node.label}\n${node.brand ?? ""}\n대표 어코드: ${
            node.primary_accord ?? "Unknown"
          }`,
          borderWidth: 2,
          color: {
            border: "#C8A24D",
            background: "#F8F4EC",
          },
          font: { color: "#4D463A", size: 12 },
        };
      }
      return {
        id: node.id,
        label: node.label,
        shape: "dot",
        size: 14,
        color: { background: "#E8DDCA", border: "#BFA67A" },
        font: { color: "#5C5448", size: 11 },
      };
    });

    const edges = payload.edges.map((edge) => {
      if (edge.type === "SIMILAR_TO") {
        return {
          from: edge.from,
          to: edge.to,
          value: edge.weight ?? 0.1,
          color: { color: "#B89138", opacity: 0.6 },
          width: edge.weight ? Math.max(1, edge.weight * 4) : 1,
          smooth: true,
        };
      }
      return {
        from: edge.from,
        to: edge.to,
        value: edge.weight ?? 0.1,
        color: { color: "#9C8D7A", opacity: 0.4 },
        dashes: true,
      };
    });

    const data = { nodes, edges };
    const options = {
      interaction: { hover: true, navigationButtons: true },
      physics: {
        solver: "forceAtlas2Based",
        stabilization: { iterations: 150 },
      },
      nodes: { shape: "dot" },
      edges: { smooth: { type: "continuous" } },
    };

    networkRef.current = new vis.Network(containerRef.current, data, options);
  }, [scriptReady, payload]);

  const handleReset = () => {
    if (networkRef.current) {
      networkRef.current.fit({ animation: true });
    }
  };

  return (
    <div className="min-h-screen bg-[#F5F2EA] text-[#1F1F1F] px-6 py-12 space-y-8">
      <Script
        src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"
        strategy="afterInteractive"
        onLoad={() => setScriptReady(true)}
      />

      <header className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="space-y-1">
            <p className="text-xs uppercase tracking-[0.3em] text-[#7A6B57]">
              perfume network
            </p>
            <h1 className="text-2xl font-semibold text-[#1F1F1F]">
              전체 향수 관계 네트워크
            </h1>
          </div>
          <Link
            href="/"
            className="rounded-full border border-[#E2D7C5] bg-white/80 px-4 py-2 text-xs font-semibold text-[#5C5448] transition hover:bg-white"
          >
            메인으로
          </Link>
        </div>
        <p className="text-sm text-[#5C5448]">
          perfume_db 전체 데이터를 기반으로 관계 맵을 시각화합니다.
        </p>
      </header>

      <section className="grid gap-6 lg:grid-cols-[320px_1fr]">
        <div className="space-y-6 rounded-3xl bg-white/80 border border-[#E2D7C5] p-5 shadow-sm">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <p className="text-sm font-semibold text-[#1F1F1F]">
                시각화 파라미터
              </p>
              <span className="rounded-full bg-[#F2EBDD] px-2.5 py-1 text-[11px] text-[#7A6B57]">
                Layering
              </span>
            </div>
            <label className="block text-xs text-[#7A6B57]">
              유사도 임계치 ({minSimilarity.toFixed(2)})
            </label>
            <input
              type="range"
              min="0.2"
              max="0.9"
              step="0.05"
              value={minSimilarity}
              onChange={(e) => setMinSimilarity(Number(e.target.value))}
              className="w-full accent-[#C8A24D]"
            />

            <label className="block text-xs text-[#7A6B57] mt-4">
              연결할 상위 어코드 수
            </label>
            <select
              value={topAccords}
              onChange={(e) => setTopAccords(Number(e.target.value))}
              className="w-full rounded-xl border border-[#E1D7C8] bg-white px-3 py-2 text-sm text-[#1F1F1F] focus:outline-none focus:ring-2 focus:ring-[#C8A24D]/40"
            >
              {[1, 2, 3, 4, 5].map((count) => (
                <option key={count} value={count}>
                  {count}개
                </option>
              ))}
            </select>

            <label className="block text-xs text-[#7A6B57] mt-4">
              최대 향수 수 (디버깅용)
            </label>
            <input
              type="number"
              min="1"
              placeholder="전체"
              value={maxPerfumes}
              onChange={(e) => setMaxPerfumes(e.target.value)}
              className="w-full rounded-xl border border-[#E1D7C8] bg-white px-3 py-2 text-sm text-[#1F1F1F] focus:outline-none focus:ring-2 focus:ring-[#C8A24D]/40"
            />
          </div>

          <div className="space-y-2 rounded-2xl border border-[#E6DDCF] bg-[#F8F4EC] p-4 text-xs text-[#4D463A]">
            <p>상태: {status}</p>
            {error && <p className="text-[#B13C2E]">오류: {error}</p>}
            {payload && (
              <>
                <p>향수: {payload.meta.perfume_count}개</p>
                <p>어코드: {payload.meta.accord_count}개</p>
                <p>엣지: {payload.meta.edge_count}개</p>
                <p>생성 시간: {payload.meta.build_seconds}s</p>
              </>
            )}
          </div>

          <button
            onClick={handleReset}
            className="w-full rounded-xl bg-[#2E2B28] py-2.5 text-sm font-semibold text-white shadow-md transition hover:bg-[#1E1C1A]"
          >
            화면 맞춤
          </button>

          <div className="space-y-2 text-xs text-[#7A6B57]">
            <p>요청 URL</p>
            <p className="break-all text-[#5C5448]">{lastRequest}</p>
          </div>
        </div>

        <div className="space-y-3">
          <div className="h-[70vh] rounded-3xl border border-[#E2D7C5] bg-white/90 p-4 shadow-sm">
            <div ref={containerRef} className="h-full w-full" />
          </div>
          <div className="text-xs text-[#7A6B57]">
            선 굵기는 유사도, 점선은 향수-어코드 연결입니다.
          </div>
        </div>
      </section>
    </div>
  );
}