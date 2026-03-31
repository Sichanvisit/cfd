# NAS Product Acceptance Fourth Adjustment Implementation Memo

작성일: 2026-03-30 (KST)

## 1. 목적

이번 4차 조정의 목적은
NAS 상단 혼잡 구간에서 BUY 체크를 강하게 늘리는 것이 아니라,
`BUY 흐름이 아직 완전히 죽지 않았다`는 약한 awareness 체크를
차트에 남기게 만드는 것이다.

즉 이 조정은

- 강한 진입 신호를 더 만들기 위한 조정이 아니고
- 상단 혼잡 구간에서 long 쪽 생존 신호를 읽어
  청산과 역방향 판단을 더 잘 하기 위한 조정이다.

## 2. 이번 조정 전 문제

기존 NAS 조정은

- 하단 회복 시작은 강하게 살리고
- 구조 반등은 2개 체크로 살리고
- 상단 continuation 남발은 눌러두는

방향으로 맞춰져 있었다.

이 방향은 맞지만,
상단 박스/혼잡 구간에서
`강하게 살릴 정도는 아니지만 아예 안 보이면 안 되는 BUY 자리`
도 같이 죽는 문제가 있었다.

사용자 관점에서는 이런 약한 BUY 체크가 보여야

- 아직 long 흐름을 버리지 않았는지
- 여기서 청산을 더 생각해야 하는지
- 이제 reverse sell을 준비할지

를 판단할 수 있다.

## 3. 이번 조정의 핵심

이번에는 NAS 상단 support 문맥에
`nas_upper_support_awareness` source reason을 추가했다.

이 source reason은

- 강한 2개/3개 체크를 주기 위한 이유가 아니라
- 상단 혼잡/support 구간에서 1개 BUY awareness 체크를 남겨야 하는 이유

를 기록한다.

## 4. 실제 코드 변경

대상 파일:

- [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)

핵심 변경:

1. `_display_importance_source_reason_v1(...)`에서
   NAS upper-context structural observe를
   `nas_upper_support_awareness`로 기록
2. `nas_structural_cadence_suppressed`가
   이 source reason까지 완전히 숨기지 않도록 예외 처리

즉 이전에는 반복 억제에 의해 사라졌던 장면이,
이제는 `1개 체크` 수준으로는 남을 수 있게 됐다.

## 5. 이번 조정으로 기대하는 체감

이번 조정이 제대로 먹으면
NAS 상단 혼잡 구간은 아래처럼 바뀌어야 한다.

- 계속 2개/3개 체크가 남발되지는 않음
- 하지만 의미 있는 support/reclaim 자리에서
  `1개 BUY 체크`는 살아남음
- 그 결과 차트가 너무 조용하지도 않고,
  그렇다고 confetti처럼 어지럽지도 않음

## 6. 왜 이게 이후 조정과 안 섞이게 되나

이번엔 이유를 그냥 감으로 남긴 게 아니라
source reason으로 분리했다.

즉 이후 NAS 조정이 더 들어와도
아래를 따로 읽을 수 있다.

- `nas_lower_recovery_start`
- `nas_structural_rebound`
- `nas_breakout_reclaim_confirm`
- `nas_upper_support_awareness`

이렇게 reason이 분리돼 있어야
나중에 상단 혼잡 구간만 다시 줄이거나,
오히려 더 살리는 조정을 해도
기존 lower recovery 조정과 섞이지 않는다.

## 7. 테스트

관련 검증은 아래 기준으로 다시 확인했다.

- [test_consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_consumer_check_state.py)
- [test_chart_painter.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_chart_painter.py)
- [test_entry_service_guards.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_entry_service_guards.py)
- [test_entry_engines.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_entry_engines.py)

이번 조정 후 기준:

- targeted 회귀: `191 passed`
- full unit: `1162 passed`

## 8. 한 줄 결론

```text
NAS 4차 조정의 핵심은 상단 혼잡 구간에 BUY를 세게 띄우는 것이 아니라,
청산/역방향 판단을 위해 필요한 약한 BUY awareness 체크를
reason 단위로 살려두는 것이다.
```
