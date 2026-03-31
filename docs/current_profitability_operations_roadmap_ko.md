# 수익 개선 / 운영 확장 로드맵

작성일: 2026-03-29 (KST)

## 1. 왜 새 로드맵이 필요한가

진입, 기다림, 청산의 코어 구조는 이제 상당 부분 구축됐다.
이제부터는 “구조를 더 잘게 쪼개는 일”보다
“이 구조를 사용해서 실제 기대값을 읽고 개선하는 일”이 더 중요하다.

즉 다음 단계의 질문은 아래와 같다.

- 어떤 setup과 regime이 실제로 돈을 버는가
- 어디에서 수익이 새고 있는가
- 이상 징후를 사람이 늦게 보기 전에 어떻게 감지할 것인가
- 최근 변화가 개선인지 악화인지 어떻게 비교할 것인가

이 로드맵은 그 질문에 답하기 위한 운영 확장 계획이다.


## 2. 현재 위치

현재는 아래가 준비된 상태다.

- entry / wait / exit 의미 계약
- branch truth logging
- recent runtime summary
- handoff / checklist / read guide
- continuity close-out

즉 “무슨 일이 일어났는가”와 “왜 그런가”를 읽기 위한 바닥은 이미 있다.
이제는 그 바닥 위에 수익 관점 운영 도구를 올리면 된다.


## 3. 새 로드맵의 큰 방향

새 로드맵은 아래 다섯 phase로 보는 것이 자연스럽다.

1. lifecycle correlation observability
2. expectancy / attribution observability
3. alerting / anomaly detection
4. time-series comparison
5. optimization loop / casebook 강화


## 4. Phase P1: Lifecycle Correlation Observability

### 목표

entry, wait, exit를 따로 보지 않고,
한 거래 생애주기로 이어서 읽게 만드는 것이다.

### 왜 중요한가

실전에서는 아래처럼 연결해서 봐야 한다.

- entry blocked 증가
- wait selected 증가
- exit pressure 증가
- 실제 PnL 악화

이걸 각 phase별 문서로 따로 읽으면 늦다.
운영 surface에서 한 번에 읽히는 correlation view가 필요하다.

### 해야 할 일

- lifecycle correlation summary shape 설계
- symbol별 entry-wait-exit 연결 요약 추가
- state family / decision family / blocked reason / hold class를 함께 보는 집계 추가
- 새 스레드용 lifecycle quick read 문서 추가

### 완료 기준

- “최근 손실이 entry 때문인지, wait 때문인지, exit 때문인지” 방향을 runtime summary에서 바로 잡을 수 있다.


## 5. Phase P2: Expectancy / Attribution Observability

### 목표

무엇이 실제로 기대값을 만드는지 숫자로 읽는 것이다.

### 왜 중요한가

구조가 좋아져도,
실제로 어떤 setup과 regime이 돈을 버는지 모르면 수익 개선으로 못 이어진다.

### 해야 할 일

- setup별 expectancy 요약
- regime별 expectancy 요약
- symbol별 expectancy 요약
- entry/wait/exit stage별 PnL attribution
- recovery wait, reverse now, exit_now 등 청산 family별 성과 요약

### 완료 기준

- “무엇을 늘리고 무엇을 줄일지”를 감이 아니라 숫자로 말할 수 있다.


## 6. Phase P3: Alerting / Anomaly Detection

### 목표

이상 징후를 운영자가 늦게 발견하지 않도록 자동 경고 체계를 붙이는 것이다.

### 왜 중요한가

지금은 진단은 가능하지만,
대부분 사람이 열어봐야 안다.
이건 실전 운영에서는 늦다.

### 대표 경보 후보

- wrong ready count가 0보다 커짐
- 특정 bridge mismatch 급증
- wait selected rate 급증
- reverse now 비율 급증
- exit pressure family 급증
- runtime unavailable / diagnostics source missing 지속

### 완료 기준

- 사람이 직접 파일을 열어보기 전에 이상 패턴을 먼저 인지할 수 있다.


## 7. Phase P4: Time-Series Comparison

### 목표

오늘과 어제, 이번 변경 전후를 비교해서
개선인지 악화인지 빠르게 판단하는 것이다.

### 왜 중요한가

운영에서는 “지금 상태”만 보는 것보다
“이전보다 나아졌는지”를 보는 것이 더 중요하다.

### 해야 할 일

- recent window 간 비교 summary
- 배포 전후 비교 summary
- symbol / setup / regime별 변화량 요약
- wait/exit family 비율 변화량 요약

### 완료 기준

- 변경 이후 무엇이 좋아졌고 나빠졌는지 recent compare만으로 방향을 잡을 수 있다.


## 8. Phase P5: Optimization Loop / Casebook 강화

### 목표

운영 데이터를 다시 구조 개선과 튜닝으로 돌려주는 반복 고리를 만드는 것이다.

### 왜 중요한가

수익 시스템은 한 번 잘 짠다고 끝나지 않는다.
좋은 장면과 나쁜 장면을 계속 분류해서,
정책과 threshold를 다듬는 루프가 있어야 한다.

### 해야 할 일

- 대표 승률 장면 casebook
- 대표 손실 장면 casebook
- regime별 best / worst scene 묶음
- setup blacklist / caution list
- tuning candidate queue 문서화

### 완료 기준

- 손실 장면을 수동 회고로만 다루지 않고, 다음 정책 개선 input으로 바로 연결할 수 있다.


## 9. 우선순위 제안

현재 기준 우선순위는 아래가 가장 자연스럽다.

1. P1 lifecycle correlation observability
2. P2 expectancy / attribution observability
3. P3 alerting / anomaly detection
4. P4 time-series comparison
5. P5 optimization loop / casebook 강화

이 순서가 좋은 이유는,
먼저 전체 흐름을 같이 보고,
그 다음 실제 기대값을 읽고,
그 다음 이상 징후를 자동 감지하고,
마지막으로 운영 데이터를 튜닝 루프로 돌리는 방식이기 때문이다.


## 10. 지금 당장 착수하면 좋은 첫 작업

가장 먼저 시작하기 좋은 것은 아래 두 가지다.

### 첫 번째

entry-wait-exit correlation summary 설계 문서 작성

### 두 번째

setup / regime / symbol 기준 expectancy summary 초안 설계

이 둘이 붙으면,
이후 alerting과 compare도 기준이 훨씬 선명해진다.


## 11. 결론

지금까지는 구조 공사였다.
이제부터는 운영 데이터를 통해
무엇이 실제로 기대값을 만들고,
어디에서 성능이 새는지를 읽어내는 단계다.

즉 새 로드맵의 핵심은
“엔진을 더 복잡하게 만드는 것”이 아니라
“이미 만든 구조를 수익 개선과 운영 판단으로 연결하는 것”이다.
