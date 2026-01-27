"use client";

import "./vis-network.css";
import Link from "next/link";
import Script from "next/script";
import { useSession } from "next-auth/react";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  API_CONFIG,
  GRAPH_CONFIG,
  ACCORD_LABELS,
  ACCORD_DESCRIPTIONS,
  ACCORD_ICONS,
  BRAND_LABELS,
  SEASON_LABELS,
  OCCASION_LABELS,
  GENDER_TARGET_LABELS,
  getAccordColor,
  hexToRgba,
} from "./config";
import CardTriggerBanner from "@/components/perfume-network/CardTriggerBanner";
import LoadingOverlay from "@/components/perfume-network/LoadingOverlay";
import ScentCardModal from "@/components/perfume-network/ScentCardModal";

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
  register_status?: string | null;
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

type LabelsData = {
  perfume_names: Record<string, string>;
  brands: Record<string, string>;
  accords: Record<string, string>;
  seasons: Record<string, string>;
  occasions: Record<string, string>;
  genders: Record<string, string>;
};

const API_BASE = API_CONFIG.BASE_URL;
const DEFAULT_ACCORDS = ["Floral", "Woody", "Citrus", "Fresh", "Spicy"];

// 세션 API URL
const SESSION_API_BASE = API_BASE; // scentmap 서비스 사용

export default function PerfumeNetworkPage() {
  const { data: session } = useSession();
  const sessionUserId = (
    session?.user as { id?: string | number } | undefined
  )?.id;

  // API 응답 데이터
  const [fullPayload, setFullPayload] = useState<NetworkPayload | null>(null);
  const [labelsData, setLabelsData] = useState<LabelsData | null>(null);
  const [filterOptions, setFilterOptions] = useState<{
    accords: string[];
    brands: string[];
    seasons: string[];
    occasions: string[];
    genders: string[];
  }>({
    accords: [],
    brands: [],
    seasons: [],
    occasions: [],
    genders: [],
  });
  const [status, setStatus] = useState("대기 중");
  const [scriptReady, setScriptReady] = useState(false);
  
  // 클라이언트 사이드 필터링 파라미터 (즉시 반응)
  const [minSimilarity, setMinSimilarity] = useState<number>(
    GRAPH_CONFIG.MIN_SIMILARITY_DEFAULT
  );
  const [topAccords, setTopAccords] = useState<number>(
    GRAPH_CONFIG.TOP_ACCORDS_DEFAULT
  );
  
  // 1단계: 어코드 선택 (기본값: 대중적인 어코드들)
  const [selectedAccords, setSelectedAccords] =
    useState<string[]>(DEFAULT_ACCORDS);
  
  // 2단계: 세부 필터 (선택)
  const [selectedBrands, setSelectedBrands] = useState<string[]>([]);
  const [selectedSeasons, setSelectedSeasons] = useState<string[]>([]);
  const [selectedOccasions, setSelectedOccasions] = useState<string[]>([]);
  const [selectedGenders, setSelectedGenders] = useState<string[]>([]);
  
  // 3단계: 향수 선택
  const [selectedPerfumeId, setSelectedPerfumeId] = useState<string | null>(null);

  const BRANDS_PER_PAGE = 20;
  const [brandPage, setBrandPage] = useState(1);
  
  // 유사 향수 호버 상태
  const [hoveredSimilarPerfumeId, setHoveredSimilarPerfumeId] = useState<string | null>(null);
  
  // UI 상태
  const [freezeMotion, setFreezeMotion] = useState(false);
  const [memberId, setMemberId] = useState<string | null>(null);
  const [memberIdReady, setMemberIdReady] = useState(false);
  const [isDetailFilterOpen, setIsDetailFilterOpen] = useState(false);
  const [isAccordFilterOpen, setIsAccordFilterOpen] = useState(true); // 분위기 필터 펼침 상태 (기본: 열림)
  const [displayLimit, setDisplayLimit] = useState<number>(10); // 그래프에 표시할 향수 개수
  const [showMyPerfumesOnly, setShowMyPerfumesOnly] = useState(false);
  const [showLoginPrompt, setShowLoginPrompt] = useState(false);

  // 세션 및 카드 생성 상태
  const [scentSessionId, setScentSessionId] = useState<string | null>(null);
  const [showCardTrigger, setShowCardTrigger] = useState(false);
  const [triggerMessage, setTriggerMessage] = useState("");
  const [isGeneratingCard, setIsGeneratingCard] = useState(false);
  const [showCardModal, setShowCardModal] = useState(false);
  const [generatedCard, setGeneratedCard] = useState<any>(null);

  // vis-network 참조
  const containerRef = useRef<HTMLDivElement>(null);
  const networkRef = useRef<any>(null);
  const nodesDataRef = useRef<any>(null);
  const edgesDataRef = useRef<any>(null);

  // API URL 생성 (최초 1회만 - 전체 데이터 로드용)
  const requestUrl = useMemo(() => {
    const params = new URLSearchParams({
      min_similarity: "0.0",
      top_accords: "5"
    });
    if (memberId) {
      params.set("member_id", memberId);
    }
    return `${API_BASE}/network/perfumes?${params.toString()}`;
  }, [memberId]);

  // 로그인 정보 로드
  useEffect(() => {
    if (sessionUserId) {
      setMemberId(String(sessionUserId));
      setMemberIdReady(true);
      return;
    }
    if (typeof window === "undefined") return;
    const stored = localStorage.getItem("localAuth");
    if (!stored) {
      setMemberIdReady(true);
      return;
    }
    try {
      const parsed = JSON.parse(stored) as { memberId?: number | string };
      if (parsed?.memberId) {
        setMemberId(String(parsed.memberId));
      }
      setMemberIdReady(true);
    } catch (error) {
      setMemberIdReady(true);
      return;
    }
  }, [sessionUserId]);

  // 세션 시작 (향수맵 진입 시)
  useEffect(() => {
    if (!memberIdReady) return;
    
    const startScentSession = async () => {
      try {
        const response = await fetch(`${SESSION_API_BASE}/session/start`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ member_id: memberId ? Number(memberId) : null }),
        });
        
        if (response.ok) {
          const data = await response.json();
          setScentSessionId(data.session_id);
          console.log("✅ 세션 시작:", data.session_id);
        }
      } catch (error) {
        console.warn("⚠️ 세션 시작 실패:", error);
      }
    };
    
    startScentSession();
  }, [memberIdReady, memberId]);

  // 활동 로깅 함수
  const logActivity = async (data: {
    accord_selected?: string;
    perfume_id?: number;
    reaction?: string;
  }) => {
    if (!scentSessionId) return;
    
    try {
      const response = await fetch(
        `${SESSION_API_BASE}/session/${scentSessionId}/activity`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(data),
        }
      );
      
      if (response.ok) {
        const result = await response.json();
        
        // 카드 생성 조건 충족 체크
        if (result.card_trigger_ready && !showCardTrigger) {
          setShowCardTrigger(true);
          setTriggerMessage(result.trigger_message || "지금까지 탐색한 향으로 향기카드를 만들어볼까요?");
        }
      }
    } catch (error) {
      console.warn("⚠️ 활동 로깅 실패:", error);
    }
  };

  // 카드 생성 함수
  const handleGenerateCard = async () => {
    if (!scentSessionId) return;
    
    setShowCardTrigger(false);
    setIsGeneratingCard(true);
    
    try {
      const response = await fetch(
        `${SESSION_API_BASE}/session/${scentSessionId}/generate-card`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
        }
      );
      
      if (response.ok) {
        const data = await response.json();
        setGeneratedCard(data.card);
        setShowCardModal(true);
        console.log("✅ 카드 생성 성공:", data);
      } else {
        const error = await response.json();
        alert(`카드 생성 실패: ${error.detail || "알 수 없는 오류"}`);
      }
    } catch (error) {
      console.error("❌ 카드 생성 에러:", error);
      alert("카드 생성 중 오류가 발생했습니다. 다시 시도해주세요.");
    } finally {
      setIsGeneratingCard(false);
    }
  };

  // 라벨 데이터 로딩
  useEffect(() => {
    const fetchLabels = async () => {
      try {
        const res = await fetch(`${API_BASE}/labels`);
        if (!res.ok) return;
        const data = await res.json() as LabelsData;
        setLabelsData(data);
      } catch (err) {
        console.warn("⚠️ 라벨 로드 오류:", err);
      }
    };
    fetchLabels();
  }, []);

  // 필터 옵션 로딩
  useEffect(() => {
    const fetchFilterOptions = async () => {
      try {
        const res = await fetch(`${API_BASE}/network/filter-options`);
        if (!res.ok) return;
        const data = await res.json();
        setFilterOptions(data);
      } catch (err) {
        console.warn("⚠️ 필터 옵션 로드 오류:", err);
      }
    };
    fetchFilterOptions();
  }, []);

  // 전체 데이터 로딩
  useEffect(() => {
    if (!memberIdReady) return;
    const controller = new AbortController();
    const fetchData = async () => {
      setStatus("전체 데이터 로드 중...");
      try {
        const res = await fetch(requestUrl, { signal: controller.signal });
        if (!res.ok) throw new Error("서버 오류");
        const data = await res.json();
        setFullPayload(data);
        setStatus("준비 완료");
      } catch (err) {
        if (err instanceof DOMException && err.name === "AbortError") {
          return;
        }
        setStatus("로드 실패");
      }
    };
    
    fetchData();
    return () => controller.abort();
  }, [requestUrl, memberIdReady, memberId]);

  // 헬퍼: 영문명 병기 포맷터
  const formatLabelWithEnglishPair = (value: string, formatter: (v: string) => string) => {
    const korean = formatter(value);
    return korean === value ? value : `${korean} (${value})`;
  };

  // 라벨 포맷터들
  const fmtAccord = (v: string) => {
    const trimmed = v.trim();
    // 푸제르의 다양한 표기 처리
    if (trimmed === "Fougère" || trimmed === "Foug\\u00e8re" || trimmed.includes("Foug")) {
      return "푸제르";
    }
    return labelsData?.accords[trimmed] || ACCORD_LABELS[trimmed] || v;
  };
  const fmtBrand = (v: string) => labelsData?.brands[v.trim()] || BRAND_LABELS[v.trim()] || v;
  const fmtSeason = (v: string) => labelsData?.seasons[v.trim()] || SEASON_LABELS[v.trim()] || v;
  const fmtOccasion = (v: string) => labelsData?.occasions[v.trim()] || OCCASION_LABELS[v.trim()] || v;
  const fmtGender = (v: string) => labelsData?.genders[v.trim()] || GENDER_TARGET_LABELS[v.trim()] || v;
  const getStatusBadge = (status?: string | null) => {
    if (!status) return null;
    const normalized = status.trim().toUpperCase();
    const map: Record<string, { label: string; className: string }> = {
      HAVE: { label: "보유", className: "bg-[#E8F0FF] text-[#3B5CC9]" },
      WANT: { label: "위시", className: "bg-[#FFE8EE] text-[#C24B6B]" },
      HAD: { label: "과거", className: "bg-[#F2F2F2] text-[#7A6B57]" },
      RECOMMENDED: { label: "추천", className: "bg-[#E8F6EC] text-[#2F7D4C]" },
    };
    const matched = map[normalized];
    if (matched) return matched;
    // 실제 값 그대로 표시 (정확한 매핑 보장)
    return { label: normalized, className: "bg-[#F8F4EC] text-[#8A7C68]" };
  };


  const myPerfumeIds = useMemo(() => {
    if (!fullPayload) return new Set<string>();
    // [개선] 내 향수 기준 ID 세트를 미리 파생
    return new Set(
      fullPayload.nodes
        .filter((n): n is NetworkNode => n.type === "perfume" && !!n.register_status)
        .map((n) => n.id)
    );
  }, [fullPayload]);

  const myPerfumeFilters = useMemo(() => {
    if (!fullPayload) return null;
    const myPerfumes = fullPayload.nodes.filter(
      (n): n is NetworkNode => n.type === "perfume" && !!n.register_status
    );
    const accordSet = new Set<string>();
    const brandSet = new Set<string>();
    const seasonSet = new Set<string>();
    const occasionSet = new Set<string>();
    const genderSet = new Set<string>();

    myPerfumes.forEach((p) => {
      if (p.primary_accord) accordSet.add(p.primary_accord);
      (p.accords || []).forEach((acc) => accordSet.add(acc));
      if (p.brand) brandSet.add(p.brand);
      (p.seasons || []).forEach((s) => seasonSet.add(s));
      (p.occasions || []).forEach((o) => occasionSet.add(o));
      (p.genders || []).forEach((g) => genderSet.add(g));
    });

    return {
      accords: Array.from(accordSet),
      brands: Array.from(brandSet),
      seasons: Array.from(seasonSet),
      occasions: Array.from(occasionSet),
      genders: Array.from(genderSet),
    };
  }, [fullPayload]);

  const effectiveFilterOptions = useMemo(() => {
    if (!showMyPerfumesOnly) return filterOptions;
    // [개선] 내 향수 전용 보기에서는 필터 옵션도 내 향수 기준으로 제한
    return (
      myPerfumeFilters ?? {
        accords: [],
        brands: [],
        seasons: [],
        occasions: [],
        genders: [],
      }
    );
  }, [showMyPerfumesOnly, filterOptions, myPerfumeFilters]);

  // 클라이언트 필터링 로직
  const filteredPayload = useMemo(() => {
    if (!fullPayload) return null;
    
    // [개선] 내 향수 보기 활성화 시 내 향수 범위로 먼저 제한
    const perfumeNodes = fullPayload.nodes.filter((n): n is NetworkNode => {
      if (n.type !== "perfume") return false;
      if (showMyPerfumesOnly && !myPerfumeIds.has(n.id)) return false;
      return true;
    });
    const visiblePerfumeNodes = perfumeNodes.filter(node => {
      if (selectedAccords.length > 0 && (!node.primary_accord || !selectedAccords.includes(node.primary_accord))) return false;
      if (selectedBrands.length > 0 && (!node.brand || !selectedBrands.includes(node.brand))) return false;
      if (selectedSeasons.length > 0 && !selectedSeasons.some(s => node.seasons?.includes(s))) return false;
      if (selectedOccasions.length > 0 && !selectedOccasions.some(o => node.occasions?.includes(o))) return false;
      if (selectedGenders.length > 0 && !selectedGenders.some(g => node.genders?.includes(g))) return false;
      return true;
    });
    
    const visibleIds = new Set(visiblePerfumeNodes.map(n => n.id));
    const filteredEdges: NetworkEdge[] = [];
    const accordMap = new Map<string, Array<{to: string, weight: number}>>();

    fullPayload.edges.forEach(edge => {
      if (edge.type === "SIMILAR_TO") {
        if (visibleIds.has(edge.from) && visibleIds.has(edge.to) && (edge.weight ?? 0) >= minSimilarity) {
          filteredEdges.push(edge);
        }
      } else if (edge.type === "HAS_ACCORD" && visibleIds.has(edge.from)) {
        if (!accordMap.has(edge.from)) accordMap.set(edge.from, []);
        accordMap.get(edge.from)!.push({ to: edge.to, weight: edge.weight ?? 0 });
      }
    });

    // 선택한 어코드 ID 세트
    const selectedAccordIds = new Set(
      selectedAccords.map(acc => `accord_${acc}`)
    );

    // 향수별 어코드 엣지 추가 (선택한 어코드만)
    accordMap.forEach((accords, perfumeId) => {
      accords
        .sort((a, b) => b.weight - a.weight)
        .slice(0, topAccords)
        .filter(acc => selectedAccordIds.has(acc.to)) // 선택한 어코드만
        .forEach(acc => {
          filteredEdges.push({ from: perfumeId, to: acc.to, type: "HAS_ACCORD", weight: acc.weight });
        });
    });
    
    // 엣지에 연결된 어코드만 노드로 포함
    const activeAccordIds = new Set(
      filteredEdges
        .filter(e => e.type === "HAS_ACCORD")
        .map(e => e.to)
    );
    
    const finalNodes = fullPayload.nodes.filter(n => 
      (n.type === "perfume" && visibleIds.has(n.id)) || 
      (n.type === "accord" && activeAccordIds.has(n.id))
    );

    return { nodes: finalNodes, edges: filteredEdges, meta: fullPayload.meta };
  }, [fullPayload, minSimilarity, topAccords, selectedAccords, selectedBrands, selectedSeasons, selectedOccasions, selectedGenders, showMyPerfumesOnly, myPerfumeIds]);

  useEffect(() => {
    if (!showMyPerfumesOnly || !myPerfumeFilters) return;
    setSelectedAccords(myPerfumeFilters.accords);
    setSelectedBrands(myPerfumeFilters.brands);
    setSelectedSeasons(myPerfumeFilters.seasons);
    setSelectedOccasions(myPerfumeFilters.occasions);
    setSelectedGenders(myPerfumeFilters.genders);
  }, [showMyPerfumesOnly, myPerfumeFilters]);

  // 선택 향수 어코드 비중
  const selectedPerfumeAccordWeights = useMemo(() => {
    if (!fullPayload || !selectedPerfumeId) return new Map<string, number>();
    const weights = new Map<string, number>();
    fullPayload.edges.forEach(e => {
      if (e.type === "HAS_ACCORD" && e.from === selectedPerfumeId) {
        weights.set(e.to.replace("accord_", ""), e.weight ?? 0);
      }
    });
    return weights;
  }, [fullPayload, selectedPerfumeId]);

  // 유사 향수 목록 탐색 (필터된 범위 내에서만 계산)
  const similarPerfumes = useMemo(() => {
    if (!filteredPayload || !selectedPerfumeId) return [];
    
    const scoreMap = new Map<string, number>();
    // [개선] 내 향수 보기/필터 적용 범위 내에서만 유사도 계산
    filteredPayload.edges.forEach(e => {
      if (e.type === "SIMILAR_TO") {
        if (e.from === selectedPerfumeId) scoreMap.set(e.to, e.weight ?? 0);
        else if (e.to === selectedPerfumeId) scoreMap.set(e.from, e.weight ?? 0);
      }
    });

    const perfumeMap = new Map(
      filteredPayload.nodes
        .filter(n => n.type === "perfume")
        .map(n => [n.id, n as NetworkNode])
    );
    const selected = perfumeMap.get(selectedPerfumeId);
    if (!selected) return [];

    return Array.from(scoreMap.entries())
      .map(([id, score]) => {
        const p = perfumeMap.get(id);
        if (!p) return null;
        const common = (selected.accords || []).filter(a => (p.accords || []).includes(a));
        const added = (p.accords || []).filter(a => !(selected.accords || []).includes(a));
        return { perfume: p, score, commonAccords: common, newAccords: added };
      })
      .filter((x): x is NonNullable<typeof x> => x !== null)
      .sort((a, b) => b.score - a.score)
      .slice(0, 5);
  }, [filteredPayload, selectedPerfumeId]);

  const top5SimilarIds = useMemo(() => new Set(similarPerfumes.map(s => s.perfume.id)), [similarPerfumes]);

  // 그래프 표시용 (displayLimit 적용하되 선택된 향수와 유사 향수는 항상 포함)
  const displayPayload = useMemo(() => {
    if (!filteredPayload) return null;
    
    const allPerfumes = filteredPayload.nodes.filter(n => n.type === "perfume");
    
    // 선택된 향수와 유사 향수 ID 수집
    const mustIncludeIds = new Set<string>();
    if (selectedPerfumeId) {
      mustIncludeIds.add(selectedPerfumeId);
      top5SimilarIds.forEach(id => mustIncludeIds.add(id));
    }
    
    // [개선] 필수 포함 향수도 필터 범위 내에서만 수집
    const mustIncludePerfumes: NetworkNode[] = allPerfumes.filter(p => mustIncludeIds.has(p.id));
    
    const otherPerfumes = allPerfumes.filter(p => !mustIncludeIds.has(p.id));
    
    // displayLimit 엄격히 적용
    let perfumes: NetworkNode[];
    if (mustIncludePerfumes.length >= displayLimit) {
      perfumes = mustIncludePerfumes.slice(0, displayLimit);
    } else {
      const remainingSlots = displayLimit - mustIncludePerfumes.length;
      perfumes = [...mustIncludePerfumes, ...otherPerfumes.slice(0, remainingSlots)];
    }
    
    const perfumeIds = new Set(perfumes.map(p => p.id));
    
    // [개선] 엣지는 필터 범위 내에서만 수집
    const edges = filteredPayload.edges.filter(e => {
      if (e.type === "SIMILAR_TO") {
        return perfumeIds.has(e.from) && perfumeIds.has(e.to);
      }
      return e.type === "HAS_ACCORD" && perfumeIds.has(e.from);
    });
    
    // 엣지에 연결된 어코드만 노드로 포함
    const accordIds = new Set(edges.filter(e => e.type === "HAS_ACCORD").map(e => e.to));
    const accords = filteredPayload.nodes.filter(n => n.type === "accord" && accordIds.has(n.id));
    
    return { nodes: [...accords, ...perfumes], edges };
  }, [filteredPayload, displayLimit, selectedPerfumeId, top5SimilarIds]);

  // vis-network 렌더링 및 인터랙션 설정
  useEffect(() => {
    if (!scriptReady || !displayPayload || !containerRef.current) return;
    const vis = (window as any).vis ?? (window as any).visNetwork;
    if (!vis || typeof vis.Network !== "function" || typeof vis.DataSet !== "function") {
      console.warn("⚠️ vis-network 로드 실패");
      return;
    }

    const nodes = displayPayload.nodes.map(n => {
      if (n.type === "perfume") {
        const isSel = n.id === selectedPerfumeId;
        const isSim = top5SimilarIds.has(n.id);
        const isHov = n.id === hoveredSimilarPerfumeId;
        const isBlur = !!selectedPerfumeId && !isSel && !isSim && !isHov;
        const border = getAccordColor(n.primary_accord);
        
        // 그래프 노드 호버 툴팁 생성 (간결한 정보)
        // 이 향수의 어코드 비중 정보 (상위 5개)
        const perfumeAccordWeights = new Map<string, number>();
        if (fullPayload) {
          fullPayload.edges.forEach(e => {
            if (e.type === "HAS_ACCORD" && e.from === n.id) {
              perfumeAccordWeights.set(e.to.replace("accord_", ""), e.weight ?? 0);
            }
          });
        }
        const topAccordsText = Array.from(perfumeAccordWeights.entries())
          .sort((a, b) => b[1] - a[1])
          .slice(0, 5)
          .map(([acc, weight]) => `${fmtAccord(acc)} ${Math.round(weight * 100)}%`)
          .join(", ");
        
        const statusBadge = getStatusBadge(n.register_status);
        const statusText = statusBadge ? `내 향수 상태: ${statusBadge.label}` : "";
        const tooltipText = `${n.label}\n${fmtBrand(n.brand || "")}${statusText ? `\n${statusText}` : ""}${topAccordsText ? `\n${topAccordsText}` : ""}`;

        return {
          id: n.id,
          label: isHov || isSel ? n.label : "",
          title: tooltipText,
          shape: "circularImage",
          image: n.image,
          size: isSel ? 40 : (isSim || isHov ? 32 : (isBlur ? 20 : 26)),
          borderWidth: isSel ? 8 : (isHov ? 7 : (isBlur ? 1 : 4)),
          color: { 
            border: isHov ? "#FFD700" : (isSel ? border : hexToRgba(border, isBlur ? 0.08 : 1)), 
            background: isBlur ? "rgba(255, 251, 243, 0.15)" : "#FFFBF3" 
          },
          opacity: isBlur ? 0.08 : 1,
          font: { size: isSel ? 14 : 12, bold: true, background: "white", color: isSel ? "#C8A24D" : "#2E2B28" },
          fixed: isSel ? { x: true, y: true } : false, // 선택된 향수는 중앙 고정
          x: isSel ? 0 : undefined,
          y: isSel ? 0 : undefined,
          level: isSel ? 0 : (isSim ? 1 : 2) // 계층 설정
        };
      }
      // 어코드 노드
      const isHigh = !selectedPerfumeId || displayPayload.edges.some(e => e.type === "HAS_ACCORD" && e.to === n.id && (e.from === selectedPerfumeId || top5SimilarIds.has(e.from)));
      const isBlurAccord = selectedPerfumeId && !isHigh;
      const accordDesc = ACCORD_DESCRIPTIONS[n.label] || "";
      const accordTooltip = `${fmtAccord(n.label)}\n${accordDesc}`;
      return {
        id: n.id,
        label: isBlurAccord ? "" : fmtAccord(n.label),
        title: accordTooltip,
        shape: "dot",
        size: isHigh ? 24 : (isBlurAccord ? 12 : 18),
        color: { background: hexToRgba(getAccordColor(n.label), isHigh ? 0.7 : (isBlurAccord ? 0.03 : 0.1)) },
        font: { size: isHigh ? 12 : 10, bold: isHigh },
        opacity: isBlurAccord ? 0.15 : 1,
        level: -1, // 어코드는 최상단
        mass: 5 // 어코드는 무겁게
      };
    });

    const edges = displayPayload.edges.map(e => {
      // SIMILAR_TO 엣지는 완전히 숨김
      if (e.type === "SIMILAR_TO") {
        return {
          from: e.from, 
          to: e.to, 
          value: e.weight,
          hidden: true, // 모든 유사 엣지 숨김
          color: { color: "#C8A24D", opacity: 0 },
          width: 0,
          dashes: false,
          smooth: { type: "continuous" }
        };
      }
      // HAS_ACCORD 엣지는 선택된 향수와 관련된 것만 약하게 표시, 나머지는 완전히 숨김
      const isFromSelected = selectedPerfumeId && (e.from === selectedPerfumeId || top5SimilarIds.has(e.from));
      const isBlurEdge = selectedPerfumeId && !isFromSelected;
      return {
        from: e.from, 
        to: e.to, 
        value: e.weight,
        hidden: isBlurEdge, // 관련 없는 엣지는 숨김
        color: { color: "#9C8D7A", opacity: isFromSelected ? 0.3 : (isBlurEdge ? 0 : 0.08) },
        width: isFromSelected ? 1.2 : (isBlurEdge ? 0 : 0.4),
        dashes: true,
        smooth: { type: "continuous" }
      };
    });

    if (!networkRef.current) {
      nodesDataRef.current = new vis.DataSet(nodes);
      edgesDataRef.current = new vis.DataSet(edges);
      try {
        const options: any = {
          interaction: { hover: true, navigationButtons: true, tooltipDelay: 200 },
          physics: { 
            enabled: !freezeMotion, 
            solver: "forceAtlas2Based", 
            forceAtlas2Based: { 
              gravitationalConstant: selectedPerfumeId ? -260 : -140, 
              centralGravity: selectedPerfumeId ? 0.03 : 0.01,
              springLength: selectedPerfumeId ? 320 : 240, 
              springConstant: selectedPerfumeId ? 0.02 : 0.04,
              damping: 0.9,
              avoidOverlap: 2.5 
            },
            stabilization: {
              enabled: true,
              iterations: 200
            }
          }
        };
        if (selectedPerfumeId) {
          options.layout = { hierarchical: { enabled: false } };
        }
        networkRef.current = new vis.Network(
          containerRef.current,
          { nodes: nodesDataRef.current, edges: edgesDataRef.current },
          options
        );
      } catch (err) {
        console.warn("⚠️ vis-network 초기화 실패:", err);
        return;
      }
      networkRef.current.on("click", (p: any) => {
        const nodeId = p.nodes[0];
        if (nodeId && !nodeId.startsWith("accord_")) {
          setSelectedPerfumeId(nodeId);
          // 향수 클릭 로깅 (관심 표시)
          const perfumeIdNum = nodeId.match(/\d+/)?.[0];
          if (perfumeIdNum) {
            logActivity({ 
              perfume_id: Number(perfumeIdNum), 
              reaction: "interested" 
            });
          }
        } else {
          setSelectedPerfumeId(null);
        }
      });
      networkRef.current.once("stabilizationIterationsDone", () => {
        if (!freezeMotion) {
          networkRef.current?.setOptions({ physics: { enabled: false } });
        }
      });
    } else {
      // 노드와 엣지를 완전히 새로 설정 (추가/삭제가 제대로 반영되도록)
      // 기존 노드와 새 노드 비교
      const currentNodeIds = new Set(nodesDataRef.current.getIds() as string[]);
      const newNodeIds = new Set(nodes.map(n => n.id));
      
      // 삭제할 노드 (기존에 있었지만 새로운 데이터에 없는 것)
      const nodesToRemove = Array.from(currentNodeIds).filter(id => !newNodeIds.has(id));
      if (nodesToRemove.length > 0) {
        nodesDataRef.current.remove(nodesToRemove);
      }
      
      // 추가/업데이트할 노드
      nodesDataRef.current.update(nodes);
      
      // 엣지는 완전히 새로 설정 (구조가 복잡하므로)
      edgesDataRef.current.clear();
      edgesDataRef.current.add(edges);
      
      // 선택된 향수가 있으면 중앙에 배치
      if (selectedPerfumeId) {
        try {
          networkRef.current.moveNode(selectedPerfumeId, 0, 0);
        } catch (e) {
          // 노드가 아직 렌더링되지 않은 경우 무시
        }
      }
      
      // physics 설정 동적 업데이트
      const updatedOptions: any = {
        physics: { 
          enabled: !freezeMotion, 
          solver: "forceAtlas2Based", 
          forceAtlas2Based: { 
            gravitationalConstant: selectedPerfumeId ? -260 : -140, 
            centralGravity: selectedPerfumeId ? 0.03 : 0.01,
            springLength: selectedPerfumeId ? 320 : 240, 
            springConstant: selectedPerfumeId ? 0.02 : 0.04,
            damping: 0.9,
            avoidOverlap: 2.5
          },
          stabilization: {
            enabled: true,
            iterations: 200
          }
        }
      };
      if (selectedPerfumeId) {
        updatedOptions.layout = { hierarchical: { enabled: false } };
      }
      networkRef.current.setOptions(updatedOptions);
      if (!freezeMotion) {
        networkRef.current.stabilize(200);
        networkRef.current.once("stabilizationIterationsDone", () => {
          networkRef.current?.setOptions({ physics: { enabled: false } });
        });
      }
    }
  }, [scriptReady, displayPayload, selectedPerfumeId, freezeMotion, hoveredSimilarPerfumeId, fullPayload, top5SimilarIds]);

  const totalPages = Math.ceil(effectiveFilterOptions.brands.length / BRANDS_PER_PAGE) || 1;
  const safeBrandPage = Math.min(brandPage, totalPages);
  const visibleBrands = effectiveFilterOptions.brands.slice((safeBrandPage - 1) * BRANDS_PER_PAGE, safeBrandPage * BRANDS_PER_PAGE);

  return (
    <div className="min-h-screen bg-[#F5F2EA] text-[#1F1F1F]">
      <Script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js" strategy="afterInteractive" onLoad={() => setScriptReady(true)} />
      
      <div className="max-w-7xl mx-auto px-6 py-12 space-y-12">
        <header className="flex items-center justify-between pb-8 border-b-2 border-[#E6DDCF]">
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-[#7A6B57]">perfume network</p>
            <h1 className="text-4xl font-semibold mt-2">향수 지도</h1>
            <p className="text-sm text-[#5C5448] mt-3">비슷하면서도 다른, 향수 지도로 새로운 취향을 발견해보세요.</p>
          </div>
          <Link href="/" className="h-10 px-6 flex items-center justify-center rounded-full border border-[#E2D7C5] bg-white text-[13px] font-semibold hover:bg-[#F8F4EC]">메인으로</Link>
        </header>

        {/* 1단계: 분위기 필터 (어코드) */}
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold">어떤 분위기를 원하세요?</h2>
              <p className="text-xs text-[#7A6B57]">관심 있는 분위기를 선택해 원하는 향수를 찾아보세요.</p>
            </div>
            <div className="flex gap-2">
              <button onClick={() => setIsAccordFilterOpen(!isAccordFilterOpen)} className="h-9 px-4 rounded-full border border-[#E2D7C5] bg-white text-xs font-semibold">{isAccordFilterOpen ? "▲ 접기" : "▼ 펼치기"}</button>
            </div>
          </div>
          
          {isAccordFilterOpen && (
            <div className="grid grid-cols-4 sm:grid-cols-5 md:grid-cols-7 lg:grid-cols-10 gap-3">
              {effectiveFilterOptions.accords.map(acc => (
                <button key={acc} onClick={() => { 
                  const newAccords = selectedAccords.includes(acc) ? selectedAccords.filter(a => a !== acc) : [...selectedAccords, acc];
                  setSelectedAccords(newAccords); 
                  setSelectedPerfumeId(null); 
                  // 어코드 선택 로깅
                  if (!selectedAccords.includes(acc)) {
                    logActivity({ accord_selected: acc });
                  }
                }}
                  className={`relative aspect-square rounded-2xl border-2 transition-all ${selectedAccords.includes(acc) ? "border-[#C8A24D] bg-[#C8A24D]/10" : "border-[#E2D7C5] bg-white"}`}>
                  <div className="absolute inset-0 flex flex-col items-center justify-center p-2">
                    <span className="text-2xl mb-1">{ACCORD_ICONS[acc] || "✨"}</span>
                    <span className="text-[10px] font-semibold text-center">{fmtAccord(acc)}</span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </section>

        {/* 2단계: 세부 필터 (브랜드, 계절감, 상황, 성별) */}
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold">더 꼼꼼하게 찾아보고 싶다면</h2>
              <p className="text-xs text-[#7A6B57]">브랜드와 계절, 특별한 순간을 더해 나만의 취향을 더 선명하게 찾아보세요.</p>
            </div>
            <button onClick={() => setIsDetailFilterOpen(!isDetailFilterOpen)} className="h-9 px-4 rounded-full border border-[#E2D7C5] bg-white text-xs font-semibold">{isDetailFilterOpen ? "▲ 접기" : "▼ 펼치기"}</button>
          </div>
          
          {isDetailFilterOpen && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {[
                { label: "브랜드", options: visibleBrands, selected: selectedBrands, setter: setSelectedBrands, formatter: fmtBrand, isBrand: true },
                { label: "계절감", options: effectiveFilterOptions.seasons, selected: selectedSeasons, setter: setSelectedSeasons, formatter: fmtSeason },
                { label: "어울리는 상황", options: effectiveFilterOptions.occasions, selected: selectedOccasions, setter: setSelectedOccasions, formatter: fmtOccasion },
                { label: "어울리는 성별", options: effectiveFilterOptions.genders, selected: selectedGenders, setter: setSelectedGenders, formatter: fmtGender }
              ].map((group, i) => (
                <div key={i} className="flex flex-col gap-2">
                  <div className="flex justify-between items-center">
                    <label className="text-xs font-semibold text-[#4D463A]">{group.label}</label>
                    <button onClick={() => { group.setter([]); setSelectedPerfumeId(null); }} className="text-[10px] text-[#7A6B57]">초기화</button>
                  </div>
                  <div className="h-48 flex flex-col rounded-xl border border-[#E1D7C8] bg-white p-2">
                    <div className="flex-1 overflow-y-auto">
                      {group.options.map(opt => (
                        <label key={opt} className="flex items-center gap-2 px-2 py-1.5 hover:bg-[#F5F2EA] text-sm cursor-pointer">
                          <input type="checkbox" checked={group.selected.includes(opt)} onChange={() => { group.setter(prev => prev.includes(opt) ? prev.filter(v => v !== opt) : [...prev, opt]); setSelectedPerfumeId(null); }} className="accent-[#C8A24D]" />
                          <span className="text-xs">{formatLabelWithEnglishPair(opt, group.formatter)}</span>
                        </label>
                      ))}
                    </div>
                    {group.isBrand && totalPages > 1 && (
                      <div className="flex justify-between items-center px-2 pt-2 border-t border-[#F5F2EA]">
                        <button onClick={() => setBrandPage(p => Math.max(1, p - 1))} disabled={safeBrandPage === 1} className="text-[10px] disabled:opacity-30">이전</button>
                        <span className="text-[10px]">{safeBrandPage}/{totalPages}</span>
                        <button onClick={() => setBrandPage(p => Math.min(totalPages, p + 1))} disabled={safeBrandPage === totalPages} className="text-[10px] disabled:opacity-30">다음</button>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        <div className="border-t-2 border-[#E6DDCF]"></div>

        {/* 3단계: 그래프 및 탐색 상세 정보 */}
        <section className="space-y-4">
          {/* 그래프 섹션 제목 */}
          <div>
            <h2 className="text-lg font-semibold">향수 지도</h2>
            <p className="text-xs text-[#7A6B57]">궁금한 향수를 클릭하면, 유사한 향수가 나타나요.</p>
          </div>

          <div className="grid gap-6 lg:grid-cols-[1fr_340px]">
            {/* 왼쪽: 그래프 영역 및 컨트롤러 */}
            <div className="space-y-3">
              <div className="rounded-2xl border border-[#E6DDCF] bg-white/80 p-5 space-y-5">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                  <div className="space-y-2">
                    <div className="flex justify-between items-center gap-2">
                      <div className="flex items-center gap-1.5">
                        <label className="text-[13px] font-bold">1. 표시할 향수 개수</label>
                        <div className="group relative">
                          <button className="w-4 h-4 rounded-full bg-[#E6DDCF] text-[#7A6B57] text-[10px] font-bold hover:bg-[#C8A24D] hover:text-white transition-colors flex items-center justify-center">
                            ?
                          </button>
                          <div className="absolute left-1/2 -translate-x-1/2 bottom-full mb-2 hidden group-hover:block z-50 w-64">
                            <div className="bg-[#2E2B28] text-white text-xs rounded-lg p-3 shadow-lg">
                              <p className="font-semibold mb-1">표시할 향수 개수</p>
                              <p className="text-[11px] leading-relaxed">
                                필터로 발견한 향수 중 그래프에 표시할 개수를 선택합니다. <span className="text-[#C8A24D] font-semibold">10~20개 정도를 권장해요.</span> 너무 많으면 화면이 복잡해집니다.
                              </p>
                            </div>
                          </div>
                        </div>
                      </div>
                      <span className="text-sm font-bold text-[#C8A24D]">{displayLimit}개</span>
                    </div>
                    <input 
                      type="range" 
                      min="1" 
                      max={Math.min(100, filteredPayload ? filteredPayload.nodes.filter(n => n.type === "perfume").length : 100)} 
                      value={displayLimit} 
                      onChange={e => setDisplayLimit(Number(e.target.value))} 
                      className="w-full h-1.5 accent-[#C8A24D]" 
                    />
                  </div>
                  <div className="space-y-2">
                    <div className="flex justify-between items-center gap-2">
                      <div className="flex items-center gap-1.5">
                        <label className="text-[13px] font-bold">2. 분위기 닮은 정도</label>
                        <div className="group relative">
                          <button className="w-4 h-4 rounded-full bg-[#E6DDCF] text-[#7A6B57] text-[10px] font-bold hover:bg-[#C8A24D] hover:text-white transition-colors flex items-center justify-center">
                            ?
                          </button>
                          <div className="absolute left-1/2 -translate-x-1/2 bottom-full mb-2 hidden group-hover:block z-50 w-64">
                            <div className="bg-[#2E2B28] text-white text-xs rounded-lg p-3 shadow-lg">
                              <p className="font-semibold mb-1">유사도 임계값</p>
                              <p className="text-[11px] leading-relaxed">
                                향수 간 분위기의 비슷한 정도로 <span className="text-[#C8A24D] font-semibold">0.65 이상을 권장해요.</span>
                              </p>
                            </div>
                          </div>
                        </div>
                      </div>
                      <span className="text-sm font-bold text-[#C8A24D]">{minSimilarity.toFixed(2)}</span>
                    </div>
                    <input type="range" min="0" max="1" step="0.05" value={minSimilarity} onChange={e => setMinSimilarity(Number(e.target.value))} className="w-full h-1.5 accent-[#C8A24D]" />
                  </div>
                </div>
                <div className="flex justify-between items-center pt-4 border-t border-[#E6DDCF]">
                  <span className="text-xs text-[#7A6B57]">
                    {filteredPayload ? filteredPayload.nodes.filter(n => n.type === "perfume").length : 0}개 향수 발견 
                    <span className="mx-1">•</span> 
                    {displayLimit}개 표시 중
                  </span>
                  <div className="flex gap-2">
                    <button onClick={() => networkRef.current?.fit()} className="h-9 px-4 rounded-full border border-[#E2D7C5] bg-white text-xs font-semibold">화면 맞춤</button>
                    <button onClick={() => setFreezeMotion(!freezeMotion)} className="h-9 px-4 rounded-full border border-[#E2D7C5] bg-white text-xs font-semibold">{freezeMotion ? "움직임 재개" : "움직임 멈춤"}</button>
                    <button
                      onClick={() => {
                        if (!memberId) {
                          setShowLoginPrompt(true);
                          return;
                        }
                        setSelectedPerfumeId(null);
                        setShowMyPerfumesOnly(prev => !prev);
                      }}
                      className={`h-9 px-4 rounded-full text-xs font-semibold border transition ${
                        showMyPerfumesOnly
                          ? "bg-[#C8A24D] text-white border-[#C8A24D]"
                          : "bg-white text-[#7A6B57] border-[#E2D7C5] hover:bg-[#F8F4EC]"
                      }`}
                      title={memberId ? "내 향수 보기" : "로그인이 필요해요"}
                    >
                      {showMyPerfumesOnly ? "전체 향수 보기" : "내 향수 보기"}
                    </button>
                    {!memberId && (
                      <span className="self-center text-[10px] text-[#9C8D7A]">로그인 필요</span>
                    )}
                  </div>
                </div>
              </div>
              
              <div className="h-[70vh] rounded-3xl border border-[#E2D7C5] bg-white/90 p-4 relative overflow-hidden">
                {!fullPayload && (
                  <div className="absolute inset-0 bg-white/50 backdrop-blur-sm z-10 flex flex-col items-center justify-center gap-4">
                    <div className="w-10 h-10 border-4 border-[#C8A24D] border-t-transparent rounded-full animate-spin"></div>
                    <p className="text-sm font-medium text-[#7A6B57]">{status}</p>
                  </div>
                )}
                <div ref={containerRef} className="h-full w-full" />
              </div>
            </div>

            {/* 오른쪽: 향수 상세 패널 */}
            <div className="rounded-3xl bg-white/80 border border-[#E2D7C5] p-6 min-h-[400px]">
              {selectedPerfumeId && filteredPayload ? (() => {
                const p = filteredPayload.nodes.find(n => n.id === selectedPerfumeId);
                // 어코드 정보 생성
                const accordEntries = Array.from(selectedPerfumeAccordWeights.entries()).sort((a,b) => b[1]-a[1]);
                const primaryAccord = accordEntries[0]?.[0];
                const accordList = accordEntries.slice(0, 5).map(([acc, _]) => acc);
                const accordText = accordList.map((acc, idx) => 
                  idx === 0 ? `${fmtAccord(acc)}(대표)` : fmtAccord(acc)
                ).join(", ");
                const statusBadge = getStatusBadge(p?.register_status);
                
                // 선택한 분위기 중 이 향수에 포함된 것들 찾기
                const matchedAccords = selectedAccords.filter(acc => 
                  accordList.map(a => a.toLowerCase()).includes(acc.toLowerCase())
                );
                
                // 선택하지 않은 어코드 (새로운 분위기)
                const unmatchedAccords = accordList.filter(acc => 
                  !matchedAccords.some(m => m.toLowerCase() === acc.toLowerCase())
                );
                
                return (
                  <div className="space-y-5">
                    {/* 선택한 향수 소개 */}
                    <div>
                      <div className="flex items-center gap-2 mb-3">
                        <p className="text-sm text-[#7A6B57]">
                          <span className="font-bold text-[#C8A24D] text-lg">{p?.label}</span> 향수를 선택하셨어요.
                        </p>
                        {statusBadge && (
                          <span className={`text-[10px] px-2 py-0.5 rounded-full font-semibold ${statusBadge.className}`}>
                            {statusBadge.label}
                          </span>
                        )}
                      </div>
                      
                      <div className="space-y-2 text-sm leading-relaxed text-[#2E2B28]">
                        {matchedAccords.length > 0 && (
                          <p>
                            이 향수는 선택하신 <span className="font-bold text-[#C8A24D]">{matchedAccords.map(fmtAccord).join(", ")}</span>가 포함되어 있고
                            {unmatchedAccords.length > 0 && (
                              <> <span className="font-semibold text-[#5C5448]">{unmatchedAccords.slice(0, 3).map(fmtAccord).join(", ")}</span>도 포함되어 있어요.</>
                            )}
                          </p>
                        )}
                        {matchedAccords.length === 0 && accordText && (
                          <p>
                            이 향수는 <span className="font-semibold text-[#5C5448]">{accordText}</span> 로 구성되어 있어요.
                          </p>
                        )}
                      </div>
                    </div>

                    <div className="border-t border-[#E6DDCF] pt-6 space-y-4">
                      <p className="text-sm font-semibold text-[#4D463A]">유사한 향수 Top3</p>
                      {similarPerfumes.length > 0 ? (
                        <div className="space-y-3">
                          {similarPerfumes.slice(0, 3).map(({ perfume, score, commonAccords, newAccords }, idx) => {
                            // 추천 향수의 어코드 정보 가져오기
                            const perfumeAccords = perfume.accords || [];
                            const accordsText = perfumeAccords.slice(0, 4).map(fmtAccord).join(", ");
                            const newAccordsText = newAccords.length > 0 
                              ? newAccords.slice(0, 2).map(fmtAccord).join(", ")
                              : "";
                            
                            return (
                              <div key={perfume.id} 
                                className="p-4 rounded-2xl border border-[#E6DDCF] bg-white hover:border-[#C8A24D] transition-all cursor-pointer group hover:shadow-md"
                                onMouseEnter={() => setHoveredSimilarPerfumeId(perfume.id)} 
                                onMouseLeave={() => setHoveredSimilarPerfumeId(null)}>
                                <div className="flex justify-between items-start mb-3">
                                  <div className="space-y-1">
                                    <span className="text-sm font-bold group-hover:text-[#C8A24D] transition-colors block">{perfume.label}</span>
                                    <div className="flex items-center gap-2">
                                      <span className="text-[10px] text-[#7A6B57]">{fmtBrand(perfume.brand || "")}</span>
                                      {getStatusBadge(perfume.register_status) && (
                                        <span className={`text-[10px] px-2 py-0.5 rounded-full font-semibold ${getStatusBadge(perfume.register_status)!.className}`}>
                                          {getStatusBadge(perfume.register_status)!.label}
                                        </span>
                                      )}
                                    </div>
                                  </div>
                                  <span className="text-[10px] font-bold text-[#C8A24D] bg-[#C8A24D]/10 px-2 py-1 rounded-md whitespace-nowrap ml-2">
                                    유사도 {Math.round(score * 100)}%
                                  </span>
                                </div>
                                
                                <p className="text-xs text-[#2E2B28] leading-relaxed">
                                  <span className="font-bold text-[#C8A24D]">{perfume.label}</span>은(는){" "}
                                  {accordsText && (
                                    <><span className="font-semibold text-[#5C5448]">{accordsText}</span> 로 구성되어있</>
                                  )}
                                  {newAccordsText ? (
                                    <>지만 <span className="font-semibold text-[#C8A24D]">{newAccordsText}</span> 새로운 분위기도 느낄 수 있는 향수에요.</>
                                  ) : (
                                    <>어 비슷한 분위기를 즐길 수 있는 향수에요.</>
                                  )}
                                </p>
                              </div>
                            );
                          })}
                        </div>
                      ) : (
                        <div className="py-8 text-center bg-[#F8F4EC]/50 rounded-2xl border border-dashed border-[#E6DDCF]">
                          <p className="text-xs text-[#7A6B57]">비슷한 향수를 찾을 수 없어요.<br/>닮은 정도를 조금 낮춰보세요.</p>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })() : (
                <div className="h-full flex flex-col items-center justify-center text-center py-12 space-y-4">
                  <div className="w-16 h-16 rounded-full bg-[#F8F4EC] flex items-center justify-center text-3xl">✨</div>
                  <div>
                    <h3 className="text-lg font-semibold mb-1 text-[#C8A24D]">궁금한 향수를 클릭해보세요</h3>
                  </div>
                </div>
              )}
            </div>
          </div>
        </section>
      </div>
      {showLoginPrompt && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-center justify-center p-6">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm p-6 text-center space-y-4">
            <div className="text-3xl">🔒</div>
            <h3 className="text-lg font-semibold text-[#2E2B28]">로그인이 필요해요</h3>
            <p className="text-xs text-[#7A6B57]">
              내 향수로 보기는 회원 전용 기능입니다. 로그인 후 더 편하게 이용할 수 있어요.
            </p>
            <div className="flex gap-2">
              <Link href="/login" className="flex-1 h-9 rounded-full bg-[#C8A24D] text-white text-xs font-semibold flex items-center justify-center">
                로그인하러 가기
              </Link>
              <button
                onClick={() => setShowLoginPrompt(false)}
                className="flex-1 h-9 rounded-full border border-[#E2D7C5] text-xs font-semibold"
              >
                닫기
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 카드 제안 배너 */}
      {showCardTrigger && (
        <CardTriggerBanner
          message={triggerMessage}
          onAccept={handleGenerateCard}
          onDismiss={() => setShowCardTrigger(false)}
        />
      )}

      {/* 로딩 오버레이 */}
      {isGeneratingCard && (
        <LoadingOverlay message="당신의 취향을 분석하고 있어요..." />
      )}

      {/* 카드 결과 모달 */}
      {showCardModal && generatedCard && (
        <ScentCardModal
          card={generatedCard}
          onClose={() => {
            setShowCardModal(false);
            setGeneratedCard(null);
          }}
          onSave={() => {
            // TODO: 카드 저장 API 호출
            alert("카드가 저장되었습니다!");
          }}
          onContinueExplore={() => {
            setShowCardModal(false);
            setGeneratedCard(null);
            // 탐색 계속
          }}
        />
      )}
    </div>
  );
}
