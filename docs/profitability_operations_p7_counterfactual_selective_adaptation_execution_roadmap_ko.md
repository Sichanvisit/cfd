# Profitability / Operations P7 Controlled Counterfactual / Selective Adaptation Execution Roadmap

작성일: 2026-03-30 (KST)

## 1. 목적

이 문서는 `P7 controlled counterfactual / selective adaptation`을 실제 구현 가능한 순서로 쪼개기 위한 실행 로드맵이다.

상세 기준은 아래 문서를 따른다.

- [profitability_operations_p7_counterfactual_selective_adaptation_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p7_counterfactual_selective_adaptation_detailed_reference_ko.md)

## 2. 전체 실행 순서

```text
P7-A. counterfactual input contract freeze
-> P7-B. review queue candidate extraction
-> P7-C. proposal typing / evidence scoring
-> P7-D. safety gate / guarded application filter
-> P7-E. first canonical P7 report
-> P7-F. operator handoff memo
```

## 3. P7-A. Counterfactual Input Contract Freeze

### 목표

- P4 / P5 / P6 latest 중 어떤 section을 proposal source로 쓸지 고정한다.

### 핵심 작업

- P4 worsening / improving signal section 고정
- P5 worst / strength / tuning candidate section 고정
- P6 symbol health / sizing / drift / archetype health section 고정
- coverage-aware read 규칙 고정

## 4. P7-B. Review Queue Candidate Extraction

### 목표

- worst scene와 stressed symbol을 기반으로 `counterfactual review 후보`를 추출한다.

### 핵심 작업

- scene key 기준 candidate row 생성
- symbol / setup_key / regime / side 정규화
- top candidate type, top alert type, drift pressure 연결

## 5. P7-C. Proposal Typing / Evidence Scoring

### 목표

- review candidate를 `어떤 종류의 수정 후보인지` proposal type으로 분류하고 evidence score를 준다.

### 핵심 작업

- proposal type taxonomy 정의
- evidence count / health pressure / drift pressure / information gap 반영
- `review_only` vs `guarded_apply_candidate` 기준선 정의

## 6. P7-D. Safety Gate / Guarded Application Filter

### 목표

- 공격적이거나 근거가 약한 proposal을 걸러내고 guarded application queue만 남긴다.

### 핵심 작업

- min evidence gate
- coverage gate
- identity-first gate
- stressed symbol expand 금지
- max change suggestion 제한

## 7. P7-E. First Canonical P7 Report

### 목표

- 첫 canonical P7 latest json / csv / md를 생성한다.

### 핵심 작업

- `overall_counterfactual_summary`
- `counterfactual_review_queue`
- `selective_adaptation_proposal_queue`
- `safety_gate_summary`
- `guarded_application_queue`
- `quick_read_summary`

## 8. P7-F. Operator Handoff Memo

### 목표

- operator가 바로 `실험 후보 / 보류 후보 / 금지 후보`를 읽을 수 있게 memo를 정리한다.

### 핵심 작업

- top guarded proposal 정리
- review-only proposal 정리
- no-go proposal 정리
- 다음 rerun에서 재평가할 트리거 명시

## 9. 우선순위 제안

지금 가장 자연스러운 구현 순서는 아래다.

1. `P7-A`
2. `P7-B`
3. `P7-C`
4. `P7-D`
5. `P7-E`
6. `P7-F`

즉 첫 구현에서는 `A ~ E`를 한 번에 올리고, 마지막에 operator memo로 닫는 순서가 가장 자연스럽다.

## 10. 구현 메모

P7 첫 버전에서 특히 조심할 점은 아래다.

- P7을 full auto-adaptation처럼 구현하지 않는다.
- proposal이 바로 live 적용값으로 읽히지 않게 한다.
- P6 stressed symbol에 expansion proposal이 새지 않게 한다.
- `legacy_bucket_identity_restore`가 먼저인 scene은 그 우선순위를 유지한다.

## 11. 기대 결과

P7 1차 구현이 끝나면 아래가 가능해져야 한다.

- 현재 worst scene를 `다음 실험 후보` 언어로 번역할 수 있다.
- health / drift pressure를 반영한 보수적 proposal filtering이 가능하다.
- operator가 즉시 `무엇을 검토하고 무엇을 미뤄야 하는지` 결정할 수 있다.
