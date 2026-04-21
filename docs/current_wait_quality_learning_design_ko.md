# Wait 품질 학습 상세 설계

작성일: 2026-04-03 (KST)

## 1. 설계 목표

이 설계의 목표는 `entry-side wait`를 사후 평가할 수 있는 별도 owner를 만드는 것이다.

live 엔진이 이미 아래를 결정하고 있다면:

- 지금 들어간다
- 지금 기다린다
- 지금 스킵한다

이 설계는 그 다음 질문을 담당한다.

- 그 기다림은 결과적으로 좋았는가
- 그 기다림은 결과적으로 나빴는가

즉 `판단`과 `판정 후 평가`를 분리하는 설계다.

## 2. 꼭 답해야 하는 네 가지 질문

새 owner는 최소한 아래 네 질문을 직접 판정해야 한다.

1. 기다렸더니 더 좋은 자리에서 들어갔는지
2. 기다려서 손실을 피했는지
3. 괜히 기다리다 신호를 놓쳤는지
4. 기다렸는데 결국 더 나쁜 가격이나 더 늦은 손실이 되었는지

이 네 질문이 바로 `entry wait quality`의 최소 contract다.

## 3. 새 label family

이번 설계에서 권장하는 기본 label은 아래다.

- `better_entry_after_wait`
- `avoided_loss_by_wait`
- `missed_move_by_wait`
- `delayed_loss_after_wait`
- `neutral_wait`
- `insufficient_evidence`

### 3-1. better_entry_after_wait

의미:

- wait 뒤에 실제로 더 유리한 가격에서 same-side entry가 발생함
- 그리고 그 이후 결과가 최소 neutral 이상임

예:

- BUY를 기다렸는데 더 낮은 가격에서 들어감
- SELL을 기다렸는데 더 높은 가격에서 들어감

### 3-2. avoided_loss_by_wait

의미:

- wait 직후 시장이 반대 방향으로 크게 움직였음
- same-side 재진입은 없었거나, 진입하지 않은 것이 오히려 손실 회피로 해석됨

예:

- BUY 직전 wait했는데 가격이 아래로 강하게 밀림
- SELL 직전 wait했는데 가격이 위로 강하게 튐

### 3-3. missed_move_by_wait

의미:

- wait 직후 시장이 같은 방향으로 이미 유리하게 움직였음
- 그런데 더 좋은 재진입 기회는 없었고, 결국 기회를 놓친 형태

예:

- BUY를 기다렸는데 가격이 바로 위로 달려감
- SELL을 기다렸는데 가격이 바로 아래로 밀림

### 3-4. delayed_loss_after_wait

의미:

- wait 뒤에 same-side entry는 했지만 가격이 오히려 불리해졌음
- 그리고 그 뒤 trade outcome도 음수로 끝남

예:

- BUY를 기다렸다가 더 높은 가격에 들어가서 결국 손실
- SELL을 기다렸다가 더 낮은 가격에 들어가서 결국 손실

## 4. 입력 계약

새 owner의 최소 입력은 아래 네 묶음이다.

### 4-1. decision row

필수 항목:

- `symbol`
- `action`
- `entry_wait_selected`
- `entry_wait_state`
- `entry_wait_decision`
- `blocked_by`
- `observe_reason`
- `anchor_price`

여기서 `anchor_price`는 매우 중요하다.
이 값이 없으면 `좋은 기다림 / 나쁜 기다림`을 직접 계산할 수 없다.

### 4-2. future bars

wait 시점 이후의 가격 경로가 필요하다.

최소 항목:

- `time`
- `open`
- `high`
- `low`
- `close`

이 값으로 아래를 계산한다.

- favorable move
- adverse move
- best reentry improvement

### 4-3. next entry row

가능하면 같은 symbol, 같은 side의 다음 entry row가 있어야 한다.

최소 항목:

- `time`
- `action`
- `entry_fill_price`
- `outcome`

### 4-4. next closed trade row

다음 진입이 실제로 어떤 결과였는지도 필요하다.

최소 항목:

- `profit` 또는 `net_pnl_after_cost`
- `exit_reason`

## 5. 핵심 지표

### 5-1. favorable move ratio

wait 직후 시장이 원래 기대 방향으로 얼마나 움직였는가

- BUY: 이후 고점이 anchor보다 얼마나 위로 갔는가
- SELL: 이후 저점이 anchor보다 얼마나 아래로 갔는가

### 5-2. adverse move ratio

wait 직후 시장이 반대 방향으로 얼마나 움직였는가

- BUY: 이후 저점이 anchor보다 얼마나 아래로 갔는가
- SELL: 이후 고점이 anchor보다 얼마나 위로 갔는가

### 5-3. best reentry improvement ratio

wait 덕분에 얻을 수 있었던 최선의 가격 개선 폭

- BUY: anchor보다 얼마나 더 낮은 가격이 나왔는가
- SELL: anchor보다 얼마나 더 높은 가격이 나왔는가

### 5-4. entry price delta ratio

실제로 다음 진입 가격이 anchor 대비 좋아졌는지 나빠졌는지

- BUY: 더 낮으면 양수, 더 높으면 음수
- SELL: 더 높으면 양수, 더 낮으면 음수

## 6. 판정 순서

권장 판정 우선순위는 아래다.

1. `better_entry_after_wait`
2. `delayed_loss_after_wait`
3. `avoided_loss_by_wait`
4. `missed_move_by_wait`
5. `neutral_wait`
6. `insufficient_evidence`

이 순서가 필요한 이유는
실제 same-side 재진입과 그 결과가 있으면 그게 가장 직접적인 증거이기 때문이다.

즉 `다음 entry + 다음 trade outcome`이 있으면 그걸 우선 사용하고,
없으면 price path 기준 판정을 사용한다.

## 7. 상태와 점수

### label_status

- `VALID`
- `INSUFFICIENT_EVIDENCE`

### quality_score

권장 범위:

- `-1.0 ~ +1.0`

해석:

- 양수: wait가 유익했을 가능성이 큼
- 음수: wait가 해로웠을 가능성이 큼
- 0 부근: 혼합 또는 약한 신호

## 8. 왜 이 owner를 live 엔진과 분리해야 하나

이 owner는 사후 평가용이기 때문에 live 엔진과 분리해야 한다.

이유:

- 미래 바 정보가 필요하다
- 다음 entry 정보가 필요하다
- 다음 closed trade 결과가 필요하다
- 즉 live 시점에는 모를 정보가 들어간다

그래서 이 owner는 반드시
`shadow audit / replay / backfill / closed history enrichment`
쪽에 붙어야 한다.

## 9. 현재 추가된 코드 뼈대

이번 턴에서 추가된 파일:

- `backend/services/entry_wait_quality_audit.py`

들어 있는 것:

- context builder
- per-row evaluator
- summary builder
- markdown renderer

이 파일은 아직 live에 연결되지 않았다.
지금은 `owner와 contract를 먼저 세운 단계`다.

## 10. 이후 연결 포인트

### 10-1. replay / audit 단계

먼저 recent wait rows나 replay dataset에서
새 owner를 shadow-only로 돌린다.

### 10-2. closed history enrichment 단계

이후 closed history 또는 학습용 seed에 아래 컬럼을 추가한다.

- `entry_wait_quality_label`
- `entry_wait_quality_score`
- `entry_wait_quality_reason`

### 10-3. state25 / ML 단계

그 다음에야 아래 둘 중 하나로 연결한다.

- state25 feature로 넣기
- 별도 wait-quality auxiliary target으로 넣기

## 11. 지금 설계가 의도적으로 아직 하지 않는 것

이번 설계는 아직 아래를 하지 않는다.

- live entry 판단 수정
- wait state taxonomy 변경
- state25 기존 패턴 규칙 변경
- old exit wait quality 삭제

즉 지금은 `새 owner 추가`이고,
기존 엔진을 뒤집는 작업은 아니다.
