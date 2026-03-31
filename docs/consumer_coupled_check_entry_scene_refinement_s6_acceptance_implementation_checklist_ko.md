# Consumer-Coupled Check / Entry Scene Refinement
## S6. Acceptance Implementation Checklist

### 목표

scene refinement 트랙을
`pass / hold / fail`
로 판정할 근거를 만든다.

### 현재 상태

- `S0 ~ S5`: 완료
- `S6`: 구현/판정 완료
- 다음 active step: `reopen S5 tuning`

### 진행 상태 요약

- `Step 1`: 완료
- `Step 2`: 완료
- `Step 3`: 완료
- `Step 4`: 완료
- `Step 5`: 완료
- `Step 6`: 완료
- `Step 7`: 완료
- `Step 8`: 완료

## Step 1. Immediate Window Snapshot

### 해야 할 일

- tri-symbol 최근 20~40 rows를 다시 얼린다

### 확인 항목

- `observe_reason`
- `blocked_by`
- `action_none_reason`
- `consumer_check_stage`
- `consumer_check_display_ready`
- `consumer_check_display_score`
- `consumer_check_display_repeat_count`

### 완료 기준

- 수정 직후 immediate window 상태가 문서화된다

## Step 2. Rolling Recent Window Snapshot

### 해야 할 일

- tri-symbol 최근 60~120 rows 기준 분포를 고정한다

### 확인 항목

- symbol별 family count
- stage count
- `display_ready_true/false`
- `wrong_ready_count`

### 완료 기준

- 단기/중기 window가 같이 비교 가능하다

## Step 3. Must-Show Acceptance Audit

### 해야 할 일

- S1 must-show family가 실제로 살아 있는지 본다

### 핵심 질문

- 완전히 사라진 family가 있는가
- hidden이더라도 conflict/blocked/cadence로 설명 가능한가

### 완료 기준

- must-show result가 `pass / hold / fail`로 정리된다

## Step 4. Must-Hide Acceptance Audit

### 해야 할 일

- S2 must-hide family가 다시 새는지 본다

### 핵심 질문

- immediate window에서 leaking family가 반복되는가
- rolling window에서도 재발하는가

### 완료 기준

- must-hide result가 `pass / hold / fail`로 정리된다

## Step 5. Symbol Balance Acceptance Audit

### 해야 할 일

- BTC/NAS/XAU의 display imbalance를 최종 점검한다

### 핵심 질문

- 과도한 편차가 남는가
- 남더라도 family/context 차이로 설명 가능한가

### 완료 기준

- symbol balance result가 정리된다

## Step 6. Ladder / Stage Mix Audit

### 해야 할 일

- `OBSERVE / PROBE / BLOCKED / READY / NONE`
  mix와 `70 / 80 / 90` ladder 체감을 확인한다

### 확인 항목

- weak observe가 1개 체감으로 읽히는가
- probe가 2개 체감으로 읽히는가
- ready가 3개 체감으로 읽히는가
- wrong-ready가 0인가

### 완료 기준

- ladder/stage 체감 문제가 있는지 없는지 판단된다

## Step 7. Final Verdict Selection

### 해야 할 일

- 아래 중 하나를 고른다

1. `accept and freeze`
2. `hold and observe one more window`
3. `reopen S5 tuning`
4. `reopen S4 contract`

### 완료 기준

- 최종 action이 한 줄로 정리된다

## Step 8. Acceptance Memo 작성

### 해야 할 일

- S6 결과를 memo 문서로 남긴다

### 필수 섹션

- immediate window
- rolling recent window
- must-show result
- must-hide result
- symbol balance result
- ladder/stage result
- final verdict

### 완료 기준

- 다음 스레드에서도 바로 현재 판정을 이해할 수 있다

## S6 완료 조건

아래가 충족되면 S6 완료로 본다.

- immediate window snapshot이 있다
- rolling recent snapshot이 있다
- must-show / must-hide acceptance 결과가 있다
- symbol balance acceptance 결과가 있다
- ladder/stage acceptance 결과가 있다
- 최종 verdict가 있다
- acceptance memo가 있다
