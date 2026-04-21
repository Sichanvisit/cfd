# Product Acceptance PA3 Wait / Hold Acceptance Implementation Checklist

## phase kickoff

- [x] latest baseline에서 `must_hold / must_release / bad_exit` queue 재확인
- [x] PA3와 PA4 경계 정의
- [x] first target family 선정

## PA3-1 kickoff target

target:

- `NAS100`
- `SELL`
- `exit_policy_profile=conservative`
- `hard_guard=adverse`
- `adverse_wait=timeout(...)`
- `wait_quality_label=bad_wait`

## implementation steps

### Step 0. baseline freeze

- [x] latest PA0 baseline summary 고정
- [x] top `must_hold 2` row 근거 채집
- [x] top `must_release 10` / `bad_exit 10` family 분포 확인

### Step 1. owner surface 확인

- [x] [exit_service.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_service.py) 의 `adverse_wait_state` 흐름 확인
- [x] [wait_engine.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/wait_engine.py) 의 exit wait engine 경로 확인
- [x] [exit_wait_state_policy.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_wait_state_policy.py) / [exit_wait_state_rewrite_policy.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_wait_state_rewrite_policy.py) 의 hold/rewrite 기준 확인
- [x] [storage_compaction.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/storage_compaction.py) 의 exit wait flat surface 확인

### Step 2. casebook capture

- [x] `good_wait / bad_wait / unnecessary_wait` casebook mini set 작성
- [x] `NAS SELL adverse_wait timeout` 대표 row 묶기
- [x] `XAU BUY protect exit no_wait` 대표 row를 후속 비교군으로 묶기

reference:

- [product_acceptance_pa3_wait_hold_casebook_mini_set_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa3_wait_hold_casebook_mini_set_ko.md)

### Step 3. first adjustment design

- [x] warmup / recovery_need / timeout 기준 조정 포인트 정리
- [x] hold bias rewrite가 over-hold / under-hold에 미치는 영향 분리
- [x] closed-trade label과 runtime wait-state surface의 불일치가 있는지 확인

### Step 4. implementation

- [ ] `exit_service.py` 또는 `exit_wait_state_*` policy 쪽 first patch
- [ ] 필요 시 wait-state surface/logging 보강
- [ ] 관련 unit tests 추가

### Step 5. verification

- [ ] `pytest -q tests/unit/test_wait_engine.py`
- [ ] `pytest -q tests/unit/test_exit_wait_state_policy.py`
- [ ] `pytest -q tests/unit/test_exit_wait_state_rewrite_policy.py`
- [ ] `pytest -q tests/unit/test_exit_wait_state_surface_contract.py`
- [ ] `pytest -q tests/unit/test_loss_quality_wait_behavior.py`
- [ ] 필요 시 end-to-end exit contract test

### Step 6. close-out

- [ ] PA0 baseline refreeze
- [ ] `must_hold 2` 변화 확인
- [ ] `must_release / bad_exit` composition 변화 확인
- [ ] PA3-1 implementation memo 작성

## done condition

- `must_hold 2`가 줄거나 0이 된다
- `bad_wait` timeout family에 대해 왜 더 버티거나 더 빨리 접어야 하는지가 코드/label/log 기준으로 설명된다
- PA4로 넘어갈 때 “이건 hold 문제였고, 저건 final exit 문제”가 분리된다
