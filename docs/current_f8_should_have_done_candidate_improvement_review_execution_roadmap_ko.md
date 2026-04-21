# F8. should-have-done alignment / candidate improvement review 실행 로드맵

## 1. 목적

F7에서 만든 `old vs new flow chain delta`를 should-have-done truth와 다시 묶어서,

- 새 체인이 후보를 더 잘 살렸는지
- tightening이 실제로 맞는 tightening인지
- widening이 검증되지 않은 widening인지

를 공용 review surface로 고정한다.

---

## 2. 구현 순서

### S1. upstream 정합

아래 upstream이 row에 없으면 attach helper로 다시 붙인다.

- `flow_chain_shadow_comparison`
- `dominance_validation_profile`

완료 기준:

- 단독 row 입력만으로도 F8 row builder가 self-contained하게 동작

### S2. candidate truth state 정의

truth enum:

- `NO_CANDIDATE`
- `WIDEN_EXPECTED`
- `TIGHTEN_EXPECTED`
- `REVIEW_PENDING`

완료 기준:

- `dominance_error_type_v1` 기준 widening/tightening 기대 방향이 일관되게 정해짐

### S3. review verdict 매핑

delta와 truth를 조합해 verdict를 만든다.

핵심 verdict:

- `ALIGNED_IMPROVEMENT`
- `MISSED_IMPROVEMENT`
- `OVER_TIGHTENED`
- `ALIGNED_TIGHTENING`
- `MISSED_TIGHTENING`
- `OVER_WIDENED`
- `UNVERIFIED_WIDENING`
- `SAFE_TIGHTENING`

완료 기준:

- widening/tightening의 좋고 나쁨이 truth 기준으로 분리됨

### S4. row-level flat surface

아래 field를 row에 올린다.

- `flow_candidate_truth_state_v1`
- `flow_candidate_shadow_delta_v1`
- `flow_candidate_review_alignment_v1`
- `flow_candidate_improvement_verdict_v1`
- `flow_candidate_review_priority_v1`
- `flow_candidate_improved_v1`

완료 기준:

- row 하나만 봐도 후보 개선 여부가 읽힘

### S5. summary / artifact

요약 count와 json/md artifact를 만든다.

완료 기준:

- candidate improved / missed / regression / unverified widening이 summary count로 보임

### S6. runtime_status.detail.json export

detail payload에 아래를 올린다.

- `flow_candidate_improvement_review_contract_v1`
- `flow_candidate_improvement_review_summary_v1`
- `flow_candidate_improvement_review_artifact_paths`

완료 기준:

- runtime detail에서 F8 계약/요약/artifact path를 바로 읽을 수 있음

### S7. 검증

단위 테스트:

- widen expected + widening -> aligned improvement
- widen expected + tightening -> over tightened
- tighten expected + opposed/tightening -> aligned tightening
- no candidate + widening -> unverified widening
- artifact write / runtime export

완료 기준:

- 테스트 통과
- `py_compile ok`

---

## 3. 상태 기준

- `READY`: verdict와 summary가 일관되게 surface됨
- `HOLD`: 일부 row는 truth가 `REVIEW_PENDING`으로 남아 추가 정제가 필요
- `BLOCKED`: 같은 upstream row에서 attach/recompute 결과가 verdict를 뒤집음

---

## 4. 다음 단계 연결

F8이 끝나면 다음은 두 갈래다.

1. `XAU bounded canary`에 F8 verdict를 같이 걸어, widening/tightening이 실제로 좋은 방향인지 더 보수적으로 검증
2. `NAS/BTC commonization`에서 새 flow chain widening이 검증되지 않은 widening으로 과도하게 퍼지지 않는지 확인
