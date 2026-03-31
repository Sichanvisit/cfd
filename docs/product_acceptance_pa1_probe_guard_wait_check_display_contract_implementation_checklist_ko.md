# Product Acceptance PA1 Probe-Guard Wait Check Display Contract Implementation Checklist

작성일: 2026-03-31 (KST)

## 목적

이 문서는 PA1 하위축
`probe_guard_wait_check_display_contract`
를 실제 구현 순서로 풀어놓은 체크리스트다.

선행 문서:

- [product_acceptance_pa1_probe_guard_wait_check_display_contract_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_probe_guard_wait_check_display_contract_detailed_reference_ko.md)
- [product_acceptance_pa0_refreeze_after_structural_wait_visibility_boundary_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_structural_wait_visibility_boundary_delta_ko.md)
- [product_acceptance_pa1_structural_wait_visibility_boundary_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_structural_wait_visibility_boundary_implementation_memo_ko.md)

## 이번 단계 목표

```text
probe_scene + guard + probe_not_promoted structural family를
directional leakage로 숨기지 않고,
WAIT + repeated checks chart contract로 연결한다.
```

## 작업 순서

### Step 0. target family를 다시 고정

목표:

- 새 contract를 적용할 family와 여전히 숨겨야 할 family를 분리해 둔다

작업:

- `WAIT + checks` target:
  - `BTCUSD`
  - `middle_sr_anchor_required_observe`
  - `middle_sr_anchor_guard`
  - `probe_not_promoted`
  - `btc_lower_buy_conservative_probe`
- same-family keep:
  - `XAUUSD + xau_second_support_buy_probe`
- still-hide family:
  - no-probe `observe_state_wait`

완료 조건:

- 보여줄 wait family와 숨길 family 경계가 문서상 명확해진다

### Step 1. policy에 chart wait relief contract 추가

목표:

- consumer와 painter가 공통으로 읽을 수 있는 policy axis를 만든다

작업:

- [chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py) 에
  `display_modifier.chart_wait_reliefs.probe_guard_wait_as_wait_checks`
  section을 추가한다
- allow reason / guard / action / stage / hint payload를 policy에 모은다

완료 조건:

- wait-style relief contract가 policy 축으로 고정된다

### Step 2. consumer_check_state에서 chart hint surface 연결

목표:

- live consumer state가 wait-style chart contract를 내려주게 만든다

작업:

- [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py) 에서
  structural probe family를 읽어
  `chart_event_kind_hint / chart_display_mode / chart_display_reason`
  를 채운다
- late suppression이 display를 끄면 hint도 같이 비운다
- baseline scene / score / repeat count는 그대로 유지한다

완료 조건:

- probe-scene structural wait family가 live state에서 `WAIT` chart hint를 가진다

### Step 3. painter를 neutral wait repeated checks로 번역

목표:

- chart surface가 실제로 `기다림 + 체크 여러 개`로 보이게 만든다

작업:

- [chart_painter.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_painter.py) 에서
  `chart_event_kind_hint = WAIT`를 우선 번역한다
- neutral wait event에서도 explicit repeat count를 존중한다
- neutral marker pair를 repeat count 기준으로 반복 렌더한다
- signature에 chart hint/display mode를 포함한다

완료 조건:

- wait-style relief가 history/event/overlay 모두에서 `WAIT + repeat checks`로 남는다

### Step 4. PA0 heuristic을 새 contract에 맞춘다

목표:

- accepted wait-check relief가 더 이상 problem seed queue를 채우지 않게 만든다

작업:

- [product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\scripts\product_acceptance_pa0_baseline_freeze.py) 에서
  `chart_event_kind_hint / chart_display_mode / chart_display_reason`
  를 normalize한다
- accepted wait-check relief helper를 추가한다
- must-show / must-hide / must-block builder에서 skip 처리한다

완료 조건:

- 새 contract가 실제 row에 기록되면 PA0 seed queue에서 빠질 준비가 끝난다

### Step 5. 테스트를 새 경계로 고정

목표:

- contract와 렌더링이 회귀 없이 유지되게 만든다

작업:

- [test_consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_consumer_check_state.py) 에
  wait hint surface assert를 추가한다
- [test_chart_painter.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_chart_painter.py) 에
  `WAIT + repeat_count = 2` neutral render 테스트를 추가한다
- [test_product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_product_acceptance_pa0_baseline_freeze.py) 에
  accepted wait-check relief skip 테스트를 추가한다

완료 조건:

- consumer / painter / PA0 script contract가 테스트로 고정된다

### Step 6. 문서 로그와 refreeze delta 남기기

목표:

- 다음 스레드에서 왜 이 family를 leakage가 아니라 wait로 분리했는지 바로 이해되게 만든다

작업:

- implementation memo 문서를 추가한다
- latest baseline refreeze를 수행한다
- refreeze delta 문서에
  "코드는 반영됐지만 recent stored row는 아직 old contract" 상태를 남긴다

완료 조건:

- `상세 reference -> 구현 체크리스트 -> 구현 memo -> refreeze delta`
  흐름이 이어진다

## 금지 사항

- probe-scene structural wait를 다시 directional BUY/SELL leakage로 몰아넣기
- no-probe structural hide boundary까지 되돌리기
- painter만 수정하고 consumer/PA0 contract는 비워두기
- fresh runtime row 없이 baseline count만 보고 구현 실패로 단정하기

## Done Definition

1. probe-scene structural wait family가 `WAIT + repeated checks` chart hint를 가진다
2. painter가 neutral repeated wait marker를 렌더한다
3. PA0 script가 accepted wait-check relief를 problem seed에서 제외한다
4. 테스트가 통과한다
5. implementation memo와 refreeze delta가 추가된다
