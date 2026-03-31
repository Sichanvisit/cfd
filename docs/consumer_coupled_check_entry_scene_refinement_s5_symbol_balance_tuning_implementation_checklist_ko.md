# Consumer-Coupled Check / Entry Scene Refinement
## S5. Symbol Balance Tuning Implementation Checklist

### 목표

`BTCUSD / NAS100 / XAUUSD`의 recent scene family 노출 밀도와
stage/display 체감을 더 자연스럽게 맞춘다.

### 현재 상태

- `S0 ~ S4`: 완료
- `S5`: 구현/재관측 완료
- 다음 active step: `S6 acceptance`

### 진행 상태 요약

- `Step 1`: 완료
- `Step 2`: 완료
- `Step 3`: 완료
- `Step 4`: 완료
- `Step 5`: 완료
- `Step 6`: 완료
- `Step 7`: 완료
- `Step 8`: 완료
- `Step 9`: 완료

## Step 1. Baseline Snapshot Freeze

### 해야 할 일

- recent window 기준으로 tri-symbol latest 상태를 고정한다

### 확인 항목

- symbol별 `observe_reason`
- `blocked_by`
- `action_none_reason`
- `consumer_check_stage`
- `display_score`
- `display_repeat_count`

### 완료 기준

- S5 직전 baseline이 얼려진다

## Step 2. BTC Probe Density Casebook

### 해야 할 일

- `BTC lower_rebound_probe_observe` family를 recent row 기준으로 정리한다

### 핵심 질문

- 지금 `PROBE`가 너무 많은가
- `OBSERVE`로 낮추는 게 맞는가
- cadence suppression만으로 충분한가

### 완료 기준

- BTC tuning candidate가 정리된다

## Step 3. NAS Balance Casebook

### 해야 할 일

- `NAS lower rebound family`와 `outer_band structural family`를 같이 본다

### 핵심 질문

- lower rebound family가 너무 죽었는가
- structural observe가 상대적으로 너무 많이 보이는가
- reopen이 필요한가, 아니면 structural reduce가 필요한가

### 완료 기준

- NAS tuning candidate가 정리된다

## Step 4. XAU Multi-Family Balance Casebook

### 해야 할 일

- `upper reject / middle anchor / outer band` family를 recent row로 정리한다

### 핵심 질문

- 특정 family가 과도하게 지배적인가
- reconciliation 이후 upper reject family는 충분히 맞아졌는가
- middle anchor cadence는 추가 감소가 필요한가

### 완료 기준

- XAU tuning candidate가 정리된다

## Step 5. Least-Invasive Rule Selection

### 해야 할 일

- family별 후보를 `hide / downgrade / reduce / reopen`으로 분류한다

### 우선순위

1. repeat 감소
2. stage downgrade
3. cadence suppression
4. selective reopen
5. hide

### 완료 기준

- 가장 작은 수정으로 갈 candidate rule이 정해진다

## Step 6. Code Implementation

### 해야 할 일

- owner 파일에 symbol balance rule을 반영한다

### 주 대상 파일

- `backend/services/consumer_check_state.py`
- `backend/services/entry_service.py`
- `backend/services/entry_try_open_entry.py`
- 필요 시 `backend/trading/chart_painter.py`

### 완료 기준

- 선택된 rule이 코드에 반영된다

## Step 7. Regression Test

### 해야 할 일

- symbol balance 관련 regression을 테스트로 잠근다

### 우선 대상

- `tests/unit/test_consumer_check_state.py`
- `tests/unit/test_entry_service_guards.py`
- `tests/unit/test_chart_painter.py`
- `tests/unit/test_entry_try_open_entry_probe.py`

### 완료 기준

- balance tuning regression이 테스트에 추가된다

## Step 8. Runtime Re-Observe

### 해야 할 일

- 재시작 후 tri-symbol recent row를 다시 본다

### 확인 포인트

- BTC probe density 감소
- NAS family balance 개선
- XAU family balance 개선

### 완료 기준

- tuning이 runtime recent window에 실제 반영된다

## Step 9. Reconfirm Memo 작성

### 해야 할 일

- S5 변경 결과를 memo 문서로 정리한다

### 필수 섹션

- changed family rule
- expected effect
- runtime result
- residual issue

### 완료 기준

- 다음 단계가 바로 이어질 수 있다

## S5 완료 조건

아래가 충족되면 S5를 완료로 본다.

- tri-symbol balance candidate가 정리됐다
- least-invasive rule이 선택됐다
- 코드에 반영됐다
- regression test가 있다
- runtime re-observe가 됐다
- reconfirm memo가 있다
