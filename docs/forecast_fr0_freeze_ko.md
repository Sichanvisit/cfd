# Forecast FR0 Freeze

## 고정 문장

`Forecast는 semantic owner를 새로 만드는 레이어가 아니라, 이미 만들어진 semantic outputs를 다음 전개와 관리 관점에서 해석하는 branch layer다.`

## 핵심 의미

Forecast는 아래 semantic layer를 받아서 해석한다.

- `Position`
- `Response`
- `State`
- `Evidence`
- `Belief`
- `Barrier`

하지만 Forecast가 하면 안 되는 일도 분명하다.

- `Position` 대신 위치를 새로 정의하기
- `Response` 대신 사건을 새로 정의하기
- `State` 대신 장 성격을 새로 정의하기
- `Evidence` 대신 순간 근거 owner를 뺏기
- `Belief` 대신 지속성 owner를 뺏기
- `Barrier` 대신 차단 owner를 뺏기
- 직접 `BUY/SELL action owner`가 되기

## branch 역할

Forecast는 아래 branch로만 존재한다.

- `forecast_features_v1`
  - 입력 번들
- `transition_forecast_v1`
  - 다음 방향 전개 branch
- `trade_management_forecast_v1`
  - 보유/청산 관리 branch
- `forecast_gap_metrics_v1`
  - branch 비교 요약
- `forecast_effective_policy_v1`
  - effective wrapper

## owner 경계

- `execution_side_creator_allowed = false`
- `direct_action_creator_allowed = false`
- `summary_side_metadata_allowed = true`
  - 단, `transition`과 `management`의 `dominant_side` 같은 설명용 metadata는 허용
- `summary_mode_metadata_allowed = true`
  - 단, branch 내부 경쟁 모드 설명용 metadata만 허용

## runtime에서 확인해야 할 것

아래 metadata가 붙어 있으면 freeze 계약이 적용된 상태다.

- `semantic_owner_contract = forecast_branch_interpretation_only_v1`
- `forecast_freeze_phase = FR0`
- `forecast_branch_role`
- `owner_boundaries_v1`

## 한 줄 결론

`Forecast는 방향을 새로 만드는 owner가 아니라, 이미 만든 semantic outputs를 branch별로 해석해서 downstream에 넘기는 해석 레이어다.`

