# BC8 State25 Weight Bounded Live 실행 로드맵

## 단계

1. `active candidate runtime` contract 확장
- `state25_weight_bounded_live_enabled`
- live/log-only weight override 분리

2. `apply handler` 확장
- `STATE25_WEIGHT_PATCH_REVIEW`
- `log_only` / `bounded_live` 모두 수용

3. `runtime consumption` 고정
- `forecast_state25_runtime_bridge.py`에서 live override만 소비

4. `review packet` 호환
- weight review packet이 `bounded_live` bind mode를 표현 가능하도록 유지

5. 테스트
- runtime surface
- apply handler
- forecast runtime bridge

## 완료 기준

- bounded live weight patch를 승인하면 active candidate state가 `bounded_live`로 전환된다.
- same symbol/stage scope에서 forecast runtime hint가 live weight override를 읽는다.
- log-only weight는 여전히 live runtime hint를 오염시키지 않는다.
