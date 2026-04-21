# Product Acceptance PA3 Teacher Label Wait Hold Acceptance Implementation Checklist

## kickoff

- [x] teacher-label screenshot casebook 확보
- [x] split axis를 `wait / hold`로 분리
- [x] 기존 PA3 hold queue와 teacher-label hold correctness를 분리

## implementation steps

### Step 0. anchor capture

- [x] screenshot에서 `더 기다려야 하는 자리` 의미 재정의
- [ ] NAS / XAU / BTC별 hold anchor를 1~2개씩 문장으로 고정
- [ ] release/cut 자리와 hold 자리를 혼동하지 않도록 경계 메모 작성

### Step 1. owner read

- [ ] [exit_service.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_service.py) 의 hold/wait break 경로 재확인
- [ ] [wait_engine.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/wait_engine.py) 의 utility winner 재확인
- [ ] [exit_wait_state_policy.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_wait_state_policy.py) 의 hold family 재확인

### Step 2. screenshot-to-runtime mapping

- [ ] hold teacher-label anchor가 어떤 runtime family에 대응하는지 추정
- [ ] 너무 빨리 release로 기우는 family 후보 선정
- [ ] 반대로 hold하면 안 되는 bounce family도 같이 분리

### Step 3. first patch design

- [ ] legitimate hold와 illegitimate hold를 분리하는 기준 명문화
- [ ] green-zone continuation hold와 red-zone bounce hold를 다르게 다룰지 정리

### Step 4. implementation

- [ ] first patch 반영
- [ ] 관련 unit tests 추가

### Step 5. verification

- [ ] fresh close/runtime evidence와 teacher-label 대조
- [ ] hold correctness가 좋아졌는지 casebook 기준으로 확인

## done condition

- teacher-label hold anchor를 설명 가능
- 현재 로직이 왜 그 hold를 유지/미유지하는지 owner 기준으로 설명 가능
- 필요 시 PA3 미세 조정 축이 독립적으로 닫힘
