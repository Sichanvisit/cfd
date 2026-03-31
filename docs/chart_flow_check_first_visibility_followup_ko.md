# Check-First Visibility Follow-up

## 1. 배경

자동 진입이 먼저 보이고 `BUY_PROBE / BUY_WAIT / SELL_PROBE / SELL_WAIT / BUY_READY / SELL_READY` 같은
pre-entry 체크가 차트에서 덜 보이면, 사용자는 "왜 여기서 진입했는가"를 바로 읽기 어렵다.

이번 follow-up의 목적은 실행을 늦추는 것이 아니라,
차트 history가 entered row를 처리할 때 pre-entry directional check를 먼저 보존하도록 만드는 것이다.

## 2. 문제 형태

기존 [chart_painter.py](c:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_painter.py) 흐름에서는
같은 candle / 같은 timestamp에서:

1. pre-entry directional event
2. `ENTER_BUY` 또는 `ENTER_SELL`

이 연속으로 들어오면 terminal entry가 pre-entry event를 대체할 수 있었다.

이 경우 실제로는 진입 전 `probe / wait / ready` 논리가 존재했더라도
차트에는 `ENTER_*`만 더 눈에 띄게 남아 "체크보다 진입이 먼저 보인다"는 체감이 생길 수 있다.

## 3. 이번 적용 원칙

- 실행 순서를 늦추지 않는다.
- entry owner는 유지한다.
- 차트 가시성만 `check-first visibility`로 바꾼다.
- entered row에서도 같은 row가 directional pre-entry 해석을 만들 수 있으면, 그 pre-entry event를 먼저 history에 남긴다.
- 단, 이미 직전 history에 같은 pre-entry event가 있으면 중복 생성하지 않는다.

## 4. 구현 방식

적용 파일:

- [chart_painter.py](c:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_painter.py)

추가한 핵심 동작:

1. entered row에서 `entry_decision_result_v1`를 비운 가상 row를 기준으로 pre-entry event를 다시 해석한다.
2. 해석 결과가 directional `PROBE / WATCH / WAIT / READY`이면 precursor payload를 만든다.
3. 같은 시각에 terminal `ENTER_*`가 와도, 직전 directional precursor와 같은 side면 terminal이 precursor를 덮어쓰지 않고 뒤에 이어 붙는다.
4. 이미 직전에 같은 precursor가 있으면 새로 복제하지 않는다.

## 5. 기대 효과

- 사용자는 `왜 진입했는지`를 entry marker만이 아니라 pre-entry directional check로 먼저 읽을 수 있다.
- BTC lower rebound 같은 빠른 진입 케이스도 `BUY_PROBE -> ENTER_BUY` 또는 `BUY_READY -> ENTER_BUY` 흐름으로 더 자연스럽게 보인다.
- entry engine, wait engine, exit engine의 실질 실행 순서는 유지된다.

## 6. 회귀 테스트

추가 / 갱신 테스트:

- [test_chart_painter.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_chart_painter.py)

검증 포인트:

- same-candle entered row에서도 pre-entry probe가 먼저 보존되는지
- 이미 같은 precursor가 있는 경우 중복 생성하지 않는지
- later neutral wait가 entered state를 무너뜨리지 않는지

## 7. 해석 주의점

이번 변경은 "진입을 한 바퀴 늦춘다"는 뜻이 아니다.

즉:

- `entry-second execution`을 새로 도입한 것이 아니라
- `check-first visibility`를 차트 history에 반영한 것이다.

실행 자체를 한 사이클 늦추는 계약은 별도 owner와 별도 검토가 필요하다.
