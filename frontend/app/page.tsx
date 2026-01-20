"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
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

      <main className="flex-1 flex flex-col relative w-full h-full overflow-y-auto no-scrollbar pb-[80px]">
        {/* 사이드바 열렸을 때 배경 어둡게 처리 */}
        {isSidebarOpen && (
          <div className="fixed inset-0 bg-black/50 z-40 md:hidden" onClick={() => setIsSidebarOpen(false)} />
        )}

        {/* 2. HEADER */}
        <header className="flex items-center justify-between px-5 py-4 bg-[#E5E5E5]">
          <h1 className="text-xl font-bold text-black tracking-tight">Scentence</h1>

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
            <button className="flex-1 bg-[#E0E0E0] py-4 rounded-xl text-center text-sm font-bold text-[#333]">
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

      {/* 7. BOTTOM NAVIGATION */}
      <nav className="fixed bottom-0 left-0 right-0 bg-[#E5E5E5] border-t border-[#CCC] h-[70px] px-6 z-50">
        <div className="w-full max-w-3xl mx-auto h-full flex justify-between items-center">
          <button className="flex flex-col items-center gap-1 text-black p-2">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-6 h-6"><path strokeLinecap="round" strokeLinejoin="round" d="m2.25 12 8.954-8.955c.44-.439 1.152-.439 1.591 0L21.75 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125H9.75v-4.875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21h4.125c.621 0 1.125-.504 1.125-1.125V9.75M8.25 21h8.25" /></svg>
          </button>
          <button className="flex flex-col items-center gap-1 text-[#555] p-2">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-6 h-6"><path strokeLinecap="round" strokeLinejoin="round" d="M21 8.25c0-2.485-2.099-4.5-4.688-4.5-1.935 0-3.597 1.126-4.312 2.733-.715-1.607-2.377-2.733-4.313-2.733C5.1 3.75 3 5.765 3 8.25c0 7.22 9 12 9 12s9-4.78 9-12Z" /></svg>
          </button>
          <button onClick={handleNewChat} className="flex flex-col items-center gap-1 text-[#555] p-2">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-7 h-7"><path strokeLinecap="round" strokeLinejoin="round" d="M8.625 12a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H8.25m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H12m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 0 1-2.555-.337A5.972 5.972 0 0 1 5.41 20.97a5.969 5.969 0 0 1-.474-.065 4.48 4.48 0 0 0 .978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25Z" /></svg>
          </button>
          <button className="flex flex-col items-center gap-1 text-[#555] p-2">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-6 h-6"><path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0ZM4.501 20.118a7.5 7.5 0 0 1 14.998 0A17.933 17.933 0 0 1 12 21.75c-2.676 0-5.216-.584-7.499-1.632Z" /></svg>
          </button>
        </div>
      </nav>
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