# BC5 State25 Overlap Guard Refinement 구현 로드맵

## 목표

`forecast / belief / barrier`가 같은 `state25_runtime_hint_v1`를 반복할 때
`BC2 weight-only` bridge의 blanket overlap suppression을 완화한다.

## 단계

### BC5-1. Signature extractor 추가

- `state25_runtime_hint_v1`에서 비교용 signature 추출
- 비교 필드:
  - `scene_pattern_id`
  - `entry_bias_hint`
  - `wait_bias_hint`
  - `exit_bias_hint`
  - `transition_risk_hint`
  - `reason_summary`

완료 조건:

- bridge 내부 helper에서 source별 signature를 안정적으로 만들 수 있음

### BC5-2. Same-runtime-hint duplicate 판정 추가

- `forecast / belief / barrier` 중 2개 이상 존재
- 비어있지 않은 signature가 2개 이상
- signature가 모두 같음
- `countertrend_continuation_signal_v1` 없음

완료 조건:

- `overlap_same_runtime_hint_duplicate`가 `True/False`로 계약에 실림

### BC5-3. Guard decision 추가

- `overlap_guard_decision`
  - `NO_OVERLAP`
  - `BLOCKED_OVERLAP_DUPLICATE`
  - `RELAXED_SAME_RUNTIME_HINT_DUPLICATE`

완료 조건:

- 같은 runtime hint 반복이면 `double_counting_guard_active = false`
- 나머지는 기존처럼 guard 유지

### BC5-4. Trace / flat field 보강

- `trace_reason_codes`
  - `OVERLAP_GUARD_RELAXED_SAME_RUNTIME_HINT`
- `trace_lines_ko`
  - BC5 완화 이유 1줄
- runtime flat field export에 guard decision 포함

완료 조건:

- runtime row에서 BC5 완화 여부를 바로 확인할 수 있음

### BC5-5. 테스트 보강

- 같은 runtime hint 반복이면 effective weight 유지
- 다른 signature면 guard 유지
- weight review candidate가 effective count를 실제로 들고 나오는지 확인

완료 조건:

- bridge / review 테스트 통과

### BC5-6. Audit 재생성

- overlap guard audit 최신 생성
- 기대 확인:
  - `XAUUSD`: requested 2 / effective 2
  - blanket duplicate는 남아도 guard active는 완화될 수 있음

완료 조건:

- 최신 audit에서 blanket suppression 감소가 보임

## 검증 명령

```powershell
pytest tests/unit/test_state25_context_bridge.py tests/unit/test_state25_weight_patch_review.py tests/unit/test_state25_context_bridge_overlap_guard_audit.py -q
```

```powershell
@'
from backend.services.state25_context_bridge_overlap_guard_audit import write_state25_context_bridge_overlap_guard_audit
write_state25_context_bridge_overlap_guard_audit()
'@ | python -
```

## 다음 단계

`BC5`가 안정적으로 확인되면 다음은 둘 중 하나다.

1. `BC6 threshold log-only translator`
2. `BC4/BC5 review lane`이 `/detect -> /propose`에서 어떻게 읽히는지 운영 검증
