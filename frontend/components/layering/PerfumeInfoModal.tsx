"use client";

type PerfumeInfo = {
  perfume_id: string;
  perfume_name: string;
  perfume_brand: string;
  image_url?: string | null;
  gender?: string | null;
  accords: string[];
  seasons: string[];
  occasions: string[];
  top_notes: string[];
  middle_notes: string[];
  base_notes: string[];
};

type PerfumeInfoModalProps = {
  open: boolean;
  loading?: boolean;
  errorMessage?: string | null;
  perfume: PerfumeInfo | null;
  onClose: () => void;
};

const buildSections = (perfume: PerfumeInfo) => [
  { label: "어코드", items: perfume.accords },
  { label: "탑 노트", items: perfume.top_notes },
  { label: "미들 노트", items: perfume.middle_notes },
  { label: "베이스 노트", items: perfume.base_notes },
  { label: "계절", items: perfume.seasons },
  { label: "상황", items: perfume.occasions },
].filter((section) => section.items && section.items.length > 0);

export default function PerfumeInfoModal({
  open,
  loading = false,
  errorMessage,
  perfume,
  onClose,
}: PerfumeInfoModalProps) {
  if (!open) return null;

  const sections = perfume ? buildSections(perfume) : [];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
      <div className="w-full max-w-lg rounded-3xl bg-[#F9F6EF] border border-[#E2D7C5] shadow-2xl overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#E2D7C5] bg-gradient-to-r from-[#F8F4EC] to-[#F0EAE0]">
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-[#7A6B57] font-medium">Perfume Details</p>
            <h2 className="text-lg font-semibold text-[#2E2B28]">향수 정보</h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full border border-[#E2D7C5] bg-white/80 p-2 text-[#7A6B57] hover:text-[#5C5448] hover:bg-white transition"
            aria-label="정보 닫기"
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="h-5 w-5">
              <path d="M6.225 4.811a.75.75 0 011.06 0L12 9.525l4.715-4.714a.75.75 0 111.06 1.06L13.06 10.586l4.715 4.714a.75.75 0 11-1.06 1.06L12 11.646l-4.715 4.714a.75.75 0 11-1.06-1.06l4.714-4.714-4.714-4.715a.75.75 0 010-1.06z" />
            </svg>
          </button>
        </div>

        <div className="px-6 py-5 space-y-4 max-h-[70vh] overflow-y-auto">
          {loading && (
            <div className="flex items-center gap-2 text-sm text-[#7A6B57]">
              <svg className="animate-spin h-4 w-4 text-[#7A6B57]" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              정보를 불러오는 중입니다.
            </div>
          )}

          {!loading && errorMessage && (
            <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {errorMessage}
            </div>
          )}

          {!loading && !errorMessage && perfume && (
            <>
              <div className="flex items-center gap-4">
                {perfume.image_url ? (
                  <img
                    src={perfume.image_url}
                    alt={`${perfume.perfume_name} 이미지`}
                    className="h-20 w-20 rounded-2xl object-cover border border-[#E6DDCF]"
                    loading="lazy"
                  />
                ) : (
                  <div className="h-20 w-20 rounded-2xl bg-gradient-to-br from-[#F4EBDD] to-[#E8D9C4] flex items-center justify-center text-[10px] text-[#7A6B57] border border-[#E6DDCF]">
                    No Image
                  </div>
                )}
                <div>
                  <p className="text-xs font-semibold text-[#7A6B57]">추천 향수</p>
                  <h3 className="text-lg font-bold text-[#2E2B28] leading-tight">
                    {perfume.perfume_name}
                  </h3>
                  <p className="text-sm text-[#7A6B57]">{perfume.perfume_brand}</p>
                  {perfume.gender && (
                    <p className="text-xs text-[#5C5448] mt-1">성별: {perfume.gender}</p>
                  )}
                </div>
              </div>

              <div className="space-y-4">
                {sections.map((section) => (
                  <div key={section.label}>
                    <p className="text-[11px] font-semibold text-[#7A6B57]">{section.label}</p>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {section.items.map((item) => (
                        <span
                          key={`${section.label}-${item}`}
                          className="text-[11px] px-2 py-0.5 rounded-full bg-white text-[#5C5448] border border-[#E6DDCF]"
                        >
                          {item}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
