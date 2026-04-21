# BC2 State25 Weight-Only Translator 실행 로드맵

## 목표

state25 context bridge skeleton 위에 첫 실제 translator인 `weight-only`를 올린다.


## BC2-1. Weight Baseline Intake

목표:
- 현재 baseline weight 값을 읽을 수 있게 하기

구현 항목:
- direct row weight overrides 읽기
- nested `state25_candidate_runtime_v1` / runtime state에서 baseline overrides fallback 읽기
- baseline이 없으면 기본값 `1.0`


## BC2-2. Context Pair Translation

목표:
- context를 실제 weight pair 후보로 번역

구현 항목:
- `AGAINST_HTF`
- `BREAKOUT_HELD`
- `RECLAIMED`

완료 기준:
- 각 context가 최대 2개 weight key만 건드림


## BC2-3. Bias Side Resolution

목표:
- 이번 weight translator가 어느 방향 해석을 지지하는지 보조로 계산

구현 항목:
- `context_bias_side`
- `context_bias_side_confidence`
- `context_bias_side_source_keys`


## BC2-4. Effective / Suppressed Resolution

목표:
- requested와 effective를 분리하고 suppression을 구조화

구현 항목:
- stale suppression
- low confidence / non-consolidation suppression
- overlap guard suppression
- late chase defer suppression
- cap / clamp 반영


## BC2-5. Weight Trace

목표:
- BC2 이후 trace만 봐도 왜 이 weight가 움직였는지 이해할 수 있게 하기

구현 항목:
- `trace_reason_codes`
- `trace_lines_ko`
- weight translator summary line


## BC2-6. Tests

최소 테스트:
1. `AGAINST_HTF`가 reversal/directional pair로 번역되는지
2. `BREAKOUT_HELD`가 range_reversal/directional pair로 번역되는지
3. overlap guard가 effective를 suppress하는지
4. late chase가 weight translation에서 제외되고 suppression만 남는지


## 완료 후 다음 단계

BC2 완료 후 가장 자연스러운 다음 순서는:

1. `BC3 Runtime Trace Export`
2. `BC4 Weight-Only Log-Only Review Lane`

즉 BC2는 skeleton을 넘어 **첫 실제 조정값 계산기**를 붙이는 단계다.
