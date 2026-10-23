# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 개요

GitHub 활동(Commits, PRs, Issues, Code Reviews)을 모아 Markdown 보고서를 만드는 CLI 도구다. 인사평가 첨부자료 용도.

- 코드 전체가 `github_stats.py` 파일 하나에 있다.
- 외부 Python 패키지를 쓰지 않는다. 대신 GitHub CLI(`gh`)를 subprocess로 호출한다. `requirements.txt`는 비어 있다.
- Python 3.10 이상이 필요하다 (`str | None`, `list[str]` 문법을 `__future__` import 없이 쓴다).
- README, 주석, 로그 메시지, 커밋 메시지는 모두 한국어로 쓴다.

## 명령어

테스트, 린트, 빌드 설정은 없다.

```bash
# 사전 조건 (한 번만). 이걸로 로그인해야 private repo가 조회된다.
gh auth login

# 실행. 이 머신에는 `python`이 없고 `python3`만 있다 (README는 `python`으로 적혀 있음).
python3 github_stats.py --help
python3 github_stats.py --since 2025-01-01 --until 2025-12-31 --output report.md

# 빠른 동작 확인. --no-reviews를 붙이면 API 호출이 크게 줄어 훨씬 빨리 끝난다.
python3 github_stats.py --org <org> --no-reviews --since 2025-10-01

# 문법 검사
python3 -m py_compile github_stats.py
```

## 동작 흐름

`main()`은 한 번 실행하면 다음 순서로 진행된다.

1. `load_env()`가 스크립트 옆 `.env`를 읽어 `os.environ`에 넣는다. 이미 있는 환경변수는 덮어쓰지 않는다.
2. 토큰을 확인한다. `--user`가 없으면 `gh api user`로 현재 로그인 사용자를 구한다.
3. `--org`가 있으면 `get_org_repos`, 없으면 `get_user_repos`가 `gh repo list`로 레포 목록(최대 500개)을 만든다. 두 함수는 내용이 같다.
4. 레포마다 `get_repo_commits` → `get_repo_prs` → `get_repo_issues` → (`--no-reviews`가 없으면) `get_repo_reviews`를 순서대로 호출한다. 전부 `gh api repos/...` REST 호출이다.
5. `generate_markdown_report()`가 네 개의 리스트를 받아 Markdown 문자열 하나를 만든다.
6. 결과는 항상 파일로 쓴다. 진행 로그는 전부 stderr로 나간다.

## 알아둘 점 (코드를 한 번 읽어서는 잘 안 보이는 것)

- **토큰 우선순위**: `gh auth token`이 `GITHUB_TOKEN`/`GH_TOKEN` 환경변수와 `--token` 인자보다 우선한다. `gh`에 로그인되어 있으면 `.env`와 `--token`은 사실상 무시된다. gh 로그인 토큰이 private repo 권한을 갖고 있기 때문에 일부러 이렇게 했다.
- **`run_gh_command`는 호출마다 `gh auth token` subprocess를 새로 띄운다.** API 호출 1번에 subprocess 2번이 뜬다. 속도 문제를 다룰 때 여기부터 본다.
- **`run_gh_command`는 종료 코드를 보지 않는다.** stdout에 JSON이 있으면 파싱하고, 없으면 `None`을 돌려준다. API 에러도 조용히 `None`이 되므로 "0건"과 "조회 실패"를 구분할 수 없다.
- **출력 파일 기본값**: README는 "터미널 출력"이라고 적혀 있지만, 코드는 `--output`이 없으면 `github_report_{user|org}_{since}_{until}.md`로 저장한다. README와 코드가 다르다.
- **`.gitignore`가 `*.md`를 전부 무시한다** (생성된 보고서를 커밋하지 않기 위해). `README.md`와 `CLAUDE.md`만 예외다. 새 `.md` 파일을 커밋하려면 `.gitignore`에 `!파일명` 줄을 추가해야 한다.
- **항목마다 필터 방식이 다르다**:
  - Commits: `author`, `since`, `until`, `sha`(브랜치)를 서버 쿼리로 넘긴다. 브랜치를 여러 개 돌 때 SHA로 중복을 제거한다. 페이지네이션 있음.
  - PRs: `state=all`로 전부 받아 클라이언트에서 `user.login`과 `created_at`으로 거른다. 페이지네이션 있음.
  - Issues: `creator=`와 `since=`를 서버에 넘긴다. GitHub의 `since`는 "마지막 업데이트 시각" 기준이라 기간 전에 만든 이슈도 섞일 수 있다. 응답에 `pull_request` 키가 있으면 PR이므로 뺀다.
  - Reviews: PR 목록 첫 페이지(100개)만 본다. 페이지네이션 없음. 남이 만든 PR마다 `/reviews`를 한 번 더 호출하므로 가장 느리다. 한 PR은 한 번만 센다.
- 보고서 표에 넣는 문자열은 `|`만 이스케이프한다. 커밋 메시지는 첫 줄 80자, PR/Issue 제목은 60자로 자른다.
