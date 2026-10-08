# 3교시 · 온톨로지에 따른 지식 추출

업무 원문에서 직접 호출 후보·별칭·개체를 추출하고, 사람이 검토한 사실을 다음 교시 입력으로 분리합니다.

Python 3.9 이상과 로그인된 LLM CLI가 필요합니다. Wirelog 설치 없이 이 폴더만으로 실행할 수 있습니다. 2교시 타입·관계 사전의 복사본을 `ontology/`에 보관하고 모든 LLM 단계의 입력에 포함합니다. `svc:` 접두사는 표준 서비스 ID를 사용하기 위해 제외합니다.

## 첫 실행

프로젝트 루트의 터미널에서 실행합니다.

```sh
cd ~/git/llmwiki-demos/part03
python3 run_lesson3.py --cli agy --task extract --overwrite
python3 validate_assertions.py assertions.jsonl --status pending
```

`--dry-run`은 실제 프롬프트와 원문을 `runs/`에 만들고 LLM은 호출하지 않습니다. 실제 실행은 원문 5개·온톨로지 사전과 `prompt.txt`를 `agy -p`로 전달하고 응답을 `assertions.jsonl`에 저장합니다. 기존 내용은 실행 기록의 `previous.jsonl`에 백업합니다.

검사에서 오류가 나오면 원문과 대조해 후보 파일을 수정한 뒤 다시 검사합니다. 배포된 TODO 템플릿과 빈 `approved.jsonl`이 검사에 실패하는 것은 정상입니다.

## review.csv를 직접 수정하고 반영하는 실습

LLM 호출 없이 별도 실습 폴더에서 CSV 편집을 연습하려면 다음 명령을 실행합니다.

```sh
python3 review_walkthrough.py --interactive
```

1. 화면에 표시된 **절대 경로의 `review.csv`**를 편집기로 엽니다. 원래 `part03/review.csv`와 다른 파일입니다.
2. 첫 단계에서는 방향 오류를 넣은 F03 r2의 `판정`을 `rejected`로 바꾸고 `근거 또는 이유`, `검토자`를 입력합니다. 나머지 행은 그대로 둡니다. `id`, `revision`, `content_sha256`은 변경하지 않습니다.
3. 파일을 저장하고 터미널에서 Enter를 누릅니다. 시연은 `import-review`와 같은 `Store.import_csv()` 경로로 **저장한 CSV를 읽어** DB와 이력에 반영합니다. 오류가 있으면 저장하지 않고 재편집을 기다립니다.
4. 시연이 후보를 pay → ledger로 교정하면 F03 r3가 `pending`이 됩니다. 편집기에서 새 `review.csv`를 다시 열고, 화면에 안내된 최신 버전의 승인·보류·반려 판정과 이유·검토자를 입력합니다.
5. 저장 후 Enter를 누르면 CSV를 다시 반영하고 결과를 내보냅니다. 승인 3개·보류 1개·반려 5개와 F03의 반려 → 수정 → 승인 이력을 확인합니다.

각 단계의 `01-reject-before.csv`, `01-reject-edited.csv`, `02-rereview-before.csv`, `02-rereview-edited.csv`로 편집 전후를 비교할 수 있습니다. `review_history.json`에는 반영된 판정과 수정 이력이 남습니다. 실습 도중 `q`로 종료하면 작업 파일은 보존합니다. 이 모드는 교육용 오류 사례를 사용하며 원래 후보와 검토 DB는 변경하지 않습니다.

`--interactive`를 빼면 같은 CSV 편집·반영 과정을 교육용 판정으로 자동 시연합니다.

## CLI 선택

`--cli agy`를 사용하는 도구의 실행 파일 이름으로 바꾸세요.

| 도구 | 지정 값 | 내부 호출 |
| --- | --- | --- |
| Antigravity | `agy` | `agy -p 프롬프트본문` |
| Claude | `claude` | `claude --output-format text -p 프롬프트본문` |
| Cursor | `cursor-agent` | `cursor-agent --output-format text -p 프롬프트본문` |
| GitHub Copilot | `copilot` | `copilot --silent -p 프롬프트본문` |
| Codex | `codex` | `codex exec`의 표준 입력 |

Codex의 `-p`는 프로필 옵션이므로 공통 실행기가 `exec`로 연결합니다. Cursor 실행 파일이 `agent`이면 해당 이름 또는 절대 경로를 지정합니다. 모델 옵션은 `--cli-arg=--model --cli-arg=모델명`처럼 인자별로 전달합니다.

## 원문과 추출 범위

`raw/`에는 ARCH-01 v1·v2, ADR-07 v1, INC-03 v1, GLOSS-01 v1이 있습니다. 2교시에서 보류했던 명칭은 이번에 GLOSS-01을 직접 읽고 판단합니다. OPS-04·RUN-02 전문은 포함하지 않았습니다.

- 관계: 내부 Service 간 직접 HTTP 호출인 `depends_on`만 추출합니다.
- 별칭: 명시적인 근거가 있는 표현만 표준 ID에 연결합니다.
- 개체: API의 메서드·경로·제공 서비스, 호출 구간별 타임아웃, 담당 팀을 분리합니다.
- 제외: DB·배치·간접 경로를 직접 Service 호출 사실로 적재하지 않습니다.
- 상태: ARCH-01 v2 검토안을 현재 운영 배포 사실로 취급하지 않습니다.

## 실습 A: 후보·별칭·개체 추출

추출 후보를 검토한 뒤 다음 단계를 실행합니다.

```sh
python3 run_lesson3.py --cli agy --task aliases --overwrite
python3 run_lesson3.py --cli agy --task entities --overwrite
```

| 단계 | 프롬프트 | 원문 외 추가 입력 | 출력 |
| --- | --- | --- | --- |
| extract | `prompt.txt` | 없음 | `assertions.jsonl` |
| aliases | `prompts/aliases.txt` | 없음 | `aliases.json` |
| entities | `prompts/entities.txt` | 후보·별칭 | `entities.json` |
| review | `prompts/review.txt` | 후보·별칭·개체·오류 예문 | `review_suggestions.md` |

JSONL은 한 줄에 JSON 객체 하나입니다. `source_id`, `version`, `section`, `quote`로 원문 위치와 정확한 인용을 보존합니다. 후보의 `review_status`는 `pending`, `reviewer`는 빈 문자열이어야 합니다.

`document_status`는 원문 문서의 상태이고 `review_status`는 추출 결과의 검토 상태입니다. 승인된 문서를 읽었다고 추출 결과까지 자동 승인되는 것은 아닙니다.

## 실습 B: 오류 후보와 문서 상태 검토

```sh
python3 run_lesson3.py --cli agy --task review --overwrite
```

`review_suggestions.md`는 LLM의 검토 제안이며 최종 판정은 사람이 합니다. 이제 **반려·보류 → 내용 수정 또는 재검토 요청 → 새 버전 검토**를 지원합니다. [후보별 수정·재검토 안내](REVIEW_WORKFLOW.md)를 따라 진행하세요.

```sh
python3 review_workflow.py init
python3 review_workflow.py list
```

`review.csv`의 `id`, `revision`, `content_sha256`은 유지하고 `판정`, `근거 또는 이유`, `검토자`를 작성합니다. 일부만 검토했으면 다음 명령으로 판정만 저장합니다.

```sh
python3 review_workflow.py import-review
```

후보를 수정하려면 파일로 꺼내 편집한 후 새 버전을 등록합니다. 다음의 버전 번호는 실제 `list` 결과에 맞추세요.

```sh
python3 review_workflow.py show F03 --output corrected-F03.json
# corrected-F03.json을 원문에 맞게 편집
python3 review_workflow.py revise F03 --revision 1 --file corrected-F03.json --actor "수정자 이름" --reason "수정 이유와 원문 위치"
python3 review_workflow.py history F03
```

수정된 후보는 r2의 `pending` 상태가 됩니다. 이전 승인·반려는 이력에 남고 새 내용에 자동 적용되지 않습니다. 내용 변경 없이 판정만 재검토하려면 `reopen`을 사용합니다. 잘못된 인용, 이전 버전 CSV, 이미 끝난 판정의 덮어쓰기는 거부됩니다.

모든 후보의 최신 버전을 검토한 뒤:

```sh
python3 export_review.py --overwrite
python3 validate_assertions.py approved.jsonl --status approved
```

`approved.jsonl`은 최신 승인 사실, `held.json`·`rejected.json`은 최신 보류·반려입니다. `review_history.json`과 `.review/state.sqlite3`에는 후보별 전체 버전, 수정 전후 내용, 수정자·검토자·이유·시각이 남습니다. 원래의 E 오류 예문은 직접 승인할 수 없지만 완전한 assertion으로 명시적으로 수정한 새 버전은 재검토할 수 있습니다.

후보 수정·재검토 요청·판정 변경은 기존 승인 파일을 즉시 무효화합니다. 4교시에서도 메타데이터와 현재 후보 버전을 확인해 오래된 결과의 사용을 차단합니다. `review.md`에는 별칭·API·담당 팀에 대한 별도 검토도 기록하세요. 이 기능은 사람을 대신해 관계의 의미나 실제 검토 여부를 승인하지 않습니다.

## 전체 시연

```sh
python3 run_lesson3.py --cli agy --task all --overwrite
```

네 번의 LLM 호출로 추출 → 별칭 → 개체 → 검토 제안을 순서대로 생성합니다. 검토 저장소가 있으면 변경된 추출 후보를 새 pending 버전으로 등록하고 검토 CSV를 갱신하며 기존 승인 파일을 무효화합니다. 변경이 없는 재추출은 사람의 수정 버전을 덮어쓰지 않습니다. 전체 생성이 성공하면 검토 저장소가 없는 경우 초기화하고 `review.csv`의 절대 경로와 아래 후속 명령을 안내합니다.

`review.csv`를 편집·저장한 뒤 다음 명령으로 실제 판정을 반영하고 확인합니다. 일부만 검토했다면 나머지 행은 `pending`과 빈 검토자로 둡니다. 미리 채운 근거 또는 작성 중인 근거는 그대로 남겨도 됩니다.

```sh
python3 review_workflow.py import-review
python3 review_workflow.py list
python3 review_workflow.py history F03
# 모든 후보의 최신 버전을 검토한 뒤 실행
python3 export_review.py --overwrite
```

CSV 저장만으로 판정이 반영되지는 않습니다. `import-review`가 DB와 이력에 저장하고, `export_review.py`가 최신 승인·보류·반려 파일을 내보냅니다.

중간 오류나 선행 입력의 TODO가 발견되면 중단합니다. 이미 성공한 파일과 기록은 남으므로 실패한 단계부터 다시 실행할 수 있습니다.

## 공통 실행기 직접 사용

`-p`는 프롬프트 파일, `-c`는 참고 원문, `-o`는 결과 파일입니다.

```sh
python3 run_prompt.py --cli agy -p prompt.txt -c raw/ARCH-01_v1.md -c raw/ADR-07_v1.md -c raw/INC-03_v1.md -c raw/GLOSS-01_v1.md -c raw/ARCH-01_v2.md -o assertions.jsonl --overwrite
```

입력은 `runs/날짜-고유번호/input.txt`, 응답은 `stdout.txt`, 오류는 `stderr.txt`, 실행 상태는 `run.json`에 기록합니다. CLI 실패·빈 응답·시간 초과 시 기존 결과를 교체하지 않습니다. 기본 제한은 호출당 300초이며 `--timeout 600`처럼 바꿀 수 있습니다.

## 확인할 산출물

후보·별칭·개체, LLM 검토 제안, 사람이 작성한 검토 CSV·기록, 승인·보류·반려 결과와 실행 기록을 확인합니다. `review.example.csv`는 최종 교육자료를 바탕으로 한 강사 시연용 판정 예시입니다. 원문은 실무 문서 형식을 재현한 교육용 합성 사례입니다.

```sh
python3 check_links.py .
```

링크 검사는 Markdown의 상대 파일 경로만 확인합니다. `validate_assertions.py`는 실제 `raw/`에서 문서 상태·절·인용을 읽어 후보 구조와 대조합니다. 별칭과 개체 파일의 정확성은 원문과 직접 비교하세요.

후보 내용은 `python3 review_workflow.py show F03`의 `payload`에서 확인합니다. [후보·원문 조회 및 해시 비교 방법](REVIEW_WORKFLOW.md#후보-내용은-어디서-보는가)을 먼저 읽고 CSV를 편집하세요.

## 강사 시연

실제 LLM 산출물을 포함하므로 파일을 열어 설명하거나 전체 명령으로 다시 생성할 수 있습니다.

승인·보류·반려 내보내기도 바로 시연하려면 다음 명령을 실행합니다.

```sh
python3 export_review.py --example --overwrite
python3 validate_assertions.py example_output/approved.jsonl --status approved
```

결과는 `example_output/`에 승인 3개·보류 1개·반려 5개로 생성됩니다. 이는 **교육용 판정 예시**이며 학습자의 실제 승인과 구분됩니다. 본인 실습에서는 `review.csv`를 작성하고 `--example` 없이 내보냅니다.

단계마다 JSON 구조·문서 번호·버전·절·정확한 인용을 검사하고 오류 시 중단합니다. 수정 후 해당 단계부터 다시 실행하세요. `--dry-run`은 선택적인 프롬프트 점검 용도이며 실제 실행을 대신하지 않습니다.

## 확인 문제

LLM 신뢰도만으로 원문에 없는 관계를 채택하지 않습니다. 한 출처가 철회되어도 다른 유효한 출처가 같은 관계를 지지하면 관계를 유지할 수 있으므로 근거를 출처별로 보관합니다.

## 재검토 흐름을 격리해서 시연

```sh
python3 review_walkthrough.py
python3 -m unittest discover -s tests -v
```

시연은 별도 runs 작업 공간에서 F03의 오류 버전, 반려, 교정, 재승인과 이전 CSV 차단을 확인합니다. 학습자의 실제 판정은 바꾸지 않습니다.
