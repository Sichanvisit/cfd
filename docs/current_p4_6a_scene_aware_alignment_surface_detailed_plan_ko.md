# P4-6A Scene-Aware Alignment Surface 상세 계획

## 목표

실시간 DM의 `구조 정합:` 한 줄을 thin-slice 규칙에서 한 단계 올려,
현재 장면(scene family)에 따라 `정합 ✅ / 엇갈림 ⚠️ / 중립 ➖`를 더 자연스럽게 읽게 만든다.

이번 단계의 목적은 매매 로직 변경이 아니라 `설명 surface` 정밀화다.

## 왜 지금 이 단계인가

이미 [notifier.py](C:\Users\bhs33\Desktop\project\cfd\backend\integrations\notifier.py)에
`위/아래 힘`과 `구조 정합` thin-slice는 들어가 있다.

하지만 thin-slice는 다음 한계가 있었다.

- `BUY + UPPER`를 항상 엇갈림으로 읽음
- 그래서 `breakout_retest_hold` 같은 돌파 계열에서도 과하게 보수적으로 보일 수 있음
- 반대로 `BUY + LOWER`는 항상 정합으로 읽혀서 장면 맥락이 빠짐

따라서 이번 단계는 `장면 계열을 반영한 정합 분기`만 먼저 올려,
DM 설명이 사람 체감과 더 가깝게 읽히도록 만드는 데 집중한다.

## 범위

이번 단계에서 한다.

- `runtime_scene_fine_label` 기반 scene family 분기
- `구조 정합:` 문구를 scene-aware 기준으로 변경
- 테스트 보강

이번 단계에서 하지 않는다.

- 거래 로직 변경
- detector apply
- `box_relative_position`, `wick/body`, `recent_3bar_direction` 계산
- hindsight 검증

## 입력 신호

- `consumer_check_side`
- `position_dominance`
- `runtime_scene_fine_label`
- `runtime_scene_label`
- `state25_label`
- `scene_pattern_name`
- `scene_group_hint`

## scene family 규칙

### 1. 돌파/리클레임 계열

예:

- `breakout`
- `breakout_retest_hold`
- `liquidity_sweep_reclaim`
- `reclaim_breakout`
- `early_breakout_probe`
- `mixed_breakout`
- `range_break`
- `correct_flip`
- `trend_ignition`

이 계열에서는:

- `BUY + UPPER` -> 정합 ✅
- `SELL + LOWER` -> 정합 ✅
- `BUY + LOWER` -> 엇갈림 ⚠️
- `SELL + UPPER` -> 엇갈림 ⚠️

### 2. 눌림/지속 계열

예:

- `pullback_continuation`
- `pullback_then_continue`
- `runner_hold`
- `runner_healthy`
- `correct_hold`
- `reaccumulation`
- `redistribution`
- `trend_exhaustion`
- `time_decay_risk`
- `range_reversal_scene`
- `entry_initiation`
- `defensive_exit`
- `position_management`

이 계열에서는:

- `BUY + LOWER` -> 정합 ✅
- `SELL + UPPER` -> 정합 ✅
- `BUY + UPPER` -> 엇갈림 ⚠️
- `SELL + LOWER` -> 엇갈림 ⚠️

### 3. 장면 불명

scene family를 명확히 고를 수 없으면:

- `장면 미확정으로 중립 ➖`

즉 억지로 정합/엇갈림을 확정하지 않는다.

## 출력 문구 정책

실시간 DM에는 다음 한 줄만 추가/변경한다.

예:

- `구조 정합: BUY와 상단 우세 조합은 돌파/리클레임 계열 기준 정합 ✅`
- `구조 정합: BUY와 상단 우세 조합은 눌림/지속 계열 기준 엇갈림 ⚠️`
- `구조 정합: BUY와 상단 우세 조합은 장면 미확정으로 중립 ➖`

중요:

- 이 문구는 `방향 정답 판정`이 아니다
- `현재 구조 위치와 현재 실행 방향의 정합`만 보여준다

## thin-slice -> 정식 버전 전환 기준

이번 단계는 `scene-aware 첫 정식 버전`이지만,
여전히 detector evidence 전체를 다 쓰는 최종 완성판은 아니다.

다음 단계인 `P4-6B/C/D`로 넘어갈 때 아래를 같이 본다.

- live DM 기준 3일 이상 운영
- `엇갈림 ⚠️`에 대한 실제 사용자 확인 5건 이상
- 돌파 계열에서 `엇갈림 ⚠️`가 false alarm으로 확인된 케이스 집계

## 건드릴 파일

- [notifier.py](C:\Users\bhs33\Desktop\project\cfd\backend\integrations\notifier.py)
- [test_telegram_notifier.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_telegram_notifier.py)

## 구현 순서

1. scene raw label 추출 helper 정리
2. scene family 분기 helper 추가
3. `구조 정합:` 문구를 family-aware로 변경
4. breakout/pullback/unknown 테스트 추가

## 완료 조건

- `breakout_retest_hold + BUY + UPPER`가 정합으로 읽힌다
- `pullback_continuation + BUY + LOWER`가 정합으로 읽힌다
- `scene 불명`은 중립으로 남는다
- 기존 실시간 DM 형식은 유지된다
- 거래 로직은 바뀌지 않는다

## 다음 단계

- `P4-6B` `box_relative_position`
- `P4-6C` `wick/body ratio`
- `P4-6D` `recent_3bar_direction`

즉 `P4-6A`는 설명면의 첫 정식 분기이고,
그 다음 단계부터 detector evidence가 더 직접적인 구조 측정값을 갖게 된다.
