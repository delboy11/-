# jobwatch

공고가 몇천 개 쌓여 있어도 대부분은 365일 올라와 있는 상주 공고(물류센터, 상하차, 상시채용 같은 것)입니다.
jobwatch는 이런 공고는 걸러내고, **진짜 새로 올라온 공고만** 텔레그램·디스코드·콘솔로 알려줍니다.

## 상주 공고를 거르는 규칙

| 규칙 | 설명 |
|---|---|
| 키워드 | 상시채용, 상시모집, 수시채용, 물류센터, 상하차, 쿠팡, CFS, 일용직, 당일지급 … (`extra_keywords`로 추가) |
| 재게시 | 같은 회사의 같은 제목 공고가 id만 바뀌어 다시 올라옴 (`[급구]`, `(주)` 같은 꾸밈말은 무시하고 비교) |
| 대량채용 | 한 회사가 14일 안에 5건 이상 올림 |
| 마감 유형 | 소스가 상시/수시 채용이라고 알려주는 경우 (사람인 `close-type`) |
| 오래된 공고 | 처음 봤을 때 이미 게시된 지 30일이 넘음 |
| 차단 회사 / 관심 키워드 | 직접 지정 |

한 번 본 공고는 SQLite(`jobwatch.db`)에 저장되므로 같은 공고로 알림이 두 번 오지 않습니다.
처음 실행할 때는 기존 공고를 기록만 하고 알림은 보내지 않습니다(알림 폭탄 방지).

## 사용법

```bash
pip install -r requirements.txt
cp config.example.yaml config.yaml   # 소스, 필터, 알림 설정
export SARAMIN_ACCESS_KEY=...         # 사람인 API를 쓰는 경우
export TELEGRAM_BOT_TOKEN=... TELEGRAM_CHAT_ID=...

python -m jobwatch run          # 한 번 확인
python -m jobwatch -v run       # 걸러진 공고와 이유도 출력
python -m jobwatch watch -i 600 # 10분마다 계속 확인
python -m jobwatch stats        # 공고를 쏟아내는 회사 순위
```

cron으로 돌려도 됩니다: `*/10 * * * * cd /path/to/jobwatch && python -m jobwatch run`

## 공고 소스

- `saramin`: 사람인 공식 API (access-key 필요, 검색 파라미터는 `params`에 그대로 넣음)
- `rss`: RSS/Atom 피드
- `json`: 로컬 JSON 파일 (직접 만든 크롤러 결과를 넘길 때)

다른 사이트를 붙이려면 `jobwatch/sources/base.py`의 `Source`를 상속해 `fetch()`가 `Job` 목록을 돌려주도록 구현한 뒤
`jobwatch/sources/__init__.py`의 `SOURCE_TYPES`에 등록하면 됩니다.

## 테스트

```bash
pip install pytest && python -m pytest
```
