# PA8 Historical Replay Board

## 목적

- 시장이 닫혀 있어도 기존 `checkpoint_dataset_resolved.csv`를 써서
  `NAS100 / BTCUSD / XAUUSD` action-only canary scope를 다시 재현해본다.
- 이 결과는 `live first-window`를 대체하지 않는다.
- 대신 `live row`가 들어오기 전까지 canary scope가 과거 row에서 얼마나 안정적으로 보였는지
  보조 증거로 남긴다.

## 왜 별도 board가 필요한가

- 기존 `first_window_observation`은 `post-activation live row`를 기준으로 봐야 한다.
- 주말/휴장처럼 live row가 없는 구간에는 `preview_seed_reference`만 남는다.
- 이때 live artifact를 억지로 덮어쓰면
  `진짜 live 관찰`과 `과거 replay`가 섞여서 판단이 흐려진다.

그래서 historical replay는 아래 원칙을 따른다.

- live artifact를 대체하지 않는다
- closeout을 강제로 앞당기지 않는다
- supporting evidence로만 쓴다

## 계산 방식

각 심볼별로 이미 만들어진 preview scope를 다시 사용한다.

- `NAS100`
  - `profit_hold_bias`
  - `HOLD -> PARTIAL_THEN_HOLD`
- `BTCUSD`
  - `protective_exit_surface + RECLAIM_CHECK + active_open_loss`
  - `PARTIAL_EXIT -> WAIT`
- `XAUUSD`
  - `protective_exit_surface + RECLAIM_CHECK + open_loss_protective|active_open_loss`
  - `PARTIAL_EXIT -> WAIT`

그 다음:

1. preview changed row만 고른다
2. 가장 최근 row를 `sample_floor`만큼 tail window로 자른다
3. 그 window에서
   - `replay_action_precision`
   - `replay_runtime_proxy_match_rate`
   - `replay_worsened_rows`
   를 계산한다

## 출력 의미

- `replay_ready = true`
  - historical scope 기준으로는 sample floor를 채웠고 worsened row가 없다
- `closeout_preview_state = READY_FOR_PA9_REPLAY_PREVIEW`
  - replay 관점의 supporting evidence는 충분하다
  - 하지만 여전히 live window가 필요하다
- `closeout_preview_state = HOLD_REPLAY_WINDOW_BELOW_FLOOR`
  - replay scope row가 아직 적거나 replay quality가 부족하다

## 주의

- replay board는 `PA8 live closeout`을 대신하지 않는다
- `scene bias`와는 별개로 `action-only canary` supporting evidence만 본다
- 최종 closeout은 항상 `post-activation live row`가 다시 들어온 후 판단한다

## 현재 사용 위치

- 장이 닫혀 있을 때 canary 상태를 이해하는 보조판
- `PA8 canary refresh board`와 나란히 보는 supporting artifact
- `PA9 handoff` 전 replay supporting evidence 확인용
