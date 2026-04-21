# P5-6 PA7 Narrow Review Precision and First Symbol Focus Tracking

## 목표

`P5-5`가 전이 알림을 맡는다면, `P5-6`은 그 전이 뒤에 남는 두 가지 운영 질문을 더 잘 보이게 만드는 단계다.

1. 남아 있는 `PA7 narrow review` 그룹이 정확히 어떤 종류의 혼합 review인지
2. `BTCUSD first symbol`이 아직 `WATCHLIST`일 때도 진행도가 실제로 얼마나 쌓이고 있는지

## 구현 범위

### 1. PA7 narrow review 정밀 runtime

- 입력: `checkpoint_pa7_review_processor_latest.json`
- 출력:
  - `checkpoint_improvement_pa7_narrow_review_latest.json`
  - `checkpoint_improvement_pa7_narrow_review_latest.md`

정리 항목:

- `WAIT 경계 혼합 review`
- `일반 혼합 review`
- group key
- severity score
- 왜 다시 봐야 하는지
- 어떤 lens로 재검토해야 하는지

### 2. First symbol focus tracking runtime

- 입력: master board readiness state
- 출력:
  - `checkpoint_improvement_first_symbol_focus_latest.json`
  - `checkpoint_improvement_first_symbol_focus_latest.md`

정리 항목:

- 현재 symbol / status / stage
- progress %
- 이전 대비 delta %
- progress bucket
- active trigger count
- next required action

## 기대 효과

- `PA7 narrow review 2건`이 단순 count가 아니라 실제 review 대상 두 줄로 읽힌다.
- `BTCUSD`가 아직 `WATCHLIST`이어도 "아예 멈춤"인지 "조금씩 올라오는 중"인지 보인다.
- `orchestrator watch` 결과 안에서 `전이 알림`, `집중 관찰 진행도`, `PA7 재검토 대상`이 함께 보인다.
