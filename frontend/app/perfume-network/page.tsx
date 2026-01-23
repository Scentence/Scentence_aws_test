"use client";

import "./vis-network.css";
import Link from "next/link";
import Script from "next/script";
import { useSession } from "next-auth/react";
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

const API_BASE =
  process.env.NEXT_PUBLIC_SCENTMAP_API_URL ??
  "http://127.0.0.1:8001";

// 분위기 계열별 기본 색상 매핑
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

const ACCORD_LABELS: Record<string, string> = {
  Animal: "애니멀",
  Aquatic: "아쿠아틱",
  Chypre: "시프레",
  Citrus: "시트러스",
  Creamy: "크리미",
  Earthy: "얼씨",
  Floral: "플로럴",
  "Foug\\u00e8re": "푸제르",
  Fougère: "푸제르",
  Fruity: "프루티",
  Gourmand: "구르망",
  Green: "그린",
  Leathery: "레더리",
  Oriental: "오리엔탈",
  Powdery: "파우더리",
  Resinous: "수지향",
  Smoky: "스모키",
  Spicy: "스파이시",
  Sweet: "스위트",
  Synthetic: "인공향",
  Woody: "우디",
  Fresh: "프레시",
};

const BRAND_LABELS: Record<string, string> = {
  "4711": "4711",
  "Acqua di Parma": "아쿠아 디 파르마",
  Amouage: "아무아주",
  "Ariana Grande": "아리아나 그란데",
  "Atelier Cologne": "아틀리에 코롱",
  Balenciaga: "발렌시아가",
  Bentley: "벤틀리",
  "Bond No 9": "본드 넘버 나인",
  "Bond No. 9": "본드 넘버 나인",
  BorntoStandOut: "본투스탠드아웃",
  "Bottega Veneta": "보테가 베네타",
  Boucheron: "부쉐론",
  Bulgari: "불가리",
  Burberry: "버버리",
  Byredo: "바이레도",
  "Calvin Klein": "캘빈 클라인",
  Celine: "셀린느",
  Chanel: "샤넬",
  Chloe: "끌로에",
  Clean: "클린",
  Clinique: "크리니크",
  Coach: "코치",
  Creed: "크리드",
  "D S  Durga": "디에스 앤 더가",
  Davidoff: "다비도프",
  Dior: "디올",
  Diptyque: "딥티크",
  "Dolce Gabbana": "돌체 가바나",
  "Estee Lauder": "에스티 로더",
  "Etat Libre D Orange": "에따 리브르 도랑쥬",
  "Etat Libre d Orange": "에따 리브르 도랑쥬",
  Ferrari: "페라리",
  Givenchy: "지방시",
  Goutal: "구탈",
  Gucci: "구찌",
  Guerlain: "겔랑",
  Hermes: "에르메스",
  "Hugo Boss": "휴고 보스",
  "Issey Miyake": "이세이 미야케",
  "Jean Paul Gaultier": "장 폴 고티에",
  "Jimmy Choo": "지미 추",
  "Jo Malone": "조 말론",
  "Jo Malone London": "조 말론 런던",
  "John Varvatos": "존 바바토스",
  Kenzo: "겐조",
  Kilian: "킬리안",
  "LArtisan Parfumeur": "라르티장 파퓸르",
  Lalique: "랄리크",
  Lancome: "랑콤",
  Lanvin: "랑방",
  "Lartisan Parfumeur": "라르티장 파퓸르",
  "Le Labo": "르 라보",
  "Loccitane En Provence": "록시땅 앙 프로방스",
  Loewe: "로에베",
  "Louis Vuitton": "루이 비통",
  Lush: "러쉬",
  "Maison Francis Kurkdjian": "메종 프란시스 커정",
  "Maison Margiela": "메종 마르지엘라",
  Mancera: "만세라",
  "Marc Jacobs": "마크 제이콥스",
  "Memo Paris": "메모 파리",
  "Mercedes Benz": "메르세데스 벤츠",
  "Michael Kors": "마이클 코어스",
  "Miller Harris": "밀러 해리스",
  "Miu Miu": "미우미우",
  Montale: "몽탈",
  Moschino: "모스키노",
  "Narciso Rodriguez": "나르시소 로드리게즈",
  Nishane: "니샤네",
  "Parfums de Marly": "파퓸 드 말리",
  "Penhaligon's": "펜할리곤스",
  Prada: "프라다",
  Rabanne: "라반",
  "Roja Parfums": "로자 퍼퓸",
  "Salvatore Ferragamo": "살바토레 페라가모",
  "Santa Maria Novella": "산타 마리아 노벨라",
  "Serge Lutens": "세르주 루텐",
  "The Body Shop": "더 바디샵",
  "Tiffany Co": "티파니",
  "Tiziana Terenzi": "티지아나 테렌치",
  "Tom Ford": "톰 포드",
  Valentino: "발렌티노",
  "Van Cleef Arpels": "반클리프 아펠",
  Versace: "베르사체",
  "Victoria S Secret": "빅토리아 시크릿",
  Xerjoff: "세르조프",
  "Yves Saint Laurent": "입생로랑",
  Zara: "자라",
};

const SEASON_LABELS: Record<string, string> = {
  Spring: "봄",
  Summer: "여름",
  Fall: "가을",
  Winter: "겨울",
};

const OCCASION_LABELS: Record<string, string> = {
  Business: "업무/비즈니스",
  Daily: "데일리",
  Evening: "저녁 모임",
  Leisure: "여가/휴식",
  "Night Out": "밤 외출",
  Sport: "운동",
};

const GENDER_TARGET_LABELS: Record<string, string> = {
  Feminine: "여성",
  Masculine: "남성",
  Unisex: "남녀 공용",
};

const hasKorean = (value: string) => /[ㄱ-ㅎ|ㅏ-ㅣ|가-힣]/.test(value);

const formatLabelWithEnglish = (
  value: string,
  labels?: Record<string, string>
) => {
  const trimmed = value.trim();
  if (!trimmed) return value;
  const mapped = labels?.[trimmed];
  if (mapped) return `${mapped} (${trimmed})`;
  if (hasKorean(trimmed)) return trimmed;
  return `${trimmed} (${trimmed})`;
};

// 등록 상태 라벨
const REGISTER_STATUS_LABELS: Record<string, string> = {
  HAVE: "보유",
  HAD: "보유했음",
  RECOMMENDED: "추천",
  WANT: "관심",
};

const REGISTER_STATUS_KEYS = Object.keys(REGISTER_STATUS_LABELS);
const MY_SHELF_STATUSES = ["HAVE", "HAD"];

const formatRegisterStatus = (status: string) =>
  REGISTER_STATUS_LABELS[status]
    ? `${REGISTER_STATUS_LABELS[status]} (${status})`
    : status;

export default function PerfumeNetworkPage() {
  const { data: session } = useSession();
  const sessionUserId = (
    session?.user as { id?: string | number } | undefined
  )?.id;
  // 네트워크 요청 파라미터
  const [minSimilarity, setMinSimilarity] = useState(0.85);
  const [topAccords, setTopAccords] = useState(2);
  const [maxPerfumes, setMaxPerfumes] = useState<string>("");
  const [memberId, setMemberId] = useState<string | null>(null);
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
  const [selectedRegisterStatuses, setSelectedRegisterStatuses] = useState<
    string[]
  >([]);
  const [myShelfOnly, setMyShelfOnly] = useState(false);
  const [hiddenPerfumeIds, setHiddenPerfumeIds] = useState<string[]>([]);
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
  const [registerStatusOpen, setRegisterStatusOpen] = useState(false);

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
    if (memberId) {
      params.set("member_id", memberId);
    }
    return `${API_BASE}/network/perfumes?${params.toString()}`;
  }, [minSimilarity, topAccords, maxPerfumes, memberId]);

  useEffect(() => {
    // 로그인 정보에서 memberId 로드
    if (sessionUserId) {
      setMemberId(String(sessionUserId));
      return;
    }
    if (typeof window === "undefined") return;
    const stored = localStorage.getItem("localAuth");
    if (!stored) return;
    try {
      const parsed = JSON.parse(stored) as { memberId?: number | string };
      if (parsed?.memberId) {
        setMemberId(String(parsed.memberId));
      }
    } catch (error) {
      return;
    }
  }, [sessionUserId]);

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

  const formatSelection = (
    values: string[],
    placeholder: string,
    formatValue: (value: string) => string = (value) => value
  ) => {
    if (values.length === 0) {
      return placeholder;
    }
    if (values.length === 1) {
      return formatValue(values[0]);
    }
    return `${formatValue(values[0])} 외 ${values.length - 1}`;
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
        registerStatuses: [] as string[],
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
    const registerStatusSet = new Set<string>();

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
      if (node.register_status) {
        registerStatusSet.add(node.register_status);
      }
    }

    return {
      accords: Array.from(accordSet).sort(),
      brands: Array.from(brandSet).sort(),
      seasons: Array.from(seasonSet).sort(),
      occasions: Array.from(occasionSet).sort(),
      genders: Array.from(genderSet).sort(),
      registerStatuses: Array.from(registerStatusSet).sort(),
    };
  }, [payload]);

  const selectablePerfumes = useMemo(() => {
    if (!payload) return [] as NetworkNode[];
    const statusSource =
      selectedRegisterStatuses.length > 0
        ? selectedRegisterStatuses
        : MY_SHELF_STATUSES;
    return payload.nodes.filter(
      (node) =>
        node.type === "perfume" &&
        node.register_status &&
        statusSource.includes(node.register_status)
    ) as NetworkNode[];
  }, [payload, selectedRegisterStatuses]);

  useEffect(() => {
    if (!payload) return;
    const validIds = new Set(payload.nodes.map((node) => node.id));
    setHiddenPerfumeIds((prev) => prev.filter((id) => validIds.has(id)));
  }, [payload]);

  // 선택된 필터를 기준으로 네트워크 노드/엣지 축소
  const filteredPayload = useMemo(() => {
    if (!payload) return null;

    const perfumeNodes = payload.nodes.filter(
      (node) => node.type === "perfume"
    ) as NetworkNode[];

    const matchesFilter = (node: NetworkNode) => {
      if (hiddenPerfumeIds.includes(node.id)) {
        return false;
      }
      // 대표 분위기 기준으로 필터링
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
      if (
        selectedRegisterStatuses.length > 0 &&
        (!node.register_status ||
          !selectedRegisterStatuses.includes(node.register_status))
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
    selectedRegisterStatuses,
    hiddenPerfumeIds,
  ]);

  const visiblePayload = filteredPayload ?? payload;

  const selectedPerfume = useMemo(() => {
    if (!visiblePayload || !selectedPerfumeId) return null;
    return (
      visiblePayload.nodes.find(
        (node) => node.type === "perfume" && node.id === selectedPerfumeId
      ) ?? null
    );
  }, [visiblePayload, selectedPerfumeId]);

  const similarPerfumes = useMemo(() => {
    if (!visiblePayload || !selectedPerfumeId) return [];
    const scoreById = new Map<string, number>();
    visiblePayload.edges
      .filter(
        (edge) =>
          edge.type === "SIMILAR_TO" &&
          (edge.from === selectedPerfumeId || edge.to === selectedPerfumeId)
      )
      .forEach((edge) => {
        const otherId = edge.from === selectedPerfumeId ? edge.to : edge.from;
        const nextScore = edge.weight ?? 0;
        const current = scoreById.get(otherId) ?? -1;
        if (nextScore > current) {
          scoreById.set(otherId, nextScore);
        }
      });

    const perfumeById = new Map(
      visiblePayload.nodes
        .filter((node) => node.type === "perfume")
        .map((node) => [node.id, node as NetworkNode])
    );

    return Array.from(scoreById.entries())
      .map(([id, score]) => ({
        perfume: perfumeById.get(id),
        score,
      }))
      .filter((item) => item.perfume)
      .sort((a, b) => b.score - a.score)
      .slice(0, 6) as { perfume: NetworkNode; score: number }[];
  }, [visiblePayload, selectedPerfumeId]);

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
        const statusLine = node.register_status
          ? `\n내 향수 상태: ${formatRegisterStatus(node.register_status)}`
          : "";
        return {
          id: node.id,
          label: node.label,
          shape: "circularImage",
          image: node.image || undefined,
          title: `${node.label}\n${
            node.brand ? formatLabelWithEnglish(node.brand, BRAND_LABELS) : ""
          }\n대표 분위기: ${
            node.primary_accord
              ? formatLabelWithEnglish(node.primary_accord, ACCORD_LABELS)
              : "알 수 없음"
          }${statusLine}`,
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
        title: formatLabelWithEnglish(accordLabel, ACCORD_LABELS),
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
          length: 280,
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
        length: 140,
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
        forceAtlas2Based: {
          gravitationalConstant: -70,
          springLength: 260,
          springConstant: 0.05,
          avoidOverlap: 1.5,
        },
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

  const toggleHiddenPerfume = (id: string) => {
    setHiddenPerfumeIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const handleMyShelfView = () => {
    if (!memberId) {
      setStatus("로그인 후 내 향수로 보기 버튼을 사용할 수 있어요.");
      return;
    }
    if (myShelfOnly) {
      setSelectedRegisterStatuses([]);
      setMyShelfOnly(false);
      setHiddenPerfumeIds([]);
      return;
    }
    setSelectedRegisterStatuses(MY_SHELF_STATUSES);
    setMyShelfOnly(true);
  };

  return (
    <div className="min-h-screen bg-[#F5F2EA] text-[#1F1F1F]">
      <Script
        src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"
        strategy="afterInteractive"
        onLoad={() => setScriptReady(true)}
      />

      <div className="max-w-6xl mx-auto px-6 py-12 space-y-8">
        <header className="flex flex-wrap items-center justify-between gap-4">
          <div className="space-y-2">
            <p className="text-xs uppercase tracking-[0.3em] text-[#7A6B57]">
              perfume network
            </p>
            <h1 className="text-3xl font-semibold">향수 지도</h1>
            <div className="space-y-1 text-sm text-[#5C5448]">
              <p>향수와 향수 사이의 닮음을 한눈에 보는 지도예요.</p>
              <p>향수의 대표 분위기를 중심으로 자연스럽게 연결돼 있어요.</p>
              <p>가까이 있는 향수일수록 비슷한 분위기를 가지고 있어요.</p>
            </div>
          </div>
          <Link href="/" className="rounded-full border border-[#E2D7C5] bg-white/80 px-4 py-2 text-xs font-semibold text-[#5C5448] transition hover:bg-white">
            메인으로
          </Link>
        </header>

        <section className="grid gap-6 lg:grid-cols-[340px_1fr]">
          <div className="space-y-6 rounded-3xl bg-white/80 border border-[#E2D7C5] p-6 shadow-sm">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <p className="text-sm font-semibold text-[#1F1F1F]">
                  지도 설정
                </p>
              </div>
              <label className="block text-xs text-[#7A6B57]">
                향수가 닮은 정도 ({minSimilarity.toFixed(2)})
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
                대표 분위기 표시 개수
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
                분위기 계열 (대표 분위기)
              </label>
              <div className="relative">
                <button
                  type="button"
                  onClick={() => setAccordOpen((prev) => !prev)}
                  className="flex w-full items-center justify-between rounded-xl border border-[#E1D7C8] bg-white px-3 py-2 text-sm text-[#1F1F1F] focus:outline-none focus:ring-2 focus:ring-[#C8A24D]/40"
                >
                  <span>
                    {formatSelection(
                      selectedAccords,
                      "전체",
                      (value) => formatLabelWithEnglish(value, ACCORD_LABELS)
                    )}
                  </span>
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
                            toggleSelection(
                              accord,
                              selectedAccords,
                              setSelectedAccords
                            )
                          }
                          className="accent-[#C8A24D]"
                        />
                        <span>{formatLabelWithEnglish(accord, ACCORD_LABELS)}</span>
                      </label>
                    ))}
                  </div>
                )}
              </div>

              <label className="block text-xs text-[#7A6B57] mt-4">
                비교해보고 싶은 향수 최대 개수
              </label>
              <input
                type="number"
                min="1"
                placeholder="전체 향수"
                value={maxPerfumes}
                onChange={(e) => setMaxPerfumes(e.target.value)}
                className="w-full rounded-xl border border-[#E1D7C8] bg-white px-3 py-2 text-sm text-[#1F1F1F] focus:outline-none focus:ring-2 focus:ring-[#C8A24D]/40"
              />
            </div>

            <div className="space-y-3 border-t border-[#E6DDCF] pt-4">
              <div className="flex items-center justify-between">
                <p className="text-sm font-semibold text-[#1F1F1F]">취향 상세</p>
                <button
                  type="button"
                  onClick={() => {
                    setSelectedAccords([]);
                    setSelectedBrands([]);
                    setSelectedSeasons([]);
                    setSelectedOccasions([]);
                    setSelectedGenders([]);
                    setSelectedRegisterStatuses([]);
                    setMyShelfOnly(false);
                    setHiddenPerfumeIds([]);
                  }}
                  className="text-[11px] text-[#7A6B57] hover:text-[#5C5448]"
                >
                  전체 초기화
                </button>
              </div>
              <div className="grid gap-2">
              <div className="relative">
                <button
                  type="button"
                  onClick={() => setBrandOpen((prev) => !prev)}
                  className="flex w-full items-center justify-between rounded-xl border border-[#E1D7C8] bg-white px-3 py-2 text-sm text-[#1F1F1F] focus:outline-none focus:ring-2 focus:ring-[#C8A24D]/40"
                >
                  <span>
                    {formatSelection(
                      selectedBrands,
                      "브랜드 전체",
                      (value) => formatLabelWithEnglish(value, BRAND_LABELS)
                    )}
                  </span>
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
                        <span>{formatLabelWithEnglish(brand, BRAND_LABELS)}</span>
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
                  <span>
                    {formatSelection(
                      selectedSeasons,
                      "계절감 전체",
                      (value) => formatLabelWithEnglish(value, SEASON_LABELS)
                    )}
                  </span>
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
                        <span>{formatLabelWithEnglish(season, SEASON_LABELS)}</span>
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
                  <span>
                    {formatSelection(
                      selectedOccasions,
                      "어울리는 상황 전체",
                      (value) => formatLabelWithEnglish(value, OCCASION_LABELS)
                    )}
                  </span>
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
                        <span>
                          {formatLabelWithEnglish(occasion, OCCASION_LABELS)}
                        </span>
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
                  <span>
                    {formatSelection(
                      selectedGenders,
                      "어울리는 대상 전체",
                      (value) => formatLabelWithEnglish(value, GENDER_TARGET_LABELS)
                    )}
                  </span>
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
                        <span>
                          {formatLabelWithEnglish(gender, GENDER_TARGET_LABELS)}
                        </span>
                      </label>
                    ))}
                  </div>
                )}
              </div>

              <div className="rounded-2xl border border-[#E6DDCF] bg-[#F8F4EC] p-3 text-xs text-[#5C5448]">
                <p className="font-semibold text-[#4D463A]">내 향수 관리</p>
                <p className="mt-1">
                  보유/보유했음 상태를 기준으로 내 향수만 모아서 볼 수 있어요.
                </p>
                <div className="relative mt-3">
                  <button
                    type="button"
                    onClick={() => setRegisterStatusOpen((prev) => !prev)}
                    className="flex w-full items-center justify-between rounded-xl border border-[#E1D7C8] bg-white px-3 py-2 text-sm text-[#1F1F1F] focus:outline-none focus:ring-2 focus:ring-[#C8A24D]/40"
                  >
                    <span>
                      {formatSelection(
                        selectedRegisterStatuses,
                        "내 향수 상태 전체",
                        formatRegisterStatus
                      )}
                    </span>
                    <span className="text-xs text-[#7A6B57]">
                      {registerStatusOpen ? "닫기" : "선택"}
                    </span>
                  </button>
                  {registerStatusOpen && (
                    <div className="absolute z-10 mt-2 w-full space-y-1 rounded-xl border border-[#E1D7C8] bg-white p-2 text-sm shadow-md">
                      <p className="px-2 text-[11px] text-[#7A6B57]">
                        로그인된 계정의 상태만 표시됩니다.
                      </p>
                      <div className="max-h-44 overflow-y-auto">
                        {filterOptions.registerStatuses.length === 0 && (
                          <p className="px-2 py-2 text-xs text-[#9A8E7C]">
                            로그인 후 내 향수 상태가 표시됩니다.
                          </p>
                        )}
                        {filterOptions.registerStatuses.map((statusKey) => (
                          <label
                            key={statusKey}
                            className="flex items-center gap-2 rounded-lg px-2 py-1.5 hover:bg-[#F5F2EA]"
                          >
                            <input
                              type="checkbox"
                              checked={selectedRegisterStatuses.includes(
                                statusKey
                              )}
                              onChange={() =>
                                toggleSelection(
                                  statusKey,
                                  selectedRegisterStatuses,
                                  setSelectedRegisterStatuses
                                )
                              }
                              className="accent-[#C8A24D]"
                            />
                            <span>{formatRegisterStatus(statusKey)}</span>
                          </label>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
                <button
                  type="button"
                  onClick={handleMyShelfView}
                  disabled={!memberId}
                  className={`mt-3 w-full rounded-xl px-4 py-2.5 text-sm font-semibold shadow-sm transition ${
                    memberId
                      ? "bg-[#2E2B28] text-white hover:bg-[#1E1C1A]"
                      : "bg-[#DAD2C6] text-[#8A7D6C] cursor-not-allowed"
                  }`}
                >
                  {myShelfOnly ? "전체 향수로 되돌리기" : "내 향수로 보기"}
                </button>
                {!memberId && (
                  <p className="mt-2 text-[11px] text-[#7A6B57]">
                    로그인 후 사용 가능합니다.
                  </p>
                )}
                {memberId &&
                  selectablePerfumes.length > 0 &&
                  (myShelfOnly || selectedRegisterStatuses.length > 0) && (
                  <div className="mt-3 rounded-xl border border-[#E1D7C8] bg-white p-2">
                    <p className="px-2 pb-1 text-[11px] text-[#7A6B57]">
                      내 향수 목록에서 보고 싶은 향수를 선택하세요.
                    </p>
                    <div className="max-h-40 overflow-y-auto">
                      {selectablePerfumes.map((perfume) => {
                        const isHidden = hiddenPerfumeIds.includes(perfume.id);
                        return (
                          <label
                            key={perfume.id}
                            className="flex items-start gap-2 rounded-lg px-2 py-1.5 text-sm hover:bg-[#F5F2EA]"
                          >
                            <input
                              type="checkbox"
                              checked={!isHidden}
                              onChange={() => toggleHiddenPerfume(perfume.id)}
                              className="mt-0.5 accent-[#C8A24D]"
                            />
                            <span className="space-y-0.5">
                              <span className="block text-[#1F1F1F]">
                                {perfume.label}
                              </span>
                              {perfume.brand && (
                                <span className="block text-[11px] text-[#7A6B57]">
                                  {formatLabelWithEnglish(
                                    perfume.brand,
                                    BRAND_LABELS
                                  )}
                                </span>
                              )}
                            </span>
                          </label>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="space-y-2 rounded-2xl border border-[#E6DDCF] bg-[#F8F4EC] p-4 text-xs text-[#4D463A]">
            <p className="font-semibold">지금 지도 정보</p>
            <p>상태: {status}</p>
            {error && <p className="text-[#B13C2E]">안내: {error}</p>}
            {payload && (
              <>
                <p>화면에 표시 중인 향수: {visibleCounts.perfumes}개</p>
                <p>화면에 표시 중인 분위기: {visibleCounts.accords}개</p>
                <p>연결선: {visibleCounts.edges}개</p>
                <p>데이터 준비 시간: {payload.meta.build_seconds}s</p>
              </>
            )}
          </div>

          <button
            onClick={handleReset}
            className="w-full rounded-xl bg-[#2E2B28] py-2.5 text-sm font-semibold text-white shadow-md transition hover:bg-[#1E1C1A]"
          >
            그래프 정렬하기
          </button>

          <div className="space-y-2 text-xs text-[#7A6B57]">
            <p>데이터 요청 주소 (문의/공유용)</p>
            <p className="break-all text-[#5C5448]">{lastRequest}</p>
          </div>
        </div>

        <div className="space-y-3">
          <div className="h-[70vh] rounded-3xl border border-[#E2D7C5] bg-white/90 p-4 shadow-sm">
            <div ref={containerRef} className="h-full w-full" />
          </div>
          <div className="rounded-2xl border border-[#E2D7C5] bg-white/90 p-4 text-xs text-[#7A6B57] shadow-sm">
            <div className="grid gap-4 md:grid-cols-[1.1fr_1fr]">
              <div className="space-y-1">
                <p className="font-semibold text-[#4D463A]">그래프 읽는 법</p>
                <p>
                  원형 사진은 향수, 작은 점은 분위기예요. 점선은 향수와 분위기의
                  연결, 실선은 향수끼리 닮은 정도를 뜻해요.
                </p>
                <p>
                  실선이 두껍고 진할수록 더 닮았고, 가까이 모인 향수일수록 같은
                  분위기를 공유해요.
                </p>
                <p>
                  실선이 연결되지 않은 향수는 현재 닮음 기준을 넘지 않아 표시되지
                  않은 상태예요.
                </p>
              </div>

              <div className="space-y-2">
                <p className="font-semibold text-[#4D463A]">선택한 향수</p>
                {selectedPerfume ? (
                  <div className="space-y-2">
                    <div>
                      <p className="text-sm font-semibold text-[#1F1F1F]">
                        {selectedPerfume.label}
                      </p>
                      {selectedPerfume.brand && (
                        <p className="text-[11px] text-[#7A6B57]">
                          {formatLabelWithEnglish(
                            selectedPerfume.brand,
                            BRAND_LABELS
                          )}
                        </p>
                      )}
                      <p className="text-[11px] text-[#7A6B57]">
                        대표 분위기:{" "}
                        {selectedPerfume.primary_accord
                          ? formatLabelWithEnglish(
                              selectedPerfume.primary_accord,
                              ACCORD_LABELS
                            )
                          : "알 수 없음"}
                      </p>
                    </div>

                    <div className="space-y-1">
                      <p className="font-semibold text-[#4D463A]">
                        유사한 향수
                      </p>
                      {similarPerfumes.length > 0 ? (
                        <div className="max-h-32 space-y-1 overflow-y-auto pr-2">
                          {similarPerfumes.map(({ perfume, score }) => (
                            <div
                              key={perfume.id}
                              className="flex items-start justify-between gap-2 rounded-lg bg-[#F8F4EC] px-2 py-1"
                            >
                              <div>
                                <p className="text-[11px] text-[#1F1F1F]">
                                  {perfume.label}
                                </p>
                                {perfume.brand && (
                                  <p className="text-[10px] text-[#7A6B57]">
                                    {formatLabelWithEnglish(
                                      perfume.brand,
                                      BRAND_LABELS
                                    )}
                                  </p>
                                )}
                              </div>
                              <span className="text-[10px] text-[#5C5448]">
                                유사도 {Math.round(score * 100)}%
                              </span>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-[11px] text-[#7A6B57]">
                          이 향수와 연결된 유사한 향수가 없어요.
                        </p>
                      )}
                    </div>
                  </div>
                ) : (
                  <p className="text-[11px] text-[#7A6B57]">
                    그래프에서 향수를 클릭하면 유사한 향수 목록이 보여요.
                  </p>
                )}
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
    </div>
  );
}