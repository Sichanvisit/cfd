# PA7 Round-11 Hydration And Mixed-Review Decomposition

## 목적

`policy_mismatch_review`가 사실상 정리된 뒤,
남은 `PA7` queue를 더 설명력 있게 나누는 단계다.

이번 round의 초점은:

- `hydration gap`인데 사실상 이미 맞아진 그룹
- `mixed_review`인데 사실상 backfill 값 스케일 문제인 그룹
- `mixed_review`인데 사실상 WAIT 경계 흔들림인 그룹

을 따로 떼는 것이다.

## 새 분류

### 1. hydration_gap_confirmed_cluster

조건:

- `blank_baseline_share >= 0.60`
- `missing_score_share >= 0.60`
- `baseline_match_rate >= 0.66`
- `policy_replay_match_rate >= 0.66`
- `baseline == replay == hindsight`

의미:

- baseline이 듬성듬성 비어 있지만
- 실제 행동 방향은 이미 같은 쪽으로 모여 있음

즉 rule patch 우선순위가 아니라,
hydration 정리 메모로 내려도 되는 그룹이다.

### 2. mixed_backfill_value_scale_review

조건:

- `backfill_source_share >= 0.75`
- `abs(avg_current_profit) >= 50`
- `avg_giveback_ratio <= 0.10`
- `baseline == replay`
- `hindsight = WAIT`

의미:

- 현재 정책 문제라기보다
- `closed/open trade backfill` 값 스케일이 섞이면서 review를 흐리는 그룹

즉 rule patch보다 backfill normalization / value audit 쪽이 먼저다.

### 3. mixed_wait_boundary_review

조건:

- `baseline == replay`
- `hindsight = WAIT`
- `row_count >= 2`
- `baseline_match_rate <= 0.50`
- `policy_replay_match_rate <= 0.50`

의미:

- 현재 정책이 일관되게 한쪽으로 가고는 있지만
- hindsight는 WAIT로 남는 경계 family

즉 진짜 다음 rule patch 후보에 가깝다.

## 기대 효과

- `PA7` queue를 "무엇부터 고칠지"가 더 읽히는 상태로 바꿈
- hydration / backfill / 실제 정책 경계 문제를 분리
- 다음 round에서
  - hydration 보강
  - backfill 값 정규화 검토
  - mixed WAIT boundary patch
  중 무엇을 먼저 할지 바로 고를 수 있게 함
