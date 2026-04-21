# Economic Learning Target Implementation Roadmap

## 목적

이 문서는 `state25`와 `wait quality` 다음 단계인 `AI2 경제적 학습 목표`를 어떻게 붙일지 정리한다.

핵심 질문은 이렇다.

- 어떤 라벨이 `맞췄다`보다 `돈이 됐다`에 더 직접 연결되는가
- 어떤 값은 feature가 아니라 target으로만 써야 leakage가 없는가
- 지금 당장 무엇을 seed/report에 먼저 붙여야 하는가

## 현재 상태

현재 closed history에는 이미 아래 값들이 존재한다.

- `profit`
- `signed_exit_score`
- `loss_quality_label / loss_quality_score`
- `wait_quality_label / wait_quality_score`
- `learning_entry_score`
- `learning_wait_score`
- `learning_exit_score`
- `learning_total_score`
- `learning_total_label`

즉 경제적 학습 목표를 위한 재료가 완전히 없는 상태는 아니다.
문제는 이 값들이 아직 `economic target contract`라는 이름으로 정리되어 있지 않고,
`state25 seed`와 `pilot baseline`에서 별도 축으로 잘 보이지 않았다는 점이다.

## AI2에서 먼저 잡는 메인 target

AI2 1차 구현은 아래처럼 잡는다.

### 1. primary economic target

- `learning_total_label`
- 값: `positive / neutral / negative`
- 의미:
  - entry, wait, exit, pnl을 합친 종합 경제적 outcome
  - 지금 단계에서 가장 간단하고 직접적으로 `돈이 됐는가`를 보기 좋은 target

### 2. secondary risk-control target

- `loss_quality_label`
- 값 예시: `non_loss / good_loss / neutral_loss / bad_loss`
- 의미:
  - 수익 그 자체보다 `손실을 얼마나 잘 제한했는가`
  - risk-control 품질을 따로 본다

### 3. secondary value-bucket target

- `economic_value_bucket_v1`
- source: `learning_total_score`
- 값:
  - `strong_positive`
  - `positive`
  - `neutral`
  - `negative`
  - `strong_negative`
- 의미:
  - `learning_total_label`보다 한 단계 더 세밀한 economic zone

## 왜 feature가 아니라 target인가

이 값들은 전부 trade가 끝난 뒤에 확정된다.

- `profit`
- `signed_exit_score`
- `loss_quality_label`
- `learning_total_label`

이걸 현재 시점 feature로 바로 넣으면 미래 결과가 현재 판단에 들어가므로 leakage다.

따라서 AI2의 원칙은 명확하다.

- 현재 시점 feature는 그대로 둔다
- 경제적 값은 `auxiliary target`으로만 먼저 쓴다
- 그다음 AI3/AI4에서 candidate compare와 promote gate에 활용한다

## 이번 구현 범위

이번 AI2 1차 구현은 아래까지만 한다.

1. `economic_target_summary_v1` 생성
2. `teacher_pattern_experiment_seed_report.py`에 economic summary 포함
3. `teacher_pattern_pilot_baseline_report.py`에 `economic_target_integration` 포함
4. `economic_total_task`를 auxiliary task로 연결

즉 이번 단계는 `실행 정책 반영`이 아니라
`경제적 target을 seed/report에서 공식 계약으로 보이게 만드는 단계`다.

## 보고서에서 이제 보게 되는 것

### seed report

- `economic_target_summary.coverage`
- `economic_target_summary.primary_target`
- `economic_target_summary.secondary_targets.loss_quality_label`
- `economic_target_summary.secondary_targets.economic_value_bucket_v1`

여기서 바로 볼 수 있다.

- economic target row가 몇 개인지
- class support가 어느 정도인지
- `positive / neutral / negative` 분포가 어떤지
- 손실 품질 분포가 어떤지

### pilot baseline report

- `economic_target_integration`
- `tasks.economic_total_task`

여기서 바로 볼 수 있다.

- 지금 economic auxiliary task를 열 수 있는지
- support가 충분한지
- 어떤 label이 supported인지
- sparse해서 아직 skip 상태인지

## 완료 기준

AI2 1차 구현 완료 기준은 아래다.

1. seed report에서 economic summary가 보인다
2. pilot baseline report에서 economic auxiliary readiness가 보인다
3. sparse해도 baseline 전체를 막지 않는다
4. support가 충분하면 `economic_total_task`가 실제로 열린다

## 다음 단계

AI2 다음 실무는 이 순서가 맞다.

1. `learning_total_label` 분포와 skew를 계속 본다
2. `economic_total_task`가 안정적으로 열리는지 본다
3. 필요하면 `loss_quality_label`도 별도 auxiliary task로 확장한다
4. 그 다음 `AI3 retrain / compare / promote`에서 economic metric을 비교축으로 넣는다

## 한 줄 요약

AI2는 새 수익 라벨을 무작정 더 만드는 단계가 아니라,
이미 있는 `learning_total / loss_quality / signed_exit_score`를
`경제적 학습 계약`으로 승격해서 seed와 baseline에서 공식적으로 다루기 시작하는 단계다.
