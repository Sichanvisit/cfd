# D5 tempo_profile_v1 상세 계획

## 1. 목적

D5의 목적은 state 해석을 한 장면 snapshot으로만 소비하지 않고,
**지속성(persistence)과 반복성(repeat)** 을 공용 modifier로 고정하는 것이다.

이번 단계는 아직 기존 dominance 계산이나 execution/state25를 바꾸지 않는다.
우선 문서, 코드, runtime detail이 같은 tempo profile 언어를 보게 만드는 것이 목표다.

---

## 2. 왜 필요한가

같은 hold라도 지속성이 다르다.

- hold 1봉
- hold 5봉

같은 reject도 반복성이 다르다.

- reject 1회
- reject 3회 반복

즉 D5는 signal 이름만 보지 않고,
**얼마나 오래 유지됐는지, 얼마나 반복됐는지**를 공용 계약으로 고정하는 단계다.

---

## 3. D5에서 고정할 핵심 규칙

### 3-1. tempo profile state

- `NONE`
- `EARLY`
- `PERSISTING`
- `REPEATING`
- `EXTENDED`

### 3-2. tempo 판단 재료

- `breakout_hold_bars_v1`
- `higher_low_count_v1`
- `lower_high_count_v1`
- `reject_repeat_count_v1`
- `counter_drive_repeat_count_v1`

### 3-3. 해석 규칙

- `EARLY`는 persistence가 아직 얕고 장면이 막 시작된 상태다
- `PERSISTING`은 같은 방향 hold/structure count가 누적되는 상태다
- `REPEATING`은 reject나 counter-drive 반복이 의미를 가지는 상태다
- `EXTENDED`는 persistence와 반복이 이미 late-stage behavior로 누적된 상태다

### 3-4. 금지 규칙

- tempo는 core slot이 아니라 raw count + modifier summary로 시작한다
- `single reject`를 `repeated rejection tempo`와 같게 취급하지 않는다
- `single hold`를 `persistent hold tempo`와 같게 취급하지 않는다
- `EXTENDED`만으로 reversal을 선언하지 않는다
- tempo profile은 `dominant_side`를 바꾸지 못한다
- tempo profile은 execution/state25를 직접 바꾸지 않는다

즉 D5는 state를 더 잘게 설명하지만,
기존 dominance ownership과 execution separation은 계속 유지해야 한다.

---

## 4. D5에서 surface할 계약

runtime/detail에서는 아래를 읽을 수 있어야 한다.

- `tempo_profile_contract_v1`
- `tempo_profile_summary_v1`
- `tempo_profile_artifact_paths`

contract 필드 카탈로그:

- `tempo_profile_v1`
- `tempo_profile_confidence_v1`
- `tempo_reason_summary_v1`
- `breakout_hold_bars_v1`
- `higher_low_count_v1`
- `lower_high_count_v1`
- `reject_repeat_count_v1`
- `counter_drive_repeat_count_v1`

이번 버전은 row-level tempo 계산을 실제로 붙이기보다,
먼저 공용 계약과 control rule을 고정하는 데 집중한다.

---

## 5. 산출물

shadow artifact:

- `tempo_profile_latest.json`
- `tempo_profile_latest.md`

runtime detail:

- `tempo_profile_contract_v1`
- `tempo_profile_summary_v1`
- `tempo_profile_artifact_paths`

---

## 6. 완료 기준

- tempo profile이 `EARLY / PERSISTING / REPEATING / EXTENDED`로 분리된 공용 계약이 문서/코드/runtime에 동시에 존재한다
- runtime detail에서 같은 contract와 summary를 읽을 수 있다
- tempo는 raw persistence/count 기반 modifier라는 control rule이 명시된다
- execution/state25 change는 여전히 `false`로 잠겨 있다

---

## 7. 상태 기준

- `READY`: tempo profile 계약, summary, artifact가 정상 surface됨
- `HOLD`: 계약은 있으나 persistence/repeat 재료 정의나 control rule 설명이 흔들림
- `BLOCKED`: tempo profile이 dominance ownership을 침범하거나 runtime export가 누락됨
