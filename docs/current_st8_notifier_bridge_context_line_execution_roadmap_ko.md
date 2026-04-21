# ST8 Notifier Bridge Context Line 실행 로드맵

## 실행 범위

- notifier
  - [notifier.py](C:\Users\bhs33\Desktop\project\cfd\backend\integrations\notifier.py)
- 테스트
  - [test_telegram_notifier.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_telegram_notifier.py)

## 단계

### ST8-1. Context Summary Helper 추가

- HTF 정렬 요약
- previous box 요약
- late chase 요약
- share 요약
- 최종 `context_line` 조립 helper 추가

### ST8-2. Formatter 연결

- `format_entry_message(...)`
- `format_wait_message(...)`
- `format_reverse_message(...)`

세 formatter에 동일한 방식으로 `맥락:` 한 줄 연결

### ST8-3. Fallback 정리

- 세부 요약이 비어 있을 때
  - `context_conflict_label_ko` fallback 허용
- context가 전혀 없으면
  - 메시지 포맷 유지

### ST8-4. Unit Test

- context helper 단위 테스트
- entry message context line 테스트
- wait message context line 테스트
- reverse message context line 테스트

## 결과물

- notifier가 state-first context를 직접 읽는 얇은 reader가 됨
- detector를 보지 않아도 runtime row만으로 `맥락:` 한 줄을 만들 수 있음
- 텔레그램 DM에서 큰 그림 경고가 더 빨리 읽힘

## 다음 단계

- `ST9 proposal / hindsight bridge`
  - detector / notifier가 읽는 같은 context contract를
    review backlog와 hindsight label에도 이어 붙이기
