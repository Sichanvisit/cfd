# State25 Context Bridge External Review Request

후속 설계 문서:
- [current_state25_context_bridge_v1_detailed_plan_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\current_state25_context_bridge_v1_detailed_plan_ko.md)
- [current_state25_context_bridge_v1_execution_roadmap_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\current_state25_context_bridge_v1_execution_roadmap_ko.md)

## 1. 이 문서를 만드는 이유

현재 시스템은 크게 두 층으로 나뉘어 있습니다.

1. **state-first context 층**
   - `HTF / previous box / context conflict / late chase risk`
   - 사람이 차트를 볼 때 같이 보는 큰 그림을 runtime state에 먼저 올리는 층
2. **state25 실행/학습 층**
   - 진입 기준, 크기, 해석 비중, bounded rollout 후보를 관리하는 층
   - 실제 점수와 실행 정책에 더 가까운 층

지금까지는 state-first context를

- runtime payload
- detector
- notifier
- `/propose`
- hindsight

까지는 연결해두었습니다.

하지만 아직 이 새 context가 **state25의 점수/실행 쪽 손잡이**에 충분히 번역되어 붙었다고 보기는 어렵습니다.

그 결과 현재 사용자가 느끼는 핵심 답답함은 이렇습니다.

> 시스템은 이미
> `상위 추세 역행`, `직전 박스 상단 돌파 유지`, `늦은 추격 위험`
> 같은 큰 그림을 어느 정도 설명할 수 있게 됐는데,
> 실제 점수 본체(state25)는 아직 그 설명을 약하게만 반영해서
> 결과적으로 “설명은 이상하다고 말하는데 점수는 예전 습관대로 가는” 장면이 남아 있다.

이 문서는 그 상황을 외부 리뷰어가 빠르게 이해하고,

- 지금 어떤 층이 이미 연결되었는지
- 왜 state25와 추가 연결이 필요해졌는지
- 어떤 방식으로 연결하려고 하는지
- 무엇을 조언받고 싶은지

를 한 번에 볼 수 있도록 정리한 요청 문서입니다.


## 2. state25가 정확히 무엇인가

`state25`는 현재 시스템에서 **학습 가능한 실행 정책의 중심 계층**에 가깝습니다.

아주 단순하게 말하면:

- detector는 “이상한 장면을 찾는 관찰자”
- notifier는 “사람에게 알려주는 전달자”
- `/propose`는 “리뷰 후보를 올리는 정리자”
- `state25`는 “실제로 무엇을 얼마나 믿고, 얼마나 보수적으로 들어가고, 어떤 bounded patch를 실험할지”를 관리하는 쪽입니다.

즉 state25는 단순 설명 레이어가 아니라,

- 진입 threshold
- 진입 size
- teacher weight override
- forecast / belief / barrier overlay와의 연결
- active candidate rollout phase

를 담는 실행/학습 축입니다.

관련 핵심 파일:

- [teacher_pattern_active_candidate_runtime.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\teacher_pattern_active_candidate_runtime.py)
- [entry_try_open_entry.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\entry_try_open_entry.py)
- [trading_application.py](C:\Users\bhs33\Desktop\project\cfd\backend\app\trading_application.py)
- [state25_weight_patch_review.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\state25_weight_patch_review.py)
- [state25_weight_patch_apply_handlers.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\state25_weight_patch_apply_handlers.py)
- [teacher_pattern_execution_policy_log_only_binding.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\teacher_pattern_execution_policy_log_only_binding.py)
- [forecast_state25_runtime_bridge.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\forecast_state25_runtime_bridge.py)

### 2-1. state25가 이미 갖고 있는 손잡이

현재 코드 기준으로 state25는 적어도 아래 세 가지 직접 손잡이를 갖고 있습니다.

1. `threshold`
   - 진입 임계값을 더 엄격하게/덜 엄격하게 볼 수 있음
   - 예: `state25_threshold_log_only_max_adjustment_abs`

2. `size`
   - 포지션 크기 multiplier를 보수적으로 줄이거나 유지할 수 있음
   - 예: `state25_size_log_only_min_multiplier`, `state25_size_log_only_max_multiplier`

3. `weight`
   - teacher 해석 항목의 비중을 조절할 수 있음
   - 예: `state25_teacher_weight_overrides`

즉 “새 context를 state25에 연결한다”는 말은 추상적인 얘기가 아니라,
결국 **이 손잡이들에 새 맥락을 어떻게 번역해서 연결할지 정하는 작업**에 가깝습니다.

### 2-2. state25는 runtime에서 어떻게 소비되는가

runtime은 이미 active candidate state를 읽고, 그 상태를 surface로 export합니다.

예를 들면 [trading_application.py](C:\Users\bhs33\Desktop\project\cfd\backend\app\trading_application.py)에서는:

- `state25_candidate_runtime_v1`
- `state25_candidate_threshold_surface_v1`
- `state25_candidate_size_surface_v1`
- `state25_candidate_weight_surface_v1`

를 payload에 함께 실어줍니다.

또 [entry_try_open_entry.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\entry_try_open_entry.py)에서는:

- `state25_candidate_log_only_trace_v1`
- `forecast_state25_runtime_bridge_v1`
- `belief_state25_runtime_bridge_v1`
- `barrier_state25_runtime_bridge_v1`

같은 trace/bridge를 실제 entry 흐름 중에 생성합니다.

즉 state25는 이미 **실행 직전의 핵심 관문**과 연결되어 있습니다.


## 3. 지금까지 새 context 쪽에서 이미 한 것

state-first 공사는 이미 아래 순서까지 끝낸 상태입니다.

1. `ST1`
   - HTF 계산/캐시
   - [htf_trend_cache.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\htf_trend_cache.py)

2. `ST2`
   - previous box 계산
   - [previous_box_calculator.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\previous_box_calculator.py)

3. `ST3`
   - context 묶음 조립
   - [context_state_builder.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\context_state_builder.py)

4. `ST4`
   - runtime latest row에 합류
   - [trading_application.py](C:\Users\bhs33\Desktop\project\cfd\backend\app\trading_application.py)

5. `ST5`
   - detector가 context bundle reader로 전환
   - [improvement_log_only_detector.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\improvement_log_only_detector.py)

6. `ST8`
   - notifier가 `맥락: <HTF> | <직전박스> | <추격위험>` 한 줄을 읽도록 연결
   - [notifier.py](C:\Users\bhs33\Desktop\project\cfd\backend\integrations\notifier.py)

7. `ST9`
   - `/propose`와 hindsight가 detector의 context/hindsight 요약을 들고 가도록 연결
   - [trade_feedback_runtime.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\trade_feedback_runtime.py)

즉 현재는 이미

`runtime state -> detector -> notifier -> propose/hindsight`

축까지는 같은 큰 그림을 보기 시작한 상태입니다.


## 4. 그런데도 왜 아직 답답한가

핵심은 아주 단순합니다.

### 지금 잘 되는 것

- detector가 “이건 상위 추세 역행 같다”를 말할 수 있음
- notifier가 “늦은 추격 위험”을 경고할 수 있음
- `/propose`가 “직전 박스/HTF 맥락까지 봤을 때 이런 패턴이 반복된다”를 정리할 수 있음

### 아직 약한 것

- state25 점수 본체가 그 큰 그림을 **직접 자기 손잡이(threshold/size/weight)**로 충분히 번역해 쓰지는 않음

그래서 사용자가 체감하는 장면은 종종 이렇게 됩니다.

1. 설명 층:
   - `HTF 전체 상승 정렬`
   - `직전 박스 상단 돌파 유지`
   - `늦은 추격 숏 위험`

2. 점수 층:
   - 여전히 기존 reversal/short 해석이 강하게 남아 있음

3. 결과:
   - “설명은 위로 더 갈 것 같다고 말하는데, 점수는 아직 그만큼 못 고친다”

이게 바로 이번 연결 논의의 출발점입니다.


## 5. 왜 state25와 연결하려 하는가

이유는 세 가지입니다.

### 5-1. 큰 그림을 점수 본체가 모르면 같은 실수가 반복된다

지금까지 구축한 context는 이미 사람 좌표계에 더 가까워졌습니다.

- 상위 시간봉 추세
- 직전 박스와 현재 위치의 관계
- 늦은 추격 위험
- 맥락 충돌

그런데 이게 score 본체에 충분히 번역되지 않으면,
결국 반복적으로

- 역추세 진입
- 돌파 유지 장면을 실패돌파처럼 해석
- 너무 늦은 추격인데도 기존 점수 논리로 들어감

같은 문제가 남습니다.

### 5-2. state25는 이미 실행 직전 손잡이를 갖고 있다

현재 state25는

- threshold
- size
- weight

를 건드릴 수 있습니다.

즉 “새 context를 실행 쪽에 연결할 수 있는 문”은 이미 열려 있습니다.
새로운 실행 엔진을 만들기보다, **기존 손잡이에 새 context를 붙이는 게 더 자연스럽고 안전**합니다.

### 5-3. 설명층과 점수층이 너무 오래 분리되면 운영 체감이 깨진다

지금은 설명은 좋아졌는데, 실제 점수/행동 변화는 제한적인 구간입니다.

이 상태가 너무 오래 가면 운영자는 이렇게 느끼게 됩니다.

> “너는 왜 이게 위험한지 잘 말하는데,
> 정작 들어갈 때는 아직도 예전처럼 들어가네?”

즉 지금 필요한 건 새 설명 기능보다, **설명층이 점수층에 bounded하게 번역되는 다리**입니다.


## 6. 어떻게 붙이려 했는가

현재 생각하는 원칙은 분명합니다.

### 6-1. 절대 바로 하드 차단으로 가지 않는다

하지 않으려는 것:

- `HTF 상승이면 SELL 금지`
- `직전 박스 위면 무조건 BUY`
- `late_chase_risk = HIGH면 무조건 진입 차단`

이유:

- 상위 상승 중에도 눌림 숏이 맞는 순간은 있음
- 박스 돌파 유지처럼 보이다 실패하는 경우도 있음
- 늦어 보여도 더 가는 경우도 있음

즉 context는 **방향 강제 규칙**이 아니라, **점수/문턱 보정 근거**로 쓰는 게 맞다고 보고 있습니다.

### 6-2. 우선순위는 `weight -> threshold -> size`

#### 1) weight first

가장 먼저 연결하려는 손잡이입니다.

예시 생각:

- `AGAINST_HTF`
- `previous_box_break_state = BREAKOUT_HELD`
- `late_chase_risk = HIGH`

같은 장면이면,
기존에 과하게 믿던

- reversal 해석
- 실패돌파 해석
- upper reject 해석

비중을 조금 낮추고,

- continuation
- directional bias
- participation

비중을 조금 올리는 방식입니다.

즉 방향을 강제로 뒤집는 것이 아니라,
**무엇을 더 믿고 덜 믿을지의 비중을 조정**하려는 것입니다.

이건 현재 구조와 가장 잘 맞습니다.
이미 [state25_weight_patch_review.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\state25_weight_patch_review.py)와
[state25_weight_patch_apply_handlers.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\state25_weight_patch_apply_handlers.py)가 있기 때문입니다.

#### 2) threshold second

그다음은 진입 문턱을 조정하는 방식입니다.

예시 생각:

- `AGAINST_HTF = HIGH`
- `context_conflict_state = AGAINST_PREV_BOX_AND_HTF`
- `late_chase_risk = HIGH`

같은 장면이면,
진입을 무조건 금지하지는 않되
**들어가려면 더 강한 confirm/점수가 필요하게** 만드는 방식입니다.

즉:

- 역추세 장면은 더 까다롭게
- 늦은 추격 장면은 더 까다롭게

보는 쪽입니다.

#### 3) size third

마지막은 size입니다.

생각하는 방향:

- conflict가 강하고
- late chase가 높고
- previous box confidence도 높게 “불편하다”고 말하면

맞더라도 **작게만 들어가는 보수적 제한**을 걸 수 있습니다.

하지만 이건 실제 돈 크기를 건드리므로,
threshold/weight보다 뒤가 더 안전하다고 보고 있습니다.


## 7. 새 context를 state25에 붙일 때의 해석 원칙

### 원칙 1. raw context를 직접 많이 먹이지 말고 interpreted context를 중심으로 본다

이미 upstream에는 아래 두 층이 있습니다.

- raw context
  - `trend_1h_direction`
  - `trend_1h_strength_score`
  - `previous_box_high`
  - `distance_from_previous_box_high_pct`
- interpreted context
  - `htf_alignment_state`
  - `htf_against_severity`
  - `previous_box_break_state`
  - `context_conflict_state`
  - `late_chase_risk_state`

state25에 연결할 때는 가능하면

- interpreted context 중심
- raw score는 보조 근거

로 가는 편이 맞다고 보고 있습니다.

이유는 interpreted context가 이미
사람이 읽는 좌표계에 맞게 요약되어 있기 때문입니다.

### 원칙 2. freshness를 무시하지 않는다

HTF와 previous box는 stale할 수 있습니다.

그래서 연결 시에는

- `updated_at`
- `age_seconds`
- `context_state_version`
- component별 version

을 보고 너무 오래된 context는 약하게 보거나 무시하는 규칙이 필요할 수 있습니다.

### 원칙 3. share는 direction authority가 아니라 confidence booster로만 쓴다

share는 마지막까지 보조로 둘 생각입니다.

즉:

- share가 높다고 방향을 바꾸지 않음
- share는 반복성/확신도/priority 보강에만 사용

하는 쪽이 맞다고 보고 있습니다.


## 8. 현재 우리가 생각하는 연결 구조

대략 아래 구조를 상정하고 있습니다.

```text
[HTF cache]
[previous box calculator]
[context_state_builder]
        ↓
runtime latest state row
        ↓
detector / notifier / propose  (already connected)
        ↓
state25 context bridge v1
        ↓
weight patch / threshold patch / size patch
        ↓
log_only trace
        ↓
review / apply / bounded rollout
```

즉 이번에 새로 만들려는 것은
`state-first context -> state25 policy knobs`
로 번역하는 **bridge layer**입니다.


## 9. 이미 연결에 유리한 준비가 되어 있는 부분

### 9-1. state25는 log-only / canary / bounded_live 철학을 이미 갖고 있다

관련 문서:

- [current_state25_execution_policy_integration_design_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\current_state25_execution_policy_integration_design_ko.md)
- [current_state25_active_candidate_runtime_consumption_design_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\current_state25_active_candidate_runtime_consumption_design_ko.md)

즉 state25는 원래부터

- read-only
- log-only
- canary
- bounded_live

같은 **보수적 rollout 철학** 위에 있습니다.

그래서 새 context를 붙일 때도
곧바로 live hard binding으로 가지 않고,
먼저 log-only로 붙이는 쪽이 구조적으로 맞습니다.

### 9-2. forecast-state25 bridge도 이미 일부 존재한다

관련 문서/코드:

- [current_forecast_state25_learning_bridge_design_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\current_forecast_state25_learning_bridge_design_ko.md)
- [forecast_state25_runtime_bridge.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\forecast_state25_runtime_bridge.py)

즉 state25는 본질적으로 “외부 보조 맥락과 연결되는 것 자체가 낯선 엔진”은 아닙니다.
문제는 이번 새 context 축이 아직 그 다리에 충분히 합류하지 않았다는 점입니다.


## 10. 현재 우리가 보고 있는 핵심 질문

외부 리뷰어에게 특히 조언받고 싶은 것은 아래입니다.

### 질문 1. 연결 순서가 `weight -> threshold -> size`가 맞는가

현재는

1. weight first
2. threshold second
3. size third

가 가장 안전하다고 보고 있습니다.

이 순서가 실제로도 맞는지,
또는 threshold를 먼저 열어야 하는지 의견을 듣고 싶습니다.

### 질문 2. state25는 raw context보다 interpreted context를 중심으로 받아야 하는가

예:

- 직접 `trend_1h_strength_score`를 많이 먹는 게 좋은지
- 아니면 `AGAINST_HTF`, `BREAKOUT_HELD`, `LATE_CHASE_RISK` 같은 interpreted 요약을 중심으로 보정하는 게 좋은지

를 묻고 싶습니다.

### 질문 3. 어떤 context는 weight에, 어떤 context는 threshold에 붙는 것이 더 자연스러운가

예를 들면:

- `AGAINST_HTF`
- `AGAINST_PREV_BOX_AND_HTF`
- `late_chase_risk`
- `BREAKOUT_HELD`

같은 것들이 각각

- weight 조정형
- threshold 강화형
- size 축소형

중 어디에 더 잘 맞는지 조언받고 싶습니다.

### 질문 4. log-only 단계에서 어떤 trace를 최소로 남겨야 안전한가

새 context를 state25에 붙이면 최소한 아래를 trace로 남겨야 한다고 생각하고 있습니다.

- 어떤 context가 발동했는지
- 어떤 손잡이(weight/threshold/size)에 번역됐는지
- 실제 live 값과 candidate log-only 값 차이
- hindsight 기준으로 그 보정이 맞았는지

이 정도가 충분한지, 더 있어야 하는지 의견을 듣고 싶습니다.

### 질문 5. context를 state25 core에 너무 빨리 섞을 때의 리스크는 무엇인가

현재는 하드 차단을 피하려고 하지만,
반대로 너무 약하게 붙이면 체감 개선이 적을 수 있습니다.

즉:

- 너무 약하면 효과가 없음
- 너무 세면 core가 오염됨

이 사이의 적절한 bounded 연결 강도에 대한 조언을 받고 싶습니다.


## 11. 현재 기준 우리의 잠정 결론

우리 쪽 잠정 결론은 이렇습니다.

1. **연결은 해야 한다**
   - 지금 문제는 설명 부족만이 아니라 점수 번역 부족이기 때문

2. **하지만 방향 강제 연결은 아직 아니다**
   - `HTF 상승 = SELL 금지` 식의 하드 차단은 과함

3. **state25의 기존 손잡이에 번역해서 붙이는 것이 맞다**
   - weight
   - threshold
   - size

4. **그중 `weight first`가 가장 안전하다**
   - 가장 bounded하고
   - 기존 review/apply 체계와도 잘 맞기 때문

5. **state-first context는 state25 core를 덮어쓰는 새 본체가 아니다**
   - state25 본체는 유지
   - 새 context는 그 본체가 큰 그림을 덜 놓치게 보정하는 층


## 12. 아주 짧은 한 줄 요약

지금 우리는
**“HTF / previous box / late chase 같은 새 큰 그림 맥락을 이미 runtime/detector/notifier/propose까지는 연결해놨고, 이제 그 맥락을 state25의 `weight / threshold / size` 손잡이에 어떻게 bounded하게 번역해서 붙일지”**
에 대한 구조적 조언을 구하고 있습니다.
