# 현재 미완료 연결 정리 및 다음 작업 지도

## 1. 이 문서의 목적

이 문서는 현재 시스템에서

- 이미 코드/배선은 있는 것
- 아직 live 적용이 안 된 것
- live는 되었지만 정확도/표현이 더 필요한 것
- 다음으로 무엇을 닫아야 하는지

를 **미완료 연결만 따로** 모아서 보는 문서다.

기준 관점은 다음과 같다.

1. 재료가 없는가
2. 재료는 있는데 detector/propose/chart까지 안 가는가
3. 거기까진 가는데 execution이 아직 안 따르는가
4. execution까지 갔지만 bounded live가 아직 안 켜졌는가

---

## 2. 가장 중요한 현재 판단

현재 시스템은 이미

- `HTF / 직전 박스 / 맥락 충돌 / continuation`
를 **보고**
- detector / propose / chart overlay에 **보여주고**
- execution guard / promotion까지 **코드로 연결**해둔 상태다.

그래서 지금의 미완료는 주로 아래 두 종류다.

1. **실제 bounded live 승격이 아직 안 된 것**
2. **판단은 맞게 하는데 live UX나 실행 우선순위가 아직 완전히 따라오지 않은 것**

즉 지금 남은 건 “재료 추가”보다 **실행 정렬 마감**에 더 가깝다.

---

## 3. 현재 운영 상태 요약

기준 파일:

- `models/teacher_pattern_state25_candidates/active_candidate_state.json`

현재 확인값:

| 항목 | 현재값 | 해석 |
| --- | --- | --- |
| `active_candidate_id` | `20260414_162914` | 현재 활성 candidate는 존재함 |
| `current_rollout_phase` | `log_only` | 실제 bounded live로는 아직 승격 안 됨 |
| `current_binding_mode` | `log_only` | 실행 반영보다 trace/review 중심 모드 |
| `state25_execution_bind_mode` | `log_only` | state25 실행 bind도 아직 log_only |
| `state25_execution_symbol_allowlist` | `BTCUSD`, `NAS100` | 현재 관찰 범위가 일부 심볼로만 좁혀져 있음 |
| `state25_execution_entry_stage_allowlist` | `PROBE`, `READY` | 일부 stage만 관찰/반영 범위에 들어감 |
| `state25_threshold_log_only_enabled` | `true` | threshold는 현재 log-only 관찰 중 |
| `state25_size_log_only_enabled` | `true` | size는 log-only 관찰만 켜짐 |

즉 한 줄로 말하면:

**시스템은 이미 “실행 후보를 만들고 관찰하는 단계”까진 왔지만, 아직 state25 bounded live는 실제로 올리지 않았다.**

---

## 4. 미완료 연결 전체 표

| 연결 축 | 현재 상태 | 왜 미완료인가 | 다음 닫을 일 |
| --- | --- | --- | --- |
| state25 weight bounded live 실제 활성화 | 미완료 | 핸들러/계약은 있으나 active candidate state는 여전히 `log_only` | fresh weight 후보가 다시 뜰 때 bounded live apply |
| state25 threshold bounded live 실제 활성화 | 미완료 | 핸들러/계약은 있으나 threshold는 심볼/스테이지 범위 정리가 더 중요함 | symbol/stage 범위 좁혀 bounded live apply |
| state25 size bounded live | 사실상 미완료 | size는 `log_only` 관찰만 있고 bounded live 승격은 아직 안 닫힘 | size translator + bounded live 정책 정리 |
| continuation 판단이 execution을 완전히 이기게 만들기 | 부분 완료 | guard/promotion 코드는 있으나 실제 라이브에서 반복 검증 더 필요 | wrong-side 진입이 실제로 줄어드는지 확인 |
| chart overlay가 내부 판단을 충분히 명확히 보여주기 | 부분 완료 | overlay는 붙었지만 차트 표식 체감은 계속 다듬어야 함 | painter 강도/라벨/우선순위 추가 조정 |
| continuation 방향 정확도 장기 안정화 | 미완료 | 후보는 뜨지만 장면별 `UP/DOWN` 안정성은 더 학습 필요 | hindsight/feedback 누적 후 tuning |
| state25 allowlist 확장 | 미완료 | 현재 active state 기준 symbol/stage 범위가 좁다 | BTC/NAS에서 안정되면 XAU 포함 재확장 |
| 자동 반영 governance | 부분 완료 | readiness/apply gate는 있으나 “언제 자동 승격” 규칙은 더 필요 | bounded live auto-promotion 조건 문서화 |

---

## 5. 미완료 연결 상세

### 5-1. state25 bounded live 실제 활성화

#### 현재 된 것

- `state25_weight_patch_apply_handlers.py`
- `state25_threshold_patch_apply_handlers.py`
- `state25_context_bridge_bounded_live_readiness.py`

즉 apply handler와 readiness gate는 이미 있다.

#### 아직 안 된 것

- 실제 active candidate state를 `bounded_live`로 올리는 운영 적용

#### 왜 중요하나

지금은 detector/propose에서

- `state25 weight review`
- `state25 threshold review`

가 뜨더라도, 실제 state25 execution 본체는 아직 `log_only`이기 때문에
**실제 진입 행동이 크게 바뀌지 않는다.**

#### 다음 작업

1. fresh 후보 재표출 확인
2. 심볼/스테이지 범위를 더 좁혀 bounded live apply
3. rollback 조건과 함께 짧은 canary 운용

---

### 5-2. size bounded live

#### 현재 된 것

- active candidate state에 `state25_size_log_only_enabled`
- min/max multiplier 관찰 경로

#### 아직 안 된 것

- size bounded live 승격
- size floor 정책을 실제 live rollout으로 묶기

#### 왜 중요하나

지금은 wrong-side 진입을

- 막거나
- threshold를 높이거나
- 방향 승격하는

쪽은 많이 만들어졌지만, **“들어가더라도 작게 들어간다”**는 마지막 리스크 축은 아직 log-only에 가깝다.

#### 다음 작업

1. continuation promotion과 size 축이 겹치지 않게 역할 정리
2. size bounded live를 `canary` 수준으로 도입

---

### 5-3. continuation 판단과 execution 정렬

#### 현재 된 것

- `active_action_conflict_guard_v1`
  - 반대 방향 진입 차단
- `directional_continuation_promotion_v1`
  - continuation 방향으로 bounded promotion

#### 아직 안 된 것

- 모든 장면에서 execution이 새 continuation 판단을 일관되게 따르는지 장기 검증

#### 왜 중요하나

최근 NAS100 / BTC / XAU 사례에서 확인한 것처럼,
시스템은 이미 continuation을 `UP` 또는 `DOWN`으로 보고 있는데도
예전 `consumer_check_side` 해석이나 진입 우선순위 때문에
반대로 들어가려는 장면이 있었다.

즉 지금 남은 건

**보고 있는 판단을 execution이 확실히 따르게 마감하는 것**

이다.

#### 다음 작업

1. wrong-side SELL/BUY 사례 수집
2. guard 적용 후 실제 반대 진입 감소 여부 확인
3. promotion이 과하지 않은지 점검

---

### 5-4. chart 표식의 체감 마감

#### 현재 된 것

- `directional_continuation_overlay_v1`
- painter에서 `BUY_WATCH / SELL_WATCH`

#### 아직 안 된 것

- 내부 continuation 판단이 차트에서 항상 충분히 강하게 보이는지 확정

#### 왜 중요하나

내부적으로는 `UP`으로 보고 있어도,
차트에서 표식이 약하거나 기존 ENTER/SELL 표식에 가리면
사용자는 여전히 오해할 수 있다.

#### 다음 작업

1. overlay 강도와 레벨 우선순위 재검토
2. 기존 ENTER/SELL 표식과 continuation watch 표식의 충돌 규칙 정리

---

### 5-5. continuation 방향 정확도 안정화

#### 현재 된 것

- `상승 지속 누락`
- `하락 지속 누락`

을 같은 급의 학습 후보로 생성

#### 아직 안 된 것

- 장면별 `UP/DOWN` 분류를 더 안정적으로 만드는 tuning

#### 왜 중요하나

지금 중요한 건 “혼조”로 뭉개지지 않고 이름을 붙이기 시작했다는 점이지만,
그 다음 단계는 **정확도 안정화**다.

특히

- XAU 상단 재테스트 후 하락 지속
- NAS 상단 돌파 유지 후 상승 지속
- BTC 중단 재가속 continuation

같은 유형을 더 안정적으로 구분해야 한다.

#### 다음 작업

1. hindsight resolved 케이스를 continuation 방향 기준으로 누적
2. symbol/family별 강한 잘못 분류 사례를 따로 분리
3. priority score와 overlay score 보정

---

### 5-6. allowlist / governance 확장

#### 현재 된 것

- 현재 active candidate state는 `BTCUSD`, `NAS100`
- stage는 `PROBE`, `READY`

에 좁혀 운영되고 있다.

#### 아직 안 된 것

- XAU 포함 전심볼 확장
- stage 확대
- auto-promotion governance 명확화

#### 왜 중요하나

bounded live는 한 번에 넓게 열면 위험하므로 지금 방식은 맞다.
하지만 계속 `log_only` 범위에만 머물면 실제 개선이 더뎌진다.

#### 다음 작업

1. BTC/NAS에서 bounded live 안전성 확인
2. XAU까지 단계적 확대
3. symbol/stage별 rollback trigger 정의

---

## 6. 앞으로 해야 할 일 우선순위

### 1순위

- `weight bounded live` 실제 적용
- `threshold bounded live` 실제 적용

이유:

- 지금 가장 큰 gap은 “보고는 있는데 실행이 아직 완전히 안 따른다”는 점이기 때문

### 2순위

- execution guard / promotion 장기 검증
- continuation 방향 정확도 안정화

이유:

- bounded live를 올려도 continuation 방향 자체가 불안정하면 오염될 수 있음

### 3순위

- size bounded live
- chart painter UX 마감
- allowlist 확장

이유:

- 이 축들은 중요하지만, 현재 가장 먼저 줄여야 하는 오해는 wrong-side execution 쪽

---

## 7. 운영 체크리스트

### bounded live 직전

- fresh candidate가 다시 떴는가
- review count가 cooldown 때문에 0이 아닌가
- symbol / stage 범위가 좁혀져 있는가
- rollback trigger가 적혀 있는가

### bounded live 직후

- wrong-side SELL/BUY가 실제 줄었는가
- continuation promotion이 과승격하지 않는가
- chart와 `/detect`, `/propose`가 같은 방향을 말하는가

---

## 8. 결론

현재 미완료는 “재료 부족”이 아니라

**실행층 정렬과 bounded live 실제 승격**

에 집중돼 있다.

즉 지금 시스템은 이미 많이 연결돼 있고,
앞으로 해야 할 일은

- continuation / context 판단을
- state25와 execution이
- 얼마나 안정적으로 실제 행동으로 따르게 만들지

를 마감하는 쪽이다.

---

## 9. 추가 보강: next_action 포함 상태표

이 표는 “지금 어디까지 왔는가”뿐 아니라 “바로 다음에 무엇을 해야 하는가”를 함께 보이기 위한 운영표다.

| 축 | 현재 상태 | 다음 행동 |
| --- | --- | --- |
| state-first 맥락축 | 거의 완료 / 확인됨 | 유지 관찰 |
| continuation 학습축 | 완료 / 확인됨 | accuracy 측정 시작 |
| continuation 차트 overlay | 연결 완료 / 부분 확인 | chart UX 보정 계속 |
| state25 bridge log-only | 완료 / 확인됨 | counterfactual 누적 |
| state25 bounded live 인프라 | 완료 | activation 기준표 확정 |
| state25 bounded live 실제 활성화 | 미완료 | log-only 100건 후 판단 |
| wrong-side guard | 코드 완료 | 최근 50건 검증 |
| continuation promotion | 코드 완료 | 최근 50건 검증 |
| size bounded live | 미완료 | size 정책 초안 정리 |

---

## 10. 추가 보강: 라이브 검증 기준표

### 10-1. wrong-side guard

| 항목 | 기준 |
| --- | --- |
| 표본 | 최근 `50건` 진입 시도 |
| 발동 빈도 | `1~5건`이면 정상 가능성 |
| 과민 신호 | `10건 이상` |
| hindsight 적중률 | guard 발동건 중 `70% 이상`이 막은 게 맞음 |
| 재검토 기준 | 적중률 `50% 미만` |

### 10-2. continuation promotion

| 항목 | 기준 |
| --- | --- |
| 표본 | 최근 `50건` 진입 시도 |
| 승격 빈도 | `1~3건`이면 보수적 정상 가능성 |
| 과승격 신호 | `10건 이상` |
| 승격 승률 | `60% 이상` |
| 재검토 기준 | 승률 `40% 미만` |

### 10-3. continuation 방향 안정화

| 항목 | 기준 |
| --- | --- |
| 기본 horizon | `20봉` |
| 보조 horizon | `10봉`, `30봉` |
| 안정적 | 정확도 `65% 이상` |
| 관찰 유지 | `55~65%` |
| 재검토 | `55% 미만` |

---

## 11. 추가 보강: bounded live 전환 기준

| 항목 | 기준 |
| --- | --- |
| log-only 표본 | `100건 이상` |
| counterfactual helpful rate | `60% 이상` |
| wrong-side guard | 최근 `50건` 기준 통과 |
| continuation promotion | 최근 `50건` 기준 통과 |
| 시스템 안정성 | 최근 `1주` 무계획 장애 없음 |

권장 순서:

1. `1 symbol`
2. `1 entry_stage`
3. `weight only`
4. 짧은 canary

---

## 12. 추가 보강: 장애 시나리오와 fallback 원칙

| 시나리오 | 영향 | fallback 원칙 |
| --- | --- | --- |
| HTF 캐시 stale | conflict/guard 품질 저하 | stale 축은 보정 0으로 약화 |
| previous_box 계산 실패 | 박스 축 품질 저하 | previous_box 축 skip |
| `context_state_builder` 실패 | 맥락 카드 없음 | bridge 전체 no-op, 기존 매매는 계속 |
| detector 장애 | `/detect` 빈약 | propose와 기존 매매는 계속 |
| state25 apply 오류 | bounded live 반영 중단 | 즉시 `log_only` rollback |

핵심 원칙:

**체인 어디가 끊어져도 기존 매매는 돌아가야 한다.**
