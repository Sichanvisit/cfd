# Belief B6 Pre-ML Readiness

## 목표

`Belief`를 나중에 ML calibration 입력 feature로 안전하게 쓸 수 있도록 계약을 고정한다.

핵심 문장:

`Belief는 ML의 입력 feature가 될 수 있지만, ML이 Belief를 통해 Position/Response/State의 owner를 덮어써서는 안 된다.`

## 현재 고정된 필수 출력

- `buy_belief`
- `sell_belief`
- `buy_persistence`
- `sell_persistence`
- `belief_spread`
- `transition_age`
- `dominant_side`
- `dominant_mode`

## 현재 고정된 추천 출력

- `flip_readiness`
- `belief_instability`

## 의미

- `buy_belief`
  - 현재 `BUY thesis` 누적 확신
- `sell_belief`
  - 현재 `SELL thesis` 누적 확신
- `buy_persistence`
  - `BUY thesis`가 몇 bar째 유지되는지의 정규화 값
- `sell_persistence`
  - `SELL thesis`가 몇 bar째 유지되는지의 정규화 값
- `belief_spread`
  - buy/sell belief 격차
- `transition_age`
  - 현재 dominant thesis가 몇 bar째 유지되는지
- `dominant_side`
  - 현재 belief 우세 방향
- `dominant_mode`
  - 현재 우세 방향의 성격이 `reversal`인지 `continuation`인지
- `flip_readiness`
  - 기존 thesis 붕괴 + 반대 thesis 상승이 충분한지
- `belief_instability`
  - belief가 deadband, 혼합, fresh flip 상태로 흔들리는지

## B6 계약

현재 코드 메타데이터:
- `belief_pre_ml_phase = B6`
- `pre_ml_readiness_contract_v1.status = READY`

계약 의미:
- `semantic_explainable_without_ml = true`
  - ML 없이도 Belief가 무엇을 의미하는지 충분히 설명 가능해야 한다
- `ml_usage_role = feature_only_not_owner`
  - ML은 Belief를 calibration feature로만 사용한다
- `owner_collision_allowed = false`
  - ML이 Belief를 근거로 Position/Response/State owner를 재정의하면 안 된다

## ML에 안전하게 쓰는 방식

가능:
- `wait_quality_calibration`
- `entry_quality_calibration`
- `hold_exit_patience_calibration`
- `flip_readiness_calibration`

불가:
- `Position identity` 재정의
- `Response event identity` 재정의
- `State regime identity` 재정의
- `직접 BUY/SELL action owner` 대체

## 한 줄 결론

`B6는 Belief를 ML의 입력 feature로 열어두되, 의미 owner는 여전히 사람이 정의한 semantic layer에 남겨두는 단계다.`
