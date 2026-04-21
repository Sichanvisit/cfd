# Semantic Gate Review Candidate Lane

## 목적

`semantic baseline_no_action`이 반복될 때 단순히 군집만 보는 데서 멈추지 않고,
어떤 gate를 먼저 review backlog로 올릴지 후보를 만든다.

## 왜 필요한가

- 현재 semantic은 `baseline_no_action`이 많아 live eligible이 거의 생기지 않는다.
- 그런데 이 상태에서 threshold를 바로 낮추면 잘못된 장면까지 같이 열릴 수 있다.
- 따라서 먼저 `blocked_by / action_none_reason / trace_quality` 기준으로
  어떤 gate가 반복적으로 semantic promotion을 막는지 review 후보로 분해한다.

## 입력

- `semantic_baseline_no_action_sample_audit_latest.json`

## 출력

- `semantic_baseline_no_action_gate_review_candidate_latest.json`
- `semantic_baseline_no_action_gate_review_candidate_latest.md`
- `/propose` payload의 `semantic_gate_review_candidates`

## 핵심 원칙

- 거래 로직 변경 없음
- threshold/guard 자동 변경 없음
- detector feedback과 semantic cluster 관찰과 분리된 `review backlog 후보`만 추가

## 기대 결과

- 운영자는 `energy_soft_block`, `outer_band_guard`, `probe_not_promoted`, `execution_soft_blocked` 중
  무엇을 먼저 review할지 명확히 볼 수 있다.
- semantic cluster 관찰과 semantic gate review 후보가 같은 proposal 언어로 이어진다.
- 나중에 gate를 조절할 때 “왜 이 gate를 먼저 봤는지” 근거가 남는다.
