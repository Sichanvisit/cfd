# Teacher-Label Micro-Structure Top10 Step 7 상세 기준서

## 목표

Step 7의 목적은 `teacher-state 25`를 단순 이름표로 두지 않고, 현재 시스템이 계산하는 `micro-structure Top10`과 기존 state/forecast 흐름 위에 실제로 연결하는 것이다.

이번 단계의 핵심 산출물은 아래 질문에 답하는 것이다.

- 각 teacher-state를 가장 잘 설명하는 micro field는 무엇인가
- 그 pattern에서 진입/기다림/청산 중 무엇이 기본 행동이어야 하는가
- micro Top10만으로 부족할 때 어떤 기존 state/forecast field를 같이 봐야 하는가

## Step 7에서 고정할 원칙

1. 한 pattern에는 `핵심 micro field 2~4개`만 뽑는다
2. micro field만으로 부족한 경우에만 기존 state/forecast field를 보조 근거로 붙인다
3. teacher-state는 학습 입력의 대체물이 아니라 `해석용/정답용 상위 레이어`다
4. casebook은 사람이 읽을 수 있어야 하고, 나중에 compact daily dataset으로도 축약 가능해야 한다

## 이번 단계에서 만들 bridge 구조

각 pattern마다 아래 6칸을 고정한다.

- `주패턴`
- `보조패턴 가능 조합`
- `핵심 micro field 2~4개`
- `같이 볼 기존 시스템 field`
- `행동 바이어스`
- `왜 이 필드 조합이 이 패턴을 설명하는가`

## Step 7에서 기대하는 효과

- teacher-state 25를 나중에 사람이 수동 라벨링할 때 기준이 흔들리지 않는다
- micro Top10을 실제로 어떤 패턴과 연결해야 하는지 명확해진다
- 이후 daily compact dataset에서 pattern별 field importance를 줄이거나 늘리는 근거가 생긴다

## 구현 성격

- 이번 단계는 코드보다 문서/케이스북 산출물이 중심이다
- production code 수정이 꼭 필요한 단계는 아니다
- 다만 이후 자동 라벨 추천기를 만들려면 이 문서가 기준서 역할을 한다
