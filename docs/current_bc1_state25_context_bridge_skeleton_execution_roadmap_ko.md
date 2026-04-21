# BC1 State25 Context Bridge Skeleton 실행 로드맵

## 목표

`state25_context_bridge.py`의 skeleton을 먼저 구현해서,
BC2 이후 translator가 들어와도 흔들리지 않는 contract / trace / gating 틀을 고정한다.


## BC1-1. Contract / Meta 고정

목표:
- contract version과 skeleton stage를 고정

구현 항목:
- `STATE25_CONTEXT_BRIDGE_CONTRACT_VERSION`
- `bridge_stage = BC1_SKELETON`
- `translator_state = SKELETON_ONLY`

완료 기준:
- 서비스 출력이 어떤 단계인지 한눈에 구분 가능


## BC1-2. Intake Normalize

목표:
- runtime row에서 필요한 입력만 안정적으로 읽기

구현 항목:
- symbol / stage / side normalize
- interpreted context 필드 normalize
- age/confidence/band normalize
- overlap source 존재 여부 normalize

완료 기준:
- 입력이 비어 있거나 타입이 흔들려도 안전하게 기본값 반환


## BC1-3. Freshness / Activation

목표:
- translator 이전에 component activation 틀을 먼저 만들기

구현 항목:
- HTF freshness state
- previous_box freshness state
- component activation
- component activation reasons

완료 기준:
- HTF / previous_box / late_chase / share activation이 숫자와 이유로 같이 보임


## BC1-4. Guard / Failure Skeleton

목표:
- overlap / stale / low confidence를 translator 이전에 잡을 수 있게 하기

구현 항목:
- `overlap_sources`
- `overlap_class`
- `double_counting_guard_active`
- `failure_modes`
- `guard_modes`

완료 기준:
- 왜 translator가 아직 약하거나 꺼져 있어야 하는지 구조적으로 보임


## BC1-5. Trace Skeleton

목표:
- BC2 이후에도 유지할 공통 trace 구조를 먼저 고정

구현 항목:
- `trace_reason_codes`
- `trace_lines_ko`
- `decision_counterfactual` placeholder
- `bridge_decision_id`
- `hindsight_link_key`
- `proposal_link_key`
- `override_scope`
- `override_scope_detail`

완료 기준:
- 사람용 trace와 기계용 trace가 동시에 존재


## BC1-6. Tests

목표:
- skeleton이 안정적으로 기본 contract를 반환하는지 검증

최소 테스트:
1. 빈 row에서도 안정적으로 contract 반환
2. freshness / activation / reasons 계산 확인
3. overlap source가 있으면 guard mode가 채워지는지 확인


## 구현 우선순위

1. `state25_context_bridge.py` 파일 생성
2. contract/meta 기본 함수
3. intake normalize
4. freshness/activation
5. guard/failure
6. trace skeleton
7. 단위 테스트


## 이번 단계에서 하지 않는 것

- 실제 weight delta 계산
- 실제 threshold delta 계산
- 실제 size delta 계산
- runtime export 합류
- detector/propose 연결
- bounded live


## 완료 후 다음 단계

BC1 완료 후 바로 이어질 자연스러운 순서는 아래다.

1. `BC2 Weight-Only Translator`
2. `BC3 Runtime Trace Export`

즉 BC1은 translator를 넣기 전에 **틀을 잠그는 단계**다.
