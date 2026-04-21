# BC11 State25 Bounded Live Activation Canary 실행 로드맵

## 실행 순서

1. latest runtime / detect / propose / readiness artifact에서 fresh weight 후보 재표출 확인
2. 심볼별 KPI 기준으로 첫 canary symbol과 stage를 확정
3. `weight bounded live`를 `symbol 1개 + stage 1개` 범위로 apply
4. execution diff / continuation accuracy / guard / promotion KPI를 짧은 canary 윈도우 동안 관찰
5. `READY / HOLD / BLOCKED` 판정
6. weight canary가 통과하면 같은 심볼/스테이지에서 `threshold bounded live`로 확장
7. threshold는 symbol별 delta 계약 충돌이 없을 때만 진행
8. `size`는 마지막 단계로 보류

## 체크포인트

### CP1. Fresh candidate

- `state25 weight review`가 detector/propose에 다시 surface
- runtime row에서 requested/effective가 실제로 찍힘

### CP2. Canary scope

- 첫 canary 심볼 1개
- stage 1개
- cap과 allowlist 명시

### CP3. Weight apply

- `active_candidate_state.json`이 `bounded_live` 범위로 실제 승격
- rollback 기준 즉시 사용 가능

### CP4. Canary observation

- 1시간 batch KPI
- 일간 readiness
- execution diff live trace
- degraded mode / invalidation 감시

### CP5. Threshold decision

- weight canary 통과 시에만 threshold canary 검토
- symbol별 threshold delta 계약 정리 필수

## 적용 우선순위

1. `weight bounded live`
2. `threshold bounded live`
3. `size`

## 운영 원칙

- 전체 전환 금지
- fresh 후보 없는 apply 금지
- blocker면 즉시 `BLOCKED`
- 경고 band면 기본 `HOLD`
- rollback과 invalidation을 분리

## 산출물

- bounded-live canary 적용 기록
- `active_candidate_state.json` 변경
- readiness / KPI artifact
- canary 결과 판정 메모
