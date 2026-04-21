# Flow Mismatch Audit

## 목적

재시작 후 실제 runtime row 기준으로 `chart/overlay/watch` 표기와 `flow gate/support state`가 왜 어긋나는지 종목별로 고정한다.

## 현재 관찰

### NAS100

- 표기:
  - `chart_event_kind_hint = BUY_WATCH`
  - `directional_continuation_overlay_direction = UP`
- flow:
  - `flow_structure_gate_v1 = INELIGIBLE`
  - `flow_support_state_v1 = FLOW_OPPOSED`
- 핵심 원인:
  - `dominance_shadow_dominant_side_v1 = BULL`
  - 그런데 slot은 bearish family에서 내려온 `BEAR_*` 계열로 생성되어 `POLARITY_MISMATCH`
  - 동시에 `AMBIGUITY_HIGH`가 같이 걸림
- 해석:
  - NAS는 점수 문제보다 `slot 생성 규칙`이 local reject / pending review 신호를 너무 빨리 bearish 쪽으로 끌어가는 문제가 더 큼

### XAUUSD

- 표기:
  - `chart_event_kind_hint = BUY_WATCH`
  - `directional_continuation_overlay_direction = UP`
- flow:
  - `flow_support_state_v1 = FLOW_UNCONFIRMED`
- 핵심 원인:
  - slot polarity와 dominance는 둘 다 `BULL`
  - 그러나 `AMBIGUITY_HIGH` 단일 hard disqualifier 때문에 구조 gate가 막힘
- 해석:
  - XAU는 slot mislabel보다 `ambiguity/gate 과긴축` 문제가 본체에 가까움

### BTCUSD

- 표기:
  - overlay는 비활성 또는 low alignment
- flow:
  - `flow_support_state_v1 = FLOW_OPPOSED`
- 핵심 원인:
  - slot은 `BULL_*`
  - dominance는 `NONE`
  - 결과적으로 `POLARITY_MISMATCH + AMBIGUITY_HIGH`
- 해석:
  - BTC는 해석 오분류라기보다 `dominance 미결정 상태를 곧장 hard opposed로 읽는 문제`가 큼

## 결론

- 세 종목은 같은 증상이 아니다.
- 우선순위는 아래가 맞다.
  1. NAS: slot 생성 규칙 보정
  2. XAU: ambiguity/gate 완화 검토
  3. BTC: dominance NONE 처리 완화 검토

## 이번 수정 방향

- NAS에 한해
  - `SEPARATE_PENDING`
  - `dominance = BULL`
  - `WITH_HTF`
  - `BREAKOUT_HELD/ABOVE`
  - `breakout_direction = UP`
  - 다중 HTF 상승 정렬
  가 동시에 나오면 bearish pending family를 그대로 slot polarity로 쓰지 않고 `BULL_CONTINUATION` 쪽으로 보정한다.

이 수정은 공통 gate를 완화하는 것이 아니라, `state_slot_symbol_extension_surface` 입력 품질을 먼저 바로잡는 조치다.
