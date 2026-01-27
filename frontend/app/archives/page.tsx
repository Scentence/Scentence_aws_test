/* page.tsx (3-State Tabs: All / HAVE / HAD / WISH) */
"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import ArchiveSidebar from "@/components/archives/ArchiveSidebar";
import CabinetShelf from "@/components/archives/CabinetShelf";
import PerfumeSearchModal from "@/components/archives/PerfumeSearchModal";
import PerfumeDetailModal from "@/components/archives/PerfumeDetailModal";
import HistoryModal from '@/components/archives/HistoryModal'; // <--- [추가]

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const MEMBER_ID = 1;

interface MyPerfume {
    my_perfume_id: number;
    perfume_id: number;
    name: string;
    brand: string;
    image_url: string | null;
    register_status: string; // HAVE, HAD, RECOMMENDED
    preference?: string;
    // 프론트 UI용 status 매핑
    status: string;
}

type TabType = 'ALL' | 'HAVE' | 'HAD' | 'WISH';

export default function ArchivesPage() {
    const [collection, setCollection] = useState<MyPerfume[]>([]);
    const [selectedPerfume, setSelectedPerfume] = useState<MyPerfume | null>(null);
    const [activeTab, setActiveTab] = useState<TabType>('ALL');
    const [isSidebarOpen, setIsSidebarOpen] = useState(false);
    const [isSearchOpen, setIsSearchOpen] = useState(false);
    const [isKorean, setIsKorean] = useState(true); // Default: Korean
    const [isHistoryOpen, setIsHistoryOpen] = useState(false); // <--- [추가] 중요!

    const fetchPerfumes = async () => {
        try {
            const res = await fetch(`${API_URL}/users/${MEMBER_ID}/perfumes`);
            if (res.ok) {
                const data = await res.json();
                const mapped = data.map((item: any) => ({
                    my_perfume_id: item.perfume_id, // my_perfume_id는 DB에 없으므로 PK인 perfume_id 사용
                    perfume_id: item.perfume_id,
                    name: item.perfume_name,
                    name_kr: item.name_kr, // Added
                    brand: item.brand || "Unknown",
                    image_url: item.image_url || null,
                    register_status: item.register_status,
                    register_dt: item.register_dt, // Added
                    preference: item.preference,
                    status: item.register_status // CabinetShelf 호환
                }));
                setCollection(mapped);
            }
        } catch (e) {
            console.error("Failed to fetch perfumes", e);
        }
    };

    useEffect(() => {
        fetchPerfumes();
    }, []);

    const handleAdd = async (perfume: any, status: string) => {
        try {
            const payload = {
                perfume_id: perfume.perfume_id,
                perfume_name: perfume.name,
                register_status: status,
                register_reason: "USER",
                preference: "NEUTRAL"
            };
            await fetch(`${API_URL}/users/${MEMBER_ID}/perfumes`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            fetchPerfumes();
            setIsSearchOpen(false);
        } catch (e) { console.error("Add failed", e); }
    };

    const handleUpdateStatus = async (id: number, status: string) => {
        try {
            await fetch(`${API_URL}/users/${MEMBER_ID}/perfumes/${id}`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ register_status: status })
            });
            fetchPerfumes();
            if (selectedPerfume && selectedPerfume.my_perfume_id === id) {
                setSelectedPerfume({ ...selectedPerfume, register_status: status, status: status });
            }
        } catch (e) { console.error("Update failed", e); }
    };

    const handleDelete = async (id: number, rating?: number) => {
        try {
            if (rating !== undefined) {
                let pref = "NEUTRAL";
                if (rating === 3) pref = "GOOD";
                if (rating === 1) pref = "BAD";

                await fetch(`${API_URL}/users/${MEMBER_ID}/perfumes/${id}`, {
                    method: "PATCH",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ register_status: "HAD", preference: pref })
                });
            } else {
                await fetch(`${API_URL}/users/${MEMBER_ID}/perfumes/${id}`, {
                    method: "DELETE"
                });
            }
            fetchPerfumes();
            setSelectedPerfume(null);
        } catch (e) { console.error("Delete failed", e); }
    };

    const handleUpdatePreference = async (id: number, preference: string) => {
        try {
            await fetch(`${API_URL}/users/${MEMBER_ID}/perfumes/${id}`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ register_status: "HAD", preference: preference })
            });
            fetchPerfumes();
            setSelectedPerfume(prev => prev ? { ...prev, register_status: 'HAD', status: 'HAD', preference: preference } : null);
        } catch (e) { console.error("Update preference failed", e); }
    };

    // 통계 계산
    const stats = {
        have: collection.filter(p => p.register_status === 'HAVE').length,
        had: collection.filter(p => p.register_status === 'HAD').length,
        wish: collection.filter(p => p.register_status === 'RECOMMENDED').length
    };

    // 필터링된 목록
    const filteredCollection = collection.filter(item => {
        if (activeTab === 'ALL') return item.register_status !== 'HAD'; // HAD 제외
        if (activeTab === 'HAVE') return item.register_status === 'HAVE';
        if (activeTab === 'HAD') return item.register_status === 'HAD';
        if (activeTab === 'WISH') return item.register_status === 'RECOMMENDED';
        return true;
    });

    return (
        <div className="min-h-screen bg-[#FDFBF8] text-gray-800 font-sans selection:bg-[#C5A55D] selection:text-white">
            <ArchiveSidebar isOpen={isSidebarOpen} onClose={() => setIsSidebarOpen(false)} />
            {isSidebarOpen && <div className="fixed inset-0 bg-black/20 z-40 backdrop-blur-sm" onClick={() => setIsSidebarOpen(false)} />}

            {/* Header */}
            <header className="fixed top-0 left-0 right-0 z-30 flex items-center justify-between px-8 py-5 bg-[#FDFBF8] border-b border-[#F0F0F0]">
                <Link href="/" className="text-xl font-bold tracking-tight text-[#333] hover:opacity-70 transition">
                    Scentence
                </Link>
                <div className="flex items-center gap-4">
                    {/* Language Toggle */}
                    <button
                        onClick={() => setIsKorean(!isKorean)}
                        className="flex items-center gap-1 px-3 py-1.5 rounded-full border border-gray-200 text-xs font-bold text-gray-600 hover:bg-gray-50 transition"
                    >
                        <span>🌐</span>
                        <span>{isKorean ? "한글" : "ENG"}</span>
                    </button>

                    <button onClick={() => setIsSearchOpen(true)} className="flex items-center gap-2 px-4 py-2 bg-[#C5A55D] text-white rounded-full hover:bg-[#B09045] transition shadow-md shadow-[#C5A55D]/20">
                        <span className="text-xs font-bold md:inline hidden">ADD PERFUME</span>
                    </button>
                    <button onClick={() => setIsSidebarOpen(true)} className="p-2 text-[#333] hover:bg-gray-100 rounded-lg transition">☰</button>
                </div>
            </header>

            {/* Main */}
            <main className="pt-[120px] pb-24 px-6 max-w-7xl mx-auto min-h-[80vh]">
                <section className="flex flex-col md:flex-row justify-between items-end mb-12 px-2">
                    <div>
                        <h1 className="text-4xl font-bold text-[#222] mb-3 tracking-tight">My Archive</h1>
                        <p className="text-[#888] text-sm font-medium">나만의 향기 컬렉션을 기록해보세요.</p>
                    </div>

                    <div className="flex gap-4 mt-8 md:mt-0 bg-white px-2 py-2 rounded-2xl shadow-sm border border-gray-100 items-center">
                        <TabItem
                            label="전체 (ALL)"
                            count={stats.have + stats.wish} // HAD 제외한 개수
                            isActive={activeTab === 'ALL'}
                            onClick={() => setActiveTab('ALL')}
                        />
                        <div className="h-6 w-px bg-gray-100"></div>
                        <TabItem
                            label="보유 (HAVE)"
                            count={stats.have}
                            color="text-indigo-600"
                            isActive={activeTab === 'HAVE'}
                            onClick={() => setActiveTab('HAVE')}
                        />
                        <div className="h-6 w-px bg-gray-100"></div>
                        <TabItem
                            label="위시 (WISH)"
                            count={stats.wish}
                            color="text-rose-500"
                            isActive={activeTab === 'WISH'}
                            onClick={() => setActiveTab('WISH')}
                        />
                    </div>

                    {/* History Popover Container */}
                    <div className="relative ml-4 z-40">
                        <button
                            onClick={() => setIsHistoryOpen(!isHistoryOpen)}
                            className={`
                                flex items-center gap-2 px-5 py-3 rounded-2xl border transition-all shadow-sm
                                ${isHistoryOpen
                                    ? 'bg-[#2da44e] text-white border-[#2da44e] shadow-md ring-4 ring-[#2da44e]/10'
                                    : 'bg-white text-gray-500 border-gray-100 hover:bg-green-50 hover:text-[#2da44e] hover:border-[#2da44e]/30'}
                            `}
                        >
                            <span>📜</span>
                            <span className="font-bold text-sm">History</span>
                            <span className={`ml-1 text-xs px-1.5 py-0.5 rounded-full ${isHistoryOpen ? 'bg-white/20' : 'bg-gray-100 text-gray-500'}`}>
                                {stats.had}
                            </span>
                        </button>
                        {/* Popover Component */}
                        {isHistoryOpen && (
                            <HistoryModal
                                historyItems={collection.filter(p => p.register_status === 'HAD')}
                                onClose={() => setIsHistoryOpen(false)}
                                onSelect={setSelectedPerfume}
                            />
                        )}
                    </div>
                </section>

                {/* Filtered List */}
                {filteredCollection.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-20 border border-[#C5A55D]/30 rounded-3xl bg-white/50">
                        <p className="text-gray-400 font-medium mb-4">해당하는 향수가 없습니다.</p>
                        <button onClick={() => setIsSearchOpen(true)} className="text-[#C5A55D] font-bold text-sm hover:underline">
                            + 향수 추가하기
                        </button>
                    </div>
                ) : (
                    <section className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-6 animate-fade-in-up">
                        {filteredCollection.map((item) => (
                            <CabinetShelf
                                key={item.my_perfume_id}
                                perfume={item}
                                onSelect={setSelectedPerfume}
                                isKorean={isKorean}
                            />
                        ))}
                    </section>
                )}
            </main>

            <Link href="/perfume-network" className="fixed bottom-10 right-10 z-30 shadow-xl rounded-full transition-transform hover:scale-105">
                <div className="bg-[#C5A55D] text-white px-8 py-4 rounded-full flex items-center gap-3 font-bold text-sm shadow-[#C5A55D]/30 hover:bg-[#B09045] transition-colors">
                    <span>향수 관계 맵</span>
                </div>
            </Link>

            {isSearchOpen && <PerfumeSearchModal memberId={String(MEMBER_ID)} onClose={() => setIsSearchOpen(false)} onAdd={handleAdd} />}
            {selectedPerfume && <PerfumeDetailModal perfume={selectedPerfume} onClose={() => setSelectedPerfume(null)} onUpdateStatus={handleUpdateStatus} onDelete={handleDelete} onUpdatePreference={handleUpdatePreference} isKorean={isKorean} />}
        </div>
    );
}

function TabItem({ label, count, color = "text-[#555]", isActive, onClick }: { label: string; count: number; color?: string; isActive: boolean; onClick: () => void }) {
    return (
        <button
            onClick={onClick}
            className={`
                flex flex-col items-center min-w-[70px] px-3 py-2 rounded-xl transition-all
                ${isActive ? 'bg-gray-50 ring-1 ring-gray-200 shadow-sm' : 'hover:bg-gray-50/50'}
            `}
        >
            <span className={`text-[10px] font-bold uppercase tracking-wide mb-1 transition-colors ${isActive ? 'text-gray-800' : 'text-gray-400'}`}>{label}</span>
            <span className={`text-xl font-bold transition-all ${isActive ? color : 'text-gray-300'}`}>{count}</span>
        </button>
    );
}