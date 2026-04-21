# D8. XAU should-have-done / dominance 검증 강화 상세 계획

## 목적

D7에서 surface된 XAU decomposition row를 should-have-done / canonical / dominance 검증과 다시 묶어,
XAU에서 어떤 장면이 over-veto, under-veto, boundary 과체류, friction 오분류로 소비되는지 수치로 읽는 단계다.

## 왜 필요한가

D7은 “XAU row를 decomposition 언어로 읽는 것”까지 해결한다.

하지만 다음 질문은 아직 남아 있다.

- 이 decomposition surface가 실제로 error typing을 더 잘 설명하는가?
- XAU에서 over-veto를 줄이는 방향으로 읽히는가?
- friction rejection과 reversal rejection이 실제 검증 레이어에서도 분리되는가?
- boundary에 너무 오래 머무는 장면을 더 잘 표시하는가?

그래서 D8은 decomposition surface를 검증 teacher와 다시 묶는 단계다.

## 핵심 원칙

- D8은 XAU 전용 검증층이다.
- execution/state25는 바꾸지 않는다.
- should-have-done candidate는 calibration teacher 입력일 뿐 직접 액션이 아니다.
- `dominant_side` 변경 권한은 여전히 dominance layer에만 있다.

## row-level validation fields

- `xau_decomposition_validation_profile_v1`
- `xau_slot_alignment_state_v1`
- `xau_should_have_done_candidate_v1`
- `xau_over_veto_flag_v1`
- `xau_under_veto_flag_v1`
- `xau_decomposition_error_type_v1`
- `xau_dominance_validation_reason_summary_v1`

## alignment 상태

- `ALIGNED`
- `DOMINANCE_MISMATCH`
- `BOUNDARY_OVERRUN`
- `REVIEW_PENDING`
- `NOT_APPLICABLE`

## 핵심 검증 지표

- `slot_alignment_rate`
- `should_have_done_candidate_count`
- `over_veto_rate`
- `under_veto_rate`
- `friction_separation_quality`
- `boundary_dwell_quality`
- `dominance_error_type_count_summary`
- `pilot_window_match_count_summary`

## 판단 철학

- `ALIGNED`
  - slot surface와 dominance/canonical 소비가 잘 맞음
- `DOMINANCE_MISMATCH`
  - continuation underpromotion, reversal overcall, true reversal miss 같은 dominance 계열 오판
- `BOUNDARY_OVERRUN`
  - boundary가 과도하게 길어져 기회를 놓친 케이스
- `REVIEW_PENDING`
  - profile/pilot match가 아직 충분하지 않아 검증 유보

## artifact

- `xau_decomposition_validation_summary_v1`
- `xau_decomposition_validation_latest.json`
- `xau_decomposition_validation_latest.md`

## 완료 기준

- XAU row에서 decomposition slot과 dominance error가 함께 읽힌다.
- over-veto / under-veto / boundary 과체류를 XAU 기준으로 바로 볼 수 있다.
- 이후 NAS/BTC 일반화 전에 XAU pilot 품질을 수치로 확인할 수 있다.

## 상태 기준

- `READY`: XAU validation summary와 row-level field가 정상 생성됨
- `HOLD`: XAU row는 있으나 validation join이 불완전함
- `BLOCKED`: XAU validation layer 때문에 runtime export가 깨짐
