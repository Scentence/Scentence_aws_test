'use client';

import { FormEvent, useMemo, useState } from "react";
import Link from "next/link";
import Sidebar from "@/components/common/sidebar";
import { useRouter } from "next/navigation";

export default function SignupPage() {
  const router = useRouter();
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [termsAgree, setTermsAgree] = useState(false);
  const [privacyAgree, setPrivacyAgree] = useState(false);
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [sex, setSex] = useState<"M" | "F" | "">("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isPasswordVisible, setIsPasswordVisible] = useState(false);
  const [isConfirmVisible, setIsConfirmVisible] = useState(false);
  const [hasTypedConfirm, setHasTypedConfirm] = useState(false);
  const [submitMessage, setSubmitMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const allAgree = termsAgree && privacyAgree;

  const handleAllAgreeChange = (checked: boolean) => {
    setTermsAgree(checked);
    setPrivacyAgree(checked);
  };

  const handleTermsChange = (checked: boolean) => {
    setTermsAgree(checked);
  };

  const handlePrivacyChange = (checked: boolean) => {
    setPrivacyAgree(checked);
  };

  const passwordRules = useMemo(() => {
    const minLength = password.length >= 8;
    const allowedSpecialsOnly = password.length > 0 && /^[A-Za-z\d!@#$%]*$/.test(password);
    const hasLower = /[a-z]/.test(password);
    const hasUpper = /[A-Z]/.test(password);
    const hasNumber = /\d/.test(password);
    const hasSpecial = /[!@#$%]/.test(password);
    const hasRequiredSets = hasLower && hasUpper && hasNumber && hasSpecial;

    return {
      minLength,
      hasRequiredSets,
      allowedSpecialsOnly,
    };
  }, [password]);

  const confirmMessage = useMemo(() => {
    if (!hasTypedConfirm) return null;
    if (confirmPassword.length === 0) {
      return { text: "비밀번호가 일치하지 않습니다.", isMatch: false };
    }
    if (password === confirmPassword) {
      return { text: "비밀번호가 일치합니다.", isMatch: true };
    }
    return { text: "비밀번호가 일치하지 않습니다.", isMatch: false };
  }, [confirmPassword, hasTypedConfirm, password]);

  const canSubmit =
    email.trim().length > 0 &&
    passwordRules.minLength &&
    passwordRules.hasRequiredSets &&
    passwordRules.allowedSpecialsOnly &&
    password === confirmPassword &&
    termsAgree &&
    privacyAgree;

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!canSubmit) {
      setSubmitMessage("필수 항목을 확인해주세요.");
      return;
    }

    setIsSubmitting(true);
    setSubmitMessage(null);

    try {
      const response = await fetch("/api/users/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: email.trim(),
          password,
          name: name.trim() || null,
          sex: sex || null,
          req_agr_yn: termsAgree && privacyAgree ? "Y" : "N",
        }),
      });

      if (!response.ok) {
        const data = await response.json().catch(() => null);
        const detail = data?.detail || "회원가입에 실패했습니다.";
        setSubmitMessage(detail);
        return;
      }

      router.push("/login");
    } catch (error) {
      setSubmitMessage("회원가입에 실패했습니다.");
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
          <h2 className="text-2xl font-bold">회원가입</h2>
          <p className="text-sm text-[#666]">필수 정보를 입력해주세요.</p>
        </div>

        <form className="space-y-5" onSubmit={handleSubmit}>
          <div className="space-y-2">
            <label htmlFor="email" className="text-sm font-medium text-[#333]">이메일</label>
            <input
              id="email"
              name="email"
              type="email"
              placeholder="example@email.com"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="w-full rounded-xl border border-[#DDD] px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-black/20"
            />
          </div>

          <div className="space-y-2">
            <label htmlFor="password" className="text-sm font-medium text-[#333]">비밀번호</label>
            <div className="relative">
              <input
                id="password"
                name="password"
                type={isPasswordVisible ? "text" : "password"}
                placeholder="비밀번호를 입력하세요"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                className="w-full rounded-xl border border-[#DDD] px-4 py-3 pr-12 text-sm focus:outline-none focus:ring-2 focus:ring-black/20"
              />
              <button
                type="button"
                className="absolute right-3 top-1/2 -translate-y-1/2 p-1"
                onMouseDown={() => setIsPasswordVisible(true)}
                onMouseUp={() => setIsPasswordVisible(false)}
                onMouseLeave={() => setIsPasswordVisible(false)}
                onTouchStart={() => setIsPasswordVisible(true)}
                onTouchEnd={() => setIsPasswordVisible(false)}
                aria-label="비밀번호 보기"
              >
                <img src="/eye.svg" alt="비밀번호 보기" className="w-5 h-5" />
              </button>
            </div>
            <div className="space-y-2 text-xs">
              <div className="flex items-start gap-2">
                <span className={`mt-1 inline-block w-2 h-2 rounded-full ${passwordRules.minLength ? "bg-green-500" : "bg-red-500"}`} />
                <p className={`${passwordRules.minLength ? "text-green-600" : "text-red-600"}`}>비밀번호는 8자리 이상이어야 합니다.</p>
              </div>
              <div className="flex items-start gap-2">
                <span className={`mt-1 inline-block w-2 h-2 rounded-full ${passwordRules.hasRequiredSets ? "bg-green-500" : "bg-red-500"}`} />
                <p className={`${passwordRules.hasRequiredSets ? "text-green-600" : "text-red-600"}`}>대소문자, 숫자, 특수문자를 각각 하나 이상 포함해야 합니다.</p>
              </div>
              <div className="flex items-start gap-2">
                <span className={`mt-1 inline-block w-2 h-2 rounded-full ${passwordRules.allowedSpecialsOnly ? "bg-green-500" : "bg-red-500"}`} />
                <p className={`${passwordRules.allowedSpecialsOnly ? "text-green-600" : "text-red-600"}`}>특수문자는 !, @, #, $, %만 사용 가능합니다.</p>
              </div>
            </div>
          </div>

          <div className="space-y-2">
            <label htmlFor="confirmPassword" className="text-sm font-medium text-[#333]">비밀번호 확인</label>
            <div className="relative">
              <input
                id="confirmPassword"
                name="confirmPassword"
                type={isConfirmVisible ? "text" : "password"}
                placeholder="비밀번호를 다시 입력하세요"
                value={confirmPassword}
                onChange={(event) => {
                  setConfirmPassword(event.target.value);
                  if (!hasTypedConfirm) {
                    setHasTypedConfirm(true);
                  }
                }}
                className="w-full rounded-xl border border-[#DDD] px-4 py-3 pr-12 text-sm focus:outline-none focus:ring-2 focus:ring-black/20"
              />
              <button
                type="button"
                className="absolute right-3 top-1/2 -translate-y-1/2 p-1"
                onMouseDown={() => setIsConfirmVisible(true)}
                onMouseUp={() => setIsConfirmVisible(false)}
                onMouseLeave={() => setIsConfirmVisible(false)}
                onTouchStart={() => setIsConfirmVisible(true)}
                onTouchEnd={() => setIsConfirmVisible(false)}
                aria-label="비밀번호 확인 보기"
              >
                <img src="/eye.svg" alt="비밀번호 확인 보기" className="w-5 h-5" />
              </button>
            </div>
            {confirmMessage && (
              <p className={`text-xs ${confirmMessage.isMatch ? "text-green-600" : "text-red-600"}`}>
                {confirmMessage.text}
              </p>
            )}
          </div>

          <div className="space-y-2">
            <label htmlFor="name" className="text-sm font-medium text-[#333]">이름</label>
            <input
              id="name"
              name="name"
              type="text"
              placeholder="이름을 입력하세요"
              value={name}
              onChange={(event) => setName(event.target.value)}
              className="w-full rounded-xl border border-[#DDD] px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-black/20"
            />
          </div>

          <div className="space-y-2">
            <span className="text-sm font-medium text-[#333]">성별</span>
            <div className="flex gap-4">
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="radio"
                  name="gender"
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
                  name="gender"
                  value="F"
                  checked={sex === "F"}
                  onChange={() => setSex("F")}
                  className="accent-black"
                />
                여자
              </label>
            </div>
          </div>

          <div className="space-y-3 rounded-xl border border-[#EEE] p-4">
            <label className="flex items-center gap-2 text-sm font-semibold">
              <input
                type="checkbox"
                className="accent-black"
                checked={allAgree}
                onChange={(event) => handleAllAgreeChange(event.target.checked)}
              />
              약관 전체동의
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                className="accent-black"
                checked={termsAgree}
                onChange={(event) => handleTermsChange(event.target.checked)}
              />
              이용약관 동의
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                className="accent-black"
                checked={privacyAgree}
                onChange={(event) => handlePrivacyChange(event.target.checked)}
              />
              개인정보 수집 및 이용 동의
            </label>
          </div>

          {submitMessage && (
            <p className="text-xs text-red-600">{submitMessage}</p>
          )}

          <button
            type="submit"
            disabled={!canSubmit || isSubmitting}
            className={`w-full py-3 rounded-xl font-bold transition ${
              !canSubmit || isSubmitting
                ? "bg-gray-300 text-gray-500 cursor-not-allowed"
                : "bg-black text-white hover:opacity-90"
            }`}
          >
            가입 완료
          </button>
        </form>
      </main>
    </div>
  );
}
