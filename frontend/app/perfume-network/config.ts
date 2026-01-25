// 향수 네트워크 설정

// API 설정
export const API_CONFIG = {
  BASE_URL: process.env.NEXT_PUBLIC_SCENTMAP_API_URL ?? "http://127.0.0.1:8001",
  CACHE_VERSION: "v2.0", // 데이터 구조 변경 시 버전 업데이트
  CACHE_EXPIRY_HOURS: 24, // 캐시 만료 시간 (24시간)
} as const;

// 그래프 설정
export const GRAPH_CONFIG = {
  // API 파라미터 (필터링용)
  MIN_SIMILARITY_DEFAULT: 0.65, // 유사도 임계값 기본값 (0.0 ~ 1.0)
  MIN_SIMILARITY_MIN: 0.0, // 유사도 최소값
  MIN_SIMILARITY_MAX: 1.0, // 유사도 최대값
  MIN_SIMILARITY_STEP: 0.05, // 유사도 조절 단위
  
  TOP_ACCORDS_DEFAULT: 3, // 향수당 표시할 어코드 수 기본값
  TOP_ACCORDS_MIN: 1, // 어코드 최소 개수
  TOP_ACCORDS_MAX: 5, // 어코드 최대 개수
  
  API_MAX_PERFUMES: null, // API에서 가져올 최대 향수 개수 (null = 전체)
  
  // 물리 엔진 설정
  PHYSICS: {
    STABILIZATION_ITERATIONS: 150, // 안정화 반복 횟수
    UPDATE_INTERVAL: 25, // 업데이트 간격 (ms)
    MIN_VELOCITY: 0.01, // 최소 속도 (더 작게 = 더 빨리 안정화)
    MAX_VELOCITY: 0.3, // 최대 속도 (더 작게 = 부드러운 움직임)
    GRAVITATIONAL_CONSTANT: -50, // 중력 상수 (작게 = 노드들이 더 가까이)
    SPRING_LENGTH: 80, // 스프링 길이 (짧게 = 어코드 근처에 향수 배치)
    SPRING_CONSTANT: 0.08, // 스프링 상수 (강하게 = 구조 유지)
    DAMPING: 0.95, // 감쇠 계수 (높게 = 빠른 안정화)
    AVOID_OVERLAP: 1.0, // 겹침 방지
  },
  
  // 노드 크기 설정
  NODE_SIZE: {
    PERFUME: {
      DEFAULT: 24,
      SIMILAR: 26,
      SELECTED: 28,
    },
    ACCORD: {
      DEFAULT: 18,      // 향수보다 작게
      HIGHLIGHTED: 22,  // 강조시에도 향수보다 작게
    },
  },
  
  // 노드 질량 설정
  NODE_MASS: {
    PERFUME: 0.8, // 가볍게 (어코드 주변으로 끌림)
    ACCORD: 15, // 무겁게 (중심 유지)
  },
  
  // 애니메이션 설정
  ANIMATION: {
    FOCUS_SCALE: 1.5,
    FOCUS_OFFSET_X: -100,
    FOCUS_OFFSET_Y: 0,
    FOCUS_DURATION: 600,
    FIT_DURATION: 400,
  },
} as const;

// 분위기 계열별 기본 색상 매핑
export const ACCORD_COLORS: Record<string, string> = {
  Animal: "#7A5C3E",
  Aquatic: "#5FBED7",
  Chypre: "#3F6F5E",
  Citrus: "#E6E04A",
  Creamy: "#F1E8D6",
  Earthy: "#AD868B",
  Floral: "#F6B3C6",
  "Foug\\u00e8re": "#6F7A4A",
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

export const ACCORD_ICONS: Record<string, string> = {
  Animal: "🦁",
  Aquatic: "🌊",
  Chypre: "🍃",
  Citrus: "🍊",
  Creamy: "🥛",
  Earthy: "🌍",
  Floral: "🌸",
  "Foug\\u00e8re": "🌿",
  Fougère: "🌿",
  Fruity: "🍓",
  Gourmand: "🍰",
  Green: "🌱",
  Leathery: "👜",
  Oriental: "🌺",
  Powdery: "💨",
  Resinous: "🍯",
  Smoky: "💨",
  Spicy: "🌶️",
  Sweet: "🍬",
  Synthetic: "🔬",
  Woody: "🌲",
  Fresh: "💨",
};

export const ACCORD_LABELS: Record<string, string> = {
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

export const ACCORD_DESCRIPTIONS: Record<string, string> = {
  Animal: "관능적이고 야성적인 매력, 은은한 무스크와 암브레트의 깊이",
  Aquatic: "시원하고 청량한 물결, 바다와 빗소리가 주는 맑은 느낌",
  Chypre: "우아하고 세련된 클래식, 모스와 베르가못의 조화로운 깊이",
  Citrus: "상쾌하고 생동감 넘치는 활력, 레몬과 오렌지의 밝은 에너지",
  Creamy: "부드럽고 포근한 감촉, 바닐라와 산달우드의 따스한 포옹",
  Earthy: "자연 그대로의 흙내음, 이끼와 뿌리가 주는 안정감",
  Floral: "화사하고 우아한 꽃의 향연, 로즈와 재스민의 낭만적 순간",
  "Foug\\u00e8re": "청량하고 허브향 가득한 고전미, 라벤더와 쿠마린의 조화",
  Fougère: "청량하고 허브향 가득한 고전미, 라벤더와 쿠마린의 조화",
  Fruity: "달콤하고 싱그러운 과실향, 복숭아와 베리의 즐거운 산뜻함",
  Gourmand: "달콤하고 맛있는 디저트 같은 향기, 카라멜과 초콜릿의 유혹",
  Green: "신선하고 생기 넘치는 풀잎향, 새싹과 이파리의 생명력",
  Leathery: "강렬하고 터프한 가죽 향기, 스웨이드와 담배의 카리스마",
  Oriental: "이국적이고 신비로운 감각, 스파이스와 레진의 깊은 매혹",
  Powdery: "부드럽고 포근한 파우더 감촉, 아이리스와 바이올렛의 온화함",
  Resinous: "따뜻하고 깊은 수지의 향연, 엠버와 미르의 묵직한 감성",
  Smoky: "깊고 그윽한 훈연향, 인센스와 연기가 주는 미스터리",
  Spicy: "따뜻하고 자극적인 향신료, 시나몬과 페퍼의 열정적 에너지",
  Sweet: "달콤하고 사랑스러운 감미로움, 프랄린과 캔디의 행복한 순간",
  Synthetic: "현대적이고 세련된 인공향, 독특하고 실험적인 감각",
  Woody: "깊고 차분한 나무의 향기, 시더와 샌달우드의 안정감",
  Fresh: "시원하고 깨끗한 청량감, 민트와 유칼립투스의 상쾌함",
};

export const BRAND_LABELS: Record<string, string> = {
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

export const SEASON_LABELS: Record<string, string> = {
  Spring: "봄",
  Summer: "여름",
  Fall: "가을",
  Winter: "겨울",
};

export const OCCASION_LABELS: Record<string, string> = {
  Business: "업무/비즈니스",
  Daily: "데일리",
  Evening: "저녁 모임",
  Leisure: "여가/휴식",
  "Night Out": "밤 외출",
  Sport: "운동",
};

export const GENDER_TARGET_LABELS: Record<string, string> = {
  Feminine: "여성",
  Masculine: "남성",
  Unisex: "남녀 공용",
};

// 유틸리티 함수
export const getAccordColor = (accord?: string): string =>
  (accord && ACCORD_COLORS[accord]) || "#E8DDCA";

export const hexToRgba = (hex: string, alpha: number): string => {
  const normalized = hex.replace("#", "");
  const full =
    normalized.length === 3
      ? normalized
          .split("")
          .map((char) => char + char)
          .join("")
      : normalized;
  const value = Number.parseInt(full, 16);
  const r = (value >> 16) & 255;
  const g = (value >> 8) & 255;
  const b = value & 255;
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
};

