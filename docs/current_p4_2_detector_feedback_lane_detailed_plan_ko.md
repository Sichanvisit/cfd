# P4-2 Detector Feedback Lane Detailed Plan

## 목표

`/detect`로 surface된 detector 관찰 결과에 대해
사용자가 텔레그램에서 바로

- 맞았음
- 과민했음
- 놓쳤음
- 애매함

을 남길 수 있게 만들고,
그 피드백이 다음 detector 축소와 proposal 우선순위의 입력이 되도록 한다.

## 이번 버전 원칙

- detector는 여전히 `OBSERVE` 전용이다.
- 피드백은 `적용`이 아니라 `학습 라벨`이다.
- 번호 기반으로 빠르게 남길 수 있어야 한다.
- raw key 대신 한국어 summary 기준으로 본다.

## 사용자 흐름

### 1. detector 실행

사용자:

```text
/detect
```

시스템:

- report topic에 detector 관찰 보고 발송
- check topic에 detector inbox 요약 발송
- 명령 reply에 detector 번호 노출

예:

```text
/detect 관찰 보고를 체크/보고서 topic에 올렸습니다.
- 분석 거래 수: 50건 기준
- surface detector: 5건
- D1: trend_exhaustion 장면 불일치 반복 관찰
- D2: BTCUSD scene trace 누락 반복 감지
- D3: trend exhaustion preview changed 관찰
- 피드백 예시: /detect_feedback D1 맞았음
```

### 2. detector 피드백 입력

사용자:

```text
/detect_feedback D1 맞았음
/detect_feedback D2 과민했음
/detect_feedback D3 놓쳤음 메모
```

시스템:

- check topic에 짧은 피드백 기록 메시지 발송
- 명령 reply로 기록 결과 반환
- latest feedback snapshot 갱신

## verdict 표준

- `맞았음`
- `과민했음`
- `놓쳤음`
- `애매함`

영문 fallback:

- `confirmed`
- `oversensitive`
- `missed`
- `ambiguous`

## 상태 저장

Telegram ops state 안에 아래를 유지한다.

- `latest_detect_issue_refs`
  - 마지막 `/detect` 기준 번호 맵
- `detect_feedback_history`
  - 누적 detector 피드백 이력

## 산출물

- [improvement_detector_feedback_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\shadow_auto\improvement_detector_feedback_latest.json)
- [improvement_detector_feedback_latest.md](C:\Users\bhs33\Desktop\project\cfd\data\analysis\shadow_auto\improvement_detector_feedback_latest.md)

## 이번 단계에서 얻는 것

- detector가 맞았는지 틀렸는지 눈에 보인다
- `scene disagreement / missed reverse / candle overweight` 중
  어느 축이 과민한지 누적해서 볼 수 있다
- 나중에 detector를 좁힐 때 감이 아니라 라벨 기준으로 조정할 수 있다

## 아직 하지 않는 것

- detector 피드백 자동 patch 반영
- detector 피드백 자동 proposal 승격
- detector 피드백에 따른 live rule 변경

## 다음 단계 연결

이 피드백 lane이 쌓이면 다음에는

- detector confusion snapshot 강화
- detector별 과민/놓침 비율 기준
- 반자동 proposal 승격 조건

으로 이어간다.
