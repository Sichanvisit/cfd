# 현재 남은 적용/연결 항목 통합 상세 계획

## 1. 문서 목적

이 문서는 지금까지 여러 BC/CA 문서로 흩어져 있던

- 필수 배선 미완료 항목
- 적용 예정 항목
- bounded live 직전까지 반드시 닫아야 하는 연결

을 한 장에 모아 보는 **통합 상세 계획서**다.

즉 앞으로는

- 전체 방향은 상위 문서로 보고
- 실제로 남은 구현/적용 항목은 이 문서에서 한 번에 확인하고
- 필요할 때만 BC/CA 분기 문서로 내려가는

구조로 운영한다.

## 2. 왜 지금 이 문서가 필요한가

지금 프로젝트는 이미

- state-first 맥락축
- continuation 학습/표식축
- state25 bridge log-only
- execution guard / promotion

까지 많이 연결되어 있다.

문제는 이제 “기능이 없어서 못 한다”가 아니라,

- 어디가 아직 live 반영 전인지
- 무엇이 실제 행동까지 닿지 않았는지
- 무엇을 먼저 닫고 나서 live를 봐야 하는지

가 문서 여러 장에 흩어져 있다는 점이다.

그래서 지금 단계에서는 새 설계를 늘리는 것보다
**남은 필수 연결과 적용 예정 항목을 한 장으로 묶어 우선순위를 고정하는 것**이 더 중요하다.

## 3. 이번 통합 계획의 범위

### 포함

- current-cycle continuation overlay가 실행층까지 닿도록 하는 배선
- chart painter가 최신 enriched row를 보게 하는 배선
- `execution_diff_*` live row / trace 축적
- `directional_continuation_accuracy_*` live 누적
- wrong-side guard / continuation promotion KPI 집계 준비
- state25 bounded live canary 준비
- `weight -> threshold -> size` 적용 순서 고정

### 제외

- 새 context 축 추가
- 새 차트 재료 추가
- execution core 대규모 재설계
- size bounded live 실제 rollout
- canary 자동화 / 전면 자동 전환

즉 이번 문서는 “남은 필수 연결을 닫고 canary 전환 준비를 완료하는 것”까지만 다룬다.

## 4. 현재 큰 그림

지금 전체 구조는 이미 아래까지 와 있다.

1. 차트 재료 수집
2. HTF / previous box / context conflict 조립
3. continuation 후보 생성
4. `/detect -> /propose` surface
5. chart overlay
6. state25 bridge log-only
7. execution guard / promotion

그래서 지금 남은 핵심은 세 가지다.

1. **필수 배선 완결**
2. **live 로그 / KPI 축적**
3. **bounded live canary 진입**

## 5. 남은 항목 통합 목록

### 5-1. 메인 엔진 / heartbeat 안정화

#### 목표

- main 엔진이 혼자 내려앉지 않고
- `runtime_status.json`, `runtime_status.detail.json`
- `latest_signal_by_symbol`

을 계속 갱신하는 상태를 유지한다.

#### 아직 중요한 이유

나머지 live 검증은 전부 main loop가 안정적으로 도는 것을 전제로 한다.
heartbeat가 멈추면 KPI나 execution diff도 의미가 없어진다.

#### 완료 기준

- main loop 재시작 후 추가 크래시 없음
- runtime status 갱신 지속
- `latest_signal_by_symbol` row가 지속적으로 채워짐

### 5-2. current-cycle continuation overlay -> execution 직접 연결

#### 목표

- `entry_try_open_entry.py`가 과거 row나 export 후 row가 아니라
- **현재 사이클에서 방금 enrich된 continuation overlay**를 직접 보게 한다.

#### 중요 장면

- NAS/BTC/XAU에서
  - continuation은 `UP`
  - 기존 consumer/action은 `SELL`
  인 경우
  guard/promotion이 최신 판단을 실제로 따라야 한다.

#### 완료 기준

- `active_action_conflict_guard_v1`
- `directional_continuation_promotion_v1`
- `execution_action_diff_v1`

가 current-cycle overlay 기준으로 바뀐 것이 live row에서 보임

### 5-3. chart painter / flow history 최신 판단 동기화

#### 목표

- chart painter가 enrichment 전 row를 그리지 않게 하고
- 최신 continuation overlay가 `BUY_WATCH / SELL_WATCH`로 실제 차트에 보이게 한다.

#### 완료 기준

- XAU/BTC/NAS 주요 장면에서
  - runtime row의 overlay hint
  - chart flow history의 event_kind
  가 큰 방향에서 일치

### 5-4. execution diff live 축적

#### 목표

- 아래 필드가 live row와 trace에 계속 쌓이게 한다.

- `execution_diff_original_action_side`
- `execution_diff_guarded_action_side`
- `execution_diff_promoted_action_side`
- `execution_diff_final_action_side`
- `action_change_reason_keys`

#### 완료 기준

- runtime row / ai trace / detail payload에서 확인 가능
- missing rate가 낮음
- wrong-side 차단 / promotion 성공 / no-change 케이스 구분 가능

### 5-5. continuation accuracy live 축적

#### 목표

- `10 / 20 / 30 bars` horizon 기준
- pending / resolved / correct / false alarm / unresolved

이 실제로 쌓이게 한다.

#### 필수 지표

- `primary_correct_rate`
- `up_correct_rate`
- `down_correct_rate`
- `direction_bias_gap`
- `pending_observation_count`
- `resolved_observation_count`

#### 완료 기준

- resolved sample이 실제로 생김
- 심볼별 요약 가능
- accuracy artifact가 주기적으로 갱신됨

### 5-6. wrong-side guard / promotion KPI 집계

#### 목표

- guard와 promotion을 “있다/없다”가 아니라
- 실제로 가치가 있는지 숫자로 보게 한다.

#### 필수 지표

- guard
  - helpful
  - missed
  - overblock
  - helpful_rate_by_side
  - overblock_rate_by_side
- promotion
  - trigger_count
  - win_rate
  - false_rate
  - baseline delta
  - entry_change_rate
- 공통
  - `execution_diff_logic_conflict`
  - `no_change_rate`
  - `final_action_quality`

#### 완료 기준

- 심볼별 KPI artifact 생성
- `READY / HOLD / BLOCKED` 판정 가능

### 5-7. state25 bounded live canary 준비

#### 목표

- `weight bounded live`
- 그다음 `threshold bounded live`

를 실제로 active candidate state에 적용할 수 있게 한다.

#### 선행 조건

- fresh review 후보가 다시 표출됨
- readiness artifact가 최신
- KPI가 canary 기준을 충족
- symbol / stage 범위가 좁게 정리됨

#### 완료 기준

- `weight bounded live` canary 대상 symbol / stage가 정해짐
- 적용 / rollback / invalidation 기준이 고정됨

### 5-8. threshold bounded live 준비

#### 목표

- weight canary 이후 threshold canary로 넘어갈 준비

#### 조건

- symbol별 delta 계약 안정
- harden only 유지
- double counting 없음
- requested/effective drift가 안정

#### 완료 기준

- threshold canary `READY / HOLD / BLOCKED` 판정 가능

### 5-9. size는 마지막

#### 현재 해석

size는 아직 log-only에 가까운 상태다.
지금 단계에서는 필수 배선/검증보다 우선순위가 낮다.

#### 원칙

- size는 마지막
- weight / threshold가 안정된 뒤

## 6. 지금 먼저 닫아야 할 필수 배선 체크리스트

아래 여섯 개는 bounded live canary 전에 반드시 닫아야 한다.

1. main 엔진이 안정적으로 heartbeat를 쓴다
2. current-cycle continuation overlay가 entry 직전에 보인다
3. chart painter가 최신 continuation overlay를 본다
4. execution diff가 live row / trace에 남는다
5. continuation accuracy가 resolved sample을 만들기 시작한다
6. state25 bounded live apply 경로가 `active_candidate_state.json`까지 실제로 닿는다

## 7. 이 문서와 다른 문서의 역할 분담

### 이 문서

- 남은 연결과 적용 항목 전체를 통합해서 본다
- 지금 무엇을 먼저 닫아야 하는지 순서를 잡는다

### CA2

- KPI, readiness, guard/promotion 검증, bounded live 전환 기준

### BC11

- state25 bounded live canary 실제 적용 절차

즉 앞으로는

- “지금 전체적으로 뭐가 남았지?”
  -> 이 문서
- “지금 KPI 기준은 뭐지?”
  -> CA2
- “지금 state25 canary는 어떻게 적용하지?”
  -> BC11

으로 보면 된다.

## 8. 실행 원칙

지금 단계의 원칙은 이거다.

1. 필수 배선을 먼저 닫는다
2. 그다음 짧게 live를 본다
3. 숫자를 쌓는다
4. canary를 아주 좁게 켠다
5. `weight -> threshold -> size`

즉 “live를 오래 보며 감으로 맞춘다”가 아니라,
**필수 연결을 먼저 완결하고, 그 뒤 관찰과 canary로 넘어간다**가 기본 원칙이다.

## 9. 완료 기준

아래가 되면 이 통합 계획은 1차 완료로 본다.

1. 필수 배선 6개가 닫힘
2. live row / trace / chart flow history가 같은 방향을 큰 틀에서 공유
3. continuation accuracy와 execution diff가 누적되기 시작함
4. guard / promotion KPI artifact가 생성됨
5. `weight bounded live canary` 진입 여부를 실제로 판정 가능

## 10. 결론

지금부터는 분기 문서를 여기저기 늘리는 것보다,
이 문서를 기준으로 “남은 적용/연결 항목 전체”를 먼저 보고,
필요한 주제만 CA2나 BC11로 내려가는 방식이 가장 빠르고 덜 헷갈린다.

즉 이 문서의 역할은
**지금 남은 것을 한 번에 보고, 구현 순서를 흔들리지 않게 고정하는 통합 기준서**다.
