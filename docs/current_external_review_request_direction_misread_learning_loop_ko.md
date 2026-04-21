# 외부 조언 요청서: 상하단 방향 오판 / 캔들-박스 위치 불일치 / 힘 우세 설명 surface

## 1. 이 문서를 만든 이유

현재 자동매매 시스템은 구조적으로는 많이 완성되어 있다.

- 자동 진입/대기/청산 런타임
- checkpoint -> review -> canary -> closeout -> handoff 축
- Telegram check/report/control plane
- `/detect -> /detect_feedback -> /propose` 학습 루프
- state25 weight patch review/apply 통로

즉 지금 단계의 핵심 문제는 “구조 부재”가 아니라, 아래와 같은 **해석 품질과 설명 품질**이다.

- 차트상으로는 상단 힘이 더 강한데 하단 쪽으로 읽히는 것처럼 느껴지는 장면
- 박스/캔들 위치상 방향 표기가 비거나 반대로 느껴지는 장면
- 시스템은 내부적으로 뭔가를 보고 판단했겠지만, 사용자가 왜 그렇게 읽었는지 바로 납득하기 어려운 장면

특히 NAS100 / XAUUSD / BTCUSD에서 이런 장면이 라이브 관찰 중 반복적으로 보였다.

그래서 이번 단계는 실제 매매 로직을 바꾸기보다,
먼저 **이 오판을 더 잘 관찰하고, 설명하고, 학습 루프에 태우는 것**을 목표로 잡았다.

## 2. 현재 시스템에 대해 중요한 전제

이번 작업은 “기존 시스템이 고장났다”는 전제에서 출발한 것이 아니다.

오히려 현재 판단은 다음과 같다.

- 엔진은 계속 동작하고 있음
- 관찰/오케스트레이션/approval/apply/retention 루프는 대부분 살아 있음
- 문제는 일부 장면에서 **scene 해석과 체감 차이** 또는 **방향 설명 부족**이 있다는 점

즉 이번 작업의 질문은 이것이다.

1. 시스템이 위/아래 힘을 읽는 현재 방식이 적절한가
2. 방향 오판을 detector로 surface하는 현재 방식이 적절한가
3. 캔들/박스 위치 불일치를 현재 학습 루프에 태우는 방식이 적절한가

## 3. 실제로 관찰된 문제 유형

현재 사용자가 라이브 차트를 보며 느낀 문제는 아래와 같다.

### A. 상하단 방향 오판처럼 느껴지는 장면

예:

- 상단 압력이 더 강해 보이는데 하단 쪽으로 읽힌다
- 위로 갈 여지가 더 커 보이는데 체크 표기나 해석이 아래쪽으로 붙는다
- 혹은 반대로 아래가 강한데 위로 읽는 듯한 장면이 있다

### B. 캔들/박스 위치 대비 해석 불일치

예:

- 박스 상단/하단에 가까운 위치인데 그 위치성을 충분히 반영하지 못하는 듯한 장면
- 윗꼬리/아랫꼬리/몸통의 비중이 체감과 다르게 먹는 듯한 장면
- 박스 내부 위치와 캔들 구조를 함께 보면 다른 방향 해석이 더 자연스러워 보이는 장면

### C. 설명 부족

현재는 시스템 내부 신호가 있어도, 실시간 DM이나 detector surface에서 그 내용이 직접 보이지 않으면
사용자는 “왜 이 방향으로 읽었는지”를 추적하기 어렵다.

## 4. 기존에 이미 있던 것

이번 작업은 완전히 빈 바닥에서 시작한 것이 아니다.

기존 시스템에는 이미 다음 데이터/루프가 있었다.

### 4-1. scene disagreement 감지

파일:

- [checkpoint_scene_disagreement_audit_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\shadow_auto\checkpoint_scene_disagreement_audit_latest.json)

현재 상태 예시:

- `high_conf_scene_disagreement_count = 617`
- `recommended_next_action = keep_scene_candidate_log_only_and_patch_overpull_labels_before_sa6`
- top profile:
  - `candidate_selected_label = breakout_retest_hold`
  - `row_count = 36`

즉 시스템은 이미 “scene candidate와 사후 더 좋았던 해석이 어긋난 케이스”를 꽤 많이 쌓고 있었다.

### 4-2. detector feedback / proposal promotion 루프

이미 다음 흐름은 작동 중이었다.

1. `/detect`
2. `/detect_feedback D번호 맞았음|과민했음|놓쳤음|애매함`
3. feedback-aware narrowing
4. feedback-aware proposal promotion
5. `/propose`

즉 `observe -> feedback -> promotion -> propose`의 학습 루프는 이미 존재했다.

### 4-3. live position energy 신호

가장 중요한 점은,
상하단 힘을 위한 새로운 수학 모델을 만든 것이 아니라
**이미 런타임에 존재하던 force 신호를 surface로 끌어올렸다는 점**이다.

실제 runtime detail payload에는 이미 아래가 있었다.

- `upper_position_force`
- `lower_position_force`
- `middle_neutrality`
- `position_dominance`
- `consumer_check_side`
- `consumer_check_reason`
- `blocked_by`
- `next_action_hint`

즉 이번 작업은 “새 판단 모델”이 아니라, **기존 판단 모델을 더 잘 보이게 만드는 작업**에 가깝다.

## 5. 이번에 실제로 추가한 것

### 5-1. 상하단 방향 오판 detector

파일:

- [improvement_log_only_detector.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\improvement_log_only_detector.py)

핵심 아이디어:

- 기존 `scene disagreement` row를 그대로 쓰되
- live force context가 강한 심볼이면
- detector summary를 더 직접적인 한국어로 바꾼다

예:

- 기존: `trend_exhaustion 장면 불일치 반복 관찰`
- 현재: `BTCUSD 상하단 방향 오판 가능성 관찰`

왜 이렇게 했나:

- 기존 detector key와 피드백 루프를 유지할 수 있음
- 새 detector 종류를 또 만들지 않아도 됨
- 기존 `scene_aware -> feedback -> promotion -> propose` 흐름이 그대로 살아 있음

### 5-2. 캔들/박스 위치 대비 방향 해석 불일치 detector

파일:

- [improvement_log_only_detector.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\improvement_log_only_detector.py)

핵심 아이디어:

- 기존 candle/weight detector는 유지
- 다만 `upper/lower/reject/rebound/reclaim/box/range/mixed/compression/wick/band`
  계열 문제군이면 summary를 더 직접적인 문장으로 바꾼다

예:

- 기존: `upper_reject_mixed_confirm 패턴 가중치 점검 제안`
- 현재: `XAUUSD 캔들/박스 위치 대비 방향 해석 불일치 관찰`

왜 이렇게 했나:

- weight patch preview는 여전히 재사용 가능
- 하지만 사용자는 “가중치 점검”보다 “어떤 오판을 봤는지”를 더 빨리 이해할 수 있음

### 5-3. 위/아래 힘 우세 설명 surface

파일:

- [notifier.py](C:\Users\bhs33\Desktop\project\cfd\backend\integrations\notifier.py)

실시간 DM `진입 / 대기 / 반전`에 아래 한 줄을 추가했다.

예:

- `위/아래 힘: 상단 우세 (하단 0.05 / 상단 0.34 / 중립 0.00)`
- `위/아래 힘: 하단 우세 (하단 0.20 / 상단 0.00 / 중립 0.00)`

이 줄은 의사결정을 바꾸지 않는다.
오직 현재 런타임이 어떤 위치 에너지/힘 균형을 보고 있는지를 표면에 드러낸다.

## 6. 현재 실제 snapshot 상태

최신 detector snapshot:

- [improvement_log_only_detector_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\shadow_auto\improvement_log_only_detector_latest.json)

현재 기준:

- `surfaced_detector_count = 6`
- `scene_rows = 3`
- `candle_rows = 1`
- `reverse_rows = 2`

현재 scene detector example:

- `BTCUSD 상하단 방향 오판 가능성 관찰`
- `BTCUSD scene trace 누락 반복 감지`
- `XAUUSD scene trace 누락 반복 감지`

즉 기능은 이미 artifact level에서는 올라온 상태다.

## 7. 이번 변경에서 의도적으로 하지 않은 것

아래는 일부러 하지 않았다.

- 실제 진입/청산/반전 로직 변경
- detector 결과의 자동 apply
- 위/아래 힘 우세만으로 방향 강제 교정
- detector에서 곧바로 weight patch 적용

이유:

현재 단계의 핵심은 `바로 교정`이 아니라 `잘못 읽는 장면을 더 잘 surface해서 feedback/propose로 보내는 것`이기 때문이다.

즉 지금도 원칙은 그대로다.

- observe
- report
- feedback
- propose
- review
- apply

## 8. 왜 이 접근이 적합하다고 판단했는가

현재 시스템 상태를 보면,
바로 전략을 교정하는 것보다 먼저 필요한 것은 아래였다.

1. 사용자가 “왜 이 방향으로 읽었는지”를 이해할 수 있어야 함
2. detector가 `맞았음 / 과민했음 / 놓쳤음` 피드백을 받을 수 있어야 함
3. 그 피드백이 `/propose` 우선순위로 연결돼야 함

즉 이번 변경은 다음 질문에 답하기 위해 적합하다고 봤다.

- 지금 이 장면을 시스템이 어떻게 보고 있나?
- 그 해석이 체감과 왜 다른가?
- 이 오판을 바로 고치지 않고도 학습 재료로 쌓을 수 있나?

## 9. 아직 남은 한계

현재도 분명한 한계는 있다.

### 9-1. 아직 자동 교정 단계는 아니다

현재는 어디까지나

- detector surface
- DM 설명
- feedback
- proposal promotion

까지다.

### 9-2. candle detector는 아직 generic issue가 남는다

현재 live top candle issue는 아직 manual/H1/RSI 계열처럼 generic하게 뜨는 경우가 있다.
즉 인프라는 열려 있지만, **심볼/구조별 분해는 아직 더 다듬을 여지**가 있다.

### 9-3. 결국 live 데이터와 feedback이 더 쌓여야 한다

이 detector는 이론적으로 맞아 보여도,
실제 `놓쳤음 / 과민했음 / 맞았음`이 쌓여야 비로소 잘 좁혀진다.

## 10. 외부 조언에서 받고 싶은 핵심 질문

이번 요청에서 가장 듣고 싶은 조언은 아래다.

### A. 방향 오판 정의가 적절한가

현재는

- `scene disagreement`
- `upper/lower force`
- `current side`
- `current reason`

조합으로 방향 오판 가능성을 surface하고 있다.

이 조합이 적절한가?
아니면 여기에 꼭 더 들어가야 할 것이 있는가?

### B. 캔들/박스 위치 불일치 detector 기준이 적절한가

현재는 reason token 기반으로

- upper
- lower
- reject
- rebound
- reclaim
- box
- range
- mixed
- compression
- wick
- band

등을 잡고 candle/box mismatch로 surface한다.

이 기준이 충분한가?
아니면 더 직접적으로

- box relative position
- wick/body ratio
- 최근 3봉 구조
- anchor/middle 거리

같은 축을 넣는 게 맞는가?

### C. 위/아래 힘 우세 설명은 적절한가

현재는 DM에 아래 한 줄이 들어간다.

- `위/아래 힘: 상단 우세 (하단 x.xx / 상단 x.xx / 중립 x.xx)`

이 정도가 적절한가?
아니면 정렬/비정렬까지 같이 보여주는 게 나은가?

예:

- 현재 방향과 정합
- 현재 방향과 엇갈림

### D. 이걸 바로 apply하지 않고 feedback/propose로 한 번 더 거치는 구조가 맞는가

현재는 의도적으로 아래를 막아뒀다.

- detector -> 바로 apply
- force dominance만으로 방향 변경

이 보수적 접근이 맞는가?
아니면 특정 좁은 lane에서는 더 빨리 promotion해도 되는가?

## 11. 외부에 그대로 붙여넣을 수 있는 요청문

```text
현재 자동매매 시스템에서 NAS100/XAUUSD/BTCUSD 라이브 차트를 보며,
상하단 방향 표기가 비거나 반대로 느껴지는 장면,
그리고 캔들/박스 위치상 방향 해석이 어색한 장면이 반복적으로 보였습니다.

중요한 점은 기존 시스템이 망가진 것은 아니고,
이런 장면을 사용자가 납득할 수 있게 직접 설명하거나,
이 오판을 detector/feedback/propose 학습 루프로 끌어올리는 부분이 부족했다는 점입니다.

그래서 이번에는 실제 거래 로직은 건드리지 않고,
다음 3가지를 기존 관찰-학습 루프에 얹었습니다.

1. 상하단 방향 오판 detector
2. 캔들/박스 위치 대비 방향 해석 불일치 detector
3. 위/아래 힘 우세 설명 surface

구현은 새 판단 엔진을 만든 것이 아니라,
이미 런타임에 존재하는 신호를 surface로 끌어올리는 방식입니다.
사용한 신호는:

- upper_position_force
- lower_position_force
- middle_neutrality
- position_dominance
- consumer_check_side
- consumer_check_reason
- blocked_by
- next_action_hint

실시간 DM에는
'위/아래 힘: 상단 우세 (하단 0.xx / 상단 0.xx / 중립 0.xx)'
같은 한 줄을 추가했고,
detector는 기존 /detect -> /detect_feedback -> /propose 루프를 그대로 탑니다.

의도적으로 하지 않은 것은:
- 실제 진입/청산/반전 로직 변경
- detector 결과의 자동 apply
- 힘 우세만으로 방향 강제 교정

즉 현재 목표는
'바로 고치기'가 아니라
'오판을 더 잘 보이게 하고, 피드백을 쌓아, 나중에 더 정확히 좁히는 것'입니다.

이 접근이 적절한지,
그리고 상하단 방향 오판 / 캔들-박스 위치 불일치를 더 잘 정의하려면
어떤 기준이나 신호를 추가하는 게 좋을지 조언을 받고 싶습니다.
```

## 12. 관련 파일

- [improvement_log_only_detector.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\improvement_log_only_detector.py)
- [notifier.py](C:\Users\bhs33\Desktop\project\cfd\backend\integrations\notifier.py)
- [improvement_detector_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\improvement_detector_policy.py)
- [current_p4_5_direction_misread_candle_box_force_surface_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\current_p4_5_direction_misread_candle_box_force_surface_ko.md)
