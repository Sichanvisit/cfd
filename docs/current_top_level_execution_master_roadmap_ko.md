# Current Top-Level Execution Master Roadmap

## 목적

이 문서는 현재 CFD 프로젝트에서

- 어떤 상위 로드맵이 실제로 살아 있고
- 지금 우리가 어디까지 구축했으며
- 무엇이 선행 blocker이고
- 그 다음 어떤 순서로 진행해야 하는지

를 한 장에서 보려는 master roadmap이다.

이 문서의 핵심은
개별 하위 로드맵을 없애는 것이 아니라,
`상위 방향 -> 현재 활성 구현축 -> 선행 hotfix -> 다음 운영층`
관계를 한 번에 보이게 하는 것이다.

## 한 줄 요약

현재 상태는 아래 순서로 읽는 것이 맞다.

1. `state25 / product acceptance`가 가장 큰 상위 배경이다
2. 그 아래 `execution authority integration`이 owner / conflict / bounded multi-owner의 중간 상위 실행축이다
3. 그 아래 `market-family multi-surface`가 최근 실제 구현의 중심축이다
4. 다만 `CL 운영층`으로 바로 가지 않고, 먼저 `P0 wrong-side active-action conflict hotfix`를 선행해야 한다
5. 그 다음에 `MF17 manual signoff -> bounded activation`으로 넘어간다
6. 그리고 `follow_through / continuation_hold / protective_exit`를 더 잘 다루기 위해
   `path-aware checkpoint decision` 설계 질문을 병행한다
7. 그 뒤 `CL1~CL9`로 운영층을 닫는다

## 현재 상위 로드맵 스택

### 1. State25 / Product Acceptance 상위 배경

기준 문서:

- [product_acceptance_teacher_label_state25_current_handoff_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_state25_current_handoff_ko.md)
- [product_acceptance_teacher_label_state25_master_plan_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_state25_master_plan_ko.md)
- [product_acceptance_reorientation_execution_roadmap_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_reorientation_execution_roadmap_ko.md)

역할:

- 사람이 보는 차트 패턴과 시스템 state/forecast/decision을 더 잘 맞추는 최상위 기준축
- state25, micro-structure, acceptance, bounded live의 큰 배경을 정의

현재 해석:

- 최상위 기준과 문서 체인은 이미 존재한다
- 지금 최근 구현은 이 상위 체인 아래에서 `execution authority -> market-family multi-surface -> continuous learning` 쪽으로 내려온 상태다

### 2. Execution Authority Integration 중간 상위 실행축

기준 문서:

- [current_execution_authority_integration_implementation_roadmap_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_execution_authority_integration_implementation_roadmap_ko.md)

역할:

- entry/exit owner
- veto owner
- conflict/demotion
- bounded multi-owner

를 실제 runtime/action trace로 연결하는 중간 상위 로드맵

현재 해석:

- owner, veto, bounded multi-owner 철학은 이미 이 문서에서 많이 정리됐다
- 하지만 최근 runtime에서 드러난 `old baseline active action vs directional owner conflict`는
  이 상위 원칙을 실제 runtime resolution으로 더 밀어 넣어야 한다는 뜻이다

### 3. Market-Family Multi-Surface 현재 구현축

기준 문서:

- [current_market_family_multi_surface_execution_design_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_market_family_multi_surface_execution_design_ko.md)
- [current_market_family_multi_surface_execution_implementation_roadmap_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_market_family_multi_surface_execution_implementation_roadmap_ko.md)

현재까지 구축된 범위:

- `PF0` 성능 baseline hold 완료
- `MF1 ~ MF16` 구현 완료
- `MF17` 구조 구현 완료
  - candidate gate
  - review manifest
  - signoff criteria
  - signoff packet
  - activation contract
  - NAS/XAU initial-entry label apply

현재 도달 상태:

- `BTCUSD initial_entry_surface`
- `NAS100 initial_entry_surface`
- `XAUUSD initial_entry_surface`

세 symbol 모두 같은 공통 signoff packet과 공통 activation contract 안에서
`READY_FOR_MANUAL_SIGNOFF / PENDING_MANUAL_SIGNOFF` 상태까지 올라왔다.

즉 `구축 단계` 자체는 거의 끝났고,
원래라면 다음은 `manual signoff -> bounded activation -> CL 운영층`으로 가는 구간이었다.

## 왜 P0가 먼저인가

최근 runtime audit 기준으로,
현재 시스템은 어떤 장면에서는 이미 `directional layer`가 반대 방향을 보고 있는데도
`old baseline active action`이 실행 우선권을 계속 쥐고 있다.

대표 문제:

- XAU recent row에서
  - 실제 실행: `SELL`
  - source: `baseline_score`
  - 그런데 같은 row directional layer:
    - `UP_PROBE`
    - `BUY`
    - 높은 `up_bias_score`

즉 문제는

- 상승 continuation을 못 보는 것

이 아니라

- old baseline이 너무 강하게 reversal을 해석하고
- candidate bridge는 아직 `baseline_no_action`에서만 작동하며
- active baseline과 directional candidate의 충돌을 해소하지 못하는 것

이다.

따라서 다음 순서는 아래가 맞다.

1. `P0 wrong-side active-action conflict hotfix`
2. `MF17 manual signoff`
3. `bounded activation`
4. `path-aware checkpoint decision`
5. `CL1~CL9 continuous operating layer`

## P0. Wrong-Side Active-Action Conflict Hotfix

전용 상세 요청 문서:

- [current_wrong_side_active_action_conflict_external_review_request_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_wrong_side_active_action_conflict_external_review_request_ko.md)

핵심 목표:

- `baseline SELL`인데 `directional BUY / UP_PROBE`가 강하면 바로 `SELL`을 실행하지 않게 막는다
- 그 conflict row를 학습용 failure/contrast label로 자동 승격한다

세부 단계:

1. `P0A Wrong-Side Active-Action Conflict Audit`
2. `P0B Active-Action Conflict Guard`
3. `P0C Baseline-vs-Directional Bridge Conflict Resolution`
4. `P0D Wrong-Side Conflict Harvest`
5. `P0E XAU Upper-Reversal Conflict Validation`

P0 완료 기준:

- old baseline active action이 더 이상 directional layer와 강하게 충돌하는 장면에서 바로 진입하지 않는다
- conflict row가 audit + harvest + validation artifact에 동시에 남는다
- 그 다음에야 MF17 signoff를 다시 재개할 수 있다

## MF17. Signoff / Bounded Activation

P0 이후 바로 재개할 단계:

1. `BTC/NAS/XAU initial_entry_surface` 수동 signoff
2. signoff된 symbol-surface만 bounded activation
3. 이후 follow-through / continuation_hold / protective_exit도 같은 gate로 순차 승격

현재 남아 있는 데이터 보강:

- `follow_through negative expansion`
- `continuation_hold / protective_exit` augmentation

즉 MF17의 남은 일은
`새 구조 만들기`가 아니라
이미 만든 구조를 실제 승인/제한적 활성화로 올리는 것이다.

## Path-Aware Checkpoint Decision

전용 외부 조언 요청 문서:

- [current_path_aware_checkpoint_decision_external_review_request_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_path_aware_checkpoint_decision_external_review_request_ko.md)

핵심 문제:

- 지금까지는 `point decision`을 많이 다뤘다
  - 지금 살까
  - 지금 기다릴까
  - 지금 팔까
- 하지만 실제 차트는 한 번의 큰 leg 안에서
  `1, 2, 3, 4, 5` 체크포인트를 계속 다시 읽는 구조다
- 따라서 다음 단계는
  `entry/hold/partial_exit/full_exit/rebuy`
  를 leg 안의 checkpoint마다 다시 판단하게 만드는 것이다

핵심 질문:

- 이 구조를 새 surface로 볼지,
  기존 `follow_through / continuation_hold / protective_exit`
  위의 공통 checkpoint layer로 볼지
- checkpoint row schema와 상태기계를 어떻게 잡을지
- 어떤 라벨은 auto-apply로, 어떤 라벨은 manual-exception으로 남길지

현재 판단:

- `P0`는 응급처치다
- `MF17 initial_entry`는 signoff/activation 계속 간다
- 그 다음 `follow_through / hold / exit`는
  `path-aware checkpoint decision`을 통해 더 정교화하는 것이 맞다

## CL. Continuous Operating Layer

P0와 MF17 이후의 다음 큰 줄기:

- `CL1 Continuous Learning Orchestrator`
- `CL2 Candidate Package Schema Standardization`
- `CL3 Signoff Queue / Lifecycle Status`
- `CL4 Symbol-Specific Observability Registries`
- `CL5 Surface KPI Collector`
- `CL6 Canary Runtime Guard / Rollback Engine`
- `CL7 Auto-Apply / Manual-Exception / Diagnostic Policy`
- `CL8 LLM Summary Layer`
- `CL9 Operating Mode System`

이 단계의 핵심은
전략 로직을 더 붙이는 것이 아니라,

`runtime rows -> harvest -> rebuild -> eval -> signoff -> canary -> rollback -> observability`

를 자동으로 닫는 운영층을 구축하는 것이다.

## 지금 실제 진행 순서

지금부터는 아래 순서로 읽고 실행하는 것이 맞다.

1. 상위 배경 확인
   - [product_acceptance_teacher_label_state25_current_handoff_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_state25_current_handoff_ko.md)
   - [product_acceptance_teacher_label_state25_master_plan_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_state25_master_plan_ko.md)
2. 현재 활성 구현축 확인
   - [current_market_family_multi_surface_execution_implementation_roadmap_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_market_family_multi_surface_execution_implementation_roadmap_ko.md)
3. 선행 blocker 확인
   - [current_wrong_side_active_action_conflict_external_review_request_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_wrong_side_active_action_conflict_external_review_request_ko.md)
4. P0 해결
5. MF17 signoff / bounded activation 재개
6. path-aware checkpoint decision 검토
7. CL1~CL9 운영층 구축

## 최종 요약

이 프로젝트는 지금

- `전략 로직을 더 만드는 단계`

가 아니라

- `이미 만든 판단 구조를 잘못된 old baseline 실행으로부터 먼저 보호하고`
- `그다음 candidate/signoff/canary/rollback 운영 루프로 닫는 단계`

에 있다.

한 줄로 요약하면:

> 현재 활성 순서는 `P0 runtime correction -> MF17 signoff/activation -> path-aware checkpoint decision -> CL operating layer`다.
