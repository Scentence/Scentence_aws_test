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
  accords?: string[];
  seasons?: string[];
  occasions?: string[];
  genders?: string[];
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
  process.env.NEXT_PUBLIC_SCENTMAP_API_URL ??
  process.env.NEXT_PUBLIC_API_URL ??
  "http://127.0.0.1:8001";

// 어코드별 기본 색상 매핑
const ACCORD_COLORS: Record<string, string> = {
  Animal: "#7A5C3E",
  Aquatic: "#5FBED7",
  Chypre: "#3F6F5E",
  Citrus: "#E6E04A",
  Creamy: "#F1E8D6",
  Earthy: "#AD868B",
  Floral: "#F6B3C6",
  Fougère: "#6F7A4A",
  Fruity: "#F39A4C",
  Gourmand: "#B97A4B",
  Green: "#4FA66A",
  Leathery: "#2E2B28",
  Oriental: "#7A3E2F",
  Powdery: "#E9CFCF",
  Resinous: "#4B6F8A",
  Smoky: "#7B7B7B",
  Spicy: "#9E3B32",
  Sweet: "#F4A3C4",
  Synthetic: "#7FA1D6",
  Woody: "#6B4F2A",
  Fresh: "#8FB5FF",
};

const getAccordColor = (accord?: string) =>
  (accord && ACCORD_COLORS[accord]) || "#E8DDCA";

export default function PerfumeNetworkPage() {
  // 네트워크 요청 파라미터
  const [minSimilarity, setMinSimilarity] = useState(0.45);
  const [topAccords, setTopAccords] = useState(2);
  const [maxPerfumes, setMaxPerfumes] = useState<string>("");
  // API 응답 및 상태 표시
  const [payload, setPayload] = useState<NetworkPayload | null>(null);
  const [status, setStatus] = useState("대기 중");
  const [error, setError] = useState("");
  const [scriptReady, setScriptReady] = useState(false); // vis-network 로드 여부
  const [lastRequest, setLastRequest] = useState(""); // 디버그용 요청 URL
  // 필터 선택 상태
  const [selectedAccords, setSelectedAccords] = useState<string[]>([]);
  const [selectedBrands, setSelectedBrands] = useState<string[]>([]);
  const [selectedSeasons, setSelectedSeasons] = useState<string[]>([]);
  const [selectedOccasions, setSelectedOccasions] = useState<string[]>([]);
  const [selectedGenders, setSelectedGenders] = useState<string[]>([]);
  // 선택된 향수 노드 강조
  const [selectedPerfumeId, setSelectedPerfumeId] = useState<string | null>(
    null
  );
  // 드롭다운 열림 상태
  const [accordOpen, setAccordOpen] = useState(false);
  const [brandOpen, setBrandOpen] = useState(false);
  const [seasonOpen, setSeasonOpen] = useState(false);
  const [occasionOpen, setOccasionOpen] = useState(false);
  const [genderOpen, setGenderOpen] = useState(false);

  // vis-network 렌더링용 참조
  const containerRef = useRef<HTMLDivElement>(null);
  const networkRef = useRef<any>(null);
  const nodesDataRef = useRef<any>(null);
  const edgesDataRef = useRef<any>(null);

  // 요청 파라미터가 바뀔 때마다 URL 갱신
  const requestUrl = useMemo(() => {
    const params = new URLSearchParams();
    params.set("min_similarity", String(minSimilarity));
    params.set("top_accords", String(topAccords));
    if (maxPerfumes.trim()) {
      params.set("max_perfumes", maxPerfumes.trim());
    }
    return `${API_BASE}/network/perfumes?${params.toString()}`;
  }, [minSimilarity, topAccords, maxPerfumes]);

  const toggleSelection = (
    value: string,
    current: string[],
    onChange: (next: string[]) => void
  ) => {
    if (current.includes(value)) {
      onChange(current.filter((item) => item !== value));
      return;
    }
    onChange([...current, value]);
  };

  const formatSelection = (values: string[], placeholder: string) => {
    if (values.length === 0) {
      return placeholder;
    }
    if (values.length === 1) {
      return values[0];
    }
    return `${values[0]} 외 ${values.length - 1}`;
  };

  // 필터 UI에 필요한 옵션 목록 추출
  const filterOptions = useMemo(() => {
    if (!payload) {
      return {
        accords: [] as string[],
        brands: [] as string[],
        seasons: [] as string[],
        occasions: [] as string[],
        genders: [] as string[],
      };
    }

    const perfumeNodes = payload.nodes.filter(
      (node) => node.type === "perfume"
    ) as NetworkNode[];

    const accordSet = new Set<string>();
    const brandSet = new Set<string>();
    const seasonSet = new Set<string>();
    const occasionSet = new Set<string>();
    const genderSet = new Set<string>();

    for (const node of perfumeNodes) {
      if (node.primary_accord) {
        accordSet.add(node.primary_accord);
      }
      if (node.brand) {
        brandSet.add(node.brand);
      }
      node.seasons?.forEach((season) => seasonSet.add(season));
      node.occasions?.forEach((occasion) => occasionSet.add(occasion));
      node.genders?.forEach((gender) => genderSet.add(gender));
    }

    return {
      accords: Array.from(accordSet).sort(),
      brands: Array.from(brandSet).sort(),
      seasons: Array.from(seasonSet).sort(),
      occasions: Array.from(occasionSet).sort(),
      genders: Array.from(genderSet).sort(),
    };
  }, [payload]);

  // 선택된 필터를 기준으로 네트워크 노드/엣지 축소
  const filteredPayload = useMemo(() => {
    if (!payload) return null;

    const perfumeNodes = payload.nodes.filter(
      (node) => node.type === "perfume"
    ) as NetworkNode[];

    const matchesFilter = (node: NetworkNode) => {
      // 대표 어코드 기준으로 필터링
      if (
        selectedAccords.length > 0 &&
        (!node.primary_accord || !selectedAccords.includes(node.primary_accord))
      ) {
        return false;
      }
      if (
        selectedBrands.length > 0 &&
        (!node.brand || !selectedBrands.includes(node.brand))
      ) {
        return false;
      }
      if (
        selectedSeasons.length > 0 &&
        !selectedSeasons.some((season) => node.seasons?.includes(season))
      ) {
        return false;
      }
      if (
        selectedOccasions.length > 0 &&
        !selectedOccasions.some((occasion) => node.occasions?.includes(occasion))
      ) {
        return false;
      }
      if (
        selectedGenders.length > 0 &&
        !selectedGenders.some((gender) => node.genders?.includes(gender))
      ) {
        return false;
      }
      return true;
    };

    const visiblePerfumeIds = new Set(
      perfumeNodes.filter(matchesFilter).map((node) => node.id)
    );

    const visibleAccordIds = new Set(
      payload.edges
        .filter((edge) => edge.type === "HAS_ACCORD")
        .filter((edge) => visiblePerfumeIds.has(edge.from))
        .map((edge) => edge.to)
    );

    const nodes = payload.nodes.filter((node) => {
      if (node.type === "perfume") {
        return visiblePerfumeIds.has(node.id);
      }
      return visibleAccordIds.has(node.id);
    });

    const nodeIdSet = new Set(nodes.map((node) => node.id));
    const edges = payload.edges.filter(
      (edge) => nodeIdSet.has(edge.from) && nodeIdSet.has(edge.to)
    );

    return { ...payload, nodes, edges };
  }, [
    payload,
    selectedAccords,
    selectedBrands,
    selectedSeasons,
    selectedOccasions,
    selectedGenders,
  ]);

  const visiblePayload = filteredPayload ?? payload;

  // 화면에 표시되는 노드/엣지 개수
  const visibleCounts = useMemo(() => {
    if (!visiblePayload) {
      return { perfumes: 0, accords: 0, edges: 0 };
    }
    const perfumes = visiblePayload.nodes.filter(
      (node) => node.type === "perfume"
    ).length;
    const accords = visiblePayload.nodes.filter(
      (node) => node.type === "accord"
    ).length;
    return { perfumes, accords, edges: visiblePayload.edges.length };
  }, [visiblePayload]);

  useEffect(() => {
    // 네트워크 데이터 요청
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
    // vis-network 초기화 및 데이터 반영
    if (!scriptReady || !visiblePayload || !containerRef.current) return;
    const vis = (window as any).vis;
    if (!vis) return;

    const nodes = visiblePayload.nodes.map((node) => {
      if (node.type === "perfume") {
        const borderColor = getAccordColor(node.primary_accord);
        const isAccordSelected = selectedAccords.length > 0;
        return {
          id: node.id,
          label: node.label,
          shape: "circularImage",
          image: node.image || undefined,
          title: `${node.label}\n${node.brand ?? ""}\n대표 어코드: ${
            node.primary_accord ?? "Unknown"
          }`,
          borderWidth: isAccordSelected ? 4 : 2,
          color: {
            border: borderColor,
            background: "#F8F4EC",
          },
          font: { color: "#4D463A", size: 12 },
        };
      }
      const accordLabel = node.label;
      const accordColor = getAccordColor(accordLabel);
      const isSelectedAccord = selectedAccords.includes(accordLabel);
      return {
        id: node.id,
        label: node.label,
        shape: "dot",
        size: isSelectedAccord ? 20 : 14,
        borderWidth: isSelectedAccord ? 3 : 1,
        color: { background: accordColor, border: accordColor },
        font: { color: "#5C5448", size: isSelectedAccord ? 13 : 11 },
      };
    });

    const edges = visiblePayload.edges.map((edge) => {
      const edgeId = `${edge.type}:${edge.from}:${edge.to}`;
      if (edge.type === "SIMILAR_TO") {
        const isSelectedEdge =
          selectedPerfumeId &&
          (edge.from === selectedPerfumeId || edge.to === selectedPerfumeId);
        return {
          id: edgeId,
          from: edge.from,
          to: edge.to,
          value: edge.weight ?? 0.1,
          color: {
            color: "#B89138",
            opacity: isSelectedEdge ? 0.8 : 0.15,
          },
          width: isSelectedEdge
            ? edge.weight
              ? Math.max(2, edge.weight * 5)
              : 2
            : 1,
          smooth: true,
        };
      }
      return {
        id: edgeId,
        from: edge.from,
        to: edge.to,
        value: edge.weight ?? 0.1,
        color: { color: "#9C8D7A", opacity: 0.4 },
        dashes: true,
      };
    });

    if (!networkRef.current) {
      nodesDataRef.current = new vis.DataSet(nodes);
      edgesDataRef.current = new vis.DataSet(edges);
    }

    const nodeIds = new Set(nodes.map((node) => node.id));
    const edgeIds = new Set(edges.map((edge) => edge.id));

    if (nodesDataRef.current) {
      const existingNodeIds = nodesDataRef.current.getIds();
      const removeNodeIds = existingNodeIds.filter(
        (id: string) => !nodeIds.has(id)
      );
      if (removeNodeIds.length) {
        nodesDataRef.current.remove(removeNodeIds);
      }
      nodesDataRef.current.update(nodes);
    }

    if (edgesDataRef.current) {
      const existingEdgeIds = edgesDataRef.current.getIds();
      const removeEdgeIds = existingEdgeIds.filter(
        (id: string) => !edgeIds.has(id)
      );
      if (removeEdgeIds.length) {
        edgesDataRef.current.remove(removeEdgeIds);
      }
      edgesDataRef.current.update(edges);
    }

    const data = {
      nodes: nodesDataRef.current,
      edges: edgesDataRef.current,
    };
    const options = {
      interaction: { hover: true, navigationButtons: true },
      physics: {
        solver: "forceAtlas2Based",
        stabilization: { iterations: 150 },
      },
      nodes: { shape: "dot" },
      edges: { smooth: { type: "continuous" } },
    };

    if (!networkRef.current) {
      networkRef.current = new vis.Network(containerRef.current, data, options);
      networkRef.current.once("stabilizationIterationsDone", () => {
        // 초기 배치 후 위치 고정
        networkRef.current?.setOptions({ physics: false });
      });
    } else {
      // 필터 변경 시 재배치 허용
      networkRef.current.setOptions({ physics: true });
      networkRef.current.once("stabilizationIterationsDone", () => {
        networkRef.current?.setOptions({ physics: false });
      });
      networkRef.current.setData(data);
    }

    networkRef.current.off("click");
    networkRef.current.on("click", (params: { nodes: string[] }) => {
      const targetId = params.nodes?.[0];
      if (targetId && !targetId.startsWith("accord_")) {
        setSelectedPerfumeId(targetId);
        return;
      }
      setSelectedPerfumeId(null);
    });
  }, [scriptReady, visiblePayload, selectedAccords, selectedPerfumeId]);

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

          <div className="space-y-3 border-t border-[#E6DDCF] pt-4">
            <div className="flex items-center justify-between">
              <p className="text-sm font-semibold text-[#1F1F1F]">필터</p>
              <button
                type="button"
                onClick={() => {
                  setSelectedAccords([]);
                  setSelectedBrands([]);
                  setSelectedSeasons([]);
                  setSelectedOccasions([]);
                  setSelectedGenders([]);
                }}
                className="text-[11px] text-[#7A6B57] hover:text-[#5C5448]"
              >
                초기화
              </button>
            </div>

            <label className="block text-xs text-[#7A6B57]">
              카테고리 (어코드)
            </label>
            <div className="relative">
              <button
                type="button"
                onClick={() => setAccordOpen((prev) => !prev)}
                className="flex w-full items-center justify-between rounded-xl border border-[#E1D7C8] bg-white px-3 py-2 text-sm text-[#1F1F1F] focus:outline-none focus:ring-2 focus:ring-[#C8A24D]/40"
              >
                <span>{formatSelection(selectedAccords, "전체")}</span>
                <span className="text-xs text-[#7A6B57]">
                  {accordOpen ? "닫기" : "선택"}
                </span>
              </button>
              {accordOpen && (
                <div className="absolute z-10 mt-2 max-h-52 w-full overflow-y-auto rounded-xl border border-[#E1D7C8] bg-white p-2 text-sm shadow-md">
                  {filterOptions.accords.map((accord) => (
                    <label
                      key={accord}
                      className="flex items-center gap-2 rounded-lg px-2 py-1.5 hover:bg-[#F5F2EA]"
                    >
                      <input
                        type="checkbox"
                        checked={selectedAccords.includes(accord)}
                        onChange={() =>
                          toggleSelection(accord, selectedAccords, setSelectedAccords)
                        }
                        className="accent-[#C8A24D]"
                      />
                      <span>{accord}</span>
                    </label>
                  ))}
                </div>
              )}
            </div>

            <label className="block text-xs text-[#7A6B57] mt-3">
              서브 필터
            </label>
            <div className="grid gap-2">
              <div className="relative">
                <button
                  type="button"
                  onClick={() => setBrandOpen((prev) => !prev)}
                  className="flex w-full items-center justify-between rounded-xl border border-[#E1D7C8] bg-white px-3 py-2 text-sm text-[#1F1F1F] focus:outline-none focus:ring-2 focus:ring-[#C8A24D]/40"
                >
                  <span>{formatSelection(selectedBrands, "브랜드 전체")}</span>
                  <span className="text-xs text-[#7A6B57]">
                    {brandOpen ? "닫기" : "선택"}
                  </span>
                </button>
                {brandOpen && (
                  <div className="absolute z-10 mt-2 max-h-52 w-full overflow-y-auto rounded-xl border border-[#E1D7C8] bg-white p-2 text-sm shadow-md">
                    {filterOptions.brands.map((brand) => (
                      <label
                        key={brand}
                        className="flex items-center gap-2 rounded-lg px-2 py-1.5 hover:bg-[#F5F2EA]"
                      >
                        <input
                          type="checkbox"
                          checked={selectedBrands.includes(brand)}
                          onChange={() =>
                            toggleSelection(brand, selectedBrands, setSelectedBrands)
                          }
                          className="accent-[#C8A24D]"
                        />
                        <span>{brand}</span>
                      </label>
                    ))}
                  </div>
                )}
              </div>

              <div className="relative">
                <button
                  type="button"
                  onClick={() => setSeasonOpen((prev) => !prev)}
                  className="flex w-full items-center justify-between rounded-xl border border-[#E1D7C8] bg-white px-3 py-2 text-sm text-[#1F1F1F] focus:outline-none focus:ring-2 focus:ring-[#C8A24D]/40"
                >
                  <span>{formatSelection(selectedSeasons, "계절 전체")}</span>
                  <span className="text-xs text-[#7A6B57]">
                    {seasonOpen ? "닫기" : "선택"}
                  </span>
                </button>
                {seasonOpen && (
                  <div className="absolute z-10 mt-2 max-h-52 w-full overflow-y-auto rounded-xl border border-[#E1D7C8] bg-white p-2 text-sm shadow-md">
                    {filterOptions.seasons.map((season) => (
                      <label
                        key={season}
                        className="flex items-center gap-2 rounded-lg px-2 py-1.5 hover:bg-[#F5F2EA]"
                      >
                        <input
                          type="checkbox"
                          checked={selectedSeasons.includes(season)}
                          onChange={() =>
                            toggleSelection(
                              season,
                              selectedSeasons,
                              setSelectedSeasons
                            )
                          }
                          className="accent-[#C8A24D]"
                        />
                        <span>{season}</span>
                      </label>
                    ))}
                  </div>
                )}
              </div>

              <div className="relative">
                <button
                  type="button"
                  onClick={() => setOccasionOpen((prev) => !prev)}
                  className="flex w-full items-center justify-between rounded-xl border border-[#E1D7C8] bg-white px-3 py-2 text-sm text-[#1F1F1F] focus:outline-none focus:ring-2 focus:ring-[#C8A24D]/40"
                >
                  <span>{formatSelection(selectedOccasions, "상황 전체")}</span>
                  <span className="text-xs text-[#7A6B57]">
                    {occasionOpen ? "닫기" : "선택"}
                  </span>
                </button>
                {occasionOpen && (
                  <div className="absolute z-10 mt-2 max-h-52 w-full overflow-y-auto rounded-xl border border-[#E1D7C8] bg-white p-2 text-sm shadow-md">
                    {filterOptions.occasions.map((occasion) => (
                      <label
                        key={occasion}
                        className="flex items-center gap-2 rounded-lg px-2 py-1.5 hover:bg-[#F5F2EA]"
                      >
                        <input
                          type="checkbox"
                          checked={selectedOccasions.includes(occasion)}
                          onChange={() =>
                            toggleSelection(
                              occasion,
                              selectedOccasions,
                              setSelectedOccasions
                            )
                          }
                          className="accent-[#C8A24D]"
                        />
                        <span>{occasion}</span>
                      </label>
                    ))}
                  </div>
                )}
              </div>

              <div className="relative">
                <button
                  type="button"
                  onClick={() => setGenderOpen((prev) => !prev)}
                  className="flex w-full items-center justify-between rounded-xl border border-[#E1D7C8] bg-white px-3 py-2 text-sm text-[#1F1F1F] focus:outline-none focus:ring-2 focus:ring-[#C8A24D]/40"
                >
                  <span>{formatSelection(selectedGenders, "성별 전체")}</span>
                  <span className="text-xs text-[#7A6B57]">
                    {genderOpen ? "닫기" : "선택"}
                  </span>
                </button>
                {genderOpen && (
                  <div className="absolute z-10 mt-2 max-h-52 w-full overflow-y-auto rounded-xl border border-[#E1D7C8] bg-white p-2 text-sm shadow-md">
                    {filterOptions.genders.map((gender) => (
                      <label
                        key={gender}
                        className="flex items-center gap-2 rounded-lg px-2 py-1.5 hover:bg-[#F5F2EA]"
                      >
                        <input
                          type="checkbox"
                          checked={selectedGenders.includes(gender)}
                          onChange={() =>
                            toggleSelection(
                              gender,
                              selectedGenders,
                              setSelectedGenders
                            )
                          }
                          className="accent-[#C8A24D]"
                        />
                        <span>{gender}</span>
                      </label>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="space-y-2 rounded-2xl border border-[#E6DDCF] bg-[#F8F4EC] p-4 text-xs text-[#4D463A]">
            <p>상태: {status}</p>
            {error && <p className="text-[#B13C2E]">오류: {error}</p>}
            {payload && (
              <>
                <p>향수: {visibleCounts.perfumes}개</p>
                <p>어코드: {visibleCounts.accords}개</p>
                <p>엣지: {visibleCounts.edges}개</p>
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