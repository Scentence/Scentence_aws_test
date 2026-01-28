import { useState, useEffect, useMemo, useRef } from "react";
import { 
  NetworkPayload, 
  LabelsData, 
  FilterOptions, 
  NetworkNode, 
  NetworkEdge 
} from "./types";
import { API_CONFIG, GRAPH_CONFIG } from "../config";

const API_BASE = API_CONFIG.BASE_URL;
const DEFAULT_ACCORDS = ["Floral", "Woody", "Citrus", "Fresh", "Spicy"];
const SESSION_API_BASE = API_BASE;

export function usePerfumeNetwork(sessionUserId?: string | number) {
  // API 응답 데이터
  const [fullPayload, setFullPayload] = useState<NetworkPayload | null>(null);
  const [labelsData, setLabelsData] = useState<LabelsData | null>(null);
  const [filterOptions, setFilterOptions] = useState<FilterOptions>({
    accords: [],
    brands: [],
    seasons: [],
    occasions: [],
    genders: [],
  });
  const [status, setStatus] = useState("대기 중");
  
  // 클라이언트 사이드 필터링 파라미터
  const [minSimilarity, setMinSimilarity] = useState<number>(
    GRAPH_CONFIG.MIN_SIMILARITY_DEFAULT
  );
  const [topAccords, setTopAccords] = useState<number>(
    GRAPH_CONFIG.TOP_ACCORDS_DEFAULT
  );
  
  const [selectedAccords, setSelectedAccords] = useState<string[]>(DEFAULT_ACCORDS);
  const [selectedBrands, setSelectedBrands] = useState<string[]>([]);
  const [selectedSeasons, setSelectedSeasons] = useState<string[]>([]);
  const [selectedOccasions, setSelectedOccasions] = useState<string[]>([]);
  const [selectedGenders, setSelectedGenders] = useState<string[]>([]);
  const [selectedPerfumeId, setSelectedPerfumeId] = useState<string | null>(null);

  const [memberId, setMemberId] = useState<string | null>(null);
  const [memberIdReady, setMemberIdReady] = useState(false);
  const [displayLimit, setDisplayLimit] = useState<number>(10);
  const [showMyPerfumesOnly, setShowMyPerfumesOnly] = useState(false);

  // 세션 및 카드 생성 상태
  const [scentSessionId, setScentSessionId] = useState<string | null>(null);
  const [showCardTrigger, setShowCardTrigger] = useState(false);
  const [triggerMessage, setTriggerMessage] = useState("");
  const [isGeneratingCard, setIsGeneratingCard] = useState(false);
  const [showCardModal, setShowCardModal] = useState(false);
  const [generatedCard, setGeneratedCard] = useState<any>(null);
  const [generatedCardId, setGeneratedCardId] = useState<string | null>(null);
  const [cardTriggerReady, setCardTriggerReady] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 1. 로그인 정보 로드
  useEffect(() => {
    if (sessionUserId) {
      setMemberId(String(sessionUserId));
      setMemberIdReady(true);
      return;
    }
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
    } catch (e) {
      setMemberIdReady(true);
    }
  }, [sessionUserId]);

  // 2. 세션 시작
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
        }
      } catch (e) {
        console.warn("⚠️ 세션 시작 실패:", e);
      }
    };
    
    startScentSession();
  }, [memberIdReady, memberId]);

  // 3. 활동 로깅
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
        setCardTriggerReady(result.card_trigger_ready);
        if (result.card_trigger_ready && !showCardTrigger) {
          setShowCardTrigger(true);
          setTriggerMessage(result.trigger_message || "지금까지 탐색한 향으로 향기카드를 만들어볼까요?");
        }
      }
    } catch (e) {
      console.warn("⚠️ 활동 로깅 실패:", e);
    }
  };

  // 4. 카드 생성
  const handleGenerateCard = async () => {
    if (!scentSessionId) return;
    setShowCardTrigger(false);
    setIsGeneratingCard(true);
    setError(null);
    
    try {
      const response = await fetch(`${SESSION_API_BASE}/session/${scentSessionId}/generate-card`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      
      if (response.ok) {
        const data = await response.json();
        if (!data.card) throw new Error("카드 데이터가 없습니다.");
        
        const cardId = data.card_id || data.card.card_id;
        if (!cardId) throw new Error("카드 ID가 없습니다.");

        setGeneratedCard(data.card);
        setGeneratedCardId(String(cardId));
        setShowCardModal(true);
      } else {
        const errData = await response.json().catch(() => ({ detail: "알 수 없는 오류" }));
        setError(errData.detail || "카드 생성에 실패했습니다.");
      }
    } catch (e: any) {
      setError(e.message || "카드 생성 중 오류가 발생했습니다.");
    } finally {
      setIsGeneratingCard(false);
    }
  };

  // 5. 라벨 및 필터 옵션 로드
  useEffect(() => {
    const fetchLabels = async () => {
      try {
        const res = await fetch(`${API_BASE}/labels`);
        if (res.ok) setLabelsData(await res.json());
      } catch (e) {}
    };
    const fetchFilters = async () => {
      try {
        const res = await fetch(`${API_BASE}/network/filter-options`);
        if (res.ok) setFilterOptions(await res.json());
      } catch (e) {}
    };
    fetchLabels();
    fetchFilters();
  }, []);

  // 6. 전체 데이터 로드
  const requestUrl = useMemo(() => {
    const params = new URLSearchParams({ min_similarity: "0.0", top_accords: "5" });
    if (memberId) params.set("member_id", memberId);
    return `${API_BASE}/network/perfumes?${params.toString()}`;
  }, [memberId]);

  useEffect(() => {
    if (!memberIdReady) return;
    const controller = new AbortController();
    const fetchData = async () => {
      setStatus("전체 데이터 로드 중...");
      try {
        const res = await fetch(requestUrl, { signal: controller.signal });
        if (res.ok) {
          setFullPayload(await res.json());
          setStatus("준비 완료");
        }
      } catch (e) {
        if (e instanceof DOMException && e.name === "AbortError") return;
        setStatus("로드 실패");
      }
    };
    fetchData();
    return () => controller.abort();
  }, [requestUrl, memberIdReady]);

  // 7. 내 향수 필터 파생
  const myPerfumeIds = useMemo(() => {
    if (!fullPayload) return new Set<string>();
    return new Set(fullPayload.nodes.filter(n => n.type === "perfume" && !!n.register_status).map(n => n.id));
  }, [fullPayload]);

  const myPerfumeFilters = useMemo(() => {
    if (!fullPayload) return null;
    const myPerfumes = fullPayload.nodes.filter(n => n.type === "perfume" && !!n.register_status);
    const sets = {
      accords: new Set<string>(),
      brands: new Set<string>(),
      seasons: new Set<string>(),
      occasions: new Set<string>(),
      genders: new Set<string>(),
    };
    myPerfumes.forEach(p => {
      if (p.primary_accord) sets.accords.add(p.primary_accord);
      p.accords?.forEach(a => sets.accords.add(a));
      if (p.brand) sets.brands.add(p.brand);
      p.seasons?.forEach(s => sets.seasons.add(s));
      p.occasions?.forEach(o => sets.occasions.add(o));
      p.genders?.forEach(g => sets.genders.add(g));
    });
    return {
      accords: Array.from(sets.accords),
      brands: Array.from(sets.brands),
      seasons: Array.from(sets.seasons),
      occasions: Array.from(sets.occasions),
      genders: Array.from(sets.genders),
    };
  }, [fullPayload]);

  // 내 향수 보기 모드일 때 자동 필터 적용
  useEffect(() => {
    if (!showMyPerfumesOnly || !myPerfumeFilters) return;
    setSelectedAccords(myPerfumeFilters.accords);
    setSelectedBrands(myPerfumeFilters.brands);
    setSelectedSeasons(myPerfumeFilters.seasons);
    setSelectedOccasions(myPerfumeFilters.occasions);
    setSelectedGenders(myPerfumeFilters.genders);
  }, [showMyPerfumesOnly, myPerfumeFilters]);

  return {
    fullPayload,
    labelsData,
    filterOptions,
    status,
    minSimilarity, setMinSimilarity,
    topAccords, setTopAccords,
    selectedAccords, setSelectedAccords,
    selectedBrands, setSelectedBrands,
    selectedSeasons, setSelectedSeasons,
    selectedOccasions, setSelectedOccasions,
    selectedGenders, setSelectedGenders,
    selectedPerfumeId, setSelectedPerfumeId,
    memberId,
    displayLimit, setDisplayLimit,
    showMyPerfumesOnly, setShowMyPerfumesOnly,
    scentSessionId,
    showCardTrigger, setShowCardTrigger,
    triggerMessage,
    isGeneratingCard,
    showCardModal, setShowCardModal,
    generatedCard, setGeneratedCard,
    generatedCardId, setGeneratedCardId,
    cardTriggerReady,
    error, setError,
    logActivity,
    handleGenerateCard,
    myPerfumeIds,
    myPerfumeFilters,
  };
}
