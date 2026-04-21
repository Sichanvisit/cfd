# Teacher-Label State25 Auto-Improvement Execution Roadmap

## 목적

이 문서는 `state25`와 `wait quality` 기반 시스템을
`그냥 라벨이 붙는 구조`에서
`데이터가 쌓일수록 더 나은 후보를 만들고, 검증하고, 안전하게 실운영에 반영하는 구조`
로 확장하기 위한 상위 로드맵이다.

쉽게 말하면 이 문서는 아래 질문에 답한다.

- 무엇이 남아 있어야 `자동으로 더 좋아지는 구조`가 되는가
- 무엇이 남아 있어야 `수익 개선`과 더 직접 연결되는가
- 어떤 순서로 붙여야 leakage 없이 안전하게 갈 수 있는가

## 현재까지 이미 된 것

현재까지 이미 확보된 기반은 아래와 같다.

- `micro-structure Top10` 구축 완료
- `teacher_pattern_* compact schema` 구축 완료
- `state25 rule-based labeler` 구축 완료
- `Step 8 labeling QA gate` 구축 완료
- bounded / richer backfill 구축 완료
- `Step 9 E1~E5` 측정/재확인 프레임 구축 완료
- `wait quality WQ1~WQ5` 기본 구현 완료
- old live ML 제거 완료
- guarded runtime recycle 기본 구현 완료

즉 지금은 `공사가 안 된 상태`가 아니라,
`자동 개선 구조로 넘어가기 직전의 기반`이 거의 마련된 상태다.

## 이 로드맵이 다루는 남은 큰 축 5개

이 문서는 아래 5개를 한 묶음의 상위 로드맵으로 본다.

1. `표본 더 쌓기`
2. `수익과 직접 연결된 학습 목표 만들기`
3. `state25 새 ML의 재학습-비교-승격 파이프라인`
4. `배포 게이트와 롤백`
5. `실행 정책 연결`

핵심 원칙은 간단하다.

- 먼저 `재료`
- 그다음 `돈과 연결된 목표`
- 그다음 `후보 생성`
- 그다음 `승격/보류 판단`
- 마지막에만 `실행 반영`

즉 `학습 -> 승격 -> 실행`의 마지막 고리를 단계적으로 붙이는 문서다.

## 왜 이 순서가 맞는가

이 다섯 개는 서로 독립이 아니다.

- 표본이 부족하면 학습 목표가 약해진다
- 학습 목표가 약하면 후보 비교가 무의미하다
- 후보 비교가 약하면 자동 승격이 위험하다
- 승격 게이트가 약하면 실운영 반영이 위험하다
- 실행 반영 없이 후보만 만들면 돈과 연결되지 않는다

즉 아래 순서가 자연스럽다.

1. `재료 확보`
2. `목표 정의`
3. `후보 생성`
4. `후보 평가와 승격 판단`
5. `실행 정책에 연결`

## 단계별 상위 로드맵

### AI1. Seed / Coverage Accumulation

목표:

- `state25` labeled seed를 `10K+` 수준까지 누적한다
- `wait quality` 표본도 auxiliary task가 실제로 열릴 만큼 누적한다
- `watchlist pair`, `rare pattern`, `runtime recycle`, `live accumulation`을 같이 본다

현재 상태:

- `state25 labeled_rows`는 약 `2.6K`
- `wait_quality target_rows`는 `3`
- `wait_quality_task`는 아직 `skipped`

이 단계에서 할 일:

- `teacher_pattern_step9_watch_report.py`로 state25 seed 상태 추적
- `entry_wait_quality_replay_report.py`로 wait-quality 판정 누적
- `backfill_entry_wait_quality_learning_seed.py`로 closed history enrichment 누적
- `teacher_pattern_pilot_baseline_report.py`에서 `wait_quality_integration.ready` 변화를 추적
- `fresh closed +100` 기준으로 재확인 루틴 유지

핵심 출력:

- `labeled_rows`
- `covered_primary_count`
- `supported_pattern_count`
- `entry_wait_quality_coverage.rows_with_entry_wait_quality`
- `wait_quality_integration.target_rows`
- `watchlist pair` 관측 여부

완료 기준:

- `state25 labeled_rows >= 10,000`
- `wait_quality`는 최소 2개 이상 class가 support threshold를 넘겨 `wait_quality_task.skipped = false`
- `E5` 재확인 조건 충족

주의:

- 이 단계는 손 놓고 기다리는 단계가 아니라
  `누적 + 감시 + 체크포인트 재평가` 단계다.

### AI2. Economic Learning Targets

기준 구현 문서:

- `docs/current_economic_learning_target_implementation_roadmap_ko.md`

목표:

- `맞췄는가`보다 `돈이 되는가`를 더 직접 반영하는 학습 목표를 만든다
- pattern/group 분류만이 아니라, 기대값과 손실 회피, 슬리피지/노이즈 비용을 학습 재료로 만든다

왜 필요한가:

- pattern을 잘 맞춰도 수익과 직접 연결되지 않을 수 있다
- 좋은 wait / 나쁜 wait 구분이 있어도 그게 실제 기대값 개선과 연결되지 않을 수 있다
- 결국 실운영에서는 `정답률`보다 `기대값`, `손실 회피`, `비용 회피`가 중요하다

권장 목표 축:

- `better_entry_after_wait` / `delayed_loss_after_wait` 같은 wait-quality auxiliary target
- `trade_ev_bucket` 같은 기대값 bucket
- `avoided_loss_signal` 같은 손실 회피 target
- `slippage_noise_risk` 같은 비용/노이즈 target

권장 순서:

1. 현재 있는 `entry_wait_quality_*`부터 auxiliary target으로 충분히 연다
2. 다음으로 `trade outcome`과 `execution cost`를 묶은 경제적 label을 만든다
3. 마지막으로 단일 score나 bucket summary로 합친다

핵심 출력:

- economic label schema
- label coverage report
- class support report
- baseline 대비 utility metric 비교

완료 기준:

- 최소 1개 이상의 `경제적 auxiliary target`이 seed report / baseline report에 같이 잡힌다
- 해당 target의 coverage와 support가 관찰 가능하다

주의:

- 미래 결과에서 만들어진 값을 현재 feature에 직접 넣으면 leakage다
- 먼저 `target`으로 만들고, 그 다음에만 downstream policy에 연결한다

### AI3. State25 Retrain / Compare / Promote Pipeline

기준 구현 문서:

- `docs/current_state25_retrain_compare_promote_design_ko.md`
- `docs/current_state25_retrain_compare_promote_implementation_roadmap_ko.md`

목표:

- 새 `state25` 기반 후보 모델을 자동으로 다시 학습하고,
  기존 기준선과 비교 가능한 형태로 만든다

왜 필요한가:

- 지금은 baseline을 수동으로 돌릴 수는 있지만
  `새 표본이 쌓일수록 자동으로 후보를 다시 만드는 루프`는 아직 완성되지 않았다

이 단계에서 만들 것:

- candidate training script
- candidate metrics artifact
- previous vs current compare report
- candidate registry 또는 bundle metadata
- 최소 승격 조건 판정기

권장 파이프라인:

1. seed snapshot freeze
2. candidate retrain
3. metrics + confusion + utility compare
4. promote candidate only if gate passes
5. otherwise keep current candidate or hold

핵심 비교 항목:

- pattern/group macro F1
- watchlist pair confusion
- wait-quality auxiliary 성능
- symbol별 bias
- utility metric
- data coverage delta

완료 기준:

- `후보 모델 재학습 -> 메트릭 생성 -> 이전 후보와 비교`가 명령 1개나 스케줄 1개로 반복 가능하다
- candidate bundle에 version, seed snapshot, metrics가 남는다

주의:

- old ML처럼 별도 재학습 루프가 live runtime과 뒤엉키면 안 된다
- 후보 생성은 `offline candidate loop`로 먼저 분리해야 한다

### AI4. Promotion Gate / Rollback

기초 구현 문서:

- `docs/current_state25_promotion_gate_rollback_design_ko.md`
- `docs/current_state25_promotion_gate_rollback_implementation_roadmap_ko.md`

목표:

- 아무 후보 모델이나 live에 올리지 않도록,
  `보류 / 승격 / 롤백`을 자동 판단하는 게이트를 만든다

왜 필요한가:

- 자동 학습만 있고 자동 승격 판단이 없으면
  성능이 나쁜 후보도 실운영에 들어갈 수 있다

필수 단계:

1. offline compare
2. `log_only` 또는 shadow
3. small canary
4. promote or hold
5. rollback if degraded

승격 판단 예시:

- pattern/group baseline이 기준 이상
- wait-quality auxiliary가 최소한 악화되지 않음
- watchlist confusion이 악화되지 않음
- utility metric이 유지 또는 개선
- symbol skew가 비정상적으로 커지지 않음

롤백 조건 예시:

- canary에서 blocked/wait drift가 비정상 증가
- utility metric 악화
- 특정 symbol만 과도하게 몰림
- false release / bad exit가 급증

완료 기준:

- 후보가 `promote_ready / hold / rollback` 중 어디인지 자동으로 요약된다
- canary 실패 시 이전 안정 버전으로 되돌릴 수 있다

주의:

- 이 단계 전까지는 execution bias를 직접 건드리지 않는다
- 먼저 `올려도 되는 후보인지`만 판단해야 한다

### AI5. Execution Policy Integration

기초 구현 문서:

- `docs/current_state25_execution_policy_integration_design_ko.md`
- `docs/current_state25_execution_policy_integration_implementation_roadmap_ko.md`

목표:

- 모델 출력이 실제로 `entry / wait / skip / sizing / risk`를 바꾸게 한다
- 여기까지 가야 비로소 `돈을 벌어오는 구조 개선`과 직접 연결된다

권장 연결 방식:

- action gate threshold 조정
- wait / skip policy 조정
- spread / slippage / noise 회피 가중
- position size 또는 risk band 조정
- bad wait 감소 / good wait 유지 방향의 policy modifier

권장 rollout:

1. read-only recommendation
2. log-only comparison
3. narrow canary
4. bounded live action
5. broader rollout

핵심 출력:

- policy recommendation report
- pre/post execution compare
- live canary metrics
- rollback-safe config surface

완료 기준:

- 최소 한 가지 execution 축이 state25 candidate output과 연결된다
- 그 변경이 canary에서 추적 가능하다
- degraded면 rollback 가능하다

주의:

- execution 연결은 마지막 단계다
- pattern 분류만 좋아졌다고 바로 live gate를 바꾸면 안 된다

## 권장 전체 순서

위 5개를 실제로 진행할 때는 아래 순서가 가장 자연스럽다.

1. `AI1 Seed / Coverage Accumulation`
2. `AI2 Economic Learning Targets`
3. `AI3 Retrain / Compare / Promote Pipeline`
4. `AI4 Promotion Gate / Rollback`
5. `AI5 Execution Policy Integration`

즉:

- 먼저 더 쌓고
- 돈과 연결된 target을 만들고
- 후보를 자동으로 다시 만들고
- 올릴지 말지 판단하고
- 마지막에만 실제 실행에 연결한다

## 지금 기준으로 어디까지 와 있나

현재 위치를 한 줄로 요약하면 아래와 같다.

- `AI1`은 진행 중
- `AI2`는 초입 진입 완료
- `AI3~AI5`는 아직 본격 미착수

조금 더 풀면:

- `state25 seed / Step 9 watch`는 이미 운영 중
- `wait quality WQ1~WQ5`로 `AI2`의 첫 재료는 생김
- `pilot baseline`에도 `wait_quality_integration`이 붙음
- 그러나 `wait_quality_task`는 아직 표본 부족으로 열리지 않음
- candidate retrain / compare / promote 루프는 아직 없다
- live 승격 게이트와 rollback 루프도 아직 없다
- execution policy를 state25 candidate output에 묶는 단계도 아직 없다

## 추천 체크포인트

이 상위 로드맵은 아래 체크포인트로 운용하는 것이 좋다.

### 체크포인트 A

- `state25 labeled_rows`
- `wait_quality target_rows`
- `watchlist pair`
- `runtime recycle log_only`

질문:

- 재료가 충분히 쌓이고 있는가

### 체크포인트 B

- `economic auxiliary target` coverage
- baseline report의 `wait_quality_integration`

질문:

- 돈과 연결된 target이 실제로 학습 가능한가

### 체크포인트 C

- candidate vs previous compare
- confusion / utility / skew

질문:

- 새 후보가 진짜 더 나은가

### 체크포인트 D

- shadow/log-only/canary 결과

질문:

- 실운영에 올려도 안전한가

### 체크포인트 E

- pre/post execution metric
- rollback 여부

질문:

- 실제 돈을 더 버는 구조에 가까워졌는가

## 관련 문서

- [state25 current handoff](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_state25_current_handoff_ko.md)
- [state25 experiment tuning roadmap](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_state25_experiment_tuning_roadmap_ko.md)
- [wait quality learning roadmap](/C:/Users/bhs33/Desktop/project/cfd/docs/current_wait_quality_learning_implementation_roadmap_ko.md)
- [runtime recycle operating note](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_state25_runtime_recycle_operating_note_ko.md)

## 최종 결론

지금 남은 것은 단순히 `데이터를 더 쌓자`만이 아니다.

정확히는 아래 3단계가 남아 있다.

1. `재료를 더 쌓고`
2. `돈과 연결된 target을 만들고`
3. `후보 생성 -> 승격 판단 -> 실행 반영`의 마지막 고리를 붙인다

즉 이 문서의 요지는 아래 한 줄이다.

`state25 기반 시스템을 자동 개선 구조로 만들려면, 이제부터는 seed 누적 위에 economic target, retrain/promotion gate, execution integration을 차례대로 붙여야 한다.`
