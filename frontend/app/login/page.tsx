'use client';

import { FormEvent, useState } from "react";
import Link from "next/link";
import Sidebar from "@/components/common/sidebar";

export default function LoginPage() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [loginId, setLoginId] = useState("");
  const [password, setPassword] = useState("");
  const [submitMessage, setSubmitMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || "";

  const handleKakaoPopup = () => {
    if (typeof window === "undefined") return;
    const width = 420;
    const height = 640;
    const left = window.screenX + (window.outerWidth - width) / 2;
    const top = window.screenY + (window.outerHeight - height) / 2;
    window.open(
      "/kakao-login",
      "kakao-login",
      `width=${width},height=${height},left=${left},top=${top},resizable=yes,scrollbars=yes`
    );
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitMessage(null);

    if (!loginId.trim() || !password) {
      setSubmitMessage("아이디와 비밀번호를 입력해주세요.");
      return;
    }

    setIsSubmitting(true);

    try {
      const response = await fetch(`${apiBaseUrl}/users/login/local`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: loginId.trim(),
          password,
        }),
      });

      if (!response.ok) {
        const data = await response.json().catch(() => null);
        setSubmitMessage(data?.detail || "로그인에 실패했습니다.");
        return;
      }
      const data = await response.json().catch(() => null);
        if (data?.withdraw_pending && data?.member_id) {
          window.location.href = `/recover?memberId=${data.member_id}`;
          return;
        }
      let nickname = null;
      let roleType = data?.role_type ?? null;
      if (data?.member_id) {
        const profileResponse = await fetch(`${apiBaseUrl}/users/profile/${data.member_id}`);
        if (profileResponse.ok) {
          const profileData = await profileResponse.json().catch(() => null);
          nickname = profileData?.nickname ?? null;
          roleType = profileData?.role_type ?? roleType;
        }
      }
      if (typeof window !== "undefined") {
        localStorage.setItem(
          "localAuth",
          JSON.stringify({
            memberId: data?.member_id ?? null,
            email: loginId.trim(),
            nickname,
            roleType: roleType,
            loggedInAt: new Date().toISOString(),
          })
        );
      }
      window.location.href = "/";
    } catch (error) {
      setSubmitMessage("로그인에 실패했습니다.");
    } finally {
      setIsSubmitting(false);
    }
  };

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

        <form className="space-y-5" onSubmit={handleSubmit}>
          <div className="space-y-2">
            <label htmlFor="loginId" className="text-sm font-medium text-[#333]">아이디</label>
            <input
              id="loginId"
              name="loginId"
              type="text"
              placeholder="아이디를 입력하세요"
              value={loginId}
              onChange={(event) => setLoginId(event.target.value)}
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
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="w-full rounded-xl border border-[#DDD] px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-black/20"
            />
          </div>

          <button
            type="button"
            className="text-xs text-right text-[#666] underline hover:text-black"
          >
            비밀번호를 잊어버리셨나요?
          </button>

          {submitMessage && (
            <p className="text-xs text-red-600">{submitMessage}</p>
          )}

          <button
            type="submit"
            disabled={isSubmitting}
            className={`w-full py-3 rounded-xl font-bold transition ${
              isSubmitting
                ? "bg-gray-300 text-gray-500 cursor-not-allowed"
                : "bg-black text-white hover:opacity-90"
            }`}
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
            <span>또는</span>
            <div className="flex-1 h-px bg-[#E5E5E5]" />
          </div>

          <button
            type="button"
            onClick={handleKakaoPopup}
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
