# PA4 Countertrend Topdown Exit Context Fast-Exit Bias Implementation Checklist

## Step 1. input contract 재확인

- [x] [exit_utility_input_contract.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_utility_input_contract.py) 에서 `countertrend_with_entry / prefer_fast_cut / topdown_state_label`가 이미 제공되는지 확인

## Step 2. config knob 추가

- [x] [config.py](/C:/Users/bhs33/Desktop/project/cfd/backend/core/config.py) 에 `EXIT_COUNTERTREND_TOPDOWN_*` knob 추가

## Step 3. scene bias 구현

- [x] [exit_utility_scene_bias_policy.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_utility_scene_bias_policy.py) 에 `countertrend_topdown_exit_pressure` flag 추가
- [x] lower-edge / opposite-edge / hold-bias 예외와 충돌하지 않도록 guard 추가

## Step 4. unit regression

- [x] [test_exit_utility_scene_bias_policy.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_exit_utility_scene_bias_policy.py) 에 direct policy test 추가
- [x] [test_wait_engine.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_wait_engine.py) 회귀 확인

## Step 5. runtime 반영

- [x] `main.py` 재기동
- [x] restart log 기록

## Step 6. baseline check

- [x] [product_acceptance_pa0_baseline_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/product_acceptance/product_acceptance_pa0_baseline_latest.json) 재생성
- [x] 이번 축은 immediate cleanup보다 future close bias라는 점 확인
