# Product Acceptance PA4 Exit Acceptance Implementation Checklist

## phase kickoff

- [x] latest baseline에서 `must_release / bad_exit` queue 재확인
- [x] PA3와 PA4 경계 정의
- [x] first target family 선정

## PA4-1 kickoff target

target:

- `NAS100`
- `SELL`
- `exit_policy_profile=conservative`
- `wait_quality_label=no_wait`
- `Protect Exit`
- `Flow: BB 20/2 mid 돌파지지 (+80점)`
- `TopDown 1M: bullish (+20점)`
- `hard_guard=adverse`

## implementation steps

### Step 0. baseline freeze

- [x] latest PA0 baseline summary 고정
- [x] top `must_release 10` row 근거 채집
- [x] top `bad_exit 10` family 분포 확인

### Step 1. owner surface 확인

- [x] [exit_service.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_service.py) 의 exit reason normalize / stage mapping 확인
- [x] [exit_engines.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_engines.py) 의 stage router / action executor 확인
- [x] [wait_engine.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/wait_engine.py) 의 exit utility / wait_selected path 확인
- [x] [trade_csv_schema.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/trade_csv_schema.py) 의 `loss_quality_label / wait_quality_label` 계산 확인

### Step 2. casebook capture

- [ ] `bad_exit protect` 대표 row 묶기
- [ ] `same-context but different quality` control row 묶기
- [ ] `NAS SELL protect adverse`와 `XAU BUY protect adverse` 비교 묶기

### Step 3. first adjustment design

- [ ] `Protect Exit`가 너무 빠른 경우와 맞는 경우를 나누는 기준 정리
- [ ] `hard_guard=adverse`와 `plus_to_minus`를 같은 축으로 볼지 분리
- [ ] `utility_exit_now / utility_hold / utility_reverse`와 final close reason 불일치 확인

### Step 4. implementation

- [ ] `exit_service.py` / `exit_engines.py` 쪽 first patch
- [ ] 필요 시 closed-trade label surface 보강
- [ ] 관련 unit tests 추가

### Step 5. verification

- [ ] `pytest -q tests/unit/test_exit_service.py`
- [ ] `pytest -q tests/unit/test_wait_engine.py`
- [ ] `pytest -q tests/unit/test_loss_quality_wait_behavior.py`
- [ ] 필요 시 exit end-to-end contract test

### Step 6. close-out

- [ ] PA0 baseline refreeze
- [ ] `must_release 10` 변화 확인
- [ ] `bad_exit 10` composition 변화 확인
- [ ] PA4-1 implementation memo 작성

## done condition

- `Protect Exit` family에 대해 왜 너무 빨랐는지 / 왜 맞는지 코드와 label 기준으로 설명된다
- `must_release / bad_exit`가 실제로 감소한다
- PA5 product-level integration review로 넘어갈 때 exit quality 설명이 가능하다
