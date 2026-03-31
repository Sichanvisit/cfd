# Product Acceptance PA1 Structural Wait Visibility Boundary Detailed Reference

작성일: 2026-03-31 (KST)

## 1. 목적

이 문서는 PA1 chart acceptance 안에서
`structural wait visibility boundary`를 별도 하위축으로 고정하는 상세 reference다.

이번 하위축의 핵심 질문은 아래 하나다.

```text
같은 structural observe family라도
probe_scene가 붙은 structural probe_wait는 must-show로 살리고,
probe_scene가 없는 structural observe wait는 must-hide leakage로 눌러야 하는가?
```

이번 reference는 이 경계를 문서로 먼저 고정하고,
그 뒤 구현 체크리스트와 코드 변경을 이어가기 위한 기준점이다.

## 2. 왜 지금 이 문서가 필요한가

PA1 1차 구현과 conflict soft cap follow-up 이후에도
refreeze delta에서는 아래 패턴이 남아 있었다.

### 2-1. 남아 있는 must-hide leakage

대표 family:

- `BTCUSD`
- `observe_reason = middle_sr_anchor_required_observe`
- `blocked_by = middle_sr_anchor_guard`
- `action_none_reason = observe_state_wait`
- `probe_scene_id = (blank)`

이 family는 chart에서 directional visibility가 남아 있고,
must-hide leakage queue로 올라왔다.

### 2-2. 동시에 살려야 하는 must-show family

대표 family:

- `BTCUSD`
- `observe_reason = middle_sr_anchor_required_observe`
- `blocked_by = middle_sr_anchor_guard`
- `action_none_reason = probe_not_promoted`
- `probe_scene_id = btc_lower_buy_conservative_probe`

그리고:

- `XAUUSD`
- `observe_reason = middle_sr_anchor_required_observe`
- `blocked_by = middle_sr_anchor_guard`
- `action_none_reason = probe_not_promoted`
- `probe_scene_id = xau_second_support_buy_probe`

이 family는 current build raw replay 기준으로
`OBSERVE + visible`로 이미 복원되어 있었고,
must-show family로 계속 살아 있어야 한다.

즉 지금 필요한 건 “structural family를 전부 살리거나 전부 누르는 것”이 아니라,
`probe_scene boundary`를 기준으로 visible / hidden을 분리하는 것이다.

## 3. 현재 코드에서 경계가 흐려져 있는 지점

현재 [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py) 에서는
아래 두 층이 아직 완전히 분리되지 않았다.

1. structural importance uplift

- `_btc_display_importance_tier(...)`
- `_display_importance_source_reason_v1(...)`

2. final visibility suppression

- `_apply_state_aware_display_modifier_v1(...)`

현재 BTC에서는 `middle_sr_anchor_required_observe`가
probe_scene 없이도 structural rebound importance로 읽히는 경향이 있고,
그 결과 no-probe observe wait도 directional medium/visible로 남을 수 있다.

하지만 casebook 기준으로는
이 no-probe family는 leakage로 보는 쪽이 맞다.

## 4. 이번 하위축에서 고정할 경계

### 4-1. scene owner가 계속 책임지는 것

scene owner는 아래까지만 책임진다.

- candidate 여부
- side
- baseline stage
- entry-ready 여부
- raw structural reason

즉 `middle_sr_anchor_required_observe` 같은 semantic reason은 그대로 둔다.

### 4-2. importance boundary

BTC structural rebound importance는
`probe_scene_id = btc_lower_buy_conservative_probe`가 붙은 structural probe family에만 부여한다.

즉 no-probe `middle_sr_anchor_required_observe`는
더 이상 `btc_structural_rebound` source reason으로 uplift하지 않는다.

### 4-3. visibility boundary

공통 modifier는 아래 조합을 별도 soft cap family로 본다.

- `observe_reason in {outer_band_reversal_support_required_observe, middle_sr_anchor_required_observe}`
- `blocked_by in {outer_band_guard, middle_sr_anchor_guard}`
- `action_none_reason = observe_state_wait`
- `probe_scene_id = (blank)`

이 family는 `structural_wait_hide_without_probe`로 숨긴다.

반대로:

- `probe_scene_id`가 있는 structural probe_wait
- `action_none_reason = probe_not_promoted`

family는 must-show visibility 후보로 남긴다.

## 5. 이번 하위축의 구현 방향

### 5-1. BTC importance source boundary 조정

[consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py) 에서
BTC structural rebound importance는
`probe_scene_u == btc_lower_buy_conservative_probe`일 때만 부여한다.

### 5-2. common modifier soft cap 추가

[chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py) 의
`display_modifier.soft_caps`에
`structural_wait_hide_without_probe` section을 추가한다.

이 soft cap은:

- semantic meaning을 바꾸지 않고
- final directional visibility만 숨긴다
- modifier debug surface에 reason을 남긴다

### 5-3. structural probe_wait visibility 유지

기존 probe_scene structural family는 이번 단계에서 일부러 유지한다.

대표 target:

- `btc_lower_buy_conservative_probe`
- `xau_second_support_buy_probe`
- `nas_clean_confirm_probe`

즉 이번 단계는 “probe_scene structural family를 죽이는 단계”가 아니다.

## 6. 이번 하위축에서 일부러 안 하는 것

아래는 이번 단계에서 일부러 하지 않는다.

- cadence suppression family 재설계
- entry / wait / hold acceptance owner 수정
- painter translation 조정
- symbol override policy 전체 재정리

이번 단계는 오직
`structural wait visibility boundary`
하나만 자르는 작업이다.

## 7. Done Definition

이번 하위축은 아래 조건을 만족하면 닫는다.

1. BTC structural rebound importance가 probe_scene boundary 기준으로 분리된다
2. no-probe structural observe wait가 common modifier soft cap으로 숨겨진다
3. probe_scene structural probe_wait visibility는 유지된다
4. 관련 테스트가 current contract 기준으로 갱신된다
5. implementation memo가 남는다

## 8. 한 줄 요약

```text
이번 PA1 하위축의 목적은
structural family를 전부 올리거나 전부 숨기는 것이 아니라,
probe_scene boundary를 기준으로 no-probe structural wait leakage와 structural probe_wait visibility를 분리하는 것이다.
```
