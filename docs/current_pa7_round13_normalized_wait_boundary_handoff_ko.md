# PA7 Round-13 Normalized Wait-Boundary Handoff

## 목적

`XAU mixed_backfill_value_scale_review` 그룹을
더 이상 raw backfill scale 문제 기준으로 rule patch 후보로 보지 않고,
`normalized preview` 기준 다음 review 큐로 넘기는 단계다.

핵심 원칙:

- raw `current_profit` scale mismatch는 별도 audit로 남긴다
- rule patch는 raw backfill scale 값을 보고 하지 않는다
- normalized preview가 `mixed_wait_boundary_review`를 가리키면
  PA7 queue는 그 그룹을 `WAIT boundary review`로 handoff한다

## 이번 round에서 추가한 것

processor row에 아래 필드를 추가한다.

- `normalized_review_handoff_state`
- `normalized_review_handoff_disposition`
- `normalized_review_handoff_priority`
- `normalized_review_handoff_reason`
- `raw_rule_patch_blocked_by_backfill_scale`

## 해석

### raw disposition

- `mixed_backfill_value_scale_review`

의미:

- raw 값만 보면 먼저 backfill scale incompatibility를 봐야 함

### normalized handoff disposition

- `mixed_wait_boundary_review`

의미:

- scale noise를 잠깐 빼고 나면
  다음 실질 검토 대상은 `WAIT / PARTIAL_EXIT` 경계라는 뜻

즉 다음 rule patch는
backfill raw profit 자체가 아니라
`WAIT boundary` family를 기준으로 검토해야 한다.

## summary next action

이제 `normalized_review_handoff_counts`에
`mixed_wait_boundary_review`가 있으면
processor summary는

- `work_through_normalized_wait_boundary_handoffs`

를 추천한다.

즉 review queue 운영 순서도 아래처럼 바뀐다.

1. raw scale 문제를 audit로 확인
2. raw scale 때문에 직접 patch하지 않음
3. normalized preview가 가리키는 boundary queue로 넘김

## 현재 의미

이번 round로 XAU top group은

- raw: `mixed_backfill_value_scale_review`
- normalized handoff: `mixed_wait_boundary_review`

의 2단 분리 상태가 된다.

이제 다음 단계는
XAU 그룹을 `backfill normalization issue`와
`WAIT boundary review`로 동시에 보되,
실제 rule 조정은 두 번째 축에서만 하게 된다.
