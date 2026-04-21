# Teacher-Label State25 Experiment Tuning Roadmap

## 목적

이 문서는 `teacher-state 25` 라벨이 compact dataset에 붙은 이후,
무엇을 어떤 순서로 실험하고 조정할지를 정리한 로드맵이다.

핵심 원칙은 두 가지다.

- 라벨링 기준과 QA 기준은 먼저 고정한다.
- threshold, split, weighting, baseline, execution 반영은 실험 단계에서 조정한다.

즉 이 문서는 `실행 룰 변경` 문서가 아니라
`실험/검증/튜닝` 문서다.

## 전제

이 로드맵은 아래 전제가 충족된 뒤에 진행한다.

- Step 8 labeling QA gate가 동작한다.
- `teacher_pattern_*` compact schema가 실제 row에 붙는다.
- bounded backfill 또는 runtime accumulation으로 labeled seed가 확보된다.

참고 문서:

- [product_acceptance_teacher_label_state25_labeling_qa_detailed_reference_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_state25_labeling_qa_detailed_reference_ko.md)
- [product_acceptance_teacher_label_state25_threshold_calibration_detailed_reference_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_state25_threshold_calibration_detailed_reference_ko.md)
- [product_acceptance_teacher_label_state25_step9_asset_calibration_detailed_reference_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_state25_step9_asset_calibration_detailed_reference_ko.md)
- [product_acceptance_teacher_label_state25_step9_full_labeling_qa_detailed_reference_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_state25_step9_full_labeling_qa_detailed_reference_ko.md)

## 운영 해석 원칙

이 로드맵은 시장 불균형을 전제로 한다.

- 조용한 장과 압축장은 자주 나온다.
- 발작장, 원웨이장, 희귀 반전장은 드물다.
- 따라서 `25개 패턴을 균등 빈도`로 맞추는 것이 목표는 아니다.

즉 `group skew`나 `rare pattern scarcity`는
즉시 실패 사유가 아니라,
실험 단계에서 보정해야 할 시장 현실 정보로 본다.

## 불균형 대응 원칙

- `group skew`는 관찰 지표로 기록한다.
- `rare pattern`은 장기 누적과 별도 buffer 관리 대상으로 본다.
- pilot baseline에서는 class weight를 기본으로 사용한다.
- split과 sampling은 stratified 원칙을 우선한다.
- compact labeled row는 누적 유지하고, raw는 주기적으로 purge해도 된다.
- execution 반영 전까지는 rolling window 운영을 유지한다.

## Step E1. 1K seed asset calibration

목표:

- BTC / XAU / NAS seed의 자산별 분포와 flatness를 먼저 확인한다.
- `entry_atr_ratio`, `regime_volatility_ratio`, `micro_*` payload가 seed에서 살아 있는지 본다.

핵심 출력:

- 자산별 labeled row 수
- 자산별 group distribution
- 자산별 primary pattern distribution
- 자산별 confidence summary
- 자산별 flatness / skew 경고

조정 후보:

- ATR multiplier
- `VB >= 1.8 / 2.5 / 3.0` 경계
- `C >= 0.70 / 0.75` 경계

참고 문서:

- [product_acceptance_teacher_label_state25_step9_asset_calibration_detailed_reference_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_state25_step9_asset_calibration_detailed_reference_ko.md)

## Step E2. full labeling QA

목표:

- 현재 labeled seed가 어디에 치우쳐 있는지 정량적으로 본다.
- 25개 전체 coverage와 missing/rare 패턴을 확인한다.
- primary-secondary pair를 confusion proxy로 먼저 본다.

핵심 출력:

- labeled row 수와 shortfall
- 25개 primary/secondary 분포
- covered primary count / missing primary ids / rare primary ids
- group distribution
- symbol별 top pattern / group skew
- watchlist pair(`12-23`, `5-10`, `2-16`)
- pair concentration 경고

해석 원칙:

- 현재 seed가 `25개 전체 완성용`이 아닐 수 있어도 괜찮다.
- 다만 pilot baseline 전에 skew를 숫자로 알고 들어가야 한다.

참고 문서:

- [product_acceptance_teacher_label_state25_step9_full_labeling_qa_detailed_reference_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_state25_step9_full_labeling_qa_detailed_reference_ko.md)

## Step E3. pilot baseline model

목표:

- 현재 seed로 작은 baseline을 먼저 돌려
  라벨 품질과 파이프라인이 학습 가능한지 확인한다.

권장 시작:

- XGBoost 또는 유사한 트리 기반 baseline

핵심 지표:

- macro F1
- pattern-wise recall
- 상위 confusion pair precision / recall
- group-level precision / recall

주의:

- 단일 `F1` 숫자만으로 execution 전환을 결정하지 않는다.
- 현재 seed가 skew되어 있으면 class weight를 기본으로 사용한다.

## Step E4. top confusion pair tuning

목표:

- confusion 상위 3쌍만 먼저 조정한다.

예상 watchlist:

- `12 ↔ 23`
- `5 ↔ 10`
- `16 ↔ 2`

방법:

- threshold 조정
- secondary 허용 조건 조정
- 구조 확인 조건 강화 또는 완화

주의:

- 현재 seed에서 watchlist pair가 거의 없으면,
  이 단계는 `관찰`이 먼저고 `조정`은 뒤로 미룬다.

## Step E5. execution handoff gate

목표:

- teacher-label quality와 pilot/baseline 결과가 충분히 안정된 뒤에만
  execution 반영 여부를 판단한다.

이 단계에서만 논의할 것:

- execution bias 조정
- action gate 조정
- 실제 live decision 반영 범위

즉 execution은 마지막 단계다.

참고 문서:

- [product_acceptance_teacher_label_state25_step9_execution_handoff_gate_detailed_reference_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_state25_step9_execution_handoff_gate_detailed_reference_ko.md)
- [product_acceptance_teacher_label_state25_step9_execution_handoff_gate_implementation_checklist_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_state25_step9_execution_handoff_gate_implementation_checklist_ko.md)
- [product_acceptance_teacher_label_state25_step9_execution_handoff_gate_implementation_memo_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_state25_step9_execution_handoff_gate_implementation_memo_ko.md)

## 현재 seed에 대한 해석

현재 `2K+` seed는 다음 용도로는 충분하다.

- pipeline sanity check
- 라벨러 초기 품질 점검
- pilot baseline
- bias/confidence/provenance 검토

반대로 아래 용도에는 아직 이르다.

- 25개 전체 coverage 기반 최종 baseline
- 희귀 패턴 포함 confusion 튜닝
- execution handoff 최종 판단

따라서 현재 로드맵 해석은 다음과 같다.

1. `E1/E2`는 지금 seed로 바로 진행
2. `E3`는 pilot baseline부터 시작
3. labeled row를 계속 누적
4. `E4/E5`는 coverage가 더 늘어난 뒤 본격 진행

## 결론

앞으로의 순서는 아래처럼 간다.

1. QA 고정
2. seed asset calibration
3. full labeling QA
4. pilot baseline
5. top confusion pair tuning
6. execution handoff

즉 `문서 고정 -> 현재 seed 측정 -> pilot baseline -> 누적 관찰 -> confusion 미세조정 -> execution 반영`의 순서가 맞다.

## 현재 E4/E5 재확인 기준

현재 `E4`와 `E5`는 매번 즉시 다시 돌리는 단계가 아니라,
`labeled row`와 `fresh close`가 더 쌓였을 때 재실행하는 watch 항목으로 둔다.

현재는 `coverage / support 확장`보다 `10K labeled seed 누적`, `watchlist pair 관찰`,
`E5 재확인 타이밍 관리`가 메인이다.

이미 충족된 milestone:

- `labeled row 2500+`
- `covered_primary_count 8+`
- `supported_pattern_ids` 증가와 `supported pattern count 6+`

재확인 트리거는 아래 중 하나다.

- fresh closed row가 직전 확인 대비 `+100` 이상 증가
- watchlist pair `12-23`, `5-10`, `2-16` 중 하나라도 `0 -> positive count`로 전환
- execution handoff blocker set이 변함
- `teacher_pattern_step9_watch_report.py` 기준 `recheck_now`가 켜짐

같이 볼 운영 watch 항목은 아래와 같다.

- `runtime recycle`은 먼저 `log_only` 한 사이클을 관찰한다
- `runtime_recycle.last_reason`, `last_block_reason`, `log_only_count`로 due/blocked 흐름을 확인한다
- 한 사이클 관찰 전에는 `RUNTIME_RECYCLE_MODE=reexec` 전환을 보류한다

즉 현재 `NOT_READY`는 실패라기보다, handoff 판단을 더 미루는 상태로 해석한다.
현재 직접 blocker가 사실상 `full_qa_seed_shortfall` 1개인지 함께 확인한다.

운영 순서는 아래처럼 둔다.

1. runtime accumulation 지속
2. 필요 시 bounded backfill / relabel
3. `teacher_pattern_step9_watch_report.py`로 seed / watchlist / blocker 변화 확인
4. 위 트리거 충족 시 `E4 confusion` 재실행
5. 직후 `E5 handoff` 재판정
6. 병렬로 `runtime recycle log_only` 한 사이클 관찰
7. 그 외 시간에는 독립 작업(예: housekeeping, 문서 보강, 수동 tag 관찰) 진행
