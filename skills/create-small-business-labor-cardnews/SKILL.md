---
name: create-small-business-labor-cardnews
description: Create, review, and optionally schedule Korean Instagram and Threads labor card-news campaigns for 싸인해주세요 using concrete questions from small-business owners. Use whenever planning, writing, redesigning, reviewing, or publishing 소상공인 노무 카드뉴스, including requests mentioning 노무 질문, 알바 고용, 근로계약서, 주휴수당, 5인 미만, 3.3%, 해고, Buffer 예약 발행, Instagram 카드뉴스, or Threads posts.
---

# 소상공인 노무 카드뉴스 제작

## 필수 입력

1. 프로젝트 루트의 `AGENTS.md`와 `context.md`를 읽는다.
2. `references/topic-db.md`에서 실제 사장님 질문과 관련 주제를 검색한다. 파일 전체를 매번 불러오기보다 다음 검색을 우선 사용한다.

```bash
rg -n "<질문 키워드>|^### LABOR-|대표 실제 질문" skills/create-small-business-labor-cardnews/references/topic-db.md
```

3. 기존 `topics_week_*.json` 및 이미 예약·게시된 캠페인을 확인한다.

## 제작 절차

1. 추상적인 법률 항목이 아니라 하나의 구체적인 사건을 고른다. 업종, 근무시간, 당사자 행동, 금액 또는 문제 발언 중 최소 2개를 명시한다.
2. 질문을 사장님이 검색창에 입력할 말로 쓴다.
3. 후보를 JSON 배열로 저장하고 다음 검사를 통과시킨다.

```bash
python3 scripts/check_topic_overlap.py --proposed-file <proposed.json>
```

4. `direct`는 폐기한다. `similar`는 새로운 사건·조건·행동 가이드가 명확할 때만 사용한다.
5. 게시일 기준 대한민국 공식 출처를 확인한다. 숫자, 적용 기준, 예외, 제재는 법령·정부·공단 자료만 근거로 사용하고 `evidence_registry.json`에 URL, 검토일, 만료일, 사실을 기록한다.
6. 한 게시물은 다음 5장으로 구성한다.
   - 1장: 구체적 현장 상황과 질문
   - 2장: 단정하지 않는 두괄식 결론
   - 3장: 판단 기준 또는 가장 흔한 오해
   - 4장: 사장님이 바로 할 행동 3단계 이내
   - 5장: 한 줄 정리와 자연스러운 CTA
7. 제품 소개만 하는 슬라이드를 만들지 않는다. 먼저 실제 행동 가이드를 제공한 뒤 마지막 카드와 카피에서 다음처럼 연결한다.
   - 합의한 근로조건을 문서로 남기는 것이 노무 리스크를 줄이는 첫 단계라고 설명한다.
   - `무료 전자근로계약서 싸인해주세요`로 작성·서명·보관을 챙기도록 안내한다.
   - 전자근로계약서가 모든 분쟁이나 제재를 완전히 방지한다고 주장하지 않는다.
8. 모든 게시글 마지막에 정확히 다음 CTA를 넣는다.

```text
지금 바로 시작해보세요.
https://signplease.kr
```

Instagram URL에는 UTM을 넣지 않는다. Threads에는 `utm_source=threads`를 붙인다. 브랜드명은 게시글 마지막 전환부에서 1회만 사용한다.

## 디자인

- 사용자가 사진형 잡지 디자인을 원하면 `$imagegen`을 사용한다.
- 배경은 슬라이드 상황에 맞는 서로 다른 사진으로 새로 생성한다.
- 참고 이미지는 분위기·여백·명암 참고용으로만 사용하고 텍스트·브랜드·인물·정확한 레이아웃을 복제하지 않는다.
- ImageGen에는 읽을 수 있는 텍스트를 생성하지 않는다. 정확한 한글은 SVG에서 조판한다.
- 사진 위에 어두운 딤을 적용하고 흰색 본문과 노란색 강조색으로 가독성을 확보한다.
- SVG 원본과 1080×1350 PNG를 모두 저장한다.
- PNG는 `docs/assets/campaigns/<run-id>/.../cards/`에도 export한다.

## 게시 전 검수

- 구체적 상황, 두괄식 결론, 오해 또는 판단 기준, 행동 가이드가 있는지 확인한다.
- `무조건`, `100%`, `완벽`, `노동청 신고 피하기`처럼 과장되거나 회피를 조장하는 표현을 제거한다.
- 사실관계에 따라 달라질 때 면책 문구와 확인 기관을 넣는다.
- 브랜드 1회, 필수 CTA, 플랫폼별 URL, 공식 근거와 검토일을 확인한다.
- 카드 5장, PNG 1080×1350, 캡션 길이, Buffer payload와 이미지 URL 수를 기계적으로 확인한다.

## Buffer 예약 발행

1. `.env`의 비밀값을 출력하거나 코드에 저장하지 않는다.
2. 게시 직전에 Instagram과 Threads의 현재 예약 수를 Buffer API로 조회한다.
3. 무료 플랜의 채널당 10건에서 현재 예약 수를 뺀 값만큼만 새 콘텐츠를 만든다. 두 채널에 함께 올릴 때는 두 채널 중 더 적은 잔여 슬롯을 제작 개수로 사용한다.
4. `POST_TIMES`의 오전 9시·오후 9시 순서로 미래 슬롯을 배정한다.
5. Instagram에는 5장 carousel, Threads에는 첫 카드를 첨부한다.
6. 에셋을 GitHub Pages에 배포한 뒤 모든 첨부 URL이 HTTP 200과 이미지 Content-Type을 반환할 때까지 기다린다.
7. Buffer 응답에 post id가 있을 때만 성공으로 기록한다.
8. 한도 오류가 발생한 payload는 `pending_payloads.json`에 남기고 성공으로 세지 않는다.

## 결과물

각 실행 디렉터리에 `campaign.json`, 각 게시물의 `content.json`, `review.json`, `buffer_payloads.json`, `publish_results_approved.json`, `summary.json`, SVG와 PNG를 보관한다. 최종 보고에는 예약된 플랫폼별 post id와 예정 시각, 실패·대기 건수, 저장 경로를 포함한다.
