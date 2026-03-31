# Product Acceptance PA1 Structural Wait Visibility Boundary Implementation Checklist

작성일: 2026-03-31 (KST)

## 목적

이 문서는 PA1 하위축
`structural_wait_visibility_boundary`
를 실제 구현 순서로 풀어놓은 체크리스트다.

선행 문서:

- [product_acceptance_pa1_structural_wait_visibility_boundary_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_structural_wait_visibility_boundary_detailed_reference_ko.md)
- [product_acceptance_common_state_aware_display_modifier_v1_casebook_review_followup_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_common_state_aware_display_modifier_v1_casebook_review_followup_ko.md)
- [product_acceptance_pa0_refreeze_after_conflict_soft_cap_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_conflict_soft_cap_delta_ko.md)

## 이번 단계 목표

```text
probe_scene 없는 structural observe wait는 leakage로 숨기고,
probe_scene 있는 structural probe_wait는 계속 must-show visibility로 남긴다.
```

## 작업 순서

### Step 0. current boundary seed를 다시 고정

목표:

- 이번 수정이 무엇을 숨기고 무엇을 유지해야 하는지 raw family 기준으로 다시 고정한다

작업:

- `must-hide` target:
  - `BTCUSD`
  - `middle_sr_anchor_required_observe`
  - `middle_sr_anchor_guard`
  - `observe_state_wait`
  - `probe_scene_id = (blank)`
- `must-show` keep target:
  - `BTCUSD` + `btc_lower_buy_conservative_probe`
  - `XAUUSD` + `xau_second_support_buy_probe`

완료 조건:

- 숨길 family와 유지할 family가 문서상 명확해진다

### Step 1. BTC structural importance boundary를 probe_scene 기준으로 좁히기

목표:

- BTC no-probe structural wait가 importance uplift source를 먹지 않게 만든다

작업:

- [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py) 에서
  BTC structural rebound tier/source reason 규칙을 probe_scene boundary 기준으로 수정한다

완료 조건:

- no-probe `middle_sr_anchor_required_observe`가 더 이상 `btc_structural_rebound`로 uplift되지 않는다

### Step 2. common modifier soft cap 추가

목표:

- no-probe structural observe wait를 final display surface에서 숨긴다

작업:

- [chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py) 에
  `display_modifier.soft_caps.structural_wait_hide_without_probe`를 추가한다
- [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py) 에
  해당 soft cap read/apply 경로를 연결한다

완료 조건:

- no-probe structural observe wait가 `check_display_ready = False`로 내려간다
- modifier debug surface에 reason이 남는다

### Step 3. probe_scene structural probe_wait visibility를 보호

목표:

- 숨김 경계가 probe_scene structural family까지 번지지 않게 만든다

작업:

- `probe_scene_id`가 있는 BTC/XAU/NAS structural probe family를 테스트로 고정한다
- soft cap 적용 조건이 no-probe case에만 걸리는지 확인한다

완료 조건:

- `probe_not_promoted + probe_scene` family visibility가 유지된다

### Step 4. 테스트 갱신

목표:

- 이전 expectation을 새 boundary 기준으로 맞춘다

작업:

- 기존 BTC no-probe structural visibility 테스트를 새 기준으로 갱신
- no-probe hidden 테스트 추가
- probe-scene visible 유지 테스트 추가

완료 조건:

- 새 visibility boundary가 테스트로 고정된다

### Step 5. 구현 memo 남기기

목표:

- 다음 스레드에서 왜 이 경계를 이렇게 잘랐는지 바로 이해되게 만든다

작업:

- implementation memo 문서를 추가한다
- 아래를 적는다
  - 어떤 family를 숨겼는지
  - 어떤 family를 보호했는지
  - common modifier와 BTC importance boundary를 어떻게 나눴는지
  - 어떤 테스트를 돌렸는지

완료 조건:

- `상세 reference -> 구현 체크리스트 -> 구현 memo` 흐름이 이어진다

## 금지 사항

- structural family 전체 일괄 suppression
- probe_scene structural family visibility까지 같이 죽이기
- entry/wait/exit owner로 범위 확장
- painter에서 먼저 해결하려고 하기

## Done Definition

1. BTC no-probe structural wait leakage가 숨겨진다
2. BTC/XAU/NAS probe_scene structural probe_wait visibility가 유지된다
3. modifier debug surface에 새로운 reason이 남는다
4. 테스트가 통과한다
5. implementation memo가 추가된다
