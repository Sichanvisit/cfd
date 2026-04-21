# Product Acceptance PA1 BTC Middle-Anchor Wait Hide Without Probe Detailed Reference

작성일: 2026-04-01 (KST)

## 1. 목적

이 문서는 PA1 chart acceptance 하위축 중
`BTCUSD + middle_sr_anchor_required_observe + middle_sr_anchor_guard + observe_state_wait + no_probe`
family를 `accepted hidden suppression`으로 정리한 이유와 구현 경계를 고정한다.

관련 문서:

- [product_acceptance_pa1_structural_wait_visibility_boundary_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_structural_wait_visibility_boundary_detailed_reference_ko.md)
- [product_acceptance_pa1_btc_lower_probe_guard_wait_display_contract_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_btc_lower_probe_guard_wait_display_contract_detailed_reference_ko.md)

## 2. 문제 family

이번 축의 residue는 아래 family였다.

- `symbol = BTCUSD`
- `observe_reason = middle_sr_anchor_required_observe`
- `blocked_by = middle_sr_anchor_guard`
- `action_none_reason = observe_state_wait`
- `probe_scene_id = (blank)`

직전 PA0 latest 기준으로 이 family는 아래처럼 queue를 채우고 있었다.

- `must_show_missing = 13`
- `must_hide_leakage = 5`
- `must_block_candidates = 12`

## 3. 해석

이 family는 이미 초기에 정한 기준상 `WAIT surface로 살리는 family`가 아니라
`probe scene이 없는 structural no-probe wait`이므로 숨기는 쪽이 맞다.

즉 판단은 아래와 같다.

```text
probe scene 없이 middle anchor guard만 걸린 observe_state_wait는
아직 구조 인지를 노출할 수준이 아니므로 accepted hidden suppression으로 본다.
```

## 4. 실제 문제

이번 residue는 두 갈래였다.

1. `BUY` side no-probe row는 이미 `structural_wait_hide_without_probe`로 숨겨지고 있었지만,
   PA0 / painter accepted hidden 목록에 이 generic reason이 빠져 있었다.
2. `SELL` side no-probe row는 BTC 전용 hide reason이 없어 `check_display_ready=True`로 새어 나가고 있었다.

즉 family 자체 해석이 틀린 게 아니라,
`accepted hidden reason 목록 누락 + BTC sell-middle-anchor 전용 hide 부재`
가 실제 구현 gap이었다.

## 5. representative replay 기준

대표 row:

- `2026-04-01T00:23:14` (`BUY`)
- `2026-04-01T00:25:02` (`SELL`)

current build replay 결과:

- `BUY` row
  - `check_display_ready = False`
  - `modifier_primary_reason = structural_wait_hide_without_probe`
- `SELL` row
  - `check_display_ready = False`
  - `modifier_primary_reason = btc_sell_middle_anchor_wait_hide_without_probe`

resolve replay에서도 같은 hidden contract가 유지된다.

## 6. 목표 contract

이번 축에서 고정하는 목표 contract는 아래와 같다.

- `check_display_ready = False`
- `check_stage = OBSERVE`
- `blocked_display_reason = middle_sr_anchor_guard`
- `chart_event_kind_hint = ""`
- `chart_display_mode = ""`
- `chart_display_reason = ""`
- `modifier_primary_reason = structural_wait_hide_without_probe | btc_sell_middle_anchor_wait_hide_without_probe`

즉 `no-probe middle-anchor wait`는 차트 surface에서 제거하는 것이 목표다.

## 7. 구현 방향

1. [chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)에 `btc_sell_middle_anchor_wait_hide_without_probe` soft cap을 추가한다.
2. [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)에 같은 soft cap 적용 로직을 추가한다.
3. [product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\scripts\product_acceptance_pa0_baseline_freeze.py)에
   `structural_wait_hide_without_probe`와 `btc_sell_middle_anchor_wait_hide_without_probe`를 accepted hidden reason으로 추가한다.
4. [chart_painter.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_painter.py)도 같은 hidden reason을 suppression set에 추가한다.

## 8. 이번 축에서 하지 않는 것

- BTC conflict wait residue 정리
- BTC upper sell probe residue 정리
- XAU mixed energy-soft-block residue 정리
- entry / hold / exit acceptance 조정

## 9. 완료 기준

1. representative replay에서 `BUY` / `SELL` no-probe middle-anchor row가 모두 hidden contract로 내려간다.
2. PA0 baseline script가 두 hidden reason을 problem seed queue에서 제외한다.
3. painter가 두 hidden reason row를 flow surface에 그리지 않는다.
4. live exact recurrence가 없더라도 delta 문서에 `must-show/must-block 해소 + must-hide old backlog 잔존` 상태를 분리 기록한다.
