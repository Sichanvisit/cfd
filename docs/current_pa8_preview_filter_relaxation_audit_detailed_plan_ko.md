# PA8 Preview Filter Relaxation Audit

## 목적

PA8에서 `post-activation` row는 존재하지만 `preview_changed_row_count`가 계속 `0`으로 남는 이유를
`threshold/sample_floor` 이전 단계에서 분해한다.

이번 단계의 핵심은 규칙을 바로 완화하는 것이 아니라,
`BTCUSD / XAUUSD / NAS100` 각각이 어떤 preview filter reason에서 막히는지와
어떤 scope 완화 후보를 review backlog로 올릴지 정리하는 것이다.

## 왜 지금 필요한가

- 현재 PA8 병목은 단순 live row 부족만이 아니라 `preview_filter_rejection_dominant`가 함께 보인다.
- 이 상태에서 threshold나 sample floor를 먼저 낮추면 잘못된 장면까지 같이 통과시킬 수 있다.
- 따라서 먼저 `surface / checkpoint_type / family / baseline_action / source / position_side` 단위로
  어떤 규칙이 좁은지 review 후보를 만든다.

## 입력

- `checkpoint_pa8_post_activation_root_cause_audit_latest.json`
- symbol profile
  - `surface_name`
  - `checkpoint_type_allowlist`
  - `family_allowlist`
  - `baseline_action_allowlist`
  - `source_allowlist`
  - `position_side_allowlist`

## 출력

- `checkpoint_pa8_preview_filter_relaxation_audit_latest.json`
- `checkpoint_pa8_preview_filter_relaxation_audit_latest.md`

## 핵심 규칙

- 이 audit은 `preview_filter_rejection_dominant`인 심볼만 다룬다.
- live apply를 직접 바꾸지 않는다.
- 각 rejection reason에 대해 현재 allowlist 밖에서 많이 반복된 값을 review candidate로 제시한다.
- candidate는 `review_priority_score`로만 정렬한다.

## 기대 결과

- BTC/XAU/NAS 중 어떤 심볼이 어떤 filter에서 가장 자주 잘리는지 한눈에 본다.
- `scope relaxation`은 threshold 완화 전에 review 가능한 backlog가 된다.
- 이후 `/propose`와 별개로 운영자가 “무엇을 먼저 좁게 열어볼지”를 고를 수 있다.
