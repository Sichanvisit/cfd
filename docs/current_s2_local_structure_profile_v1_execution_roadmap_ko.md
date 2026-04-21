# S2 local_structure_profile_v1 실행 로드맵

## 1. 목적

`S2`는 최근 구조를 공용 상태 등급으로 고정하는 단계다.

핵심은 raw candle 전체를 새로 계산하는 것이 아니라, 이미 row에 들어와 있는 breakout/retest/hold proxy를
`higher_low / lower_high / breakout_hold / body_drive` 언어로 surface하는 것이다.

## 2. 구현 범위

### 포함

- `local_structure_profile_contract_v1` 계약 정의
- row-level `local_structure_profile_v1` surface
- `local_structure_summary_v1` artifact 생성
- runtime detail export
- 단위 테스트

### 제외

- dominance resolver
- veto tier
- local continuation discount
- execution/state25 변경

## 3. 단계

### S2-A. 계약 정의

아래 enum/필드 계약을 고정한다.

- `few_candle_higher_low_state_v1`
- `few_candle_lower_high_state_v1`
- `breakout_hold_quality_v1`
- `body_drive_state_v1`
- `few_candle_structure_bias_v1`

완료 기준:

- 계약 문서와 코드 builder가 같은 enum을 surface한다

### S2-B. 구조 재료 재사용

v1 입력 재료:

- `breakout_event_runtime_v1`
- `checkpoint_runtime_hold_quality_score`
- `previous_box_high_retest_count`
- `previous_box_low_retest_count`
- `previous_box_break_state`
- `previous_box_relation`
- `leg_direction`
- `state_strength_side_seed_v1`

완료 기준:

- raw candle 복원 없이도 local structure 상태를 계산할 수 있다

### S2-C. primary axes 계산

필수 출력:

- `few_candle_higher_low_state_v1`
- `few_candle_lower_high_state_v1`
- `breakout_hold_quality_v1`
- `body_drive_state_v1`

보조 출력:

- `few_candle_structure_bias_v1`
- `local_structure_reason_summary_v1`

완료 기준:

- continuation favor / mixed / reversal favor를 한 줄 구조 설명으로 남길 수 있다

### S2-D. summary/artifact 생성

artifact:

- `local_structure_summary_latest.json`
- `local_structure_summary_latest.md`

summary:

- `higher_low_state_count_summary`
- `lower_high_state_count_summary`
- `breakout_hold_quality_count_summary`
- `body_drive_state_count_summary`
- `structure_bias_count_summary`

완료 기준:

- snapshot 전체 local structure 분포를 읽을 수 있다

### S2-E. runtime detail export

detail payload에 아래를 추가한다.

- `local_structure_profile_contract_v1`
- `local_structure_summary_v1`
- `local_structure_artifact_paths`

완료 기준:

- live runtime detail에서 S2 상태를 바로 읽을 수 있다

### S2-F. 테스트

최소 테스트:

- bull breakout held 장면에서 `higher_low = HELD/CLEAN_HELD`
- breakout failure 위험이 큰 장면에서 `breakout_hold_quality = FAILED/WEAK`
- counter direction breakout이면 `body_drive_state = COUNTER_DRIVE`
- summary/artifact 생성
- runtime detail export

## 4. 상태 기준

- `READY`
  - contract, row surface, summary, artifact, runtime export 모두 생성
- `HOLD`
  - 일부 state만 생성되거나 summary가 비어 있음
- `BLOCKED`
  - S2가 기존 runtime payload를 깨거나 구조 축이 일관되게 surface되지 않음

## 5. 다음 연결

`S2`가 완료되면 그 다음은 아래 순서다.

1. `S3 runtime read-only combined surface`
2. `S4 dominance resolver shadow-only`

즉 S2는 local structure 자체를 계약으로 고정하는 단계이고, dominance 판단은 다음 단계에서 한다.
