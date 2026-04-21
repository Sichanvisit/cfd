# Product Acceptance PA2 Teacher Label Entry Acceptance Implementation Checklist

## kickoff

- [x] teacher-label screenshot casebook 확보
- [x] split axis를 `entry`로 분리
- [x] owner와 evidence surface 후보 정의

## implementation steps

### Step 0. anchor capture

- [x] `NAS / XAU / BTC` 스크린샷을 entry teacher-label 기준으로 해석
- [ ] 심볼별 `들어갔어야 한 anchor`를 2~3개씩 문장으로 고정
- [ ] 심볼별 `들어가면 안 되는 chase/noise anchor`를 1~2개씩 고정

### Step 1. owner read

- [ ] [consumer_check_state.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/consumer_check_state.py) 에서 entry promotion 경로 재확인
- [ ] [entry_service.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/entry_service.py) 의 open-entry gating 재확인
- [ ] [entry_try_open_entry.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/entry_try_open_entry.py) 의 final open path 재확인

### Step 2. screenshot-to-family mapping

- [ ] teacher-label entry anchor를 현재 runtime family 후보로 매핑
- [ ] `should-enter`가 `observe/wait/hidden`에 머무는 대표 family 1차 선정
- [ ] `should-not-enter`가 잘 막히는지도 같이 확인

### Step 3. first patch design

- [ ] entry promotion을 더 빨리 해야 하는 축과
- [ ] chase/noise를 더 막아야 하는 축을 분리
- [ ] 심볼별 차이를 threshold로 둘지 family policy로 둘지 정리

### Step 4. implementation

- [ ] first patch 반영
- [ ] 관련 unit tests 추가

### Step 5. verification

- [ ] PA0 baseline refreeze
- [ ] teacher-label anchor와 runtime row 대조
- [ ] `must_enter`와 별도로 teacher-label miss-entry 개선 여부 확인

## done condition

- teacher-label 기준 `들어갔어야 한 자리`가 어떤 family인지 설명 가능
- 그 family가 왜 entry로 못 올라왔는지 owner 기준으로 설명 가능
- first patch 이후 missed-entry 축이 줄어드는 방향이 확인됨
