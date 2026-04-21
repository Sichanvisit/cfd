# P5-4 First Symbol Closeout/Handoff and PA7 Narrow Review Lane

## 목표

`PA8 closeout -> PA9 handoff`가 실제로 닫히는 첫 심볼을 계속 보이게 만들고,
남아 있는 `mixed_wait_boundary_review / mixed_review`는 전체 blocker로 다시 키우지 않고
별도 `narrow review lane`으로 surface한다.

## 왜 이 단계가 필요한가

- `P5-1`, `P5-2`, `P5-3`까지 오면 closeout/handoff 통로는 거의 닫힌다.
- 그런데 실제 운영에서는 "지금 어느 심볼을 제일 먼저 봐야 하는지"가 더 중요해진다.
- 동시에 `PA7`에 남는 아주 좁은 혼합 review는 전체 phase를 다시 막아버리기보다
  `좁게 다시 봐야 하는 lane`으로 surface하는 편이 더 맞다.

즉 `P5-4`는

- 승격축을 억지로 당기지 않고
- first symbol observation을 계속 보이게 하며
- 남은 혼합 review는 별도 narrow lane으로 관리하는 단계다.

## 구현 범위

### 1. first symbol closeout/handoff surface

추가 위치:

- `backend/services/improvement_readiness_surface.py`
- `backend/services/checkpoint_improvement_master_board.py`

핵심 필드:

- `first_symbol_closeout_handoff_status`
- `first_symbol_closeout_handoff_symbol`
- `first_symbol_closeout_handoff_stage`
- `first_symbol_closeout_handoff_reason`
- `first_symbol_closeout_handoff_next_required_action`

상태 해석:

- `WATCHLIST`
- `CONCENTRATED`
- `READY_FOR_CLOSEOUT_REVIEW`
- `READY_FOR_HANDOFF_REVIEW`
- `READY_FOR_HANDOFF_APPLY`
- `APPLIED`
- `BLOCKED`
- `NOT_APPLICABLE`

우선순위:

1. `PA9 handoff apply candidate`
2. `PA9 handoff review candidate`
3. `PA8 closeout focus primary symbol`
4. 그 외 첫 번째 available symbol

### 2. PA7 narrow review lane

입력:

- `checkpoint_pa7_review_processor_latest.json`

surface 대상:

- `mixed_wait_boundary_review`
- `mixed_review`

출력 필드:

- `pa7_narrow_review_status`
- `pa7_narrow_review_group_count`
- `pa7_narrow_review_primary_group_key`
- `pa7_narrow_review_next_required_action`

상태 해석:

- `CLEAR`
- `WATCHLIST`
- `REVIEW_NEEDED`
- `NOT_APPLICABLE`

정책:

- `mixed_wait_boundary_review`가 하나라도 남으면 `REVIEW_NEEDED`
- `mixed_review`만 남으면 `WATCHLIST`
- 남은 narrow group이 없으면 `CLEAR`

## 기대 효과

1. `PA8/PA9`가 아직 hold여도
   지금 가장 먼저 닫힐 후보 심볼을 한 줄로 바로 읽을 수 있다.

2. `PA7`에 아주 좁은 혼합 review가 남아도
   전체 blocker로 다시 끌어올리지 않고
   `narrow review lane`으로만 따로 본다.

3. `P5` 후반부는 이제
   "무엇이 막혔는가"보다
   "어느 심볼을 먼저 닫을 것인가"와
   "남은 혼합 review를 어디까지 좁게 볼 것인가"가 선명해진다.

## 완료 조건

- readiness surface에 `first symbol closeout/handoff`가 보인다.
- master board summary/readiness에 같은 상태가 surface된다.
- `PA7 narrow review lane`이 `CLEAR / WATCHLIST / REVIEW_NEEDED` 중 하나로 보인다.
- 1일 PnL readiness 요약에도 first symbol / narrow review가 같이 보인다.
- 관련 테스트가 통과한다.
