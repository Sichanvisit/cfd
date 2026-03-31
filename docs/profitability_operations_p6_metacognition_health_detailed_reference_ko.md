# Profitability / Operations P6 Meta-Cognition / Health / Drift / Sizing Detailed Reference

작성일: 2026-03-30 (KST)

## 1. 목적

이 문서는 `P6 meta-cognition / health / drift / sizing`이 무엇인지, 왜 필요한지, 어떤 입력을 기반으로 advisory surface를 구성해야 하는지 고정하기 위한 상세 기준 문서다.

P6의 핵심 질문은 하나다.

`지금 이 시스템이 어디에서 건강하고, 어디에서 약해졌으며, 사이징을 얼마나 보수적으로 봐야 하는가?`

## 2. 왜 P6가 필요한가

P5까지 오면 이미 아래가 가능하다.

- 어떤 scene이 worst candidate인지
- 어떤 scene이 strength candidate인지
- 어떤 tuning candidate type이 우세한지

하지만 아직 시스템이 자기 상태를 요약해서 말해주지는 않는다.

운영 관점에서는 아래 질문이 남는다.

- 지금 XAUUSD는 건강한가, 스트레스 상태인가
- 어떤 setup family가 지금 약해지고 있는가
- 최근 악화는 drift로 볼 수 있는가
- sizing을 그대로 둘지, 줄일지, 약간 키울지

P6는 바로 이 질문에 답하는 첫 advisory layer다.

## 3. P6가 아닌 것

P6는 아직 자동 적응 단계가 아니다.

- live sizing을 자동으로 바꾸지 않는다
- threshold를 자동으로 재설정하지 않는다
- rule weight를 자동으로 수정하지 않는다

즉 P6는 `시스템 자기 상태에 대한 advisory surface`다.

## 4. P6 입력 소스

### 4-1. P3 anomaly latest

- [profitability_operations_p3_anomaly_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\profitability_operations\profitability_operations_p3_anomaly_latest.json)

주로 사용하는 입력:

- `symbol_alert_summary`
- `active_alerts`

### 4-2. P4 compare latest

- [profitability_operations_p4_compare_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\profitability_operations\profitability_operations_p4_compare_latest.json)

주로 사용하는 입력:

- `overall_delta_summary`
- `p3_alert_type_deltas`
- `symbol_alert_deltas`
- `worsening_signal_summary`
- `improving_signal_summary`

### 4-3. P5 casebook latest

- [profitability_operations_p5_casebook_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\profitability_operations\profitability_operations_p5_casebook_latest.json)

주로 사용하는 입력:

- `worst_scene_candidates`
- `strength_scene_candidates`
- `tuning_candidate_queue`

## 5. P6 첫 버전의 핵심 출력

### 5-1. symbol health

각 symbol에 대해 아래를 요약한다.

- active alert 상태
- recent worsening / improving delta
- worst scene 집중도
- strength scene 존재 여부
- health score / health state
- size multiplier advisory

### 5-2. archetype health

첫 버전에서는 `setup_key`를 archetype proxy로 본다.

즉 setup_key 단위로 아래를 요약한다.

- caution scene count
- strength scene count
- information gap scene count
- top candidate type
- health state

### 5-3. drift signal

drift는 아래와 같이 본다.

- alert type delta가 recent window에서 의미 있게 증가하는가
- symbol alert delta가 최근 창에서 집중되는가
- system 전체 active alert가 늘고 있는가

## 6. sizing advisory 원칙

첫 버전의 sizing은 advisory multiplier다.

- `hard_reduce`
- `reduce`
- `hold`
- `normal`
- `allow_expand`

이 multiplier는 아래를 함께 반영한다.

- critical / high alert 수
- active alert delta
- worst scene count
- information gap scene count
- strength scene count

## 7. canonical 출력 shape

### latest json

필수 section:

- `overall_health_summary`
- `symbol_health_summary`
- `archetype_health_summary`
- `drift_signal_summary`
- `sizing_overlay_recommendations`
- `operator_review_queue`
- `quick_read_summary`

### latest csv

symbol health / sizing recommendation flat row export.

### latest md

operator가 바로 읽는 health / drift / sizing memo.

## 8. 완료 기준

P6 첫 버전이 완료됐다고 보려면 아래가 가능해야 한다.

1. symbol 단위 health state가 나온다.
2. setup_key 단위 archetype health가 나온다.
3. drift 상태를 worsening / stable / improving 계열로 읽을 수 있다.
4. sizing advisory multiplier가 symbol 단위로 나온다.
5. operator가 latest markdown만 보고 `어디를 줄이고 어디를 그대로 두거나 약간 키울지` 말할 수 있다.

## 9. 결론

P6는 `관측된 문제를 시스템 자기 상태와 sizing advisory로 승격하는 첫 자기 인식 단계`다.
자동 적응이 아니라, 다음 P7 이전에 시스템이 스스로를 읽는 표면을 여는 단계라고 보면 된다.
