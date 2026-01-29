'use client';

import { useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import Sidebar from "@/components/common/sidebar";

export default function RecoverPage() {
  const searchParams = useSearchParams();
  const memberId = searchParams.get("memberId");
  const [nickname, setNickname] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isRecovering, setIsRecovering] = useState(false);
  const apiBaseUrl = "/api";

  useEffect(() => {
    if (!memberId) return;
    fetch(`${apiBaseUrl}/users/profile/${memberId}`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        setNickname(data?.nickname || "회원");
      })
      .catch(() => setNickname("회원"));
  }, [apiBaseUrl, memberId]);

  const handleRecover = async () => {
    if (!memberId) return;
    setIsRecovering(true);
    setMessage(null);
    try {
      const response = await fetch(`${apiBaseUrl}/users/recover?member_id=${memberId}`, {
        method: "POST",
      });
      if (!response.ok) {
        const data = await response.json().catch(() => null);
        setMessage(data?.detail || "계정 복구에 실패했습니다.");
        return;
      }
      if (typeof window !== "undefined") {
        localStorage.setItem(
          "localAuth",
          JSON.stringify({
            memberId,
            nickname,
            loggedInAt: new Date().toISOString(),
          })
        );
      }
      window.location.href = "/";
    } catch (error) {
      setMessage("계정 복구에 실패했습니다.");
    } finally {
      setIsRecovering(false);
    }
  };

  return (
    <div className="min-h-screen bg-white text-black flex flex-col">
      <Sidebar isOpen={isSidebarOpen} onClose={() => setIsSidebarOpen(false)} context="home" />

      {isSidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 md:hidden"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}

      <header className="fixed top-0 left-0 w-screen flex items-center justify-between px-5 py-4 bg-[#E5E5E5] z-50">
        <Link href="/" className="text-xl font-bold text-black tracking-tight">
          Scentence
        </Link>
        <button onClick={() => setIsSidebarOpen(true)} className="p-1">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-8 h-8 text-[#555]">
            <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
          </svg>
        </button>
      </header>

      <main className="flex-1 px-5 py-8 w-full max-w-md mx-auto pt-[72px] space-y-6">
        <div>
          <h2 className="text-2xl font-bold">계정 복구</h2>
          <p className="text-sm text-[#666]">현재 {nickname ?? "회원"}님은 탈퇴 요청 상태입니다.</p>
          <p className="text-sm text-[#666]">계정을 복구하시겠습니까?</p>
        </div>

        {message && <p className="text-sm text-red-600">{message}</p>}

        <button
          type="button"
          disabled={isRecovering}
          onClick={handleRecover}
          className={`w-full py-3 rounded-xl font-bold transition ${
            isRecovering
              ? "bg-gray-300 text-gray-500 cursor-not-allowed"
              : "bg-black text-white hover:opacity-90"
          }`}
        >
          계정 복구
        </button>
      </main>
    </div>
  );
}
