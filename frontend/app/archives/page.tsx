/* page.tsx (Restored) */
"use client";

import { useState } from "react";
import Link from "next/link";
import ArchiveSidebar from "@/components/archives/ArchiveSidebar";
import CabinetShelf from "@/components/archives/CabinetShelf";
import PerfumeSearchModal from "@/components/archives/PerfumeSearchModal";
import PerfumeDetailModal from "@/components/archives/PerfumeDetailModal";

interface MyPerfume {
    my_perfume_id: number;
    perfume_id: number;
    name: string;
    brand: string;
    image_url: string | null;
    status: string;
}

export default function ArchivesPage() {
    const [isSidebarOpen, setIsSidebarOpen] = useState(false);
    const [collection, setCollection] = useState<MyPerfume[]>([
        {
            my_perfume_id: 101,
            perfume_id: 201,
            name: "Bal d'Afrique Absolu",
            brand: "Byredo",
            image_url: "/perfumes/BaldAfrique Absolu Byredo (unisex).png",
            status: "HAVE"
        },
        {
            my_perfume_id: 102,
            perfume_id: 202,
            name: "Fleur de Peau",
            brand: "Diptyque",
            image_url: "/perfumes/Fleur de Peau Eau de Toilette Diptyque (unisex).png",
            status: "WANT"
        }
    ]);
    const [isSearchOpen, setIsSearchOpen] = useState(false);
    const [selectedPerfume, setSelectedPerfume] = useState<MyPerfume | null>(null);

    const handleAdd = (perfume: any, status: string) => {
        const newItem: MyPerfume = {
            my_perfume_id: Date.now(),
            perfume_id: perfume.perfume_id,
            name: perfume.name,
            brand: perfume.brand,
            image_url: perfume.image_url,
            status: status
        };
        setCollection(prev => [...prev, newItem]);
        setIsSearchOpen(false);
    };

    const handleUpdateStatus = (id: number, status: string) => {
        setCollection(prev => prev.map(p =>
            p.my_perfume_id === id ? { ...p, status } : p
        ));
        if (selectedPerfume) setSelectedPerfume(prev => prev ? { ...prev, status } : null);
    };

    const handleDelete = (id: number, rating: number) => {
        console.log(`Deleting ${id} with Rating: ${rating}`);
        setCollection(prev => prev.filter(p => p.my_perfume_id !== id));
        setSelectedPerfume(null);
    };

    const stats = {
        have: collection.filter(p => p.status === 'HAVE').length,
        want: collection.filter(p => p.status === 'WANT').length,
    };

    return (
        <div className="min-h-screen bg-[#FDFBF8] text-gray-800 font-sans selection:bg-[#C5A55D] selection:text-white">

            <ArchiveSidebar isOpen={isSidebarOpen} onClose={() => setIsSidebarOpen(false)} />
            {isSidebarOpen && (
                <div className="fixed inset-0 bg-black/20 z-40 backdrop-blur-sm" onClick={() => setIsSidebarOpen(false)} />
            )}

            {/* 헤더 */}
            <header className="fixed top-0 left-0 right-0 z-30 flex items-center justify-between px-8 py-5 bg-[#FDFBF8] border-b border-[#F0F0F0]">
                <Link href="/" className="text-xl font-bold tracking-tight text-[#333] hover:opacity-70 transition">
                    Scentence
                </Link>
                <div className="flex items-center gap-4">
                    <button
                        onClick={() => setIsSearchOpen(true)}
                        className="flex items-center gap-2 px-4 py-2 bg-[#C5A55D] text-white rounded-full hover:bg-[#B09045] transition shadow-md shadow-[#C5A55D]/20"
                    >
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-4 h-4">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
                        </svg>
                        <span className="text-xs font-bold md:inline hidden">ADD PERFUME</span>
                    </button>
                    <button onClick={() => setIsSidebarOpen(true)} className="p-2 text-[#333] hover:bg-gray-100 rounded-lg transition">
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-6 h-6">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
                        </svg>
                    </button>
                </div>
            </header>

            {/* 메인 */}
            <main className="pt-[120px] pb-24 px-6 max-w-7xl mx-auto min-h-[80vh]">

                <section className="flex flex-col md:flex-row justify-between items-end mb-12 px-2">
                    <div>
                        <h1 className="text-4xl font-bold text-[#222] mb-3 tracking-tight">My Archive</h1>
                        <p className="text-[#888] text-sm font-medium">나만의 향기 컬렉션을 기록해보세요.</p>
                    </div>

                    <div className="flex gap-8 mt-8 md:mt-0 bg-white px-6 py-3 rounded-2xl shadow-sm border border-gray-100 items-center">
                        {/* 통계 아이템 (Large Fonts & Colors) */}
                        <StatItem label="보유 (HAVE)" count={stats.have} color="text-indigo-600" />
                        <div className="h-8 w-px bg-gray-200"></div>
                        <StatItem label="위시 (WANT)" count={stats.want} color="text-rose-500" />
                    </div>
                </section>

                {collection.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-20 border border-[#C5A55D]/30 rounded-3xl bg-white/50">
                        <div className="w-20 h-20 bg-gray-50 rounded-full flex items-center justify-center mb-4 text-[#C5A55D]">
                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-8 h-8 opacity-70">
                                <path fillRule="evenodd" d="M10.5 1.5a1 1 0 0 1 1-1h1a1 1 0 0 1 1 1v1.323c2.348.67 4.12 2.656 4.435 5.177H18a1 1 0 0 1 1 1v2a1 1 0 0 1-1 1h-.065C17.65 15.65 14.935 19 12 19c-2.935 0-5.65-3.35-5.935-7H6a1 1 0 0 1-1-1v-2a1 1 0 0 1 1-1h.065A5.5 5.5 0 0 1 10.5 2.823V1.5Zm-2.6 6.5h8.2a4.004 4.004 0 0 0-1.077-2.31 3.997 3.997 0 0 0-6.046 0C8.523 6.38 8.163 7.155 7.9 8Zm5.352 9.478A16.03 16.03 0 0 1 12 17.5c-1.636 0-3.136-.5-4.252-1.397.35-2.002 1.39-3.69 2.877-4.908.577.29 1.157.435 1.75.405.592.03 1.171-.115 1.748-.405 1.488 1.218 2.527 2.906 2.877 4.908Z" clipRule="evenodd" />
                            </svg>
                        </div>
                        <p className="text-gray-400 font-medium mb-4">아직 수집된 향수가 없습니다.</p>
                        <button onClick={() => setIsSearchOpen(true)} className="text-[#C5A55D] font-bold text-sm hover:underline">
                            + 첫 번째 향수 추가하기
                        </button>
                    </div>
                ) : (
                    <section className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-6">
                        {collection.map((item) => (
                            <CabinetShelf
                                key={item.my_perfume_id}
                                perfume={item}
                                onSelect={setSelectedPerfume}
                            />
                        ))}
                    </section>
                )}
            </main>

            <Link href="/perfume-network" className="fixed bottom-10 right-10 z-30 shadow-xl rounded-full transition-transform hover:scale-105">
                <div className="bg-[#C5A55D] text-white px-8 py-4 rounded-full flex items-center gap-3 font-bold text-sm shadow-[#C5A55D]/30 hover:bg-[#B09045] transition-colors">
                    <span>향수 관계 맵</span>
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" /></svg>
                </div>
            </Link>

            {isSearchOpen && (
                <PerfumeSearchModal
                    memberId="1"
                    onClose={() => setIsSearchOpen(false)}
                    onAdd={handleAdd}
                />
            )}

            {selectedPerfume && (
                <PerfumeDetailModal
                    perfume={selectedPerfume}
                    onClose={() => setSelectedPerfume(null)}
                    onUpdateStatus={handleUpdateStatus}
                    onDelete={handleDelete}
                />
            )}
        </div>
    );
}

function StatItem({ label, count, color = "text-[#333]" }: { label: string; count: number; color?: string }) {
    return (
        <div className="flex flex-col items-center min-w-[80px]">
            <span className="text-gray-400 text-xs font-bold uppercase tracking-wide mb-1">{label}</span>
            <span className={`text-2xl font-bold ${color}`}>{count}</span>
        </div>
    );
}
