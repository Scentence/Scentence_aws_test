"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Sidebar from "@/components/common/sidebar"; // 우리가 만든 스마트 사이드바

export default function LandingPage() {
  const router = useRouter();
  const [isSidebarOpen, setIsSidebarOpen] = useState(false); // 사이드바 열림/닫힘 상태

  const handleNewChat = () => {
    router.push("/chat");
  };

  return (
    <div className="flex h-screen bg-white overflow-hidden text-black relative font-sans">

      {/* 1. 스마트 사이드바 (context="home") */}
      <Sidebar
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
        context="home"
      />

      <main className="flex-1 flex flex-col relative w-full h-full overflow-y-auto no-scrollbar pb-8 pt-[72px]">
        {/* 사이드바 열렸을 때 배경 어둡게 처리 */}
        {isSidebarOpen && (
          <div className="fixed inset-0 bg-black/50 z-40 md:hidden" onClick={() => setIsSidebarOpen(false)} />
        )}

        {/* 2. HEADER */}
        <header className="fixed top-0 left-0 right-0 flex items-center justify-between px-5 py-4 bg-[#E5E5E5] z-50">
          <Link href="/" className="text-xl font-bold text-black tracking-tight">
            Scentence
          </Link>

          {/* 햄버거 버튼 (클릭 시 사이드바 열림) */}
          <button onClick={() => setIsSidebarOpen(true)} className="p-1">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-8 h-8 text-[#555]">
              <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
            </svg>
          </button>
        </header>

        <div className="px-5 space-y-8 mt-6 w-full max-w-3xl mx-auto">
          {/* 3. HERO CAROUSEL */}
          <section className="relative w-full aspect-[4/3.5] bg-[#E0E0E0] rounded-2xl overflow-hidden group">
            <div
              className="flex w-full h-full overflow-x-auto snap-x snap-mandatory no-scrollbar"
              id="hero-carousel"
              style={{ scrollBehavior: 'smooth' }}
            >
              {[1, 2, 3].map((num) => (
                <div key={num} className="snap-center shrink-0 w-full h-full relative">
                  <img
                    src={`/perfumes/news${num}.png`}
                    alt={`News ${num}`}
                    className="w-full h-full object-cover"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/50 via-transparent to-transparent opacity-60" />
                </div>
              ))}
            </div>
            <div className="absolute bottom-4 right-4 bg-black/60 backdrop-blur-sm text-white text-xs px-3 py-1 rounded-full font-medium z-10">
              News
            </div>
          </section>

          {/* 자동 스크롤 스크립트 실행 */}
          <AutoScrollScript />

          {/* 4. QUICK MENU BUTTONS */}
          <section className="flex gap-4">
            <button className="flex-1 bg-[#E0E0E0] py-4 rounded-xl text-center text-sm font-bold text-[#333]">
              향수 백과
            </button>
            <button
              onClick={handleNewChat}
              className="flex-1 bg-[#E0E0E0] py-4 rounded-xl text-center text-sm font-bold text-[#333]"
            >
              향수 추천
            </button>
          </section>

          {/* 5. SCENTENCE PICK */}
          <section className="space-y-4">
            <h3 className="text-lg font-bold text-black">Scentence Pick</h3>
            <div className="flex gap-4 overflow-x-auto no-scrollbar pb-2">
              {[
                { file: "Angels Share Paradis By Kilian (unisex).png", name: "Angels' Share", brand: "By Kilian" },
                { file: "Angham Lattafa Perfumes (unisex).png", name: "Angham", brand: "Lattafa Perfumes" },
                { file: "BaldAfrique Absolu Byredo (unisex).png", name: "Bal d'Afrique Absolu", brand: "Byredo" },
                { file: "Fleur de Peau Eau de Toilette Diptyque (unisex).png", name: "Fleur de Peau", brand: "Diptyque" },
                { file: "Guidance 46 Amouage (unisex).png", name: "Guidance 46", brand: "Amouage" },
                { file: "Shalimar_L_Essence Guerlain (female).png", name: "Shalimar L'Essence", brand: "Guerlain" },
                { file: "Tilia Marc-Antoine Barrois (unisex).png", name: "Tilia", brand: "Marc-Antoine Barrois" },
                { file: "Valaya Exclusif Parfums de Marly (female).png", name: "Valaya Exclusif", brand: "Parfums de Marly" },
                { file: "Yum Boujee Marshmallow_81 Kayali Fragrances (female).png", name: "Yum Boujee Marshmallow", brand: "Kayali" }
              ].map((item, idx) => (
                <div key={idx} className="shrink-0 w-32 flex flex-col gap-2">
                  <div className="w-32 h-32 bg-[#E0E0E0] rounded-2xl overflow-hidden">
                    <img src={`/perfumes/${item.file}`} alt={item.name} className="w-full h-full object-cover" />
                  </div>
                  <div className="text-xs text-center">
                    <p className="font-bold text-[#333] truncate">{item.name}</p>
                    <p className="text-[#666] truncate">{item.brand}</p>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* 6. SCENTENCE 어떠신가요? */}
          <section className="space-y-4">
            <h3 className="text-lg font-bold text-black">Scentence 어떠신가요?</h3>
            <div className="w-full aspect-video bg-[#E0E0E0] rounded-2xl border border-[#D0D0D0]" />
          </section>
        </div>

      </main>

    </div>
  );
}

// 자동 스크롤 기능 컴포넌트 (그대로 유지)
function AutoScrollScript() {
  useEffect(() => {
    const carousel = document.getElementById('hero-carousel');
    if (!carousel) return;

    let interval: NodeJS.Timeout;
    const startAutoScroll = () => {
      interval = setInterval(() => {
        const nextScroll = carousel.scrollLeft + carousel.clientWidth;
        if (nextScroll >= carousel.scrollWidth) {
          carousel.scrollTo({ left: 0, behavior: 'smooth' });
        } else {
          carousel.scrollTo({ left: nextScroll, behavior: 'smooth' });
        }
      }, 4000);
    };

    const stopAutoScroll = () => clearInterval(interval);

    carousel.addEventListener('touchstart', stopAutoScroll);
    carousel.addEventListener('touchend', startAutoScroll);
    carousel.addEventListener('mouseenter', stopAutoScroll);
    carousel.addEventListener('mouseleave', startAutoScroll);

    startAutoScroll();

    return () => {
      stopAutoScroll();
      carousel.removeEventListener('touchstart', stopAutoScroll);
      carousel.removeEventListener('touchend', startAutoScroll);
      carousel.removeEventListener('mouseenter', stopAutoScroll);
      carousel.removeEventListener('mouseleave', startAutoScroll);
    };
  }, []);

  return null;
}