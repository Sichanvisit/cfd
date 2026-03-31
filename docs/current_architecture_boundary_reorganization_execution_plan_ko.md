# CFD 현재 아키텍처 정리 실행 계획

작성일: 2026-03-27 (KST)

## 1. 문서 목적

이 문서는 현재 아키텍처 정리를 실제 작업 단계로 나눠 실행하기 위한 상위 계획서다.

같이 읽으면 좋은 문서:

- [current_architecture_boundary_objective_audit_ko.md](C:/Users/bhs33/Desktop/project/cfd/docs/current_architecture_boundary_objective_audit_ko.md)
- [current_architecture_boundary_reorganization_detail_ko.md](C:/Users/bhs33/Desktop/project/cfd/docs/current_architecture_boundary_reorganization_detail_ko.md)


## 2. 전체 목표

이번 정리의 목표는 새 기능 추가가 아니다.

목표는 아래 네 가지다.

- truth owner를 하나로 모은다
- `BLOCKED`를 끝까지 보존한다
- runtime 표면을 recent diagnostics 중심으로 보강한다
- EntryService를 점진적으로 execution guard 중심으로 되돌린다


## 3. Phase 구성

### Phase 1

문서:

- [current_architecture_boundary_reorganization_phase1_single_owner_blocked_checklist_ko.md](C:/Users/bhs33/Desktop/project/cfd/docs/current_architecture_boundary_reorganization_phase1_single_owner_blocked_checklist_ko.md)

핵심 범위:

- consumer check single owner
- `BLOCKED` visual continuity

목적:

- 최근 wrong READY 류의 truth drift 재발 가능성을 가장 먼저 줄인다

### Phase 2

문서:

- [current_architecture_boundary_reorganization_phase2_runtime_observability_checklist_ko.md](C:/Users/bhs33/Desktop/project/cfd/docs/current_architecture_boundary_reorganization_phase2_runtime_observability_checklist_ko.md)

핵심 범위:

- runtime recent diagnostics
- semantic shadow diagnostics export

목적:

- 새 스레드/운영 점검에서 csv와 코드 의존도를 낮춘다

### Phase 3

문서:

- [current_architecture_boundary_reorganization_phase3_energy_truth_logging_checklist_ko.md](C:/Users/bhs33/Desktop/project/cfd/docs/current_architecture_boundary_reorganization_phase3_energy_truth_logging_checklist_ko.md)

핵심 범위:

- energy truthful usage logging

목적:

- replay/forensics/ML rollout 설명력을 높인다

### Phase 4

문서:

- [current_architecture_boundary_reorganization_phase4_entry_service_slimming_checklist_ko.md](C:/Users/bhs33/Desktop/project/cfd/docs/current_architecture_boundary_reorganization_phase4_entry_service_slimming_checklist_ko.md)

핵심 범위:

- EntryService 경량화

목적:

- 구조 부채를 실질적으로 줄이고 owner 경계를 굳힌다


## 4. 권장 순서

권장 순서는 아래와 같다.

1. Phase 1
2. Phase 2
3. Phase 3
4. Phase 4

이 순서를 권장하는 이유:

- Phase 1이 truth owner를 먼저 안정화한다
- Phase 2가 운영 관측 표면을 강화한다
- Phase 3이 내부 usage trace 신뢰도를 높인다
- Phase 4는 가장 위험도가 높아서 앞선 세 단계로 관측/회귀 안전망을 확보한 뒤 진행하는 편이 안전하다


## 5. Phase별 산출물

### Phase 1 산출물

- 공용 consumer check effective resolver
- chart에서 `BLOCKED` 보존 규칙
- 관련 unit tests

### Phase 2 산출물

- runtime recent diagnostics 필드
- semantic shadow diagnostics 상세 export
- 관련 unit tests

### Phase 3 산출물

- branch-level energy usage trace 체계
- fallback inference compatibility 유지
- 관련 unit tests

### Phase 4 산출물

- EntryService scene-specific branch inventory
- 분리된 owner 구조
- 회귀 테스트 보강


## 6. 진행 방식 권장안

한 번에 큰 정리를 밀어붙이기보다 phase 단위로 자르는 편이 좋다.

권장 방식:

- phase 시작 전 baseline snapshot 확보
- 해당 phase의 checklist만 처리
- phase 종료 후 테스트와 runtime sanity check
- 다음 phase로 넘어가기 전 문서/contract 갱신


## 7. 최소 운영 확인 루틴

각 phase 끝날 때 최소한 아래는 확인하는 것이 좋다.

- `data/runtime_status.json`
- `data/runtime_status.detail.json`
- `data/trades/entry_decisions.csv` 최근 200~300행
- chart 관련 regression tests
- entry_service/runtime status 관련 regression tests


## 8. 최종 메모

이번 정리는 코드 예쁘게 만들기 작업이 아니다.

핵심은 아래다.

- 지금 이미 돌아가는 구조를 덜 흔들리게 만들기
- 같은 종류의 truth drift가 반복되지 않게 만들기
- 새 스레드와 운영 점검의 비용을 줄이기

따라서 phase 순서를 지키는 것이 중요하다.
