# Product Acceptance PA4 Teacher Label Release Cut Acceptance Implementation Checklist

## kickoff

- [x] teacher-label screenshot casebook 확보
- [x] split axis를 `release / cut`로 분리
- [x] 현재 PA4 active chain과 연결

## implementation steps

### Step 0. anchor capture

- [x] 스크린샷에서 `청산 또는 컷`이 맞는 장면 재정의
- [ ] NAS / XAU / BTC별 release/cut anchor를 2개 안팎으로 고정
- [ ] top maturity / regime flip / countertrend bounce failure / spike fail 로 분류

### Step 1. runtime family mapping

- [ ] 현재 PA4 residue family와 screenshot anchor를 매핑
- [ ] `TopDown-only Exit Context`
- [ ] `Protect Exit + hard_guard=adverse`
- [ ] `Adverse Stop + hard_guard=adverse`
- [ ] 기타 `Exit Context` family 분해

### Step 2. owner read

- [ ] [exit_service.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_service.py) final release path 재확인
- [ ] [exit_engines.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_engines.py) stage/action 재확인
- [ ] [exit_hard_guard_action_policy.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_hard_guard_action_policy.py) protect/adverse precedence 재확인
- [ ] [exit_utility_scene_bias_policy.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_utility_scene_bias_policy.py) giveback/topdown bias 재확인
- [ ] [exit_recovery_utility_bundle.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_recovery_utility_bundle.py) no-green countertrend gating 재확인

### Step 3. first adjustment design

- [ ] teacher-label 기준으로 더 빨라져야 하는 release/cut 조건 명문화
- [ ] 반대로 너무 이른 release가 아닌 장면과 분리
- [ ] protect/adverse/exit-context 우선순위 재정리

### Step 4. implementation

- [ ] first patch 또는 follow-up patch 반영
- [ ] 관련 tests 추가

### Step 5. verification

- [ ] fresh close turnover 기준 refreeze
- [ ] teacher-label anchor와 close artifact를 대조
- [ ] `must_release / bad_exit` 감소 확인

## done condition

- screenshot 기준 release/cut anchor를 현재 family와 연결 가능
- 왜 늦었는지 owner 기준으로 설명 가능
- follow-up patch 이후 backlog가 실제로 줄기 시작함
