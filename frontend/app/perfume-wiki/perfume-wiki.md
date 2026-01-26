### 라우팅 구조
```
/perfume-wiki
  → 시리즈별 시리즈 카드 목록 페이지

/perfume-wiki/[seriesId]
  → 시리즈 상세 + EP 리스트 페이지

/perfume-wiki/[seriesId]/[episodeId]
  → EP 상세 콘텐츠 페이지
```

### 컴포넌트
```
_components/
├── SeasonSection.tsx          # 시리즈별 섹션
├── SeriesGrid.tsx             # 시리즈 카드 그리드
├── SeriesCard.tsx             # 시리즈 카드
├── SeriesHeader.tsx           # 시리즈 상세 헤더
├── EpisodeListItem.tsx        # EP 리스트 아이템 (링크 포함)
├── EpisodeHero.tsx            # EP Hero 영역
├── EpisodeContentSection.tsx # EP 본문 섹션
├── EpisodeCTA.tsx             # EP CTA 버튼
├── SeriesRelatedCard.tsx      # 시리즈 연결 카드
├── TagList.tsx                # 태그 리스트
├── LikeButton.tsx             # 좋아요 버튼 (클라이언트)
├── ShareButton.tsx            # 공유 버튼 (클라이언트)
└── Pagination.tsx             # 페이지네이션
```

- 좋아요/공유 상태 localStorage에 저장