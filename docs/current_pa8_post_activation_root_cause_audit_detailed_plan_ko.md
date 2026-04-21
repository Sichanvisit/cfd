# PA8 Post-Activation Root Cause Audit 상세 계획

## 목표

`PA8 observed_window_row_count = 0`이 정말로 row 부재 때문인지, 아니면 post-activation row는 있는데 preview 후보 규칙에 거의 안 걸리는 것인지 분리해서 본다.

## 왜 지금 필요한가

현재 PA8 non-apply audit만 보면 `활성화 이후 live row가 아직 쌓이지 않음`으로 읽히지만, 실제 resolved dataset에는 activation 이후 row가 존재할 수 있다. 이 경우 핵심 병목은 row 부재가 아니라 `preview_changed_row_count = 0`이다.

즉 이번 단계는:

- post-activation raw row 존재 여부
- preview 후보로 실제 승격된 row 수
- 어떤 preview reason이 가장 많이 후보를 막는지

를 한 장에서 읽는 root-cause audit이다.

## 입력

- `checkpoint_dataset_resolved.csv`
- `checkpoint_pa8_*_action_only_canary_activation_apply_latest.json`
- symbol별 preview builder
  - `build_nas100_profit_hold_bias_action_preview`
  - `build_checkpoint_pa8_symbol_action_preview`

## 핵심 산출물

심볼별로 아래를 남긴다.

- `post_activation_row_count`
- `preview_changed_row_count`
- `eligible_row_count`
- `preview_reason_counts`
- `surface_counts`
- `checkpoint_type_counts`
- `baseline_action_counts`
- `root_cause_code`
- `root_cause_ko`

## root cause 분류

- `no_post_activation_rows`
- `preview_filter_rejection_dominant`
- `preview_candidate_available`

## 이번 단계에서 하지 않는 것

- preview rule 완화
- sample floor 조정
- PA8 closeout policy 수정

이번 단계는 오직 “row가 없어서인지, 규칙에 안 걸려서인지”를 분리하는 audit이다.
