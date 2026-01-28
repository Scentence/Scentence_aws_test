"use client";

import React from "react";
import { usePerfumeNetwork } from "./use-perfume-network";
import NMapHeader from "./components/NMapHeader";
import NMapFilters from "./components/NMapFilters";
import NMapGraphSection from "./components/NMapGraphSection";
import NMapDetailPanel from "./components/NMapDetailPanel";
import CardTriggerBanner from "@/app/perfume-network/shared/CardTriggerBanner";
import LoadingOverlay from "@/app/perfume-network/shared/LoadingOverlay";
import ScentCardModal from "@/app/perfume-network/ncard/ScentCardModal";

export default function NMapView({ sessionUserId }: { sessionUserId?: string | number }) {
  const {
    fullPayload,
    labelsData,
    filterOptions,
    status,
    minSimilarity, setMinSimilarity,
    topAccords, setTopAccords,
    selectedAccords, setSelectedAccords,
    selectedBrands, setSelectedBrands,
    selectedSeasons, setSelectedSeasons,
    selectedOccasions, setSelectedOccasions,
    selectedGenders, setSelectedGenders,
    selectedPerfumeId, setSelectedPerfumeId,
    memberId,
    displayLimit, setDisplayLimit,
    showMyPerfumesOnly, setShowMyPerfumesOnly,
    scentSessionId,
    showCardTrigger, setShowCardTrigger,
    triggerMessage,
    isGeneratingCard,
    showCardModal, setShowCardModal,
    generatedCard, setGeneratedCard,
    generatedCardId, setGeneratedCardId,
    cardTriggerReady,
    error, setError,
    logActivity,
    handleGenerateCard,
    myPerfumeIds,
    myPerfumeFilters,
  } = usePerfumeNetwork(sessionUserId);

  const [showLoginPrompt, setShowLoginPrompt] = React.useState(false);

  return (
    <div className="min-h-screen bg-[#F5F2EA] text-[#1F1F1F]">
      <div className="max-w-7xl mx-auto px-6 py-12 space-y-12">
        <NMapHeader />

        <NMapFilters
          filterOptions={filterOptions}
          labelsData={labelsData}
          selectedAccords={selectedAccords}
          setSelectedAccords={setSelectedAccords}
          selectedBrands={selectedBrands}
          setSelectedBrands={setSelectedBrands}
          selectedSeasons={selectedSeasons}
          setSelectedSeasons={setSelectedSeasons}
          selectedOccasions={selectedOccasions}
          setSelectedOccasions={setSelectedOccasions}
          selectedGenders={selectedGenders}
          setSelectedGenders={setSelectedGenders}
          setSelectedPerfumeId={setSelectedPerfumeId}
          logActivity={logActivity}
          showMyPerfumesOnly={showMyPerfumesOnly}
          myPerfumeFilters={myPerfumeFilters}
        />

        <div className="border-t-2 border-[#E6DDCF]"></div>

        <section className="space-y-4">
          <div>
            <h2 className="text-lg font-semibold">향수 지도</h2>
            <p className="text-xs text-[#7A6B57]">궁금한 향수를 클릭하면, 유사한 향수가 나타나요.</p>
          </div>

          <div className="grid gap-6 lg:grid-cols-[1fr_340px]">
            <NMapGraphSection
              fullPayload={fullPayload}
              labelsData={labelsData}
              selectedPerfumeId={selectedPerfumeId}
              setSelectedPerfumeId={setSelectedPerfumeId}
              displayLimit={displayLimit}
              setDisplayLimit={setDisplayLimit}
              minSimilarity={minSimilarity}
              setMinSimilarity={setMinSimilarity}
              topAccords={topAccords}
              selectedAccords={selectedAccords}
              selectedBrands={selectedBrands}
              selectedSeasons={selectedSeasons}
              selectedOccasions={selectedOccasions}
              selectedGenders={selectedGenders}
              showMyPerfumesOnly={showMyPerfumesOnly}
              myPerfumeIds={myPerfumeIds}
              logActivity={logActivity}
              memberId={memberId}
              setShowLoginPrompt={setShowLoginPrompt}
              setShowMyPerfumesOnly={setShowMyPerfumesOnly}
            />
            <NMapDetailPanel
              selectedPerfumeId={selectedPerfumeId}
              fullPayload={fullPayload}
              labelsData={labelsData}
              selectedAccords={selectedAccords}
              logActivity={logActivity}
            />
          </div>
        </section>
      </div>

      {showLoginPrompt && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-center justify-center p-6">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm p-6 text-center space-y-4">
            <div className="text-3xl">🔒</div>
            <h3 className="text-lg font-semibold text-[#2E2B28]">로그인이 필요해요</h3>
            <p className="text-xs text-[#7A6B57]">내 향수로 보기는 회원 전용 기능입니다. 로그인 후 더 편하게 이용할 수 있어요.</p>
            <div className="flex gap-2">
              <a href="/login" className="flex-1 h-9 rounded-full bg-[#C8A24D] text-white text-xs font-semibold flex items-center justify-center">로그인하러 가기</a>
              <button onClick={() => setShowLoginPrompt(false)} className="flex-1 h-9 rounded-full border border-[#E2D7C5] text-xs font-semibold">닫기</button>
            </div>
          </div>
        </div>
      )}

      {showCardTrigger && (
        <CardTriggerBanner
          message={triggerMessage}
          onAccept={handleGenerateCard}
          onDismiss={() => setShowCardTrigger(false)}
        />
      )}

      {isGeneratingCard && <LoadingOverlay />}

      {error && (
        <div className="fixed bottom-24 left-1/2 transform -translate-x-1/2 z-50 max-w-md w-full mx-6 animate-fade-in">
          <div className="bg-white border-2 border-red-300 rounded-2xl shadow-2xl p-6">
            <div className="flex items-start gap-4">
              <div className="flex-shrink-0 w-12 h-12 rounded-full bg-red-100 flex items-center justify-center"><span className="text-2xl">⚠️</span></div>
              <div className="flex-1">
                <h3 className="text-base font-bold text-red-700 mb-1">오류가 발생했습니다</h3>
                <p className="text-sm text-red-600 leading-relaxed">{error}</p>
              </div>
              <button onClick={() => setError(null)} className="flex-shrink-0 w-8 h-8 rounded-full hover:bg-red-100 flex items-center justify-center transition-colors"><span className="text-xl">×</span></button>
            </div>
            <div className="mt-4 flex gap-2">
              <button onClick={handleGenerateCard} className="flex-1 py-2.5 bg-gradient-to-r from-red-500 to-red-600 text-white rounded-xl font-semibold">다시 시도하기</button>
              <button onClick={() => setError(null)} className="px-6 py-2.5 border-2 border-red-200 text-red-600 rounded-xl font-semibold">닫기</button>
            </div>
          </div>
        </div>
      )}

      {/* 고정 버튼 (하단 우측) */}
      <div className="fixed bottom-6 right-6 z-50">
        <button
          onClick={() => cardTriggerReady ? handleGenerateCard() : alert("아직 정보가 충분하지 않아요. 관심있는 향이나 필터를 더 클릭해보세요!")}
          className={`relative w-16 h-16 rounded-full shadow-2xl flex items-center justify-center text-3xl transition-all duration-300 group ${cardTriggerReady ? "bg-gradient-to-br from-[#6B4E71] via-[#8B6E8F] to-[#9B7EAC] animate-pulse-glow hover:scale-110" : "bg-gradient-to-br from-[#6B4E71] to-[#8B6E8F] hover:scale-105"}`}
          title={cardTriggerReady ? "나의 향 MBTI 확인하기 (준비 완료!)" : "더 많은 향기를 탐색해보세요"}
        >
          {cardTriggerReady && <div className="absolute inset-0 rounded-full bg-gradient-to-r from-transparent via-white to-transparent opacity-30 animate-shimmer"></div>}
          <span className={`relative z-10 transition-transform duration-300 ${cardTriggerReady ? "group-hover:rotate-12" : "group-hover:scale-110"}`}>🫧</span>
          {cardTriggerReady && <span className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 rounded-full flex items-center justify-center text-white text-xs font-bold animate-bounce">!</span>}
        </button>
        {cardTriggerReady && (
          <div className="absolute bottom-full right-0 mb-3 bg-[#2E2B28] text-white px-4 py-2 rounded-lg text-xs font-medium whitespace-nowrap shadow-lg">
            나의 향 MBTI 확인 준비 완료! 🎉
          </div>
        )}
      </div>

      {showCardModal && generatedCard && (
        <ScentCardModal
          card={generatedCard}
          onClose={() => { setShowCardModal(false); setGeneratedCard(null); setGeneratedCardId(null); }}
          onSave={() => alert("카드가 저장되었습니다!")}
          onContinueExplore={() => { setShowCardModal(false); setGeneratedCard(null); setGeneratedCardId(null); }}
          sessionId={scentSessionId || undefined}
          cardId={generatedCardId || undefined}
          isLoggedIn={!!memberId}
        />
      )}
    </div>
  );
}
