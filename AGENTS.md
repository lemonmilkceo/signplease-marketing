# Marketing Agent Instructions

항상 한국어로 응답한다.

사용자가 "마케팅캠페인 시작하자"라고 말하면, 이 워크스페이스에서는 다음 작업을 실행한다.

1. `context.md`를 읽고 싸인해주세요의 현재 포지셔닝, 무료 전략, 타깃, 금지 표현을 확인한다.
2. 고객 리서치 관점에서 오늘 다룰 소상공인 문제를 정한다.
3. Instagram, Threads, X 각각에 맞는 콘텐츠 기획과 카피를 만든다.
4. Instagram용 카드뉴스 원고, SVG 원본, GitHub Pages용 PNG 카드 파일을 생성한다.
5. 금지 표현, 과장된 법률 표현, 글자 수, 무료 전략 일관성을 검토한다.
6. 문제가 있으면 재생성하고, 문제가 없으면 Buffer API 예약 업로드를 준비한다.
7. Buffer API 키와 채널 ID가 준비되어 있고 `DRY_RUN=false`이면 오전 9시와 오후 9시 일정으로 예약 업로드한다.
8. API 키나 채널 ID, 공개 이미지 URL이 없으면 실제 업로드 대신 `output/` 아래에 검수 결과와 Buffer 페이로드를 생성한다.
9. 카드뉴스 이미지는 `docs/assets/.../*.png`로 export한다. GitHub Pages의 `/docs` 배포가 켜져 있고 `PUBLIC_ASSET_BASE_URL`이 설정되어 있으면 Buffer에 해당 공개 PNG URL을 첨부한다.

실행 명령:

```bash
python3 scripts/marketing_campaign.py --days 7
```

실제 Buffer 예약 업로드:

```bash
DRY_RUN=false python3 scripts/marketing_campaign.py --days 7 --publish
```

비밀값은 절대 코드에 저장하지 않는다. `.env` 또는 실행 환경 변수만 사용한다.
