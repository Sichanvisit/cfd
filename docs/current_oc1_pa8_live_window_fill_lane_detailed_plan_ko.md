# OC1. PA8 Live Window Fill Lane 상세 계획

## 목적

`OC1`의 목적은 `PA8 closeout`을 실제로 닫기 위해 필요한
post-activation live row 누적 상태를 별도 lane으로 보이게 만드는 것이다.

기존에도 아래 정보는 흩어져 있었다.

- master board
- pa8 closeout runtime
- first symbol focus
- non-apply audit

하지만 운영자가 지금 바로 알고 싶은 것은 더 직접적이다.

- 어느 심볼이 실제로 row를 채우고 있는가
- sample floor까지 몇 row가 남았는가
- 이번 스냅샷에서 row가 늘었는가 멈췄는가
- rollback review가 먼저인지, 계속 fill을 봐야 하는지

즉 `OC1`은 "PA8 evidence acceleration"을 위한
운영 전용 요약 lane이다.

---

## 왜 별도 lane이 필요한가

현재 `PA8`은 구조상 거의 완료되었지만,
운영에서 막히는 이유가 심볼마다 다르다.

- `NAS100`
  - first symbol
  - live row는 들어오고 있음
  - 그러나 rollback review가 먼저 필요할 수 있음
- `BTCUSD`
  - row 자체가 거의 안 보이거나
  - preview candidate가 잘 안 생김
- `XAUUSD`
  - sample floor가 더 낮지만
  - 여전히 live row fill이 부족함

이 상태를 board의 readiness 한 줄로만 보면
"왜 다음 단계로 못 가는지"가 직감적으로 안 잡힌다.

그래서 `OC1`에서는 아래만 따로 surface한다.

- `observed_window_row_count`
- `sample_floor`
- `rows_remaining_to_floor`
- `progress_pct`
- `progress_delta_rows`
- `velocity_state`
- `fill_lane_state`

---

## 설계 원칙

### 1. PA8 readiness를 대체하지 않는다

이 lane은 readiness surface를 대체하는 것이 아니다.

- readiness는 "지금 ready냐 아니냐"
- fill lane은 "지금 얼마나 채워졌냐"

를 보여준다.

### 2. closeout apply 결정을 내리지 않는다

이 lane은 실행 로직이 아니다.

- threshold를 자동으로 바꾸지 않음
- apply를 강제하지 않음
- closeout verdict를 직접 내리지 않음

오직 운영 관찰과 우선순위 정리에만 쓴다.

### 3. snapshot delta를 보여준다

운영자가 제일 궁금한 건 "그래서 늘었나?"다.

그래서 이번 lane은 이전 스냅샷과 비교한

- `progress_delta_rows`
- `progress_delta_pct`
- `velocity_state`

를 같이 남긴다.

---

## fill lane 상태 정의

- `ROLLBACK_REVIEW_PENDING`
  - live row는 일부 들어왔지만 rollback review가 먼저 필요한 상태
- `READY_FOR_REVIEW`
  - sample floor / live observation 조건이 review 기준으로 충족된 상태
- `ACTIVE_FILL`
  - live row가 실제로 채워지고 있으나 floor는 아직 남은 상태
- `SEEDED_WAITING_ROWS`
  - first window는 열렸지만 아직 post-activation live row가 거의 없는 상태

---

## 출력 아티팩트

- `data/analysis/shadow_auto/checkpoint_pa8_live_window_fill_lane_latest.json`
- `data/analysis/shadow_auto/checkpoint_pa8_live_window_fill_lane_latest.md`

또한 orchestrator watch payload 안에도
`pa8_live_window_fill` 블록으로 같이 들어간다.

---

## 운영 해석

이 lane에서 운영자가 제일 먼저 볼 것은 아래 세 가지다.

1. `fill_lane_state`
- 지금이 rollback review인지
- active fill인지
- waiting first rows인지

2. `rows_remaining_to_floor`
- sample floor까지 얼마나 남았는지

3. `velocity_state`
- row가 늘고 있는지
- 멈췄는지
- 줄었는지

즉 이 lane은

```text
PA8이 안 닫히는 이유를
"ready 아님"이 아니라
"얼마나 찼고, 얼마나 남았고, 지금 늘고 있는가"로 읽게 하는 도구
```

이다.

---

## 완료 기준

- 심볼별 live window fill 상태가 JSON/Markdown으로 출력됨
- 이전 스냅샷 대비 증감이 보임
- orchestrator watch payload에서 함께 surface됨
- 운영자가 NAS/BTC/XAU를 같은 틀로 비교 가능함
