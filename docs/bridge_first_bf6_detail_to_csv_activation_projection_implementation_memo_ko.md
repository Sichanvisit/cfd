# BF6 Detail-to-CSV Activation Projection Implementation Memo

작성일: 2026-03-31 (KST)

## 1. 이번 구현에서 한 일

- [state_forecast_validation_detail_to_csv_activation_projection.py](C:\Users\bhs33\Desktop\project\cfd\scripts\state_forecast_validation_detail_to_csv_activation_projection.py) 추가
- detail sample loader 구현
- CSV normalized row에 `decision_row_key / replay_row_key`를 다시 붙이는 projection wrapper 추가
- `decision_row_key -> replay_row_key -> time tuple` match 구현
- `activation_slice_projection_rows` 생성
- `order_book_slice_projection_rows` 생성
- `section_value_projection_rows` 생성

## 2. 왜 이렇게 구현했나

BF6의 목적은 새 판단 로직을 넣는 게 아니라,
이미 있는 `detail trace`와 `CSV value row`를 다시 붙이는 것이다.

그래서 이번 구현은:

- runtime forecast math는 건드리지 않고
- validation / review surface만 복원

하는 방향으로 제한했다.

## 3. 현재 latest 해석

기준 산출물:

- [state_forecast_validation_bf6_projection_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\state_forecast_validation\state_forecast_validation_bf6_projection_latest.json)

현재 핵심 수치:

- `sampled_detail_rows = 3695`
- `matched_projection_rows = 3664`
- `projection_match_ratio = 0.9916`
- `exact_decision_row_key_matches = 3664`
- `unmatched_projection_rows = 31`

즉 BF6에서 확인된 건 아래 두 가지다.

1. projection bridge는 잘 붙는다
2. 남은 gap은 projection 부재가 아니라 section/value path 쪽이다

## 4. 눈에 띄는 포인트

- `activation slice projection`은 이미 usable surface가 나왔다
- `order_book_projection`도 row surface는 생겼다
- 다만 `secondary_harvest` section used ratio는 여전히 약하다

이건 BF6 실패가 아니라
historical row가 BF5 direct-use 이전 metadata를 가지고 있기 때문으로 읽는 게 맞다.

## 5. 테스트

- [test_state_forecast_validation_detail_to_csv_activation_projection.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_state_forecast_validation_detail_to_csv_activation_projection.py)

확인한 것:

- exact decision_row_key projection
- unmatched row gap reporting

## 6. 다음 단계

BF6 다음 active step은 `BF7 close-out and handoff`다.
