# PA8 Canary Scope 영어 용어 해석표

## 목적

`PA8` 관련 아티팩트에는

- `continuation_hold_surface`
- `RUNNER_CHECK`
- `profit_hold_bias`
- `PARTIAL_THEN_HOLD`

처럼 코드용 영어 값이 그대로 남아 있는 경우가 있습니다.

이 문서는 그런 값을 운영자가 바로 읽을 수 있게 한국어로 풀어쓴 해석표입니다.

---

## 핵심 scope 값

### `continuation_hold_surface`
- 한국어 해석: `추세 지속 보유 관리 장면`
- 쉬운 뜻:
  - 이미 방향이 맞게 가는 흐름에서
  - `계속 들고 갈지`, `일부 먼저 챙길지`를 보는 관리 장면
- 지금 NAS100 시험판에서는:
  - 이 장면에서만 행동을 바꿔봅니다

### `RUNNER_CHECK`
- 한국어 해석: `러너 유지 점검 체크포인트`
- 쉬운 뜻:
  - 추세가 계속 이어질 때
  - 포지션을 그대로 runner처럼 더 끌고 가도 되는지 점검하는 체크

### `profit_hold_bias`
- 한국어 해석: `수익 구간 보유 편향`
- 쉬운 뜻:
  - 수익이 나고 있을 때
  - 너무 빨리 끝내지 말고 더 들고 가려는 쪽의 해석

### `HOLD`
- 한국어 해석: `그냥 계속 보유`
- 쉬운 뜻:
  - 부분청산 없이 그대로 들고 있음

### `PARTIAL_THEN_HOLD`
- 한국어 해석: `일부 익절 후 계속 보유`
- 쉬운 뜻:
  - 전부 닫지 않고
  - 일부만 먼저 챙기고 나머지는 계속 들고 가는 방식

---

## NAS100 시험판에서 실제로 바뀌는 것

현재 NAS100 시험판은 아래처럼 읽으면 됩니다.

- 심볼:
  - `NAS100만`
- 장면:
  - `continuation_hold_surface`
- 체크 종류:
  - `RUNNER_CHECK`
- 규칙 계열:
  - `profit_hold_bias`
- 원래 행동:
  - `HOLD`
- 시험 행동:
  - `PARTIAL_THEN_HOLD`

즉 한 줄로 말하면:

`NAS100의 추세 지속 보유 장면에서, 원래는 그냥 HOLD 하던 것을 일부 익절 후 보유로 바꿔보는 좁은 시험`

입니다.

---

## scope snapshot 필드 해석

### `symbol_allowlist`
- 한국어 해석: `적용 심볼 목록`
- 쉬운 뜻:
  - 어느 종목에만 이 시험을 허용할지

### `surface_allowlist`
- 한국어 해석: `적용 장면 목록`
- 쉬운 뜻:
  - 어떤 장면에서만 이 시험을 허용할지

### `checkpoint_type_allowlist`
- 한국어 해석: `적용 체크포인트 유형 목록`
- 쉬운 뜻:
  - 어떤 종류의 체크 결과에만 적용할지

### `family_allowlist`
- 한국어 해석: `적용 규칙 계열 목록`
- 쉬운 뜻:
  - 더 세부적인 문제군/패턴군 제한

### `baseline_action_allowlist`
- 한국어 해석: `원래 행동 허용 목록`
- 쉬운 뜻:
  - 기존 런타임이 어떤 행동을 하려던 장면일 때만 바꿀지

### `candidate_action`
- 한국어 해석: `시험 행동`
- 쉬운 뜻:
  - 이번 canary에서 새로 적용해보는 행동

### `candidate_reason`
- 한국어 해석: `시험 변경 이유 ID`
- 쉬운 뜻:
  - 왜 이 시험 행동으로 바꾸는지 붙는 내부 식별자

### `change_mode = action_only_preview_candidate`
- 한국어 해석: `행동만 바꾸는 preview 후보`
- 쉬운 뜻:
  - 방향/진입/크기까지 바꾸는 게 아니라
  - 행동 하나만 바꿔보는 시험

### `manual_activation_required = true`
- 한국어 해석: `수동 활성화 필요`
- 쉬운 뜻:
  - 자동으로 바로 켜지지 않고
  - 사람이 보고 승인해야 켜짐

### `scene_bias_excluded = true`
- 한국어 해석: `scene bias 변경 제외`
- 쉬운 뜻:
  - 장면 해석 가중치 자체는 안 바꿈

### `size_change_allowed = false`
- 한국어 해석: `사이즈 변경 불가`
- 쉬운 뜻:
  - 포지션 크기는 안 바꿈

### `new_entry_logic_allowed = false`
- 한국어 해석: `새 진입 로직 불가`
- 쉬운 뜻:
  - 새 진입 규칙을 넣는 시험이 아님

---

## guardrail 필드 해석

### `sample_floor`
- 한국어 해석: `최소 표본 수`
- 쉬운 뜻:
  - 이 정도 row는 쌓여야 시험 결과를 진지하게 봄

### `worsened_row_count_ceiling`
- 한국어 해석: `악화 허용 상한`
- 쉬운 뜻:
  - 나빠진 사례를 몇 개까지 허용할지

### `hold_precision_floor`
- 한국어 해석: `보유 판단 최소 정확도`
- 쉬운 뜻:
  - HOLD 계열 판단 정확도가 이 밑으로 떨어지면 안 됨

### `runtime_proxy_match_rate_must_improve`
- 한국어 해석: `런타임 대리일치율은 개선되어야 함`
- 쉬운 뜻:
  - 새 시험이 기존보다 더 잘 맞아야 함

### `partial_then_hold_quality_must_not_regress`
- 한국어 해석: `일부 익절 후 보유 품질은 나빠지면 안 됨`
- 쉬운 뜻:
  - `PARTIAL_THEN_HOLD`로 바꿨더니 품질이 떨어지면 실패

### `rollback_watch_metrics`
- 한국어 해석: `롤백 감시 지표`
- 쉬운 뜻:
  - 이런 신호가 생기면 시험판을 끄는 쪽을 검토

---

## 운영에서 이렇게 읽으면 된다

예:

- `continuation_hold_surface`
  - `지금은 추세가 이어지는 보유 관리 장면이구나`
- `profit_hold_bias`
  - `수익 구간에서 더 끌고 가려는 편향이구나`
- `HOLD -> PARTIAL_THEN_HOLD`
  - `원래는 그냥 들고 있었는데, 시험판은 일부 익절 후 계속 들고 가는 쪽이구나`

---

## 한 줄 요약

`PA8 NAS100 canary는 "나스닥의 추세 지속 보유 장면에서, 그냥 HOLD 하던 것을 일부 익절 후 보유로 바꿔보는 좁은 관리 시험"이다.`
