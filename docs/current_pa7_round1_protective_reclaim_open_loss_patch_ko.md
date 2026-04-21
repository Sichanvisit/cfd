# Current PA7 Round-1 Protective Reclaim Open-Loss Patch

## 목적

이 문서는 `PA7 review processor`에서 가장 먼저 튀어나온
`protective_exit_surface + RECLAIM_CHECK + active_open_loss`
그룹의 mismatch를 줄이기 위한 round-1 패치 기준서다.

핵심 문제는 다음 하나였다.

- baseline action은 `PARTIAL_EXIT`
- hindsight는 반복해서 `WAIT`
- reason은 다수 `full_exit_gate_not_met_trim_fallback`

즉 `FULL_EXIT`는 gate를 못 통과했는데,
그 다음 fallback이 너무 쉽게 `PARTIAL_EXIT`로 내려가고 있었다.

## 관찰된 패턴

대표 row 공통:

- `checkpoint_type = RECLAIM_CHECK`
- `management_row_family = active_open_loss`
- `current_profit < 0`
- `giveback_ratio ~= 0.99`
- `continuation > reversal`
- `hold_quality`가 아주 낮지 않음
- `partial_exit_ev`는 높지만 trim을 강제할 정도로 우세하지 않음

즉 이 row는
“위험해서 바로 trim 해야 하는 자리”보다
“protective 문맥이긴 하지만 reclaim 재확인 구간이라 한 번 더 기다릴 수 있는 자리”
에 더 가깝다.

## 이번 patch 원칙

- open-loss 전체를 느슨하게 만들지 않는다
- `protective reclaim active_open_loss` 한 family만 좁힌다
- `FULL_EXIT gate 실패 -> PARTIAL_EXIT fallback`를 그대로 쓰지 않고,
  강한 continuation reclaim이면 `WAIT`로 남긴다

## 대상 조건

다음 조건을 모두 만족할 때만 새 wait fallback을 적용한다.

- `position_side != FLAT`
- `checkpoint_type == RECLAIM_CHECK`
- `row_family == active_open_loss`
- `current_profit < 0`
- `continuation >= reversal + 0.12`
- `hold_score >= partial_score + 0.04`
- `hold_score >= 0.38`
- `top_label == FULL_EXIT`
- `full_exit_allowed == False`

## 새 action

- `WAIT`
- reason:
  - `protective_reclaim_open_loss_wait_retest`

## 기대 효과

- `full_exit_gate_not_met_trim_fallback` 과민 사용 감소
- `PARTIAL_EXIT -> WAIT` mismatch 감소
- `PA7` 상단 policy mismatch group 축소

## 이번 단계에서 하지 않는 것

- `active_open_loss` 전체 규칙 재작성
- `open_loss_protective` 전체 규칙 재작성
- `scene bias`와 결합

## 완료 조건

- 전용 unit test 추가
- dataset / review processor 재빌드 후
  top mismatch group이 감소하거나 우선순위가 재정렬됨
