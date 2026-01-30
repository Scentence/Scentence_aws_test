'use client';

import { useEffect, useState } from "react";
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
  const [roleType, setRoleType] = useState<string | null>(null);
  const [members, setMembers] = useState<MemberRow[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const apiBaseUrl = "/api";
  useEffect(() => {
    if (session?.user?.id) {
      setMemberId(String(session.user.id));
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
      if (parsed?.roleType) {
        setRoleType(parsed.roleType);
      } else if (parsed?.isAdmin) {
        setRoleType("ADMIN");
      }
    } catch (error) {
      return;
    }
  }, [session]);

  const isAdmin = (roleType || "").toUpperCase() === "ADMIN";

  useEffect(() => {
    if (!memberId || roleType) return;
    const controller = new AbortController();

    const loadRole = async () => {
      try {
        const response = await fetch(`${apiBaseUrl}/users/profile/${memberId}`, {
          signal: controller.signal,
        });
        if (!response.ok) return;
        const data = await response.json().catch(() => null);
        if (data?.role_type) {
          setRoleType(data.role_type);
        }
      } catch (error) {
        return;
      }
    };

    loadRole();

    return () => controller.abort();
  }, [apiBaseUrl, memberId, roleType]);

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

  const [activeTab, setActiveTab] = useState<'MEMBERS' | 'CHATBOT'>('MEMBERS');

  return (
    <div className="min-h-screen bg-[#FDFBF8] text-black flex flex-col font-sans">
      <Sidebar
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
        context="home"
      />

      {isSidebarOpen && (
        <div
          className="fixed inset-0 bg-transparent z-40 md:hidden"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}

      {/* [STANDARD HEADER] Simplified for Admin */}
      <header className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-5 py-4 bg-[#FDFBF8] border-b border-[#F0F0F0]">
        <Link href="/" className="text-xl font-bold tracking-tight text-black">
          Scentence
        </Link>

        {/* 탭 네비게이션: 회원 관리 / 챗봇 테스터 (가운데 배치 등 자유롭지만 일단 중앙 또는 우측보다 좌측에 둘 수도 있음, 여기서는 Title 아래에 두는 게 일반적) */}
        {/* 여기서는 헤더에 둘 수도 있지만, 본문에 두는 게 더 자연스러움. 헤더는 글로벌 네비게이션 역할 */}

        <div className="flex items-center gap-4">
          {/* 글로벌 내비게이션 토글 버튼 */}
          <button
            id="global-menu-toggle"
            onClick={() => setIsSidebarOpen(!isSidebarOpen)}
            className="p-1 rounded-md hover:bg-gray-100 transition-colors"
          >
            {isSidebarOpen ? (
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-8 h-8 text-[#555]">
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            ) : (
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-8 h-8 text-[#555]">
                <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 9h16.5m-16.5 6.75h16.5" />
              </svg>
            )}
          </button>
        </div>
      </header>

      <main className="flex-1 px-5 py-8 w-full max-w-5xl mx-auto pt-[120px] space-y-6">
        <div>
          <h2 className="text-2xl font-bold mb-6">관리자 페이지</h2>

          {/* 탭 메뉴 */}
          <div className="flex border-b border-gray-200 gap-8">
            <button
              onClick={() => setActiveTab('MEMBERS')}
              className={`pb-3 text-sm font-medium transition-colors relative ${activeTab === 'MEMBERS'
                  ? 'text-black font-bold after:absolute after:bottom-0 after:left-0 after:w-full after:h-[2px] after:bg-black'
                  : 'text-gray-400 hover:text-gray-600'
                }`}
            >
              회원 관리
            </button>
            <button
              onClick={() => setActiveTab('CHATBOT')}
              className={`pb-3 text-sm font-medium transition-colors relative ${activeTab === 'CHATBOT'
                  ? 'text-black font-bold after:absolute after:bottom-0 after:left-0 after:w-full after:h-[2px] after:bg-black'
                  : 'text-gray-400 hover:text-gray-600'
                }`}
            >
              챗봇 테스터
            </button>
          </div>
        </div>

        {!isAdmin && (
          <div className="rounded-2xl border border-[#EEE] p-6 text-sm text-[#666]">
            관리자 권한이 없습니다.
          </div>
        )}

        {isAdmin && (
          <>
            {/* [TAB 1] 회원 관리 */}
            {activeTab === 'MEMBERS' && (
              <section className="rounded-2xl border border-[#EEE] p-6 space-y-4 animate-on-scroll">
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
                              className="rounded border border-[#DDD] px-2 py-1 text-sm outline-none focus:border-black transition-colors"
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

            {/* [TAB 2] 챗봇 테스터 (Placeholder) */}
            {activeTab === 'CHATBOT' && (
              <section className="rounded-2xl border border-dashed border-[#EEE] p-12 flex flex-col items-center justify-center min-h-[400px] text-center animate-on-scroll">
                <div className="w-16 h-16 bg-gray-50 rounded-full flex items-center justify-center mb-4 text-gray-300">
                  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-8 h-8">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 3.104v5.714a2.25 2.25 0 0 1-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 0 1 4.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0 1 12 15a9.065 9.065 0 0 0-6.23-.693L5 14.5m14.8.8 1.402 1.402c1.232 1.232.65 3.318-1.067 3.611A48.309 48.309 0 0 1 12 21c-2.773 0-5.491-.235-8.135-.687-1.718-.293-2.3-2.379-1.067-3.61L5 14.5" />
                  </svg>
                </div>
                <h3 className="text-lg font-bold text-gray-400 mb-2">챗봇 테스터 준비 중</h3>
                <p className="text-sm text-gray-400">관리자 전용 챗봇 테스트 환경이 곧 추가됩니다.</p>
              </section>
            )}
          </>
        )}
      </main>
    </div>
  );
}
