# S1 state_strength_profile_contract_v1 실행 로드맵

## 1. 목적

`S1`은 새 dominance 해석층의 첫 실체를 만드는 단계다.

핵심은 local structure나 execution 연결까지 한 번에 가지 않고,
먼저 `state strength` 원인층/도출층 계약을 read-only로 안정화하는 것이다.

## 2. 구현 범위

### 포함

- `state_strength_profile_contract_v1` 계약 정의
- row-level `state_strength_profile_v1` surface
- `state_strength_summary_v1` artifact 생성
- runtime detail export
- 단위 테스트

### 제외

- local structure 계산
- veto tier 계산
- dominance discount
- execution/state25 변경

## 3. 단계

### S1-A. 계약 정의

아래 enum/필드 계약을 고정한다.

- `side_seed_enum_v1`
- `side_seed_source_enum_v1`
- `dominant_mode_enum_v1`
- `caution_level_enum_v1`
- `dominance_gap_definition_v1`

완료 기준:

- 계약 문서와 코드 builder가 같은 정의를 surface한다

### S1-B. side seed 계산

우선순위:

1. `directional_continuation_overlay_direction`
2. `htf_alignment_state`
3. `previous_box_relation`
4. `previous_box_break_state`

출력:

- `state_strength_side_seed_v1`
- `state_strength_side_seed_source_v1`
- `state_strength_side_seed_confidence_v1`

완료 기준:

- 각 row가 `BULL / BEAR / NONE` seed를 공용 규칙으로 갖는다

### S1-C. cause-layer 계산

v1 중심축:

- `continuation_integrity`
- `reversal_evidence`
- `friction`

보조 surface:

- `trend_pressure`
- `exhaustion_risk`
- `ambiguity`

완료 기준:

- row마다 원인층 점수가 0.0~1.0 범위로 surface된다

### S1-D. derived-layer 계산

v1 도출:

- `wait_bias_strength`
- `dominance_gap`
- `dominant_side`
- `dominant_mode`
- `caution_level`

고정 원칙:

- `dominance_gap = continuation_integrity - reversal_evidence`
- `friction`은 gap에 직접 넣지 않음
- `friction`은 side를 바꾸지 않음

완료 기준:

- row마다 우세 해석이 같은 언어로 surface된다

### S1-E. summary/artifact 생성

artifact:

- `state_strength_summary_latest.json`
- `state_strength_summary_latest.md`

summary:

- `side_seed_count_summary`
- `dominant_side_count_summary`
- `dominant_mode_count_summary`
- `caution_level_count_summary`
- `avg_continuation_integrity_v1`
- `avg_reversal_evidence_v1`
- `avg_friction_v1`
- `avg_dominance_gap_v1`

완료 기준:

- row-level surface뿐 아니라 전체 snapshot 요약이 남는다

### S1-F. runtime detail export

detail payload에 아래를 추가한다.

- `state_strength_profile_contract_v1`
- `state_strength_summary_v1`
- `state_strength_artifact_paths`

완료 기준:

- live runtime detail에서 S1 상태를 바로 읽을 수 있다

### S1-G. 테스트

최소 테스트:

- overlay up + caution present일 때 `BULL + CONTINUATION_WITH_FRICTION`
- friction은 dominant_side를 바꾸지 않음
- `dominance_gap = continuation_integrity - reversal_evidence`
- summary/artifact 생성
- runtime detail export

## 4. 상태 기준

- `READY`
  - contract, row surface, summary, artifact, runtime export 모두 생성
- `HOLD`
  - contract는 있으나 row surface 또는 summary가 일부 비어 있음
- `BLOCKED`
  - surface가 기존 runtime payload를 깨거나 dominance 정의가 불안정함

## 5. 다음 연결

`S1`이 완료되면 그 다음은 아래 순서다.

1. `S2 local_structure_profile_v1`
2. `S3 runtime read-only combined surface`
3. `S4 dominance resolver shadow-only`

즉 S1은 dominance layer 전체가 아니라, 그 기반이 되는 `state strength` 언어를 먼저 고정하는 단계다.
