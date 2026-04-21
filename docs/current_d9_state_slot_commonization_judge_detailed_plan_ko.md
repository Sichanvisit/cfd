# D9. 공용화 판정 상세 계획

## 목적

XAU 파일럿에서 검증한 decomposition slot을 바로 NAS/BTC로 복사하지 않고,
무엇이 공용 언어로 승격 가능한지, 무엇이 심볼별 threshold를 더 필요로 하는지,
무엇이 아직 XAU 로컬 해석인지 summary 수준에서 판정하는 단계다.

## 왜 필요한가

XAU pilot은 훈련장이고 본체는 공용 decomposition frame이다.

그래서 D9에서는 아래를 분리해야 한다.

- `COMMON_READY`
- `COMMON_WITH_SYMBOL_THRESHOLD`
- `XAU_LOCAL_ONLY`
- `HOLD_FOR_MORE_SYMBOLS`

즉 “공용화”는 곧바로 NAS/BTC 적용이 아니라,
공용 slot 언어와 심볼별 threshold 책임을 먼저 분리하는 일이다.

## 판단 기준

### COMMON_READY

- XAU pilot support가 2회 이상 반복되고
- ambiguity가 높지 않고
- validation이 깨끗할 때

### COMMON_WITH_SYMBOL_THRESHOLD

- slot 언어는 공용으로 유효하지만
- `WITH_FRICTION` 또는 `DRIFT`처럼 심볼별 threshold 차이가 필요한 경우

### XAU_LOCAL_ONLY

- XAU 장면 해석으로는 설명되지만
- 아직 공용 slot으로 승격할 근거가 부족한 경우

### HOLD_FOR_MORE_SYMBOLS

- single-support이거나
- ambiguity가 높거나
- NAS/BTC evidence가 더 필요한 경우

## artifact

- `state_slot_commonization_judge_summary_v1`
- `state_slot_commonization_judge_latest.json`
- `state_slot_commonization_judge_latest.md`

## 완료 기준

- XAU pilot에서 나온 slot이 공용화 관점으로 정리된다.
- NAS/BTC 확장 전에 공용 slot catalog를 안정적으로 들고 갈 수 있다.
