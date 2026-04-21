# PA4 Countertrend No-Green Fast-Cut Implementation Checklist

## Step 1. target family 고정

- [x] `TopDown-only Exit Context + peak=0 + bad_loss` family를 next PA4 residue로 확정

## Step 2. config knob 추가

- [x] [config.py](/C:/Users/bhs33/Desktop/project/cfd/backend/core/config.py)에 `EXIT_COUNTERTREND_NO_GREEN_*` 추가

## Step 3. recovery gating 구현

- [x] [exit_recovery_utility_bundle.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_recovery_utility_bundle.py)에 `countertrend_no_green_fast_cut` 추가
- [x] 해당 조건에서 `wait_be / wait_tp1`를 disable 하도록 구현

## Step 4. regression

- [x] [test_exit_recovery_utility_bundle.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_exit_recovery_utility_bundle.py) direct test 추가
- [x] [test_wait_engine.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_wait_engine.py) 회귀 확인

## Step 5. runtime 반영

- [x] `main.py` 재기동
- [x] restart log 기록

## Step 6. refreeze

- [x] [product_acceptance_pa0_baseline_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/product_acceptance/product_acceptance_pa0_baseline_latest.json) 재생성
- [x] 이번 축은 `future close bias`라 immediate queue drop이 아닌 점 확인
