# 현재 남은 적용/연결 항목 통합 실행 로드맵

## 1. 기본 순서

1. 필수 배선 완결
2. 짧은 live 확인
3. KPI 누적
4. weight bounded live canary
5. threshold bounded live canary
6. size는 마지막

## 2. 단계별 실행 순서

### Phase A. 필수 배선 완결

#### A1. main 엔진 안정화

- main 크래시 원인 제거
- runtime heartbeat 재개
- `latest_signal_by_symbol` row 재생성 확인

#### A2. current-cycle continuation overlay -> execution

- entry 직전 runtime row enrich
- guard / promotion / execution diff가 최신 overlay를 직접 읽게 함

#### A3. current-cycle continuation overlay -> chart

- painter가 최신 enriched row 사용
- chart flow history 동기화

#### A4. execution diff live 누적

- runtime row
- detail row
- ai trace

에서 execution diff 필드가 보이는지 확인

#### A5. continuation accuracy live 누적

- 10/20/30 bars 추적기 갱신
- pending -> resolved sample 생성 시작 확인

### Phase B. 짧은 live 확인

#### B1. NAS / BTC / XAU 대표 장면 점검

- 잘 오르는 장면에서 SELL이 계속 들어가는지
- overlay는 UP인데 action이 SELL로 남는지
- chart 표식이 WAIT로 눌리는지

를 실제 로그/flow history로 확인

#### B2. 필수 배선 6개 상태 점검

- 통합 상세 계획 문서 기준 체크리스트 확인

### Phase C. KPI / readiness

#### C1. continuation accuracy KPI

- symbol-first 집계
- direction bias gap
- unresolved / resolved / correct rate

#### C2. guard / promotion KPI

- helpful / missed / overblock
- promotion win/false/baseline
- no-change
- logic conflict
- final action quality

#### C3. readiness / blocker 판정

- READY / HOLD / BLOCKED
- warning band / block band

### Phase D. state25 bounded live canary

#### D1. fresh 후보 재표출 확인

- `state25 weight review`
- `state25 threshold review`

#### D2. weight bounded live canary

- symbol 1개
- stage 1개
- 작은 cap
- rollback / invalidation 준비

#### D3. threshold bounded live canary

- weight canary 통과 후
- symbol별 delta 계약이 안정적일 때만

### Phase E. 마지막 단계

#### E1. size

- 지금은 보류
- weight / threshold가 안정된 뒤

## 3. 현재 최우선

지금 당장 최우선은 아래다.

1. main 엔진 안정화 확인
2. execution이 최신 continuation overlay를 실제로 따르는지 확인
3. execution diff / accuracy가 live에 쌓이는지 확인

즉 아직은 bounded live를 바로 켜는 단계가 아니라,
**canary 전에 필요한 필수 배선과 관찰 데이터가 실제로 쌓이는지 확인하는 단계**다.

## 4. 그 다음 우선순위

1. CA2 KPI artifact 생성
2. 첫 canary symbol / stage 선택
3. BC11 기준으로 weight bounded live canary 적용

## 5. 문서 사용 순서

1. [current_master_implementation_roadmap_navigation_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\current_master_implementation_roadmap_navigation_ko.md)
2. [current_remaining_integration_completion_detailed_plan_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\current_remaining_integration_completion_detailed_plan_ko.md)
3. [current_ca2_guard_promotion_bounded_live_validation_execution_roadmap_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\current_ca2_guard_promotion_bounded_live_validation_execution_roadmap_ko.md)
4. [current_bc11_state25_bounded_live_activation_canary_execution_roadmap_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\current_bc11_state25_bounded_live_activation_canary_execution_roadmap_ko.md)

즉 앞으로는

- 전체 남은 것 확인
- KPI 검증 기준 확인
- bounded live canary 절차 확인

순서로 보면 된다.
