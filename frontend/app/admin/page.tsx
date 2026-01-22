'use client';

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useSession } from "next-auth/react";
import Sidebar from "@/components/common/sidebar";

interface MemberRow {
  member_id: string;
  email: string | null;
  nickname: string | null;
  join_channel: string | null;
  join_dt: string | null;
  member_status: string | null;
}

const statusOptions = ["NORMAL", "LOCK", "DORMANT", "WITHDRAW_REQ", "WITHDRAW"] as const;

export default function AdminPage() {
  const { data: session } = useSession();
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [memberId, setMemberId] = useState<string | null>(null);
  const [adminEmail, setAdminEmail] = useState<string | null>(null);
  const [members, setMembers] = useState<MemberRow[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || "";
  const adminEmails = useMemo(() => {
    const raw = process.env.NEXT_PUBLIC_ADMIN_EMAILS || "";
    return raw
      .split(",")
      .map((email) => email.trim().toLowerCase())
      .filter(Boolean);
  }, []);

  useEffect(() => {
    if (session?.user?.id) {
      setMemberId(String(session.user.id));
      setAdminEmail(session.user?.email ?? null);
      return;
    }
    if (typeof window === "undefined") return;
    const stored = localStorage.getItem("localAuth");
    if (!stored) return;
    try {
      const parsed = JSON.parse(stored);
      if (parsed?.memberId) {
        setMemberId(String(parsed.memberId));
      }
      if (parsed?.email) {
        setAdminEmail(parsed.email);
      }
    } catch (error) {
      return;
    }
  }, [session]);

  const isAdmin = adminEmail ? adminEmails.includes(adminEmail.toLowerCase()) : false;

  useEffect(() => {
    if (!memberId || !isAdmin) return;
    const controller = new AbortController();

    const loadMembers = async () => {
      setIsLoading(true);
      setMessage(null);
      try {
        const response = await fetch(
          `${apiBaseUrl}/users/admin/members?admin_member_id=${memberId}`,
          { signal: controller.signal }
        );
        if (!response.ok) {
          const data = await response.json().catch(() => null);
          setMessage(data?.detail || "관리자 목록 조회에 실패했습니다.");
          return;
        }
        const data = await response.json();
        setMembers(data.members ?? []);
      } catch (error) {
        setMessage("관리자 목록 조회에 실패했습니다.");
      } finally {
        setIsLoading(false);
      }
    };

    loadMembers();

    return () => controller.abort();
  }, [apiBaseUrl, isAdmin, memberId]);

  const updateStatus = async (targetId: string, status: string) => {
    if (!memberId) return;
    try {
      const response = await fetch(
        `${apiBaseUrl}/users/admin/members/${targetId}/status?admin_member_id=${memberId}&status=${status}`,
        { method: "PATCH" }
      );
      if (!response.ok) {
        const data = await response.json().catch(() => null);
        setMessage(data?.detail || "상태 변경에 실패했습니다.");
        return;
      }
      setMembers((prev) =>
        prev.map((item) =>
          item.member_id === targetId ? { ...item, member_status: status } : item
        )
      );
    } catch (error) {
      setMessage("상태 변경에 실패했습니다.");
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

      <main className="flex-1 px-5 py-8 w-full max-w-5xl mx-auto pt-[72px] space-y-6">
        <div>
          <h2 className="text-2xl font-bold">관리자 페이지</h2>
          <p className="text-sm text-[#666]">회원 관리 전용 화면입니다.</p>
        </div>

        {!isAdmin && (
          <div className="rounded-2xl border border-[#EEE] p-6 text-sm text-[#666]">
            관리자 권한이 없습니다.
          </div>
        )}

        {isAdmin && (
          <section className="rounded-2xl border border-[#EEE] p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold">회원 목록</h3>
              {isLoading && <span className="text-xs text-[#999]">불러오는 중...</span>}
            </div>

            {message && <p className="text-xs text-red-600">{message}</p>}

            <div className="overflow-x-auto">
              <table className="w-full text-sm table-fixed">
                <thead className="text-left text-[#666]">
                  <tr>
                    <th className="py-2 w-20">MEMBER_ID</th>
                    <th className="py-2 w-52">이메일</th>
                    <th className="py-2 w-40">닉네임</th>
                    <th className="py-2 w-28">가입일</th>
                    <th className="py-2 w-28">상태</th>
                    <th className="py-2 w-24">가입 방식</th>
                    <th className="py-2 w-32">관리</th>
                  </tr>
                </thead>
                <tbody>
                  {members.map((member) => (
                    <tr key={member.member_id} className="border-t">
                      <td className="py-2 truncate">{member.member_id}</td>
                      <td className="py-2 truncate">{member.email ?? "-"}</td>
                      <td className="py-2 truncate">{member.nickname ?? "-"}</td>
                      <td className="py-2">{member.join_dt ? new Date(member.join_dt).toLocaleDateString() : "-"}</td>
                      <td className="py-2">{member.member_status ?? "-"}</td>
                      <td className="py-2">{member.join_channel ?? "-"}</td>
                      <td className="py-2">
                        <select
                          className="rounded border border-[#DDD] px-2 py-1 text-sm"
                          value={member.member_status ?? "NORMAL"}
                          onChange={(event) => updateStatus(member.member_id, event.target.value)}
                        >
                          {statusOptions.map((status) => (
                            <option key={status} value={status}>
                              {status}
                            </option>
                          ))}
                        </select>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
