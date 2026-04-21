# Semantic Baseline No-Action Cluster Detector/Proposal Lane

## 목적

`baseline_no_action`이 반복되는 semantic observe cluster를
그냥 audit 결과로만 두지 않고,
`/detect -> /detect_feedback -> /propose` 루프에 태울 수 있는 bounded candidate로 승격한다.

## 왜 지금 필요한가

- 최근 semantic fallback은 단순 분산 잡음이 아니라
  `BTCUSD outer_band_reversal_support_required_observe` 계열 군집으로 모여 있다.
- 이 군집은 “semantic unavailable + baseline no-action”이 함께 반복된다는 점에서
  설명 gap과 observe backlog를 동시에 만든다.
- 따라서 detector feedback을 받을 수 있는 issue 형태로 끌어올릴 필요가 있다.

## 범위

- 거래 로직 변경 없음
- threshold/allowlist 자동 변경 없음
- detector surface와 proposal candidate만 추가

## detector lane

- scene-aware detector 안에서 `semantic baseline no-action cluster`를 별도 row로 surface
- `registry_key = misread:semantic_baseline_no_action_cluster`
- `result_type = result_unresolved`
- `explanation_type = explanation_gap`
- 일반 detector feedback과 동일하게 `맞았음 / 과민했음 / 놓쳤음 / 애매함`을 받을 수 있다

## proposal lane

- manual propose snapshot에 `semantic_cluster_candidates` 섹션 추가
- 기존 손익 기반 problem pattern과 섞지 않고 별도 observe 후보로 표시
- detector feedback이 아직 없어도 반복 cluster가 충분하면 review backlog로 올린다

## 기대 결과

- BTCUSD semantic no-action 군집이 detector/feedback/proposal 언어로 이어진다
- 운영자는 semantic threshold를 바로 건드리지 않고도
  어떤 observe cluster가 실제로 불편을 만드는지 피드백으로 좁힐 수 있다
