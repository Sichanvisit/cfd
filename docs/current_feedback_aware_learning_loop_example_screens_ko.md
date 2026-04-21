# Feedback-Aware Learning Loop 예시 화면

## 목적

이 문서는 운영자가 텔레그램에서 실제로 보게 될 화면 느낌을 미리 확인하기 위한 예시 모음이다.

아래 예시는 실제 메시지 구조를 설명하기 위한 샘플이며, 숫자와 심볼은 예시다.

---

## 1. 실시간 알림방 예시

### 진입

```text
진입
시각: 01:25:02
심볼: BTCUSD
방향: SELL
가격: 72812.67000
수량: 0.01 lot
주도축: 상단 거부 확인 + 모멘텀 약화
핵심리스크: 하단 지지 반등 가능성
강도: MEDIUM
장면: 상단 재시험 실패 / gate: caution
보유: 1/3
```

### 대기

```text
대기
시각: 01:28:44
심볼: BTCUSD
방향: SELL 대기
가격: 72805.12000
대기이유: 상하단 힘이 섞여 방향 확정이 부족함
해제조건: BB20 아래 재이탈 시 SELL 검토
장면: 박스 중단 혼합 / gate: weak
보유: 1/3
```

### 청산

```text
청산
시각: 01:41:19
심볼: BTCUSD
결과: 손실
손익: -2.43 USD
가격: 72812.96000 -> 73055.82000
청산사유: 반대 점수 급변 + 변동성 급등
복기힌트: MFE 대비 실현 부족. 반전 대응 속도 재검토
장면: breakout -> runner_hold -> shock_reversal
```

### 반전

```text
반전
시각: 01:41:22
심볼: BTCUSD
방향: BUY 준비
상태: 기존 포지션 정리 후 반전 준비
주도축: 반대 점수 급변 + 상방 추진력 강화
핵심리스크: 직전 급등 이후 되밀림 가능성
강도: HIGH
전이: plus_to_minus -> reverse_ready
```

---

## 2. 체크방 `/detect` 예시

### 체크 topic 요약

```text
[detect]
최근 detector 관찰 4건

D1. BTCUSD scene trace 누락 반복
D2. XAUUSD missed reverse / shock
D3. BTCUSD trend exhaustion 장면 불일치
D4. BTCUSD candle overweight 의심

상세 원문은 보고서 topic 확인
```

### 보고서 topic 원문

```text
[detector 보고서]
기준: 최근 50건 + 최신 runtime 관찰

1. D1 | scene-aware detector
- 심볼: BTCUSD
- 요약: scene trace 누락 반복 감지
- 해석: 장면 전환 기록이 비어 있어 설명력과 detector 입력 품질이 떨어질 수 있음

2. D2 | reverse pattern detector
- 심볼: XAUUSD
- 요약: missed reverse / shock 패턴 관찰
- 해석: 반전이 늦거나 차단된 뒤 shock 청산으로 끝난 사례가 반복됨

3. D3 | scene-aware detector
- 심볼: BTCUSD
- 요약: trend exhaustion 장면 불일치 반복
- 해석: 실제 체감 장면과 내부 scene 라벨이 자주 어긋날 가능성

4. D4 | candle weight detector
- 심볼: BTCUSD
- 요약: 캔들 비중 과대 반응 의심
- 해석: 구조상 상단 힘이 더 강한데 단일 캔들 해석이 하단쪽으로 쏠렸을 가능성
```

---

## 3. 체크방 `/detect_feedback` 예시

### 입력

```text
/detect_feedback D4 과민했음
```

### 응답

```text
[detector 피드백]
대상: D4 / BTCUSD candle overweight 의심
판정: 과민했음
누적 피드백: 3건
confusion: 맞음 1 / 과민 2 / 놓침 0
```

### 다른 예시

```text
/detect_feedback D2 놓쳤음 반전이 더 빨랐어야 했음
```

```text
[detector 피드백]
대상: D2 / XAUUSD missed reverse / shock
판정: 놓쳤음
누적 피드백: 4건
confusion: 맞음 1 / 과민 0 / 놓침 3
```

---

## 4. 체크방 `/propose` 예시

### 체크 topic 요약

```text
[수동 제안 분석]
최근 50건 기준 문제 패턴 3건 / feedback-aware 2건 / 보고서 topic 확인
```

### 보고서 topic 원문

```text
수동 제안 분석 | 최근 마감 거래
기준: 최근 50건 마감 거래
전체 손익 +12.40 USD / 전체 승률 58.0%
평균 MFE 포착률 36.0%

feedback-aware 우선 검토:
- reverse pattern detector / XAUUSD / missed reverse / shock
  - 제안: reverse pattern detector에서 반복 긍정 피드백이 쌓여 proposal 우선 검토 대상으로 승격했습니다.
- candle weight detector / BTCUSD / 상단 거부 혼합 확인
  - 제안: candle weight detector에서 긍정 피드백이 누적돼 proposal 검토 우선순위를 올려볼 가치가 있습니다.

문제 패턴:
1. 상단 거부 혼합 확인 | 표본 8건 | 승률 25.0% | 손익 -18.40 USD
   - 판단: 같은 패턴에서 최근 3연속 손실이 발생했습니다.
   - MFE 포착률 22.0%
   - 제안: 진입 기준 강화 또는 WAIT 우선 전환 후보로 검토하는 편이 안전합니다.

2. 손실 보호 청산 | 표본 6건 | 승률 33.3% | 손익 -9.20 USD
   - 판단: MFE 대비 실현 수익 포착률이 25% 미만입니다.
   - 제안: 진입 자체보다 partial/청산 타이밍 조정 후보로 먼저 보는 것이 좋습니다.
```

---

## 5. PnL방 예시

### 1일 보고

```text
[손익 요약 | 1일]
구간: 2026-04-12 00:00 ~ 2026-04-13 00:00 KST
순손익 합계: +21.40 USD
총손익(비용 전): +27.20 USD
총 비용: 5.80 USD
진입 횟수(마감 기준): 7회
총 진입 랏: 0.21 lot
승/패: 4 / 3 (승률 57.1%)
구간 시작 잔고(추정): 1210.00 USD
구간 종료 잔고(추정): 1231.40 USD

진입 사유 TOP 5:
- 상단 거부 혼합 확인 | 3건 | 비중 42.9% | 승률 33.3% | 순손익 -6.80 USD
- 하단 반등 확인 | 2건 | 비중 28.6% | 승률 100.0% | 순손익 +18.20 USD

청산 사유 TOP 5:
- 손실 보호 청산 | 3건 | 비중 42.9% | 승률 33.3% | 순손익 -7.40 USD
- 추세 소진 청산 | 2건 | 비중 28.6% | 승률 100.0% | 순손익 +14.10 USD

━━ 오늘의 교훈 ━━
- 상단 거부 혼합 확인 계열 연패가 보여 진입 기준 재검토가 필요합니다.
- MFE 대비 수익 포착이 약해 partial 타이밍 보강이 필요합니다.

━━ 시스템 상태 ━━
PA8 closeout: BTCUSD 대기 / XAUUSD 대기 / NAS100 대기
PA9 handoff: PA8 완료 대기 중
reverse readiness: 정상
historical cost confidence: recent-safe
```

---

## 6. 실제 운영에서 권장 확인 순서

1. 실시간 알림방에서 진입/대기/청산/반전 설명 확인
2. 이상한 장면이 있으면 체크방에서 `/detect`
3. detector 항목에 `/detect_feedback`
4. 몇 건 쌓이면 `/propose`
5. PnL방에서 일간 교훈과 readiness 요약 확인

---

## 함께 보면 좋은 문서

- [current_telegram_room_notice_short_templates_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_telegram_room_notice_short_templates_ko.md)
- [current_feedback_aware_learning_loop_operator_guide_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_feedback_aware_learning_loop_operator_guide_ko.md)
- [current_feedback_aware_learning_loop_notice_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_feedback_aware_learning_loop_notice_ko.md)
