'use client';

import { useState } from "react";
import Link from "next/link";
import Sidebar from "@/components/common/sidebar";

export default function LoginPage() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  return (
    <div className="min-h-screen bg-white text-black flex flex-col">
      <Sidebar
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
        context="home"
      />

      {isSidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 md:hidden"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}

      <header className="fixed top-0 left-0 right-0 flex items-center justify-between px-5 py-4 bg-[#E5E5E5] z-50">
        <Link href="/" className="text-xl font-bold text-black tracking-tight">
          Scentence
        </Link>
        <button onClick={() => setIsSidebarOpen(true)} className="p-1">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-8 h-8 text-[#555]">
            <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
          </svg>
        </button>
      </header>

      <main className="flex-1 px-5 py-8 w-full max-w-md mx-auto pt-[72px]">
        <div className="space-y-2 mb-8">
          <h2 className="text-2xl font-bold">통합 로그인</h2>
          <p className="text-sm text-[#666]">아이디와 비밀번호로 로그인하세요.</p>
        </div>

        <form className="space-y-5">
          <div className="space-y-2">
            <label htmlFor="loginId" className="text-sm font-medium text-[#333]">아이디</label>
            <input
              id="loginId"
              name="loginId"
              type="text"
              placeholder="아이디를 입력하세요"
              className="w-full rounded-xl border border-[#DDD] px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-black/20"
            />
          </div>

          <div className="space-y-2">
            <label htmlFor="password" className="text-sm font-medium text-[#333]">비밀번호</label>
            <input
              id="password"
              name="password"
              type="password"
              placeholder="비밀번호를 입력하세요"
              className="w-full rounded-xl border border-[#DDD] px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-black/20"
            />
          </div>

          <button
            type="button"
            className="text-xs text-[#666] underline hover:text-black"
          >
            비밀번호를 잊어버리셨나요?
          </button>

          <button
            type="submit"
            className="w-full bg-black text-white py-3 rounded-xl font-bold hover:opacity-90 transition"
          >
            계속
          </button>

          <div className="text-sm text-center text-[#666]">
            계정이 없으신가요?{" "}
            <Link href="/signup" className="font-semibold text-black hover:underline">
              가입하기
            </Link>
          </div>

          <div className="flex items-center gap-3 text-xs text-[#999]">
            <div className="flex-1 h-px bg-[#E5E5E5]" />
            <span>--------또는--------</span>
            <div className="flex-1 h-px bg-[#E5E5E5]" />
          </div>

          <button
            type="button"
            className="w-full bg-[#FEE500] text-black py-3 rounded-xl font-bold flex items-center justify-center gap-2 hover:opacity-90 transition"
          >
            <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-black text-[#FEE500] text-xs font-bold">K</span>
            카카오 계정으로 계속
          </button>
        </form>
      </main>
    </div>
  );
}
