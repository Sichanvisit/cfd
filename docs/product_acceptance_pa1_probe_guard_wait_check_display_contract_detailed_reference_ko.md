# Product Acceptance PA1 Probe-Guard Wait Check Display Contract Detailed Reference

작성일: 2026-03-31 (KST)

## 1. 목적

이 문서는 PA1 chart acceptance 안에서
`probe_guard_wait_check_display_contract`
를 별도 하위축으로 고정하는 상세 reference다.

이번 하위축의 핵심 질문은 아래 하나다.

```text
probe_scene가 붙었고 guard도 아직 살아 있는 structural probe_wait family를
계속 leakage로 숨길 것인가,
아니면 "아직 진입은 아니지만 계속 봐야 하는 기다림"으로 차트에 남길 것인가?
```

이번 reference는 이 family를
`directional entry-like visibility`가 아니라
`neutral wait + repeated checks`
로 다루는 계약을 문서로 먼저 고정한다.

## 2. 왜 지금 이 문서가 필요한가

PA1 `structural_wait_visibility_boundary` 적용 이후
PA0 refreeze에서는 아래 family가 must-show / must-hide queue를 동시에 채웠다.

대표 family:

- `BTCUSD`
- `observe_reason = middle_sr_anchor_required_observe`
- `blocked_by = middle_sr_anchor_guard`
- `action_none_reason = probe_not_promoted`
- `probe_scene_id = btc_lower_buy_conservative_probe`
- `display_ready = True`

그리고 같은 축의 XAU family:

- `XAUUSD`
- `observe_reason = middle_sr_anchor_required_observe`
- `blocked_by = middle_sr_anchor_guard`
- `action_none_reason = probe_not_promoted`
- `probe_scene_id = xau_second_support_buy_probe`

즉 current casebook은 이 family를

- 한편으로는 `보여야 하는 structural visibility`
- 다른 한편으로는 `숨겨야 하는 leakage`

로 동시에 읽고 있었다.

사용자 판단은 이 경계에서 명확했다.

```text
이건 숨길 신호가 아니라
"아직 들어가면 안 되지만 구조적으로는 계속 봐야 하는 기다림"
으로 연결하고,
차트에는 기다림 표기와 체크 여러 개로 보여줘야 한다.
```

## 3. 이번 하위축에서 고정할 해석

### 3-1. semantic 해석

아래 조합:

- `probe_not_promoted`
- `scene_probe present`
- `guard_present`
- `visible`

은 더 이상 `directional leakage`로 보지 않는다.

대신 아래처럼 해석한다.

- 아직 entry promotion은 되지 않았다
- 구조적으로는 probe scene이 살아 있다
- guard가 남아 있어서 바로 진입하면 안 된다
- 그래서 차트에는 `WAIT`로 보이되,
  repeated checks를 통해 "계속 보고 있다"는 강도만 남긴다

### 3-2. chart 표현 해석

이 family는 아래처럼 surface에 반영한다.

- directional `BUY` / `SELL` 강조를 밀어붙이지 않는다
- neutral event kind `WAIT`로 내린다
- repeat_count를 살려서 check가 여러 개인 wait로 그린다
- semantic reason은 debug surface에 남긴다

즉 사용자가 보는 chart 의미는 아래다.

```text
이건 지금 진입하라는 뜻이 아니라,
구조적으로 유효한 대기 상태이니
체크를 여러 개 붙여 계속 관찰 중이라는 뜻이다.
```

## 4. contract boundary

### 4-1. scene owner가 계속 책임지는 것

scene owner는 아래 baseline meaning만 계속 책임진다.

- candidate 여부
- side
- baseline stage
- observe reason
- blocked_by
- probe_scene_id
- display score / repeat count baseline

즉 scene owner는 structural reason을 숨기지 않는다.

### 4-2. modifier owner가 새로 책임지는 것

modifier owner는 아래 chart display contract를 책임진다.

- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = probe_guard_wait_as_wait_checks`

이 contract는 아래 family에만 적용한다.

- `stage = OBSERVE`
- `display_ready = True`
- `entry_ready = False`
- `observe_reason in {outer_band_reversal_support_required_observe, middle_sr_anchor_required_observe}`
- `blocked_by in {outer_band_guard, middle_sr_anchor_guard}`
- `action_none_reason = probe_not_promoted`
- `probe_scene_id present`

즉 이건 "보여줄지 말지"보다
"어떤 표면으로 보여줄지"를 고정하는 계약이다.

### 4-3. painter owner가 책임지는 것

painter는 위 hint를 받아 아래처럼 번역한다.

- `WAIT` neutral event kind로 기록
- explicit `repeat_count`를 유지
- neutral wait marker를 repeat count만큼 반복 렌더

즉 painter는 semantic 판단을 새로 만들지 않고,
modifier가 내려준 `WAIT + repeated checks` surface를 그린다.

## 5. PA0 casebook alignment

이번 하위축은 chart 표면만 바꾸는 것으로 끝나지 않는다.

PA0 casebook도 아래 family를 더 이상 problem seed로 잡지 않아야 한다.

skip target:

- `display_ready = True`
- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = probe_guard_wait_as_wait_checks`

즉 이 family는 이제

- `must-show missing`
- `must-hide leakage`
- `must-block`

queue에서 빠져야 한다.

단, 이 정렬은 fresh runtime row가 새 contract를 실제로 기록한 뒤에야
artifact에 반영된다.

## 6. 이번 하위축의 구현 방향

### 6-1. policy contract 추가

[chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py) 에
`display_modifier.chart_wait_reliefs.probe_guard_wait_as_wait_checks`
section을 추가한다.

이 policy는:

- structural observe reason allow list
- guard allow list
- `probe_not_promoted` allow list
- `probe_scene required`
- `stage = OBSERVE`
- chart hint payload

를 한곳에 묶는다.

### 6-2. consumer surface 추가

[consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py) 는
modifier 결과로 아래 chart hint를 함께 반환한다.

- `chart_event_kind_hint`
- `chart_display_mode`
- `chart_display_reason`

late suppression으로 display가 꺼질 경우에는
이 hint도 같이 비운다.

### 6-3. painter neutral wait 반복 렌더

[chart_painter.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_painter.py) 는
위 contract가 들어오면 `WAIT` neutral event로 기록하고,
repeat count를 사용해 neutral marker를 여러 번 그린다.

즉 chart surface는
`directional pressure`
가 아니라
`wait + checks`
로 읽히게 된다.

### 6-4. PA0 heuristic 정렬

[product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\scripts\product_acceptance_pa0_baseline_freeze.py) 는
위 chart hint contract를 읽을 수 있어야 하고,
accepted wait-check relief family를 problem seed queue에서 제외해야 한다.

## 7. 이번 하위축에서 일부러 안 하는 것

아래는 이번 단계에서 일부러 하지 않는다.

- entry acceptance rule 수정
- wait / hold / exit acceptance owner 수정
- structural cadence suppression family 재설계
- symbol override policy 전체 재정리
- 방향성 BUY/SELL score ladder 재조정

이번 단계는 오직
`probe_scene + guard + not promoted`
family를 chart에서 `WAIT + repeated checks`로 읽히게 만드는 작업이다.

## 8. Done Definition

이번 하위축은 아래 조건을 만족하면 닫는다.

1. probe-scene structural wait family가 `WAIT` hint를 가진다
2. painter가 neutral wait marker를 repeat count 기준으로 반복 렌더한다
3. PA0 heuristic이 accepted wait-check relief를 problem seed에서 제외한다
4. 관련 테스트가 통과한다
5. implementation memo와 refreeze delta가 남는다

## 9. 한 줄 요약

```text
이번 PA1 하위축의 목적은
probe_scene + guard + probe_not_promoted structural family를
"숨겨야 하는 leakage"가 아니라
"아직 진입은 아니지만 계속 봐야 하는 WAIT + repeated checks"
chart contract로 고정하는 것이다.
```
