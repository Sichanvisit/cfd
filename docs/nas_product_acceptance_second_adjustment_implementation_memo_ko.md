# NAS Product Acceptance Second Adjustment Implementation Memo

작성일: 2026-03-30 (KST)

## 1. 왜 2차 조정을 했는가

첫 adjustment 이후 사용자가 다시 보여준 NAS chart는
`체크가 너무 많이 찍혀서 차트를 분석할 수 없게 보인다`는 피드백을 주었다.

즉 문제는 아래였다.

- lower recovery를 살린 것까지는 좋았지만
- mature continuation / upper continuation 구간까지
  2개/3개 체크가 과도하게 살아나기 시작했다

그래서 2차 패스의 목표는 아래 한 줄이었다.

```text
살릴 자리는 살리되,
성숙한 continuation 구간의 체크 남발은 강하게 줄인다.
```

## 2. 이번 패스에서 실제로 바꾼 것

핵심 변경 파일:

- [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)
- [test_consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_consumer_check_state.py)

### 2-1. NAS importance tier에 upper context 차단 추가

이제 NAS `medium` tier는 아래에서는 유지되지만,
`UPPER / ABOVE / UPPER_EDGE` 문맥에서는 기본 uplift를 받지 않는다.

즉:

- lower recovery = 계속 살림
- middle pullback = 계속 살림
- upper continuation = 자동 uplift 금지

### 2-2. upper continuation soft cap 추가

late resolve 단계에서 아래 조건이면 soft cap을 건다.

- `symbol = NAS100`
- `side = BUY`
- `display_importance_tier = medium`
- `probe_scene_id = nas_clean_confirm_probe`
- 상단 continuation 문맥

이 경우:

- `display_importance_tier`를 비운다
- `level`을 낮춘다
- 결과적으로 `1개 체크` 수준으로 내려간다

즉 2차 패스부터는
`상단 continuation이 2개/3개로 누적되는 것`
을 자동으로 가볍게 만든다.

## 3. 이번 패스에서 의도적으로 안 건드린 것

아래는 아직 그대로 뒀다.

- `nas_lower_probe_cadence_suppressed`
- `nas_structural_cadence_suppressed`
- NAS scene allow / relief 자체
- painter translation
- entry / wait / exit owner

이유:

- 지금은 “살릴 자리”보다 “남발을 줄이는 자리”를 먼저 분리하는 단계다.
- cadence suppression까지 바로 열면 overpaint가 다시 커질 위험이 있다.

## 4. 현재 NAS 해석

지금 NAS는 아래처럼 읽는다.

- 하단 회복 시작 = 여전히 강하게 보이게 유지
- 중간 재상승 = 2개 체크 후보 유지
- 상단 continuation = 1개로 더 가볍게 제한

즉 현재 방향은:

```text
NAS는 lower/mid 구조만 중요도 uplift를 받고,
upper mature continuation은 다시 조용해지는 방향으로 이동했다.
```

## 5. 테스트 결과

확인한 테스트:

- [test_consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_consumer_check_state.py)
- [test_chart_painter.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_chart_painter.py)
- [test_entry_service_guards.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_entry_service_guards.py)
- [test_entry_engines.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_entry_engines.py)
- 전체 unit

결과:

- `1148 passed, 127 warnings`

## 6. 다음 screenshot에서 볼 포인트

다음 NAS screenshot이 오면 아래 네 가지만 본다.

- 하단 반전/회복 시작이 여전히 3개로 살아 있는가
- 중간 눌림 재상승은 2개로 남아 있는가
- 상단 continuation 남발이 실제로 줄었는가
- 너무 많이 줄어서 NAS가 다시 안 보이게 되지는 않았는가

## 7. 다음 조정 후보

만약 아직도 상단 continuation이 많으면:

1. `nas_lower_probe_cadence_suppressed`
2. `nas_structural_cadence_suppressed`
3. NAS scene allow 축소

반대로 너무 안 보이면:

1. middle pullback context만 선택적으로 재완화
2. upper continuation soft cap 강도 완화
