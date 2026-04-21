# Manual Truth / Barrier Calibration External Review Request

## 목적

이 문서는 현재 CFD 자동매매 프로젝트의 `manual truth / barrier calibration` 트랙이
어디까지 구현되었는지, 어떤 조언을 이미 받아 실제로 적용했는지, 그리고 지금 남은
핵심 운영 리스크가 무엇인지 외부 모델이나 리뷰어에게 설명하고 조언을 받기 위한
요청서다.

특히 아래 질문에 대한 조언을 받고 싶다.

- 현재 프로젝트를 `owner construction phase`보다 `calibration phase`로 해석하는 것이 맞는가
- `manual truth = standalone answer key`라는 해석이 여전히 적절한가
- `Barrier/wait 자동화 70% 전후`라는 해석이 과대/과소인지
- 사람 게이트를 남겨둔 current-rich promotion / correction loop 운영이 맞는가
- 다음 우선순위를 무엇으로 잡는 것이 가장 합리적인가

---

## 1. 전체 구조와 현재 단계

현재 시스템은 크게 네 층으로 구성된다.

### 1) 실행층

- 기존 execution engine이 실제 enter / wait / exit를 수행
- 여전히 live execution owner는 기존 엔진이다

### 2) semantic owner layer

- `state25`
- `forecast`
- `belief`
- `barrier`

이 owner들은 대체로 아래 승격 프레임 위에 있다.

`runtime -> replay/outcome -> seed enrichment -> baseline auxiliary -> candidate compare/gate -> log_only`

### 3) 운영 재구성 / 검증층

- `runtime_status`
- `entry_decisions`
- `trade_history`
- `trade_closed_history`
- flat field + nested payload dual surface

### 4) manual truth / calibration layer

- heuristic owner가 낸 해석과 사람이 본 answer key를 비교
- mismatch를 `correction-worthy / freeze-worthy / needs-more-truth`로 나누는 상위 판정층

현재 프로젝트는 더 많은 owner를 새로 만드는 단계라기보다,
이미 있는 owner를 평가하고 교정하는 `calibration phase`에 들어와 있다고 해석하고 있다.

---

## 2. manual truth에 대한 현재 해석

현재 manual truth는 다음과 같이 해석하고 있다.

- `actual replay reconstruction`이 아니다
- `training seed`도 아직 아니다
- `standalone answer key`다

즉 사람이 차트를 보고:

- 여기서 바로 진입하면 안 됐다
- 여기서는 기다렸어야 했다
- 여기서 더 좋은 entry가 있었다
- 여기서는 protective exit가 맞았다

같은 판단을 `ideal / counterfactual teacher truth`로 저장하는 층이다.

운영 원칙은 다음과 같이 고정해두었다.

- storage = `episode-first`
- operations = `wait-first`

즉 episode 단위 truth를 저장하되, 현재 실제 운영용 truth 채널은
`manual_wait_teacher` 중심으로 유지하고 있다.

---

## 3. 여기까지 어떻게 진행됐는가

### A. semantic owner / barrier 구조를 먼저 올렸다

- `BR0~BR6` owner promotion
- runtime / replay / seed / compare-gate / log_only 연결

즉 barrier는 단순 보조 score가 아니라 운영 가능한 owner가 되었다.

### B. BCE를 통해 coverage / bias correction 층을 만들었다

- `BCE0~BCE13`은 대부분 구현 완료로 본다
- 이후 bias correction과 wait-family 확장으로 넘어왔다

### C. wait-family를 열었다

상위 family:

- `timing_improvement`
- `protective_exit`
- `reversal_escape`
- `neutral_wait`
- `failed_wait`

대표 subtype:

- `better_entry_after_wait`
- `profitable_wait_then_exit`
- `wait_but_missed_move`
- `wait_without_timing_edge`
- `small_value_wait`

### D. manual truth를 열었다

heuristic barrier / wait-family만으로는 좋은 기다림, missed move, protective exit를
충분히 잘 설명하지 못한다고 판단했고, 그래서 manual answer key를 별도 층으로 열었다.

### E. comparison / recovery / casebook / bias target으로 이어갔다

이후 다음이 구현되었다.

- manual vs heuristic comparison
- paired legacy detail fallback audit
- global detail fallback audit
- archive scan
- rotate-detail fallback reconstruction
- recovered casebook
- bias targets
- current-rich collection queue
- wrong-failed-wait focused audit
- current-rich proxy review

즉 manual truth는 단순 수집이 아니라,
heuristic을 교정하는 운영 surface로 계속 확장되고 있다.

---

## 4. 외부 조언을 받고 실제로 적용한 것

최근 외부 조언을 받고 아래 해석과 구현을 실제로 적용했다.

### 조언 1. manual truth는 answer key로 써라

적용 결과:

- manual truth를 `actual replay matching`보다 `standalone answer key`로 고정
- comparison 레이어를 `평가/교정 surface`로 승격

### 조언 2. comparison을 우선순위 결정 도구로 바꿔라

적용 결과:

- comparison에 `correction-worthy / freeze-worthy / needs-more-truth` 분류 추가
- family ranking에 score decomposition 추가
- patch draft / sandbox / correction loop로 연결

관련 산출물:

- `data/manual_annotations/manual_vs_heuristic_comparison_latest.csv`
- `data/manual_annotations/manual_vs_heuristic_family_ranking_latest.csv`
- `data/manual_annotations/manual_vs_heuristic_bias_sandbox_latest.csv`
- `data/manual_annotations/manual_vs_heuristic_patch_draft_latest.csv`

### 조언 3. wrong_failed_wait는 함부로 밀지 말고 freeze 여부를 봐라

적용 결과:

- `wrong_failed_wait_interpretation`는 current-rich proxy review로 다시 확인
- 즉시 rule patch가 아니라 `collect_more_truth / hold`로 정리

관련 산출물:

- `data/manual_annotations/manual_vs_heuristic_wrong_failed_wait_audit_latest.csv`
- `data/manual_annotations/manual_current_rich_wrong_failed_wait_review_results_latest.csv`

### 조언 4. current-rich draft를 canonical과 분리하고 promotion discipline을 만들라

적용 결과:

- current-rich queue / seed draft / gate / workflow / trace를 분리
- `draft / validated / canonical` discipline 추가
- first real canonical merge trace까지 열었다

관련 산출물:

- `data/manual_annotations/manual_current_rich_promotion_gate_latest.csv`
- `data/manual_annotations/manual_current_rich_review_workflow_latest.csv`
- `data/manual_annotations/manual_current_rich_review_trace_latest.csv`
- `data/manual_annotations/manual_current_rich_promotion_discipline_latest.csv`

### 조언 5. 결정 이후 검증을 구조화하라

적용 결과:

- correction loop 추가
- ranking retrospective 추가
- post-promotion audit 추가
- approval log 추가

관련 산출물:

- `data/manual_annotations/manual_vs_heuristic_correction_runs_latest.csv`
- `data/manual_annotations/manual_vs_heuristic_family_ranking_retrospective_latest.md`
- `data/manual_annotations/manual_current_rich_post_promotion_audit_latest.csv`
- `data/manual_annotations/manual_calibration_approval_log.csv`

---

## 5. 현재 canonical / draft / 비교 상태

### canonical manual truth corpus

파일:

- `data/manual_annotations/manual_wait_teacher_annotations.csv`

현재 canonical corpus:

- 총 `106건`
- `NAS100 = 35`
- `XAUUSD = 35`
- `BTCUSD = 36`

최근 추가:

- first current-rich canonical row 1건
- `manual_seed::BTCUSD::2026-04-07T03:00:00`

이 row는 좌표를 채운 뒤 `validated -> canonical`로 올린 첫 사례다.

### current-rich promotion discipline

관련 파일:

- `data/manual_annotations/manual_current_rich_promotion_gate_latest.csv`
- `data/manual_annotations/manual_current_rich_review_workflow_latest.csv`
- `data/manual_annotations/manual_current_rich_review_trace_latest.csv`
- `data/manual_annotations/manual_current_rich_promotion_discipline_latest.csv`

현재 상태:

- 총 current-rich discipline rows: `12`
- `draft = 6`
- `validated = 5`
- `canonical = 1`

즉 current-rich row는 단순히 draft로만 쌓이는 것이 아니라,
현재는 `draft -> validated -> canonical`의 운영 단계로 나뉘어 관리된다.

### post-promotion audit

관련 파일:

- `data/manual_annotations/manual_current_rich_post_promotion_audit_latest.csv`

현재 상태:

- first promoted canonical row 1건이 audit queue에 잡힘
- 현재 status는 `scheduled`

즉 승격이 끝이 아니라, 이후 3일/14일 audit로 다시 볼 수 있게 되었다.

### comparison / ranking / correction 상태

관련 파일:

- `data/manual_annotations/manual_vs_heuristic_comparison_latest.csv`
- `data/manual_annotations/manual_vs_heuristic_family_ranking_latest.csv`
- `data/manual_annotations/manual_vs_heuristic_bias_sandbox_latest.csv`
- `data/manual_annotations/manual_vs_heuristic_patch_draft_latest.csv`
- `data/manual_annotations/manual_vs_heuristic_correction_runs_latest.csv`

현재 주요 숫자:

- manual episodes: `106`
- heuristic time-matched rows: `27`
- global rotate-detail fallback used: `15`
- symbol match counts:
  - `NAS100 = 10`
  - `BTCUSD = 17`

현재 top family:

- `wrong_failed_wait_interpretation | barrier_bias_rule | failed_wait | timing_improvement | correct_wait`

하지만 현재 결론은:

- `rule_patch_ready`가 아니라
- `collect_more_truth_before_patch`

즉 top family라고 해도 바로 rule edit하지 않고,
truth를 더 모으고 다시 보자는 상태다.

---

## 6. Barrier/wait 자동화가 현재 무엇을 의미하는가

현재 말하는 `Barrier/wait 자동화 62% -> 68%`는
`barrier rule이 live에서 자동으로 수정된다`는 뜻이 아니다.

현재 자동화가 뜻하는 것은 아래다.

### 이미 자동으로 되는 것

`manage_cfd.bat`를 켜면 `manual_truth_calibration_watch.py`를 통해 다음이 자동 갱신된다.

- manual vs heuristic comparison
- family ranking
- recovered casebook
- bias targets
- bias sandbox
- patch draft
- correction candidates / correction runs
- current-rich queue
- current-rich seed draft
- promotion gate
- review workflow
- review trace
- promotion discipline
- approval log
- post-promotion audit
- corpus freshness
- corpus coverage

즉 지금 자동화의 본질은:

- `auto-prepare`
- `auto-compare`
- `auto-prioritize`
- `auto-generate review surfaces`

까지는 상당히 강해진 상태다.

### 아직 자동화되지 않은 것

- BCE rule의 실제 auto-edit
- current-rich draft의 auto-merge to canonical
- accepted patch가 반복적으로 누적되는 self-improving closed loop
- live barrier 동작이 manual truth 기준으로 자동 재조정되는 것

즉 현재는 `auto-correction system`이라기보다
`human-in-the-loop calibration automation system`에 가깝다.

### 왜 68% 정도라고 보는가

예전 62% 상태는 대체로:

- comparison 자동 갱신
- ranking 자동 갱신
- queue 자동 생성

정도였다.

지금은 여기에 더해:

- correction loop
- patch draft
- promotion gate / workflow / trace
- first canonical merge trace
- approval log
- post-promotion audit 첫 row

까지 생겼다.

즉 “분석 surface 자동화”에서
“교정 후보를 만들고 사람이 채택/기각할 수 있는 운영 surface 자동화”로 올라간 상태라
68% 정도로 보는 것이다.

---

## 7. 현재 퍼센트 해석

현재 체감 완료율을 다음처럼 보고 있다.

### 완료에 가까운 축

- `state25 자동 개선 기본 루프`: `85%`
- `manual truth 운영 모델`: `90%`
- `manual vs heuristic 비교 레이어`: `85%`
- `manage_cfd에 calibration 레이어 연결`: `85~88%`

### 최근 많이 끌어올린 축

- `Barrier bias correction`: `85%`
- `Current-rich -> canonical 승격 운영`: `88~90%`
- `Next mismatch family ranking`: `90%`
- `Barrier/wait 교정 자동화`: `70~72%`
- `manual truth freshness/coverage`: `85%`

### 아직 의도적으로 낮게 두는 축

- `Entry/Exit teacher 본격 운영`: `20%`
- `manual truth를 training seed로 직접 사용`: `10%`
- `완전 자율 self-improving closed loop`: `45~50%`

---

## 8. 현재 된 것 / 아직 안 된 것 / 지금 해야 할 것

### 이미 된 것

- 첫 current-rich canonical row 1건 생성
- 첫 canonical merge trace 생성
- 첫 post-promotion audit row 생성
- correction loop v0 생성
- ranking retrospective v0 생성
- approval log 생성
- current-rich row를 `draft / validated / canonical`로 분리 관리

### 아직 안 된 것

- accepted patch가 실제로 여러 번 쌓인 correction loop
- rejected patch와 accepted patch를 모두 가진 운영 이력
- post-promotion audit 결과가 여러 건 누적된 상태
- canonical merge 이후 post-promotion relabel / demote 경험
- rule auto-edit
- canonical auto-merge

### 지금 해야 할 것

1. first post-promotion audit result 1건 기록
2. correction loop에서 첫 `accept` 또는 `reject` 사례 1건 만들기
3. ranking retrospective를 1~2주 단위로 누적 운영하기
4. validated row 중 다음 canonical 승격 후보 1건 더 만들기

---

## 9. 외부 조언을 구하고 싶은 핵심 질문

1. 현재 해석처럼 이 프로젝트를 `construction phase`보다 `calibration phase`로 보는 것이 맞는가

2. `manual truth = standalone answer key`로 두고, training seed로 바로 섞지 않는 현재 방침이 맞는가

3. `Barrier/wait 자동화 70% 전후`라는 해석은 적절한가
   - 지금 자동화는 `auto-prepare + auto-prioritize + human-gated correction`으로 보는 것이 맞는가

4. `wrong_failed_wait_interpretation`처럼 top family가 나와도
   바로 patch하지 않고 `collect_more_truth_before_patch`로 두는 현재 운영이 적절한가

5. 다음 우선순위는 무엇이 가장 맞는가
   - post-promotion audit 실제 운영
   - correction loop에서 accept/reject 사례 만들기
   - validated -> canonical 승격 후보 확대
   - current-rich truth 추가 수집

6. 현재 사람 게이트를 남겨둔 판단이 맞는가
   - 특히 canonical promotion / rule edit를 자동화하지 않은 것이 현재 단계에선 맞는가

---

## 10. 한 줄 요약

현재 프로젝트는 단순히 owner를 더 만드는 단계가 아니라,
manual truth answer key를 기준으로 heuristic barrier/wait 해석을 교정하는
`human-in-the-loop calibration system`으로 진화하고 있다.

최근에는 first canonical merge, first post-promotion audit row, correction loop,
ranking retrospective, approval log까지 구현해서 운영 규율을 많이 강화했다.

다만 여전히 `auto-edit`와 `auto-merge`는 의도적으로 막아둔 상태이며,
현재 핵심 질문은:

> 지금 구현한 자동 교정 surface와 사람 검토 게이트의 균형이 맞는가,
> 그리고 다음 1순위를 무엇으로 잡아야 하는가

에 대한 조언이다.
