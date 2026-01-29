/* HistoryModal.tsx (Popover Version) */
"use client";
import CabinetShelf from './CabinetShelf';
interface MyPerfume {
    my_perfume_id: number;
    perfume_id: number;
    name: string;
    brand: string;
    image_url: string | null;
    status: string;
    preference?: string;
}
interface Props {
    historyItems: MyPerfume[];
    onClose: () => void;
    onSelect: (perfume: MyPerfume) => void;
}
export default function HistoryModal({ historyItems, onClose, onSelect }: Props) {
    return (
        <>
            {/* 배경 클릭 시 닫기 (투명 레이어) */}
            <div className="fixed inset-0 z-40 cursor-default" onClick={onClose} />
            {/* 팝오버 컨테이너 */}
            <div
                className="absolute top-full right-0 mt-3 w-[350px] md:w-[500px] max-h-[60vh] bg-white rounded-3xl shadow-xl border border-gray-100 z-50 flex flex-col overflow-hidden origin-top-right animate-[slideDown_0.3s_ease-out_forwards]"
                style={{ animation: 'slideDown 0.3s cubic-bezier(0.16, 1, 0.3, 1)' }}
            >
                <style jsx>{`
                    @keyframes slideDown {
                        from { opacity: 0; transform: translateY(-10px) scale(0.98); }
                        to { opacity: 1; transform: translateY(0) scale(1); }
                    }
                `}</style>
                {/* 헤더 */}
                <div className="flex items-center justify-between px-5 py-4 border-b border-gray-50 bg-[#FDFBF8]">
                    <div className="flex items-center gap-2">
                        <span className="text-lg">📜</span>
                        <h2 className="text-base font-bold text-[#333]">History Archive</h2>
                        <span className="bg-amber-100 text-amber-700 text-[10px] font-bold px-1.5 py-0.5 rounded-full">
                            {historyItems.length}
                        </span>
                    </div>
                </div>
                {/* 리스트 (스크롤 가능) */}
                <div className="flex-1 overflow-y-auto p-4 custom-scrollbar bg-white">
                    {historyItems.length === 0 ? (
                        <div className="py-10 flex flex-col items-center justify-center text-gray-400">
                            <p className="text-2xl mb-2">🍃</p>
                            <p className="text-xs font-medium">기록된 향수가 없습니다.</p>
                        </div>
                    ) : (
                        <div className="grid grid-cols-2 gap-3">
                            {historyItems.map((item) => (
                                <div key={item.my_perfume_id} className="scale-90 origin-top text-xs relative group">
                                    <CabinetShelf
                                        perfume={item}
                                        onSelect={(p) => {
                                            onClose(); // 선택 시 팝오버 닫기
                                            onSelect(p);
                                        }}
                                    />
                                    {item.preference && (
                                        <div className="absolute top-0 right-0 bg-white/90 backdrop-blur px-2 py-0.5 rounded-bl-lg text-[10px] font-bold shadow-sm border-l border-b border-gray-100 text-gray-600">
                                            {item.preference === "GOOD" && "👍"}
                                            {item.preference === "BAD" && "👎"}
                                            {item.preference === "NEUTRAL" && "👌"}
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </>
    );
}