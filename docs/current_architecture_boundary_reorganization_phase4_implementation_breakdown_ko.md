# CFD 현재 아키텍처 정리 Phase 4 구현 분해 문서

부제: EntryService Slimming 1차 구현 가이드

작성일: 2026-03-27 (KST)

## 진행 상태 (2026-03-27)

아래 4개 슬라이스는 구현과 회귀 검증까지 완료된 상태다.

- `entry_energy_relief_policy.py`
- `entry_probe_plan_policy.py`
- `entry_default_side_gate_policy.py`
- `entry_probe_handoff_policy.py`

즉 현재 `EntryService`는 scene-specific policy owner라기보다
`edge_pair_law fallback 구성 -> helper 호출 -> trace/return payload 조합`
중심의 orchestration 층에 가까워졌다.

## 1. 문서 목적

이 문서는 Phase 4를 실제 코드 수정 순서로 쪼개기 위한 구현 기준서다.

이번 라운드의 목표는 Phase 4 전체를 한 번에 끝내는 것이 아니라,
`EntryService` 안에 남아 있는 scene-specific policy 중
가장 안전하게 분리할 수 있는 첫 슬라이스를 떼어내는 것이다.

이번 슬라이스의 이름은 아래처럼 고정한다.

- `energy soft-block relief owner extraction`


## 2. 왜 이 조각부터 시작하는가

현재 `EntryService` 안에는 크게 세 종류의 policy가 섞여 있다.

- default-side semantic gate
- probe-plan / structural relief
- energy soft-block relief

이 중에서 첫 구현 대상으로 `energy soft-block relief`를 고른 이유는 다음과 같다.

- scene-specific 조건이 뚜렷하다.
- 이미 회귀 테스트가 충분히 깔려 있다.
- 계산 입력과 출력이 비교적 닫혀 있다.
- 행동 보존형 extraction이 가능하다.

반대로 probe-plan 전체를 먼저 빼려고 하면
default-side gate, structural relief, handoff archetype 보정까지 한 번에 같이 흔들릴 수 있다.


## 3. 이번 슬라이스의 범위

### 포함

- `EntryService` 안의 energy soft-block relief 판정 분리
- scene-specific relief boolean owner 이동
- `energy_soft_block_should_block` 최종 판정 owner 이동
- helper 직접 테스트 추가

### 제외

- `probe_plan_v1` 전체 owner 이동
- `default_side_gate_v1` owner 이동
- symbol temperament map 재구성
- runtime diagnostics shape 추가 변경
- chart / consumer check 의미 수정


## 4. 현재 실제 대상 블록

현재 실제 중심 블록은 아래 역할을 묶어서 처리하고 있다.

- `effective_priority_rank` 이후 energy relief 판정
- `probe_energy_relief`
- `confirm_energy_relief`
- `xau_second_support_energy_relief`
- `xau_upper_sell_probe_energy_relief`
- `xau_upper_mixed_confirm_energy_relief`
- `energy_soft_block_should_block`

이 블록은 숫자 threshold 계산이 아니라
scene-specific execution advisory policy에 더 가깝다.

즉 `EntryService`의 core owner라기보다
독립 policy owner로 분리하는 편이 구조적으로 맞다.


## 5. 새 owner 제안

### 새 파일

- `backend/services/entry_energy_relief_policy.py`

### public 함수

- `resolve_entry_energy_soft_block_policy_v1(...) -> dict`

### 이 함수가 갖는 책임

- 입력 상태를 보고 relief booleans를 계산한다.
- final `energy_soft_block_should_block`를 계산한다.
- 어떤 relief flag가 적용되었는지 표준화된 결과를 돌려준다.

### 이 함수가 갖지 않는 책임

- `effective_priority_rank` 자체 계산
- `adjusted_core_score` 자체 계산
- trace recorder 생성/저장
- 최종 action payload 작성

즉 이 helper는 `판정 owner`이고,
`EntryService`는 그 결과를 조합하고 기록하는 caller로 남는다.


## 6. 권장 입출력 형태

### 핵심 입력

- `symbol`
- `shadow_action`
- `shadow_reason`
- `consumer_archetype_id`
- `box_state`
- `bb_state`
- `default_side_gate_v1`
- `probe_plan_v1`
- `observe_metadata`
- `forecast_assist_v1`
- `energy_soft_block_active`
- `energy_soft_block_reason`
- `energy_soft_block_strength`
- `energy_action_readiness`
- `effective_priority_rank`
- `adjusted_core_score`

### 핵심 출력

- `probe_energy_relief`
- `confirm_energy_relief_local_ready`
- `confirm_energy_relief`
- `xau_second_support_energy_relief`
- `xau_upper_sell_probe_energy_relief`
- `xau_upper_mixed_confirm_energy_relief`
- `relief_flags`
- `energy_soft_block_should_block`


## 7. 구현 순서

### Step 1. helper 모듈 추가

- `backend/services/entry_energy_relief_policy.py`

먼저 기존 `entry_service.py`의 조건문을 거의 그대로 옮겨서
행동을 바꾸지 않는 pure helper를 만든다.

### Step 2. EntryService caller 치환

- `backend/services/entry_service.py`

`EntryService` 안에서는 아래만 유지한다.

- priority rank 계산
- core score 계산
- helper 호출
- trace/return payload 조합

### Step 3. trace 작성부 연결 유지

기존 `consumer_energy_usage_trace_v1`가 깨지지 않도록
recorded trace는 helper 결과만 읽도록 바꾼다.

중요한 점은
trace schema를 바꾸는 것이 아니라
relief flag owner만 교체하는 것이다.

### Step 4. helper 직접 테스트 추가

- `tests/unit/test_entry_energy_relief_policy.py`

최소한 아래 case를 고정한다.

- no relief -> blocked
- BTC confirm relief
- XAU second support probe relief
- XAU upper mixed confirm relief

### Step 5. 기존 EntryService 회귀 테스트 재확인

- `tests/unit/test_entry_service_guards.py`

특히 아래 시나리오가 유지되는지 본다.

- BTC upper confirm relief
- BTC upper break fail confirm relief
- XAU second support probe relief
- XAU upper sell probe relief
- XAU upper mixed confirm relief


## 8. 이번 슬라이스 완료 기준

- `EntryService` 안에 scene-specific energy relief 판단식이 직접 남아 있지 않다.
- 새 helper가 relief flags와 block 판정을 단일 owner로 갖는다.
- 기존 entry guard 회귀 테스트가 그대로 통과한다.
- 새 helper 직접 테스트가 추가된다.


## 9. 이번 라운드에서 일부러 하지 않는 것

- probe-plan builder 분리
- structural relief owner 이동
- default-side gate 분리
- handoff archetype fallback 정리

이건 다음 라운드의 자연스러운 후보들이다.
이번 라운드는 energy relief extraction까지만 닫는 것이 안전하다.


## 10. 다음 후보

이번 슬라이스가 끝나면 그 다음 후보는 아래 둘 중 하나다.

1. `probe_plan_v1` builder extraction
2. `default_side_gate_v1` extraction

개인적으로는 다음 순서를 권장한다.

1. energy relief extraction 완료
2. probe-plan / structural relief extraction
3. default-side gate extraction

이 순서가 `EntryService`를 execution guard 조합기로 가장 자연스럽게 되돌린다.
