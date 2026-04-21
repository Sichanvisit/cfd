# State25 Log-Only vs Canary/Live Readiness Split Implementation Roadmap

## 목표

이 문서는 readiness split을 코드에 어떻게 반영하는지 작업 순서로 정리한다.

## RS1. Step9 Summary Split

할 일:

- blocker code를 `soft`와 `critical`로 나눈다
- `log_only_gate_ready`를 계산한다
- `execution_handoff_ready`는 기존처럼 full gate로 유지한다

완료 기준:

- Step9 summary 안에 `soft_blocker_codes`, `critical_blocker_codes`, `log_only_gate_ready`가 보인다

## RS2. AI4 Gate Split

할 일:

- `critical blocker`가 남으면 `hold_step9`
- `soft blocker`만 남으면 `log_only_ready`
- canary evidence가 부족해도 `log_only_ready`로 유지

완료 기준:

- AI4가 `log_only_ready`를 실제로 출력한다

## RS3. AI5 Integration Split

할 일:

- `gate_stage = log_only_ready`일 때도 `log_only_candidate_bind_ready`를 허용한다
- threshold/size는 log_only 가능
- canary/live 관련 rollout flag는 여전히 false로 둔다

완료 기준:

- AI5가 `recommended_rollout_mode = log_only`를 출력한다
- `narrow_canary_after_log_only`는 full promote 전까지 false다

## RS4. AI6 Controller Split

할 일:

- AI6가 `log_only_ready`도 promote-log-only 후보로 본다
- 다만 적용은 여전히 dry-run 기본이다

완료 기준:

- AI6가 `promote_log_only_ready`를 출력할 수 있다

## RS5. Human Report

할 일:

- candidate watch md에 새 stage가 보이게 한다
- 최신 AI6 리포트에서도 blocker 해석이 바뀐 것을 확인한다

완료 기준:

- 사람은 md만 보고도 지금이 `log_only만 가능한지`, `canary/live까지 가능한지` 알 수 있다

## 이번 변경으로 기대하는 것

- Step9가 `seed shortfall` 때문에 완전히 막혀도 log_only는 더 자주 열린다
- 대신 canary/live는 여전히 엄격하게 유지된다

즉 `항상 readiness를 열어두는 것`이 아니라 `낮은 단계 readiness를 먼저 열어두는 것`이 이번 목표다.
