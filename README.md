# 싸인해주세요 소셜 마케팅 자동화

이 폴더는 `context.md`를 기반으로 Instagram, Threads, X용 소셜 콘텐츠를 만들고 Buffer API로 예약 업로드하기 위한 마케팅 에이전트팀 작업 공간입니다.

## 목표

사용자가 "마케팅캠페인 시작하자"라고 지시하면 다음 흐름을 실행합니다.

1. `context.md`를 읽어 싸인해주세요의 무료 전략, 타깃, 금지 표현을 확인합니다.
2. 소상공인 고객 문제를 정리합니다.
3. Instagram, Threads, X에 맞게 콘텐츠를 기획합니다.
4. 채널별 카피를 작성합니다.
5. Instagram 카드뉴스 SVG와 GitHub Pages용 PNG 파일을 생성합니다.
6. 글자 수, 금지 표현, 무료 전략 일관성을 검수합니다.
7. Buffer API용 예약 게시 페이로드를 생성합니다.
8. 설정이 완료되어 있으면 매일 오전 9시와 오후 9시에 예약 업로드합니다.

## 빠른 실행

기본 실행은 실제 업로드하지 않는 `dry-run`입니다.

```bash
python3 scripts/marketing_campaign.py --days 7
```

결과는 `output/campaigns/<run-id>/` 아래에 생성됩니다.

- `campaign.json`: 전체 콘텐츠
- `buffer_payloads.json`: Buffer API로 보낼 페이로드
- `review.json`: 검수 결과
- `summary.json`: 실행 요약
- 각 슬롯 폴더의 `cards/*.svg`: 원본 카드뉴스 파일
- `docs/assets/.../*.png`: GitHub Pages에 올릴 공개 카드뉴스 이미지

## Buffer 설정

1. `.env.example`을 복사해 `.env`를 만듭니다.
2. Buffer Settings > API에서 personal key를 발급합니다.
3. `.env`에 `BUFFER_API_KEY`를 넣습니다.
4. Buffer에 연결된 Instagram, Threads, X 채널 ID를 각각 넣습니다.
5. 실제 예약 업로드 시에만 `DRY_RUN=false`로 바꿉니다.

```bash
cp .env.example .env
```

채널 ID 조회:

```bash
python3 scripts/marketing_campaign.py --list-channels
```

실제 Buffer 예약 업로드:

```bash
DRY_RUN=false python3 scripts/marketing_campaign.py --days 7 --publish
```

`PUBLIC_ASSET_BASE_URL`이 설정되어 있고 `PUSH_ASSETS_BEFORE_PUBLISH=true`이면, 실제 Buffer 예약 업로드 전에 `docs/assets` 변경분을 자동으로 commit/push합니다. 이렇게 해야 Buffer가 예약 시점에 카드뉴스 이미지를 공개 URL에서 가져갈 수 있습니다.

## 예약 시간

기본 예약 시간은 한국시간 매일 오전 9시와 오후 9시입니다.

```env
TIMEZONE=Asia/Seoul
POST_TIMES=09:00,21:00
```

스크립트는 실행 시점 이후의 가장 가까운 예약 슬롯부터 `--days`일치 콘텐츠를 생성합니다. 예를 들어 `--days 7`이면 총 14개 슬롯이 만들어집니다.

## GitHub Pages 무료 이미지 호스팅

Buffer API는 이미지 파일 직접 업로드를 지원하지 않습니다. 이미지가 포함된 게시물을 만들려면 카드뉴스 이미지를 공개 HTTPS URL로 제공해야 합니다. 무료 운영은 GitHub Pages를 추천합니다.

이 프로젝트는 실행할 때마다 카드뉴스 원본 SVG를 만들고, GitHub Pages가 서빙할 `docs/assets/.../*.png` 파일로 export합니다.

GitHub Pages 설정 순서:

1. 이 폴더를 GitHub 저장소로 올립니다.
2. GitHub 저장소의 Settings > Pages로 이동합니다.
3. Build and deployment에서 Source를 `Deploy from a branch`로 선택합니다.
4. Branch는 `main`, Folder는 `/docs`로 선택합니다.
5. 저장 후 Pages URL을 확인합니다.
6. `.env`의 `PUBLIC_ASSET_BASE_URL`에 Pages 사이트 루트를 넣습니다.

예를 들어 GitHub Pages URL이 아래와 같다면:

```text
https://hslee.github.io/signplease-marketing
```

`.env`는 이렇게 설정합니다.

```env
PUBLIC_ASSET_BASE_URL=https://hslee.github.io/signplease-marketing
ASSET_EXPORT_DIR=docs
```

그러면 스크립트가 Buffer 페이로드에 아래 같은 공개 PNG URL을 넣습니다.

```text
https://hslee.github.io/signplease-marketing/assets/campaigns/<run-id>/01-.../cards/slide-01.png
```

이 값이 비어 있으면 카드뉴스 PNG는 `docs/assets`에 생성되지만, Buffer 페이로드에는 이미지가 첨부되지 않습니다.

## 현재 구현 범위

- 고객 리서치 관점의 문제/오해/관점 전환 생성
- Instagram 카드뉴스 원고, SVG, GitHub Pages용 PNG 생성
- Threads 대화체 카피 생성
- X 280자 이내 카피 생성
- 금지 표현 및 무료 전략 검수
- Buffer GraphQL `createPost` 페이로드 생성
- `DRY_RUN=false`와 `--publish`가 모두 있을 때 실제 Buffer API 호출

## 아직 사람이 확인해야 하는 값

- `BUFFER_API_KEY`
- `BUFFER_CHANNEL_INSTAGRAM`
- `BUFFER_CHANNEL_THREADS`
- `BUFFER_CHANNEL_X`
- Instagram 카드뉴스를 실제 첨부하려면 `PUBLIC_ASSET_BASE_URL`
- GitHub Pages export 폴더인 `ASSET_EXPORT_DIR`

## Buffer API 메모

- Endpoint: `https://api.buffer.com`
- Auth: `Authorization: Bearer <BUFFER_API_KEY>`
- 예약 게시: `createPost`
- 예약 모드: `customScheduled`
- 예약 시간: `dueAt`에 UTC ISO 8601 timestamp
- 채널별로 mutation을 각각 호출해야 합니다.
