# Current Telegram Alert Message Refresh

## 목적

텔레그램 알림을 `영문 필드 나열형`에서 `운영 판단에 바로 쓰는 한국어 요약형`으로 정리한다.

이번 정리의 핵심은 두 가지다.

1. 실시간 진입/대기/청산은 계속 자동으로 두고, 텔레그램은 개선안 승인 콘솔로만 쓴다.
2. 손익 보고는 `얼마 벌었는지`, `비용이 얼마였는지`, `얼마나 자주 어떤 이유로 진입/청산했는지`가 바로 보이게 만든다.

## 손익 요약 개편

손익 요약은 아래 6개 구간에 동일하게 적용한다.

- `15분`
- `1시간`
- `4시간`
- `1일`
- `1주`
- `1달`

각 구간 메시지는 아래 항목을 기본으로 보여준다.

- `순손익 합계`
- `총손익(비용 전)`
- `총 비용`
- `진입 횟수(마감 기준)`
- `총 진입 랏`
- `승/패`, `승률`
- `구간 시작 잔고(추정)`, `구간 종료 잔고(추정)`
- `진입 사유 TOP 5`
- `청산 사유 TOP 5`
- `기준 시각`

## 잔고 표시 원칙

정확한 historical balance snapshot이 구간별로 저장돼 있지 않으면, 잔고는 아래 방식으로 추정한다.

- 현재 계좌 잔고를 기준점으로 사용
- 대상 구간 종료 이후의 실현손익을 역산
- 그 결과로 `구간 종료 잔고(추정)` 계산
- 대상 구간 손익을 한 번 더 역산해서 `구간 시작 잔고(추정)` 계산

계좌 잔고 스냅샷을 읽지 못하면 아래 문구로 대체한다.

- `잔고 변화: 계좌 잔고 스냅샷이 아직 연결되지 않아 계산을 보류했습니다.`

즉 이 항목은 `추정치`임을 계속 명시한다.

## 사유 표시 원칙

진입/청산 사유는 raw reason을 그대로 던지지 않고, 가능한 경우 **설명 가능한 한국어 문장**으로 바꾼다.
중요한 점은 `진입 사유`와 `청산 사유`가 **같은 taxonomy를 쓰지 않는다**는 것이다.

- 진입 사유: 왜 들어갔는지
- 청산 사유: 왜 나왔는지

즉 같은 raw token이 들어 있어도 맥락이 다르면 다른 의미로 읽는다.

예:

- `reclaim -> 리클레임 진입`
- `probe -> 탐색 진입`
- `target -> 목표가 청산`
- `runner -> 러너 청산`
- `cut -> 컷 청산`

긴 내부 reason은 아래처럼 `설명 문장 + 기능 조각`으로 보여준다.

- `플랫 상태에서 리클레임 재진입 준비 (플랫, 리클레임, 재진입, 준비)`
- `손실 보호 목적 청산 (보호, 손실, 청산)`

즉 목표는 `카테고리 이름 예쁘게 붙이기`가 아니라,
`나중에 학습/조정할 때 사람이 이유를 바로 읽고 바꿀 수 있게 만드는 것`이다.

즉 `한국어 요약 + raw reason`을 함께 남겨서, 사람이 읽기 쉽고 디버깅도 가능하게 한다.

## 진입/청산 사유 TOP 5 형식

각 항목은 아래 형식으로 보여준다.

- `사유명 | n건 | 비중 xx.x% | 승률 xx.x% | 순손익 +x.xx USD`

이렇게 하면 단순히 많이 나온 이유뿐 아니라,

- 어떤 이유로 자주 들어갔는지
- 그 이유의 승률이 어땠는지
- 결국 돈을 벌었는지 잃었는지

까지 한 줄에서 같이 볼 수 있다.

## 실시간 알림 원칙

실시간 진입/청산 알림은 `설명 없는 raw score`를 더 이상 전면에 두지 않는다.

실시간 진입 알림은 아래 중심으로 정리한다.

- `실시간 진입 알림`
- `시각`
- `심볼`
- `방향`
- `가격`
- `수량`
- `진입 근거`
- `보유 포지션`

실시간 청산 알림은 아래 중심으로 정리한다.

- `실시간 청산 알림`
- `시각`
- `심볼`
- `결과`
- `손익`
- `청산 근거`

## 체크 카드 원칙

체크 카드는 아래 형태를 기본으로 유지한다.

- `권장 조치`
- `판단 강도: 높음/보통/낮음 (confidence 0.xx)`
- `근거 수준`
- `트리거`
- `범위`
- `결정 기한`

즉 텔레그램에서 사람이 보는 것은 `정체 불명의 점수`가 아니라,
`지금 어떤 개선안 후보가 왜 올라왔는지`가 되어야 한다.

## 운영 경계

이 문서의 변경은 `메시지 표현`과 `보고 구조`에 대한 것이다.

운영 경계는 아래를 유지한다.

- 실시간 `entry / wait / exit`는 자동 실행
- 텔레그램 승인/거부/보류는 `학습 결과 반영`, `bounded canary`, `closeout`, `handoff`에만 사용
- `tgops` live approval route는 기본 비활성
- `tgbridge` improvement approval route가 기본 경로

## 관련 파일

- [telegram_ops_service.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/telegram_ops_service.py)
- [telegram_notification_hub.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/telegram_notification_hub.py)
- [telegram_update_poller.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/telegram_update_poller.py)
- [notifier.py](/C:/Users/bhs33/Desktop/project/cfd/backend/integrations/notifier.py)

## 함께 볼 문서

- [current_telegram_dual_room_inbox_pattern_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_telegram_dual_room_inbox_pattern_ko.md)
