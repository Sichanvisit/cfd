# NAS Product Acceptance First Adjustment Implementation Memo

작성일: 2026-03-30 (KST)

## 1. 이번 패스에서 실제로 바꾼 것

첫 NAS adjustment pass에서는
`stage 자체를 크게 바꾸지 않고`
`display importance만 NAS 의도에 맞게 올리는 방향`으로 갔다.

핵심 변경 파일:

- [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)
- [test_consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_consumer_check_state.py)

## 2. 변경 요약

### 2-1. NAS display importance tier 추가

아래 tier를 새로 추가했다.

- `medium`
- `high`

현재는 NAS `BUY` 장면에만 우선 적용된다.

### 2-2. medium tier

아래 장면은 기본적으로 `2개 체크` 바닥을 갖도록 했다.

- `lower_rebound_probe_observe` + `nas_clean_confirm_probe`
- `lower_rebound_confirm`
- `outer_band_reversal_support_required_observe` + `nas_clean_confirm_probe`
- `middle_sr_anchor_required_observe` + `nas_clean_confirm_probe`

### 2-3. high tier

아래 장면은 기본적으로 `3개 체크` 바닥을 갖도록 했다.

- NAS BUY
- `lower_rebound_probe_observe` 또는 `lower_rebound_confirm`
- box/bb 상태가 하단 회복 시작으로 읽히는 장면
  - `box_state = BELOW`
  - `bb_state in {LOWER_EDGE, BREAKDOWN}`

즉 이번 패스부터는
`3개 체크인데 아직 READY는 아닌 장면`
이 가능해졌다.

## 3. 의도적으로 아직 안 건드린 것

이번엔 아래는 그대로 뒀다.

- `nas_lower_probe_cadence_suppressed`
- `nas_structural_cadence_suppressed`
- painter translation layer
- entry/wait/exit owner

이유:

- 첫 패스는 chart importance uplift만 보려는 목적이었다.
- cadence suppression까지 동시에 바꾸면 과표시 원인 추적이 어려워진다.

## 4. 현재 해석

이번 첫 패스의 결과를 한 줄로 정리하면 이렇다.

```text
NAS lower recovery와 mid pullback은
기존보다 더 강하게 보이게 만들었고,
반복 suppression과 실행 owner는 아직 그대로 남겨둔 상태다.
```

## 5. 테스트 결과

확인한 테스트:

- [test_consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_consumer_check_state.py)
- [test_chart_painter.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_chart_painter.py)
- [test_entry_service_guards.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_entry_service_guards.py)
- [test_entry_engines.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_entry_engines.py)
- 전체 unit

결과:

- `1146 passed, 127 warnings`

## 6. 다음 가장 자연스러운 액션

다음 액션은 새 screenshot 또는 같은 NAS 차트 재확인이다.

그때 봐야 할 것은 아래다.

- lower recovery 시작점이 실제로 3개로 살아났는지
- 중간 눌림 재상승이 2개로 살아났는지
- continuation이 과장되지 않는지
- repeated NAS 장면이 cadence suppression 때문에 아직 너무 많이 사라지는지

## 7. 다음 조정 후보

다음 screenshot 기준으로 필요하면 아래 순서로 간다.

1. `nas_lower_probe_cadence_suppressed`
2. `nas_structural_cadence_suppressed`
3. NAS scene allow / relief
4. 그 다음에만 entry/wait tie-in
