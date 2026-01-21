# 향수 네트워크 시각화 오류 해결 가이드

`perfume-network` 페이지에서 시각화 그래프가 보이지 않고 검은 화면만 뜨는 문제(CDN 로딩 실패)를 해결하기 위한 가이드입니다.

## 1. 원인
`vis-network` 라이브러리를 설치하지 않고 불안정한 CDN(`<script>`) 방식으로 불러와서 발생한 문제입니다. 네트워크 상황에 따라 `window.vis` 객체를 찾지 못해 오류가 발생합니다.

## 2. 해결 방법 (Step-by-Step)

### 단계 1: 라이브러리 설치
터미널에서 `Scentence-app/frontend` 폴더로 이동한 뒤, 아래 명령어를 실행해 주세요.

```bash
cd Scentence-app/frontend
npm install vis-network vis-data
npm install -D @types/vis
```

### 단계 2: 코드 교체
`frontend/app/perfume-network/page.tsx` 파일의 내용을 아래 코드로 **전체 교체**해 주세요.
(기존의 `<Script>` 태그를 제거하고, 설치한 라이브러리를 `import` 해서 사용하는 안전한 방식입니다.)

```tsx
"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
// ✅ 라이브러리 직접 import (안정성 확보)
import { Network } from "vis-network";
import { DataSet } from "vis-data";
import "vis-network/styles/vis-network.css"; // CSS도 여기서 불러옴

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
  const [lastRequest, setLastRequest] = useState("");

  const containerRef = useRef<HTMLDivElement>(null);
  const networkRef = useRef<Network | null>(null);

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
    if (!payload || !containerRef.current) return;

    // 기존 네트워크 파괴
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
          title: `<b>${node.label}</b><br/>${node.brand ?? ""}<br/>대표 어코드: ${
            node.primary_accord ?? "Unknown"
          }`,
          borderWidth: 2,
          color: {
            border: "#f0abfc",
            background: "#1f2937",
          },
          font: { color: "#f8fafc", size: 12 },
        };
      }
      // 어코드 노드
      return {
        id: node.id,
        label: node.label,
        shape: "dot",
        size: 14,
        color: { background: "#38bdf8", border: "#0ea5e9" },
        font: { color: "#e2e8f0", size: 11 },
      };
    });

    const edges = payload.edges.map((edge) => {
      if (edge.type === "SIMILAR_TO") {
        return {
          from: edge.from,
          to: edge.to,
          value: edge.weight ?? 0.1,
          color: { color: "#f472b6", opacity: 0.6 },
          width: edge.weight ? Math.max(1, edge.weight * 4) : 1,
          smooth: true,
        };
      }
      // HAS_ACCORD
      return {
        from: edge.from,
        to: edge.to,
        value: edge.weight ?? 0.1,
        color: { color: "#94a3b8", opacity: 0.2 },
        dashes: true,
        smooth: false
      };
    });

    // DataSet으로 변환
    const data = {
      nodes: new DataSet(nodes),
      edges: new DataSet(edges),
    };

    const options = {
      interaction: { hover: true, navigationButtons: true, zoomView: true },
      physics: {
        solver: "forceAtlas2Based",
        stabilization: { 
            enabled: true,
            iterations: 150 
        },
        forceAtlas2Based: {
            gravitationalConstant: -50,
            centralGravity: 0.01,
            springLength: 100,
            springConstant: 0.08
        }
      },
      nodes: { shape: "dot" },
      edges: { smooth: { type: "continuous" } },
    };

    // ✅ window.vis 대신 import한 Network 클래스 사용
    networkRef.current = new Network(containerRef.current, data, options);
  }, [payload]);

  const handleReset = () => {
    if (networkRef.current) {
      networkRef.current.fit({ animation: true });
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 px-6 py-10 space-y-6">
      
      {/* Script 태그 삭제됨 */}

      <header className="space-y-2">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-semibold">전체 향수 관계 네트워크</h1>
          <Link
            href="/"
            className="text-sm text-slate-300 hover:text-white transition"
          >
            메인으로
          </Link>
        </div>
        <p className="text-sm text-slate-400">
          perfume_db 전체 데이터를 기반으로 관계 맵을 시각화합니다.
        </p>
      </header>

      <section className="grid gap-6 lg:grid-cols-[320px_1fr]">
        <div className="space-y-5 rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
           {/* (왼쪽 컨트롤 패널 코드는 기존과 동일하므로 생략하지 않고 그대로 둡니다) */}
           <div className="space-y-2">
            <p className="text-sm font-semibold">시각화 파라미터</p>
            <label className="block text-xs text-slate-400">
              유사도 임계치 ({minSimilarity.toFixed(2)})
            </label>
            <input
              type="range"
              min="0.2"
              max="0.9"
              step="0.05"
              value={minSimilarity}
              onChange={(e) => setMinSimilarity(Number(e.target.value))}
              className="w-full"
            />

            <label className="block text-xs text-slate-400 mt-3">
              연결할 상위 어코드 수
            </label>
            <select
              value={topAccords}
              onChange={(e) => setTopAccords(Number(e.target.value))}
              className="w-full rounded-lg bg-slate-800 px-3 py-2 text-sm"
            >
              {[1, 2, 3, 4, 5].map((count) => (
                <option key={count} value={count}>
                  {count}개
                </option>
              ))}
            </select>

            <label className="block text-xs text-slate-400 mt-3">
              최대 향수 수 (디버깅용)
            </label>
            <input
              type="number"
              min="1"
              placeholder="전체"
              value={maxPerfumes}
              onChange={(e) => setMaxPerfumes(e.target.value)}
              className="w-full rounded-lg bg-slate-800 px-3 py-2 text-sm"
            />
          </div>

          <div className="space-y-2 text-xs text-slate-400">
            <p>상태: {status}</p>
            {error && <p className="text-rose-300">오류: {error}</p>}
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
            className="w-full rounded-lg bg-pink-600/80 py-2 text-sm font-semibold hover:bg-pink-500 transition"
          >
            화면 맞춤
          </button>

          <div className="space-y-2 text-xs text-slate-500">
            <p>요청 URL</p>
            <p className="break-all text-slate-400">{lastRequest}</p>
          </div>
        </div>

        <div className="space-y-3">
            {/* 그래프 컨테이너 */}
          <div className="h-[70vh] rounded-2xl border border-slate-800 bg-slate-900/40 p-4 relative">
             {/* 
                중요: vis-network 캔버스가 부모 div 크기를 상속받도록 
                style이나 class를 명시적으로 주는 것이 좋습니다. 
             */}
            <div ref={containerRef} className="h-full w-full" />
          </div>
          <div className="text-xs text-slate-500">
            선 굵기는 유사도, 점선은 향수-어코드 연결입니다.
            <br/>
            (마우스 휠로 줌인/줌아웃, 드래그로 이동 가능)
          </div>
        </div>
      </section>
    </div>
  );
}
```
