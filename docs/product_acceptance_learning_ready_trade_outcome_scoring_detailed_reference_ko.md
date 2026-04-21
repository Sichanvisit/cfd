# Product Acceptance Learning-Ready Trade Outcome Scoring Detailed Reference

## goal

- 실제 `진입 / 기다림 / 청산` 결과를 한 줄의 closed trade에서 바로 학습 가능하게 만들기
- rule tuning 이전에 `real trade outcome -> score -> later trainer/ML` 루프를 확보

## existing building blocks

- `entry_score`
- `signed_exit_score`
- `loss_quality_score`
- `wait_quality_score`
- `decision_reason`

## added surface

- `learning_entry_score`
- `learning_wait_score`
- `learning_exit_score`
- `learning_total_score`
- `learning_total_label`

## interpretation

- `entry`: 진입 당시 edge
- `wait`: 기다림 품질
- `exit`: 최종 청산 품질과 실현 손익
- `total`: 이후 학습에 바로 투입 가능한 통합 reward
