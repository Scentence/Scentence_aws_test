"use client";

// ✅ 사이드바 조각 (Sidebar.tsx)
// PC에서는 왼쪽 고정, 모바일에서는 숨겨져 있다가 나타날 예정입니다.


interface SidebarProps {
    isOpen: boolean;
    onToggle: () => void;       // ✅ 토글 버튼을 위한 함수 추가
    onNewChat: () => void;      // ✅ 새 대화 버튼을 위한 함수 추가
    loading: boolean;
    showToggleButton?: boolean; // ✅ 버튼 표시 여부 (선택적)
}


const Sidebar = ({ isOpen, onToggle, onNewChat, loading, showToggleButton = false }: SidebarProps) => {
    return (
        // 1. 대기조: 사이드바가 닫혀있어도 버튼만큼의 공간(w-16)은 항상 차지하거나(PC), 아예 감춥니다.
        // 여기서는 '버튼이 항상 그 자리에' 있어야 하므로, z-index를 높여서 버튼을 따로 뺍니다.
        <>
            {/* ✅ 절대 위치 고정 토글 버튼 (showToggleButton이 true일 때만 보임) */}
            {showToggleButton && (
                <button
                    onClick={onToggle}
                    className="fixed top-4 left-4 z-[60] p-2 hover:bg-[#F2F1EE] rounded-lg transition-colors bg-white/50 backdrop-blur-sm md:bg-transparent"
                >
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-6 h-6 text-[#393939]">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
                    </svg>
                </button>
            )}
            {/* ✅ 진짜 사이드바 본체 (버튼 아래에서 움직임) */}
            {/* ✅ 진짜 사이드바 본체 (버튼 아래에서 움직임) */}
            <div className={`fixed inset-y-0 right-0 z-50 w-64 bg-white border-l border-[#E5E4DE] transition-transform duration-300 transform 
                ${isOpen ? "translate-x-0" : "translate-x-full"}`}>

                <div className="flex h-full flex-col p-4 pt-4"> {/* pt-4: 상단 여백 조정 */}
                    <div className="flex justify-between items-center mb-6 px-2">
                        <span className="text-[10px] font-bold tracking-widest text-[#8E8E8E]">RECENT HISTORY</span>
                        {/* 닫기 버튼 (햄버거/X) 추가 */}
                        <button onClick={onToggle} className="p-1 text-[#8E8E8E] hover:text-[#393939] transition-colors">
                            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5">
                                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        </button>
                    </div>
                    <button onClick={onNewChat} disabled={loading} className="group flex items-center justify-center gap-2 rounded-xl border border-[#E5E4DE] bg-[#FAF8F5] py-3 text-sm font-medium text-[#393939] transition-all hover:bg-[#F2F1EE] disabled:opacity-50">
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="h-5 w-5 transition-transform group-hover:rotate-180">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M16 9h5M3 19v-5m0 0h5m-5 0l3 3a8 8 0 0013-3M4 10a8 8 0 0113-3l3 3m0-5v5" />
                        </svg>
                        새로운 대화 시작
                    </button>
                    <div className="mt-8 flex-1 overflow-y-auto no-scrollbar">
                        <p className="px-2 text-xs text-[#BCBCBC]">History (Coming Soon)</p>
                    </div>

                    <div className="mt-auto border-t border-[#E5E4DE] pt-4 flex items-center gap-3 px-2">
                        <div className="h-8 w-8 rounded-full bg-gradient-to-tr from-pink-400 to-purple-400" />
                        <div className="text-sm font-medium">Guest User</div>
                    </div>
                </div>
            </div>
        </>
    );
};
export default Sidebar;