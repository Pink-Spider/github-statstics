# GitHub 활동 통계 도구

인사평가 첨부자료용 GitHub 활동 내역 보고서 생성 도구

## 기능

- Commits 내역 조회 및 통계
- Pull Requests 내역 조회 및 통계
- Issues 내역 조회 및 통계
- Code Review 활동 조회
- 레포지토리별 활동 분류
- **Private Repository 지원**
- **브랜치별 조회 지원** (default / 특정 브랜치 / 모든 브랜치)
- Markdown 형식 보고서 출력

## 사전 요구사항

### 1. GitHub CLI (gh) 설치

```bash
# macOS
brew install gh

# Windows
winget install GitHub.cli

# Linux
sudo apt install gh
```

### 2. GitHub CLI 인증 (필수)

```bash
gh auth login
```

> **중요**: `gh auth login`으로 인증하면 Private Repository도 자동으로 조회됩니다.

## 사용법

### 기본 사용 (최근 6개월)

```bash
python github_stats.py
```

### 특정 기간 조회

```bash
# 2025년 전체
python github_stats.py --since 2025-01-01 --until 2025-12-31

# 2024년 하반기
python github_stats.py --since 2024-07-01 --until 2024-12-31
```

### 특정 사용자 조회

```bash
python github_stats.py --user octocat
```

### 특정 조직 내 활동 조회

```bash
python github_stats.py --org my-organization
```

### 파일로 저장

```bash
python github_stats.py --output report.md
```

### 브랜치 지정

```bash
# 기본값: default branch (main/master)만 조회
python github_stats.py

# 특정 브랜치만 조회 (main, develop)
python github_stats.py --branch main develop

# 모든 브랜치 조회
python github_stats.py --all-branches
```

### 코드 리뷰 제외 (속도 향상)

```bash
python github_stats.py --no-reviews
```

### 조합 예시

```bash
# 2025년 전체 활동을 파일로 저장
python github_stats.py \
  --since 2025-01-01 \
  --until 2025-12-31 \
  --output 2025_활동보고서.md

# 특정 조직의 main, develop 브랜치 활동
python github_stats.py \
  --org my-company \
  --since 2025-01-01 \
  --until 2025-12-31 \
  --branch main develop \
  --output report.md

# 모든 브랜치, 코드 리뷰 제외 (빠른 조회)
python github_stats.py \
  --all-branches \
  --no-reviews \
  --output report.md
```

## 옵션 설명

| 옵션 | 단축 | 설명 | 기본값 |
|------|------|------|--------|
| `--user` | `-u` | GitHub 사용자명 | 현재 인증된 사용자 |
| `--since` | `-s` | 시작 날짜 (YYYY-MM-DD) | 6개월 전 |
| `--until` | `-e` | 종료 날짜 (YYYY-MM-DD) | 오늘 |
| `--org` | `-o` | 조직명 (조직 내 활동만 조회) | - |
| `--output` | `-f` | 출력 파일 경로 | 터미널 출력 |
| `--branch` | `-b` | 특정 브랜치만 조회 | default branch |
| `--all-branches` | - | 모든 브랜치 조회 | False |
| `--no-reviews` | - | 코드 리뷰 조회 제외 (속도 향상) | False |

## 출력 예시

```markdown
# GitHub 활동 보고서

**작성자**: dev-minimalism
**조직**: Level-Up-Together
**기간**: 2025-01-01 ~ 2025-12-31
**생성일시**: 2026-01-26 11:30:27

---

## 활동 요약

| 항목 | 건수 |
|------|------|
| Commits | 304 |
| Pull Requests | 12 |
| Issues | 5 |
| Code Reviews | 8 |
| **총 활동** | **329** |

## 레포지토리별 활동

| Repository | Commits | PRs | Issues |
|------------|---------|-----|--------|
| my-org/project-a | 120 | 5 | 2 |
| my-org/project-b | 95 | 4 | 2 |
| my-org/project-c | 89 | 3 | 1 |
```

## 주의사항

- `gh auth login`으로 인증해야 Private Repository 조회 가능
- GitHub API Rate Limit: 5000 requests/hour (인증된 사용자)
- 레포지토리가 많은 경우 조회에 시간이 걸릴 수 있음
- `--no-reviews` 옵션으로 속도 향상 가능
- `--all-branches` 사용 시 조회 시간이 길어질 수 있음
