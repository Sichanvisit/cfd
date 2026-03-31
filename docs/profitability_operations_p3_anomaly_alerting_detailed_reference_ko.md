# Profitability / Operations P3 Anomaly / Alerting Detailed Reference

작성일: 2026-03-30 (KST)

## 1. 목적

이 문서는 `P3 anomaly / alerting`이 무엇인지, 왜 필요한지, 어떤 입력과 출력으로 구현해야 하는지 고정하기 위한 상세 기준 문서다.

P3의 핵심 질문은 하나다.

`P1 lifecycle concern과 P2 expectancy concern 중 무엇을 운영 경보로 승격해서 먼저 보게 만들 것인가?`

## 2. 왜 P3가 필요한가

P1과 P2까지 오면 이미 많은 것이 보인다.

- 어떤 symbol / setup / regime에서 fast adverse close가 반복되는지
- 어떤 bucket이 negative expectancy인지
- 어떤 bucket이 zero-pnl information gap인지
- 어떤 legacy bucket이 attribution blind 상태인지

하지만 P1/P2만으로는 아직 `운영 경보`가 아니다.

운영 관점에서는 아래 질문이 남는다.

- 지금 당장 무엇을 먼저 봐야 하는가
- 어떤 concern이 단순 참고가 아니라 경보 수준인가
- symbol 기준으로 어느 쪽이 더 뜨겁게 망가지고 있는가
- operator queue에 무엇을 먼저 올려야 하는가

P3는 바로 이 부분을 담당한다.

## 3. P3가 아닌 것

P3는 아직 자동 조정 단계가 아니다.

- threshold를 자동으로 바꾸지 않는다
- blacklist를 자동으로 적용하지 않는다
- trade를 자동 중지하지 않는다
- sizing을 자동으로 줄이지 않는다

즉 P3는 `자동 대응`이 아니라 `설명 가능한 운영 경보 surface`다.

## 4. P3 입력 소스

### 4-1. P1 lifecycle latest

- [profitability_operations_p1_lifecycle_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\profitability_operations\profitability_operations_p1_lifecycle_latest.json)

주로 사용하는 입력:

- `suspicious_clusters`
- `suspicious_cluster_type_summary`
- `quick_read_summary`

### 4-2. P2 expectancy latest

- [profitability_operations_p2_expectancy_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\profitability_operations\profitability_operations_p2_expectancy_latest.json)

주로 사용하는 입력:

- `negative_expectancy_clusters`
- `negative_expectancy_cluster_type_summary`
- `quick_read_summary`

### 4-3. P2 zero-pnl gap audit latest

- [profitability_operations_p2_zero_pnl_gap_audit_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\profitability_operations\profitability_operations_p2_zero_pnl_gap_audit_latest.json)

주로 사용하는 입력:

- `suspicious_zero_pnl_buckets`
- `pattern_summary`
- `quick_read_summary`

## 5. P3 alert source 해석 규칙

### 5-1. P1에서 alert로 올릴 것

아래 lifecycle cluster는 P3 alert 후보로 본다.

- `fast_adverse_close_cluster`
- `blocked_pressure_cluster`
- `wait_heavy_cluster`
- `cut_now_concentration_cluster`
- `reverse_now_cluster`
- `coverage_blind_spot_cluster`

### 5-2. P2에서 alert로 올릴 것

아래 expectancy cluster는 P3 alert 후보로 본다.

- `negative_expectancy_cluster`
- `forced_exit_drag_cluster`
- `reverse_drag_cluster`
- `legacy_bucket_blind_cluster`

주의:

- `zero_pnl_information_gap_cluster`는 P2 cluster에도 있지만,
  P3에서는 더 정확한 보조 audit source를 사용해서 별도 alert로 올린다.

### 5-3. zero-pnl audit에서 alert로 올릴 것

`suspicious_zero_pnl_buckets`는 `zero_pnl_information_gap_alert`의 직접 source로 사용한다.

이때 핵심은 아래 구분이다.

- 실제 0 pnl 종료 다발
- `profit`은 있는데 `net/gross`가 0으로 남는 field mismatch
- legacy / attribution gap이 같이 겹친 bucket

## 6. P3 canonical 출력 shape

### 6-1. latest json

필수 section:

- `overall_alert_summary`
- `source_summary`
- `severity_summary`
- `alert_type_summary`
- `symbol_alert_summary`
- `active_alerts`
- `operator_review_queue`
- `quick_read_summary`

### 6-2. latest csv

`active_alerts` flat row export.

### 6-3. latest md

operator가 바로 읽는 quick memo.

## 7. severity 해석 원칙

P3는 source severity를 그대로 복사하지 않고, 운영 경보 수준으로 한 번 더 정규화한다.

- `critical`: 즉시 review가 필요한 경보
- `high`: 현재 review queue 상단에 올려야 하는 경보
- `medium`: 참고가 아니라 관찰 대상
- `low`: 현재 canonical surface에는 올리지 않는다

## 8. operator queue 원칙

P3 review queue는 단순 count 순서가 아니라 아래를 함께 본다.

- severity
- score
- symbol / setup / regime 중복 억제
- 정보 공백과 실제 negative expectancy 분리

즉 아래 둘을 섞어 보여주면 안 된다.

- `경제성 정보 공백`
- `실제 음수 expectancy`

## 9. 완료 기준

P3가 완료됐다고 보려면 최소한 아래가 가능해야 한다.

1. P1/P2 concern이 하나의 canonical alert surface로 합쳐진다.
2. operator가 latest markdown만 보고 top anomaly를 말할 수 있다.
3. zero-pnl information gap을 negative expectancy와 구분해서 읽을 수 있다.
4. symbol 기준 alert 집중도를 볼 수 있다.
5. 이후 P4 compare와 P5 casebook의 입력으로 재사용 가능하다.

## 10. 결론

P3는 `P1/P2에서 보이기 시작한 concern을 실제 운영 경보와 review queue로 승격하는 단계`다.
새 전략을 추가하는 단계가 아니라, 이미 열린 observability를 운영 가능한 surface로 바꾸는 단계다.
