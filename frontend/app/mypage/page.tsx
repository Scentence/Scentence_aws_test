'use client';

import { FormEvent, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useSession } from "next-auth/react";
import Sidebar from "@/components/common/sidebar";

interface ProfileData {
  member_id: string;
  join_channel: string | null;
  sns_join_yn: string | null;
  email_alarm_yn: string | null;
  sns_alarm_yn: string | null;
  name: string | null;
  nickname: string | null;
  sex: string | null;
  phone_no: string | null;
  address: string | null;
  email: string | null;
  sub_email: string | null;
  profile_image_url: string | null;
}

export default function MyPage() {
  const { data: session } = useSession();
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [memberId, setMemberId] = useState<string | null>(null);
  const [profile, setProfile] = useState<ProfileData | null>(null);
  const [nickname, setNickname] = useState("");
  const [profileImageUrl, setProfileImageUrl] = useState("");
  const [name, setName] = useState("");
  const [sex, setSex] = useState<"M" | "F" | "">("");
  const [phoneNo, setPhoneNo] = useState("");
  const [address, setAddress] = useState("");
  const [email, setEmail] = useState("");
  const [subEmail, setSubEmail] = useState("");
  const [snsJoin, setSnsJoin] = useState(false);
  const [emailMarketing, setEmailMarketing] = useState(false);
  const [snsMarketing, setSnsMarketing] = useState(false);
  const [nicknameStatus, setNicknameStatus] = useState<"idle" | "checking" | "available" | "unavailable" | "invalid">("idle");
  const [profileMessage, setProfileMessage] = useState<string | null>(null);
  const [passwordMessage, setPasswordMessage] = useState<string | null>(null);
  const [isSubmittingProfile, setIsSubmittingProfile] = useState(false);
  const [isSubmittingPassword, setIsSubmittingPassword] = useState(false);
  const [loadMessage, setLoadMessage] = useState<string | null>(null);
  const [isUploadingImage, setIsUploadingImage] = useState(false);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || "";
  const resolvedProfileImageUrl = profileImageUrl
    ? profileImageUrl.startsWith("http")
      ? profileImageUrl
      : `${apiBaseUrl}${profileImageUrl}`
    : "/default_profile.png";

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
    } catch (error) {
      return;
    }
  }, [session]);

  useEffect(() => {
    const adminEmails = (process.env.NEXT_PUBLIC_ADMIN_EMAILS || "")
      .split(",")
      .map((email) => email.trim().toLowerCase())
      .filter(Boolean);
    const currentEmail = session?.user?.email || null;
    if (currentEmail && adminEmails.includes(currentEmail.toLowerCase())) {
      if (typeof window !== "undefined") {
        window.location.href = "/admin";
      }
    }
    if (typeof window !== "undefined") {
      const stored = localStorage.getItem("localAuth");
      if (!stored) return;
      try {
        const parsed = JSON.parse(stored);
        if (parsed?.isAdmin) {
          window.location.href = "/admin";
        }
      } catch (error) {
        return;
      }
    }
  }, [session]);

  useEffect(() => {
    if (!memberId) return;
    const controller = new AbortController();

    const loadProfile = async () => {
      try {
        const response = await fetch(`${apiBaseUrl}/users/profile/${memberId}`, {
          signal: controller.signal,
        });
        if (!response.ok) {
          if (response.status === 404) {
            setLoadMessage("회원 정보를 찾을 수 없습니다. 다시 로그인해주세요.");
            if (typeof window !== "undefined") {
              localStorage.removeItem("localAuth");
            }
          }
          return;
        }
        const data = (await response.json()) as ProfileData;
        setProfile(data);
        if (data?.member_id) {
          setMemberId(String(data.member_id));
        }
        setNickname(data.nickname || "");
        setProfileImageUrl(data.profile_image_url || "");
        setName(data.name || "");
        setSex((data.sex as "M" | "F" | "") || "");
        setPhoneNo(data.phone_no || "");
        setAddress(data.address || "");
        setEmail(data.email || "");
        setSubEmail(data.sub_email || "");
        setSnsJoin(data.sns_join_yn === "Y");
        setEmailMarketing(data.email_alarm_yn === "Y");
        setSnsMarketing(data.sns_alarm_yn === "Y");
      } catch (error) {
        return;
      }
    };

    loadProfile();

    return () => controller.abort();
  }, [apiBaseUrl, memberId]);

  useEffect(() => {
    if (!nickname) {
      setNicknameStatus("idle");
      return;
    }

    const isValid = /^[A-Za-z0-9가-힣]{2,12}$/.test(nickname);
    if (!isValid) {
      setNicknameStatus("invalid");
      return;
    }

    const timeoutId = window.setTimeout(async () => {
      if (!memberId) return;
      setNicknameStatus("checking");
      try {
        const response = await fetch(
          `${apiBaseUrl}/users/nickname/check?nickname=${encodeURIComponent(nickname)}&member_id=${memberId}`
        );
        const data = await response.json();
        setNicknameStatus(data.available ? "available" : "unavailable");
      } catch (error) {
        setNicknameStatus("idle");
      }
    }, 350);

    return () => window.clearTimeout(timeoutId);
  }, [apiBaseUrl, memberId, nickname]);

  const nicknameHint = useMemo(() => {
    if (nicknameStatus === "invalid") return "2~12자의 한글/영문/숫자만 가능합니다.";
    if (nicknameStatus === "available") return "사용 가능한 닉네임입니다.";
    if (nicknameStatus === "unavailable") return "이미 사용 중인 닉네임입니다.";
    if (nicknameStatus === "checking") return "중복 확인 중...";
    return null;
  }, [nicknameStatus]);

  const handleProfileSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!memberId) return;

    setIsSubmittingProfile(true);
    setProfileMessage(null);

    try {
      const response = await fetch(`${apiBaseUrl}/users/profile/${memberId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          nickname: nickname.trim() || null,
          profile_image_url: profileImageUrl.trim() || null,
          name: name.trim() || null,
          sex: sex || null,
          phone_no: phoneNo.trim() || null,
          address: address.trim() || null,
          email: email.trim() || null,
          sub_email: subEmail.trim() || null,
          sns_join_yn: snsJoin ? "Y" : "N",
          email_alarm_yn: emailMarketing ? "Y" : "N",
          sns_alarm_yn: snsMarketing ? "Y" : "N",
        }),
      });

      if (!response.ok) {
        const data = await response.json().catch(() => null);
        setProfileMessage(data?.detail || "회원정보 수정에 실패했습니다.");
        return;
      }

      if (typeof window !== "undefined") {
        const stored = localStorage.getItem("localAuth");
        if (stored) {
          try {
            const parsed = JSON.parse(stored);
            localStorage.setItem(
              "localAuth",
              JSON.stringify({
                ...parsed,
                nickname: nickname.trim() || null,
                email: email.trim() || parsed.email || null,
              })
            );
          } catch (error) {
            // ignore
          }
        }
      }

      setProfileMessage("회원정보가 저장되었습니다.");
    } catch (error) {
      setProfileMessage("회원정보 수정에 실패했습니다.");
    } finally {
      setIsSubmittingProfile(false);
    }
  };

  const handlePasswordSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!memberId) return;

    setIsSubmittingPassword(true);
    setPasswordMessage(null);

    try {
      const response = await fetch(`${apiBaseUrl}/users/profile/${memberId}/password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
          confirm_password: confirmPassword,
        }),
      });

      if (!response.ok) {
        const data = await response.json().catch(() => null);
        setPasswordMessage(data?.detail || "비밀번호 변경에 실패했습니다.");
        return;
      }

      setPasswordMessage("비밀번호가 변경되었습니다.");
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (error) {
      setPasswordMessage("비밀번호 변경에 실패했습니다.");
    } finally {
      setIsSubmittingPassword(false);
    }
  };

  if (!memberId) {
    return (
      <div className="min-h-screen bg-white text-black flex flex-col">
        <Sidebar
          isOpen={isSidebarOpen}
          onClose={() => setIsSidebarOpen(false)}
          context="home"
        />

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

        <main className="flex-1 px-5 py-8 w-full max-w-md mx-auto pt-[72px]">
          <h2 className="text-2xl font-bold mb-3">마이페이지</h2>
          <p className="text-sm text-[#666]">로그인이 필요합니다.</p>
        </main>
      </div>
    );
  }

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

      <main className="flex-1 px-5 py-8 w-full max-w-2xl mx-auto pt-[72px] space-y-10">
        <div>
          <h2 className="text-2xl font-bold">마이페이지</h2>
          <p className="text-sm text-[#666]">회원정보를 관리할 수 있어요.</p>
          {loadMessage && (
            <p className="text-sm text-red-600 mt-2">{loadMessage}</p>
          )}
        </div>

        <form className="space-y-5 rounded-2xl border border-[#EEE] p-6" onSubmit={handleProfileSubmit}>
          <h3 className="text-lg font-semibold">프로필</h3>

          <div className="flex items-center gap-6">
            <div className="w-28 h-28 rounded-full bg-[#F2F2F2] overflow-hidden">
              <img
                src={resolvedProfileImageUrl}
                alt="프로필"
                className="w-full h-full object-cover"
                onError={(event) => {
                  event.currentTarget.src = "/default_profile.png";
                }}
              />
            </div>
            <div className="flex-1 space-y-2">
              <input
                id="profileImage"
                name="profileImage"
                type="file"
                accept="image/*"
                className="hidden"
                onChange={async (event) => {
                  if (!memberId) return;
                  const file = event.target.files?.[0];
                  if (!file) return;
                  setIsUploadingImage(true);
                  try {
                    const formData = new FormData();
                    formData.append("file", file);
                    const response = await fetch(`${apiBaseUrl}/users/profile/${memberId}/image`, {
                      method: "POST",
                      body: formData,
                    });
                    if (!response.ok) {
                      const data = await response.json().catch(() => null);
                      setProfileMessage(data?.detail || "이미지 업로드에 실패했습니다.");
                      return;
                    }
                    const data = await response.json().catch(() => null);
                    if (data?.profile_image_url) {
                      setProfileImageUrl(data.profile_image_url);
                    }
                  } catch (error) {
                    setProfileMessage("이미지 업로드에 실패했습니다.");
                  } finally {
                    setIsUploadingImage(false);
                    event.target.value = "";
                  }
                }}
              />
              <label
                htmlFor="profileImage"
                className="inline-flex items-center gap-2 rounded-xl border border-[#DDD] px-4 py-2 text-sm cursor-pointer hover:bg-[#F7F7F7]"
              >
                <img src="/upload.svg" alt="업로드" className="w-4 h-4" />
                이미지 업로드
              </label>
              {isUploadingImage && (
                <p className="text-xs text-[#666]">업로드 중...</p>
              )}
            </div>
          </div>

          <div className="space-y-2">
            <label htmlFor="nickname" className="text-sm font-medium text-[#333]">닉네임</label>
            <input
              id="nickname"
              name="nickname"
              type="text"
              value={nickname}
              onChange={(event) => setNickname(event.target.value)}
              placeholder="닉네임을 입력하세요"
              className="w-full rounded-xl border border-[#DDD] px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-black/20"
            />
            {nicknameHint && (
              <p className={`text-xs ${nicknameStatus === "available" ? "text-green-600" : "text-red-600"}`}>
                {nicknameHint}
              </p>
            )}
          </div>

          <div className="space-y-2">
            <label htmlFor="subEmail" className="text-sm font-medium text-[#333]">보조 이메일</label>
            <input
              id="subEmail"
              name="subEmail"
              type="email"
              value={subEmail}
              onChange={(event) => setSubEmail(event.target.value)}
              placeholder="보조 이메일을 입력하세요"
              className="w-full rounded-xl border border-[#DDD] px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-black/20"
            />
          </div>

          <h3 className="text-lg font-semibold pt-4">기본정보 설정</h3>

          <div className="space-y-2">
            <label htmlFor="name" className="text-sm font-medium text-[#333]">이름</label>
            <input
              id="name"
              name="name"
              type="text"
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="이름을 입력하세요"
              className="w-full rounded-xl border border-[#DDD] px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-black/20"
            />
          </div>

          <div className="space-y-2">
            <span className="text-sm font-medium text-[#333]">성별</span>
            <div className="flex gap-4">
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="radio"
                  name="sex"
                  value="M"
                  checked={sex === "M"}
                  onChange={() => setSex("M")}
                  className="accent-black"
                />
                남자
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="radio"
                  name="sex"
                  value="F"
                  checked={sex === "F"}
                  onChange={() => setSex("F")}
                  className="accent-black"
                />
                여자
              </label>
            </div>
          </div>

          <div className="space-y-2">
            <label htmlFor="phoneNo" className="text-sm font-medium text-[#333]">핸드폰번호</label>
            <input
              id="phoneNo"
              name="phoneNo"
              type="text"
              value={phoneNo}
              onChange={(event) => setPhoneNo(event.target.value)}
              placeholder="핸드폰번호를 입력하세요"
              className="w-full rounded-xl border border-[#DDD] px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-black/20"
            />
          </div>

          <div className="space-y-2">
            <label htmlFor="address" className="text-sm font-medium text-[#333]">주소</label>
            <input
              id="address"
              name="address"
              type="text"
              value={address}
              onChange={(event) => setAddress(event.target.value)}
              placeholder="주소를 입력하세요"
              className="w-full rounded-xl border border-[#DDD] px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-black/20"
            />
          </div>

          <div className="space-y-2">
            <label htmlFor="email" className="text-sm font-medium text-[#333]">이메일</label>
            <input
              id="email"
              name="email"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="이메일을 입력하세요"
              className="w-full rounded-xl border border-[#DDD] px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-black/20"
            />
          </div>

          <h3 className="text-lg font-semibold pt-4">알림설정</h3>

          <div className="space-y-2">
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                className="accent-black"
                checked={snsJoin}
                onChange={(event) => setSnsJoin(event.target.checked)}
              />
              SNS 가입 여부
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                className="accent-black"
                checked={emailMarketing}
                onChange={(event) => setEmailMarketing(event.target.checked)}
              />
              이메일 알림 수신
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                className="accent-black"
                checked={snsMarketing}
                onChange={(event) => setSnsMarketing(event.target.checked)}
              />
              카톡 알림 수신
            </label>
          </div>

          {profileMessage && (
            <p className="text-xs text-red-600">{profileMessage}</p>
          )}

          <button
            type="submit"
            disabled={isSubmittingProfile}
            className={`w-full py-3 rounded-xl font-bold transition ${
              isSubmittingProfile
                ? "bg-gray-300 text-gray-500 cursor-not-allowed"
                : "bg-black text-white hover:opacity-90"
            }`}
          >
            저장하기
          </button>
        </form>

        <form className="space-y-5 rounded-2xl border border-[#EEE] p-6" onSubmit={handlePasswordSubmit}>
          <h3 className="text-lg font-semibold">비밀번호 변경</h3>

          <div className="space-y-2">
            <label htmlFor="currentPassword" className="text-sm font-medium text-[#333]">현재 비밀번호</label>
            <input
              id="currentPassword"
              name="currentPassword"
              type="password"
              value={currentPassword}
              onChange={(event) => setCurrentPassword(event.target.value)}
              placeholder="현재 비밀번호를 입력하세요"
              className="w-full rounded-xl border border-[#DDD] px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-black/20"
            />
          </div>

          <div className="space-y-2">
            <label htmlFor="newPassword" className="text-sm font-medium text-[#333]">새 비밀번호</label>
            <input
              id="newPassword"
              name="newPassword"
              type="password"
              value={newPassword}
              onChange={(event) => setNewPassword(event.target.value)}
              placeholder="새 비밀번호를 입력하세요"
              className="w-full rounded-xl border border-[#DDD] px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-black/20"
            />
          </div>

          <div className="space-y-2">
            <label htmlFor="confirmPassword" className="text-sm font-medium text-[#333]">새 비밀번호 확인</label>
            <input
              id="confirmPassword"
              name="confirmPassword"
              type="password"
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
              placeholder="새 비밀번호를 다시 입력하세요"
              className="w-full rounded-xl border border-[#DDD] px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-black/20"
            />
          </div>

          {passwordMessage && (
            <p className="text-xs text-red-600">{passwordMessage}</p>
          )}

          <button
            type="submit"
            disabled={isSubmittingPassword}
            className={`w-full py-3 rounded-xl font-bold transition ${
              isSubmittingPassword
                ? "bg-gray-300 text-gray-500 cursor-not-allowed"
                : "bg-black text-white hover:opacity-90"
            }`}
          >
            비밀번호 변경
          </button>
        </form>

        <section className="space-y-4 rounded-2xl border border-[#F4DADA] p-6">
          <h3 className="text-lg font-semibold text-red-600">회원탈퇴</h3>
          <p className="text-sm text-[#666]">탈퇴 요청 시 계정은 탈퇴 요청 상태로 전환됩니다.</p>
          <button
            type="button"
            onClick={async () => {
              if (!memberId) return;
              if (!window.confirm("탈퇴 요청일로부터 7일까지는 데이터가 유지됩니다. 정말 탈퇴처리하시겠습니까?")) return;
              try {
                const response = await fetch(`${apiBaseUrl}/users/profile/${memberId}/withdraw`, {
                  method: "POST",
                });
                if (!response.ok) {
                  const data = await response.json().catch(() => null);
                  setProfileMessage(data?.detail || "탈퇴 요청에 실패했습니다.");
                  return;
                }
                setProfileMessage("탈퇴 요청이 완료되었습니다.");
                if (typeof window !== "undefined") {
                  localStorage.removeItem("localAuth");
                  window.location.href = "/";
                }
              } catch (error) {
                setProfileMessage("탈퇴 요청에 실패했습니다.");
              }
            }}
            className="w-full py-3 rounded-xl font-bold text-white bg-red-600 hover:bg-red-700 transition"
          >
            회원탈퇴
          </button>
        </section>
      </main>
    </div>
  );
}
