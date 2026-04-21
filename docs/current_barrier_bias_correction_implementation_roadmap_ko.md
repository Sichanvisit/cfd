# Barrier Bias Correction Implementation Roadmap

## 목적

이 문서는 `BCE0~BCE7` 다음 단계로,
Barrier bias correction을 실제 구현 순서로 쪼갠 로드맵이다.

이 단계의 목표는 coverage를 무작정 늘리는 것이 아니라,
이미 살아난 coverage가 아래 편향으로 왜곡되는 것을 줄이는 것이다.

- `avoided_loss` 과대표집
- `missed_profit / overblock / correct_wait / relief` 저활성
- `observe_only` 과대 정규화
- reducible skip과 irreducible skip 혼재

## 전제

- `BR0~BR6` complete
- `BCE0~BCE7` complete
- runtime heartbeat healthy
- current blocker is interpretation quality, not missing bridge wiring

## 운영 원칙

1. readiness threshold를 먼저 낮추지 않는다
2. compare/gate는 계속 `strict_only`
3. weak row는 baseline/diagnostic 쪽 확장에만 우선 사용
4. `max_positions` pre-context skip은 barrier 품질 분모에서 계속 제외
5. capacity policy audit은 전체 `07` 정리 때 별도 축으로 포함

## BCE8. Bias Baseline Report

목표:

- current barrier label/cost/drift 분포를 bias correction 시작점으로 고정한다

출력:

- `barrier_bias_baseline_report.json`
- `barrier_bias_baseline_report.md`

## BCE9. Missed-Profit / Overblock / Correct-Wait / Relief Recovery

목표:

- `avoided_loss`로 과흡수되는 row를 되돌려 label distribution bias를 줄인다

해야 할 일:

- `missed_profit_strict / missed_profit_weak` 분리
- `correct_wait` 우선 규칙 재점검
- `overblock` 경계용 보조 필드 도입 검토
- `relief_success / relief_failure` weak diagnostics surface 보강
- ambiguous-cost weak promotion rule 검토

## BCE10. Action Normalization Refinement

목표:

- `wait_or_block -> observe_only` drift를 coarse bucket artifact와 실제 철학 충돌로 분리한다

해야 할 일:

- `observe_only` 세분화
- drift pair 재정의
- negative mismatch 분해

## BCE11. Reducible / Irreducible Skip Split

목표:

- 남아 있는 skip이 “줄여야 하는 skip”인지 “남겨야 하는 skip”인지 분리한다

해야 할 일:

- reducible skip taxonomy 고정
- irreducible skip taxonomy 고정
- report에 two-bucket skip surface 추가

## BCE12. Readiness Sensitivity Review

목표:

- threshold를 낮추기 전에 blocker가 진짜 coverage/bias 문제인지 sensitivity로 확인한다

해야 할 일:

- current thresholds vs actual metrics table
- +/- sensitivity check
- blocker 제거까지 필요한 추가 row 또는 refinement 추정

## 추천 구현 순서

1. `BCE8 Bias Baseline Report`
2. `BCE9 Missed-Profit / Overblock / Correct-Wait / Relief Recovery`
3. `BCE10 Action Normalization Refinement`
4. `BCE11 Reducible / Irreducible Skip Split`
5. `BCE12 Readiness Sensitivity Review`
6. `BCE13 Wait-Family Diagnostic Overlay`
7. `BCE14 Manual Good-Wait Teacher Truth Layer`
8. `BCE15 Episode-Centric Manual Truth Transition`
9. `BCE16 Manual vs Heuristic Comparison Report`

## BCE13. Wait-Family Diagnostic Overlay

목표:

- `correct_wait`를 무리하게 완화하지 않고, 기다림의 성격을 별도 진단 계층으로 적재한다.

해야 할 일:

- `wait_outcome_family / wait_outcome_subtype / wait_outcome_usage_bucket` 필드 추가
- 기존 군집을 wait-family로 매핑
  - `missed_profit_leaning`
  - `zero_entry_gain_no_continuation`
  - `small_continuation_avoided_loss`
- report에 family/subtype 분포, barrier-label별 wait-family 분포 추가
- markdown/CLI 요약에도 wait-family surface 노출

운영 원칙:

- Barrier main label은 유지
- wait-family는 초기엔 `diagnostic/usable` 중심
- compare/gate hard decision에는 바로 섞지 않음

## 중단 조건

- `weak`만 늘고 `strict`가 전혀 늘지 않음
- `overblock_ratio`가 급상승함
- `counterfactual_cost_delta_r_mean`이 급격히 악화됨
- drift mismatch가 refinement 후에도 더 나빠짐
- readiness blocker가 coverage가 아니라 runtime instability로 바뀜

## 다음 단계

1. barrier readiness 재판정
2. 필요 시 capacity policy audit 메모 연결
3. `Evidence` owner spec / rollout 착수

## 참조 문서

- [current_barrier_bias_correction_checklist_v1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_barrier_bias_correction_checklist_v1_ko.md)
- [current_barrier_coverage_engineering_design_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_barrier_coverage_engineering_design_ko.md)
- [current_barrier_coverage_engineering_implementation_roadmap_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_barrier_coverage_engineering_implementation_roadmap_ko.md)
- [current_wait_family_label_structure_v1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_wait_family_label_structure_v1_ko.md)
- [current_manual_wait_teacher_truth_spec_v1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_manual_wait_teacher_truth_spec_v1_ko.md)

## BCE15. Episode-Centric Manual Truth Transition

紐⑺몴:

- `manual_wait_teacher`瑜?踰꾨━吏 ?딄퀬, `trade episode` ?⑥쐞 truth 濡쒕줈 ?볥뵧??entry / wait / exit媛 媛숈? anchor濡?臾띿씠寃??섎뒗??

?댁빞 ????

- storage = `episode-first`
- operations = `wait-first`
- current `manual_wait_teacher` = first operational truth channel
- `ideal_entry_*` / `ideal_exit_*` = first-class truth coordinates
- `manual_entry_teacher_*` / `manual_exit_teacher_*` = nullable truth candidates
- importer v1 = wait-only backfill
- importer v2/v3 = entry / exit owner媛 ?대━硫??⑥닔 ?뺤옣

異쒕젰:

- episode-centric truth spec
- episode-centric implementation roadmap
- importer stage split (`v1 wait-only`, `v2 entry`, `v3 exit`)

李몄“:

- [current_manual_trade_episode_truth_model_v1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_manual_trade_episode_truth_model_v1_ko.md)

## BCE16. Manual vs Heuristic Comparison Report

Goal:

- treat the current manual truth corpus as an answer key above the heuristic barrier layer
- compare manual truth against barrier / wait-family interpretation episode by episode
- turn manual truth into a practical calibration and bias-correction surface

Current interpretation:

- manual truth = standalone teacher corpus
- closed-history matching = optional secondary path
- first-class next output = comparison report, not replay reconstruction

Deliverables:

- `current_manual_vs_heuristic_comparison_report_template_v1_ko.md`
- `data/manual_annotations/manual_vs_heuristic_comparison_template.csv`
- first comparison pass for the current manual corpus

Reference:

- [current_manual_vs_heuristic_comparison_report_template_v1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_manual_vs_heuristic_comparison_report_template_v1_ko.md)

## BCE14. Manual Good-Wait Teacher Truth Layer

紐⑺몴:

- heuristic `correct_wait`瑜?臾대━?섍쾶 ?섎━吏 ?딄퀬, ?ъ슜?먭? 李⑦듃?먯꽌 吏곸젒 ?쒖떆??`醫뗭? wait / 以묐┰ wait / ?섏걶 wait` truth瑜?蹂꾨룄 layer濡?怨좎젙?쒕떎.

?댁빞 ????

- `manual_wait_teacher_annotation_schema.py`濡?怨듭떇 ?섎룞 label 媛먯뭅 ?ㅽ궎留??붾떎
- `manual_wait_teacher_annotations.template.csv`濡?珥덇린 ?쒗뵆由삽쓣 ?쒓났?쒕떎
- 珥덇린 truth? `box/range regime` ?쒕낯?먯꽌留?留뚮뱺??
- Barrier main label??wait-family overlay??洹몃?濡??붾뒗??manual truth??洹?위???곷떒????layer濡?異붽??댁뼱媛꾨떎
- compare/gate?먮뒗 諛붾줈 ?ｌ? ?딅뒗??report/diagnostic/teacher review?먮쭔 ?좏??쒕떎

怨듭떇 label:

- `good_wait_better_entry`
- `good_wait_protective_exit`
- `good_wait_reversal_escape`
- `neutral_wait_small_value`
- `bad_wait_missed_move`
- `bad_wait_no_timing_edge`
