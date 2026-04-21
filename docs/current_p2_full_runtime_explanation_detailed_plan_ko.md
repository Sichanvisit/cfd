# Current P2 Full Runtime Explanation Detailed Plan

## 목표

`P2-full`의 목표는 `P2-quick`에서 붙인 3줄 설명을 실제 운영형 설명 surface로 확장하는 것이다.

이번 단계에서는 새 판단 엔진을 만들지 않는다. 대신 이미 runtime row와 state25 bridge 안에 있는 정보를 사람 언어로 끌어올린다.

즉 이번 단계는:

- `진입`에 `장면(scene)` 1줄 추가
- `대기`에 `장면(scene)` 1줄 추가
- `반전`에 `장면(scene)` + `전이` 설명 추가
- `청산`에 `복기 힌트`를 shock/review 문맥까지 확장
- reason/scene 번역을 공통 map으로 분리

까지를 목표로 한다.

---

## 이번 단계의 핵심 원칙

### 1. 설명은 짧고 구조화한다

설명을 많이 붙이는 것이 목적이 아니다. 아래처럼 표준 줄만 유지한다.

- 진입: `주도축 / 핵심리스크 / 강도 / 장면`
- 대기: `대기이유 / 해제조건 / 장면`
- 반전: `상태 / 주도축 / 핵심리스크 / 강도 / 장면 / 전이`
- 청산: `청산사유 / 복기힌트`

### 2. 새 판단을 만들지 않고 기존 판단을 surface 한다

scene 정보는 `forecast / belief / barrier` bridge의 `state25_runtime_hint_v1`나 runtime row에 이미 실린 값만 읽는다.

### 3. 한글화는 공통 map으로 고정한다

`reason`, `scene`, `gate`, `transition`은 같은 raw key가 언제나 같은 한국어로 보이도록 한다.

### 4. 복기 힌트는 있을 때만 붙인다

의미 없는 복기 문장은 붙이지 않는다. shock 대응이나 명확한 exit 맥락이 있을 때만 surface 한다.

---

## 이번 단계에서 추가할 설명 surface

### 1. 진입

추가:

- `장면: 돌파 후 재시험 유지 (breakout_retest_hold) / 게이트: 없음 / 확신: 높음`

데이터 원천:

- `runtime_scene_*` raw row
- `forecast_state25_runtime_bridge_v1.state25_runtime_hint_v1`
- `belief_state25_runtime_bridge_v1.state25_runtime_hint_v1`
- `barrier_state25_runtime_bridge_v1.state25_runtime_hint_v1`

### 2. 대기

추가:

- `장면: 추세 소진 (trend_exhaustion) / 게이트: 주의 / 확신: 보통`

의미:

- 현재 대기 판단이 어떤 scene 맥락 위에서 나왔는지
- barrier/belief/forecast 참고축과 별개로 구조 장면을 한 줄로 보여준다

### 3. 반전

추가:

- `장면: 추세 소진 (trend_exhaustion) / 게이트: 주의 / 확신: 보통`
- `전이: 반대 점수 급변 / 변동성 급등`

의미:

- 왜 반전 준비/대기인지
- 단순 pending이 아니라 어떤 전이 이유 때문에 반전이 뜬 것인지

### 4. 청산

확장:

- shock metadata가 있으면 `복기힌트`가 shock 대응 기준으로 바뀐다

예:

- `복기힌트: 쇼크 주의 대응 복기 / runner_hold->fast_exit`

---

## 공통 매핑 정책

권장 공통 파일:

- `backend/services/reason_label_map.py`

여기서 고정할 것:

- `reason` exact map
- `reason` token map
- `scene` exact map
- `scene gate` label map
- `confidence band` label map
- `transition hint` map

즉 앞으로 `/propose`, detector, report topic이 같은 raw key를 쓰더라도 같은 한국어로 보이게 만든다.

---

## 구현 대상 파일

### 코드

- `backend/services/reason_label_map.py`
- `backend/integrations/notifier.py`
- `ports/notification_port.py`
- `adapters/telegram_notifier_adapter.py`
- `backend/app/trading_application.py`
- `backend/services/entry_try_open_entry.py`
- `backend/app/trading_application_runner.py`
- `backend/app/trading_application_reverse.py`
- `backend/trading/trade_logger_close_ops.py`

### 테스트

- `tests/unit/test_reason_label_map.py`
- `tests/unit/test_telegram_notifier.py`
- `tests/unit/test_telegram_notifier_adapter.py`
- `tests/unit/test_trading_application_wait_alerts.py`
- `tests/unit/test_trading_application_reverse.py`

---

## 세부 구현 순서

### P2-full-1. 공통 reason/scene map 분리

목표:

- notifier 내부 상수에서 끝나지 않고 공통 정책 파일로 분리

완료 조건:

- `reason`, `scene`, `gate`, `transition` 한국어화가 `reason_label_map.py`에서 제공된다

### P2-full-2. scene line builder 추가

목표:

- runtime row나 state25 bridge에서 scene 정보를 읽어 `장면:` 1줄을 만든다

완료 조건:

- 진입/대기/반전 메시지에서 같은 scene surface 형식을 쓴다

### P2-full-3. reverse transition line 추가

목표:

- `opposite_score_spike`, `volatility_spike`, `plus_to_minus_protect`, `shock_*` 계열을 `전이:` 1줄로 surface

완료 조건:

- 반전 메시지가 pending/ready 상태뿐 아니라 전이 이유도 보여준다

### P2-full-4. exit review hint 확장

목표:

- close path가 갖고 있는 shock metadata를 복기 힌트에 반영

완료 조건:

- shock가 있었던 청산은 일반 힌트보다 shock 중심 힌트를 우선 표시한다

### P2-full-5. runtime 호출 경로 정합성

목표:

- entry/reverse 호출 경로가 `row`를 formatter에 전달
- exit 호출 경로가 `review_context`를 전달

완료 조건:

- formatter가 필요한 설명 surface를 받을 수 있게 wrapper/adapter/port가 맞춰진다

---

## 완료 조건

- 진입 DM에 `장면:` 1줄이 보인다
- 대기 DM에 `장면:` 1줄이 보인다
- 반전 DM에 `장면:`과 `전이:`가 보인다
- 청산 DM에서 shock metadata가 있으면 복기 힌트가 shock 기준으로 바뀐다
- reason/scene 한국어화가 공통 map으로 분리된다
- 관련 테스트가 통과한다

---

## 이번 단계에서 하지 않는 것

- detector proposal 생성
- readiness surface 추가 확장
- scene를 live decision에 직접 반영
- weight patch 자동 apply
- SA live adoption

즉 이번 단계는 끝까지 `설명 surface 확장`에만 집중한다.
