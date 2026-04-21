# 2026-04-16 재시작 후 차트 표기 점검 메모

## 목적

- 재시작 후 `runtime_status.detail.json` row에 새 flow surface가 실제로 붙는지 확인
- 오늘 NAS / XAU / BTC 스크린샷 기준으로 현재 표기 미스를 메모
- Telegram과 chart에 바로 반영할 수 있는 shadow display 기준을 정리

## 재시작 후 row 확인

재시작 후 실제 row에서 아래 필드가 확인되었다.

- `flow_support_state_v1`
- `aggregate_conviction_v1`
- `flow_persistence_v1`

즉 현재 문제는 "새 필드가 export되지 않음"보다는,
이미 붙은 flow surface가 상단 표기와 Telegram 문구에 충분히 소비되지 않는 쪽에 가깝다.

## 스크린샷 기준 표기 미스

### NAS100

- 차트 체감:
  - 우상향 continuation 채널 성격이 강함
  - 신규 추격 진입은 불리하지만, 지속성 자체는 약하지 않음
- 현재 row/표기 문제:
  - `flow_support_state_v1 = FLOW_OPPOSED`
  - 상단 말투가 continuation보다 guard / wait 쪽으로 눌림
- 원하는 보정:
  - "상승 지속 관찰"은 보이되
  - "신규 진입 품질 낮음"을 분리해서 보여야 함

### XAUUSD

- 차트 체감:
  - 하단 rebound 이후 recovery/building 성격
  - 상단 저항 아래라 매수 확인은 보수적이어야 함
- 현재 row/표기 문제:
  - `FLOW_OPPOSED`와 boundary 성격이 너무 강함
  - 차트에는 시작 기호가 거의 안 보임
- 원하는 보정:
  - recovery watch / buy watch 시작 표기 필요
  - 지속성과 진입 품질을 분리해 보여야 함

### BTCUSD

- 차트 체감:
  - 회복 시도와 저항 재충돌이 섞인 building 구간
  - 완전한 bull continuation은 아니지만 하단 rebound watch는 필요
- 현재 row/표기 문제:
  - `FLOW_OPPOSED` 또는 과도한 보수 해석으로 눌림
  - chart 시작 기호와 Telegram 지속성 정보가 부족함
- 원하는 보정:
  - buy watch 시작 표기
  - reversal risk를 같이 보이되, continuation seed도 묻히지 않게

## 적용 원칙

이번 보정은 execution 변경이 아니라 display shadow layer로만 다룬다.

- `continuation persistence`
- `fresh entry quality`
- `reversal risk`

위 3축을 row에 read-only로 붙이고,
Telegram에는 한 줄 shadow 표기로,
chart에는 기존 `BUY_WATCH / SELL_WATCH` 경로를 타는 fallback start marker로 연결한다.

## 기대 결과

- NAS:
  - chart에는 기존 watch 성격 유지
  - Telegram에는 "지속성은 중간 이상, 진입품질은 낮음"이 보임
- XAU:
  - fallback `BUY_WATCH` 시작 marker가 붙을 수 있음
  - Telegram에서 recovery shadow가 보임
- BTC:
  - fallback `BUY_WATCH` 시작 marker가 붙을 수 있음
  - Telegram에서 building/reversal 분리가 보임
