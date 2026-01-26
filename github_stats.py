#!/usr/bin/env python3
"""
GitHub 활동 통계 도구 - 인사평가 첨부자료용
Commits, Pull Requests, Issues 활동 내역을 Markdown으로 출력
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from collections import defaultdict
from pathlib import Path


def load_env():
    """Load .env file"""
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip())


def get_gh_auth_token() -> str | None:
    """Get token from gh auth (has full repo access)"""
    # 환경변수 없이 실행해야 gh CLI 자체 인증 토큰을 가져옴
    clean_env = os.environ.copy()
    clean_env.pop("GITHUB_TOKEN", None)
    clean_env.pop("GH_TOKEN", None)

    try:
        result = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True,
            text=True,
            check=True,
            env=clean_env
        )
        return result.stdout.strip() if result.stdout.strip() else None
    except subprocess.CalledProcessError:
        return None


def get_token() -> str | None:
    """Get GitHub token - prefer gh auth token for full access"""
    # 1. 환경변수에서 명시적으로 설정된 토큰
    env_token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")

    # 2. gh auth token (gh CLI 인증 - repo 권한 포함)
    gh_token = get_gh_auth_token()

    # gh auth token을 우선 사용 (private repo 접근 가능)
    return gh_token or env_token


def run_gh_command(args: list[str], silent: bool = False) -> dict | list | None:
    """gh CLI 명령어 실행"""
    env = os.environ.copy()

    # gh auth token 우선 사용 (private repo 접근 가능)
    gh_token = get_gh_auth_token()
    if gh_token:
        env["GH_TOKEN"] = gh_token
        env.pop("GITHUB_TOKEN", None)  # GITHUB_TOKEN 제거
    else:
        # fallback: 환경변수 토큰 사용
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if token:
            env["GH_TOKEN"] = token

    try:
        result = subprocess.run(
            ["gh"] + args,
            capture_output=True,
            text=True,
            env=env
        )
        # stdout에 데이터가 있으면 파싱 시도 (return code와 무관하게)
        if result.stdout.strip():
            return json.loads(result.stdout)
        return None
    except json.JSONDecodeError:
        return None
    except Exception as e:
        if not silent:
            print(f"Error: {e}", file=sys.stderr)
        return None


def get_user_info() -> dict:
    """현재 인증된 사용자 정보 조회"""
    return run_gh_command(["api", "user"]) or {}


def get_user_repos(username: str) -> list[str]:
    """사용자의 모든 레포지토리 목록 조회 (private 포함)"""
    # gh auth token 사용 (private repo 접근 가능)
    env = os.environ.copy()
    gh_token = get_gh_auth_token()
    if gh_token:
        env["GH_TOKEN"] = gh_token
        # GITHUB_TOKEN이 있으면 제거 (gh auth token 우선)
        env.pop("GITHUB_TOKEN", None)

    try:
        result = subprocess.run(
            ["gh", "repo", "list", username, "--json", "nameWithOwner", "--jq", ".[].nameWithOwner", "--limit", "500"],
            capture_output=True,
            text=True,
            check=True,
            env=env
        )
        repos = [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]
        return repos
    except subprocess.CalledProcessError:
        return []


def get_org_repos(org: str) -> list[str]:
    """조직의 모든 레포지토리 목록 조회 (private 포함)"""
    # gh auth token 사용 (private repo 접근 가능)
    env = os.environ.copy()
    gh_token = get_gh_auth_token()
    if gh_token:
        env["GH_TOKEN"] = gh_token
        env.pop("GITHUB_TOKEN", None)

    try:
        result = subprocess.run(
            ["gh", "repo", "list", org, "--json", "nameWithOwner", "--jq", ".[].nameWithOwner", "--limit", "500"],
            capture_output=True,
            text=True,
            check=True,
            env=env
        )
        repos = [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]
        return repos
    except subprocess.CalledProcessError:
        return []


def get_repo_branches(repo: str) -> list[str]:
    """레포지토리의 브랜치 목록 조회"""
    url = f"repos/{repo}/branches?per_page=100"
    result = run_gh_command(["api", url], silent=True)

    if not result or not isinstance(result, list):
        return []

    return [branch["name"] for branch in result]


def get_repo_commits(repo: str, author: str, since: str, until: str, branches: list[str] = None, all_branches: bool = False) -> list[dict]:
    """레포지토리의 커밋 조회 (직접 API 호출)"""
    commits = []
    seen_shas = set()  # 중복 제거용

    # ISO 8601 형식으로 변환
    since_iso = f"{since}T00:00:00Z"
    until_iso = f"{until}T23:59:59Z"

    # 조회할 브랜치 목록 결정
    if all_branches:
        target_branches = get_repo_branches(repo)
        if not target_branches:
            target_branches = [None]  # default branch
    elif branches:
        target_branches = branches
    else:
        target_branches = [None]  # default branch만

    for branch in target_branches:
        page = 1
        while True:
            # URL query string 방식 사용
            url = f"repos/{repo}/commits?author={author}&since={since_iso}&until={until_iso}&per_page=100&page={page}"
            if branch:
                url += f"&sha={branch}"

            result = run_gh_command(["api", url], silent=True)

            if not result or not isinstance(result, list):
                break

            for commit in result:
                sha = commit["sha"]
                if sha in seen_shas:
                    continue  # 중복 제거
                seen_shas.add(sha)

                commits.append({
                    "repo": repo,
                    "sha": sha[:7],
                    "message": commit["commit"]["message"].split("\n")[0][:80],
                    "date": commit["commit"]["author"]["date"][:10],
                    "url": commit["html_url"]
                })

            if len(result) < 100:
                break
            page += 1

    return commits


def get_repo_prs(repo: str, author: str, since: str, until: str) -> list[dict]:
    """레포지토리의 PR 조회"""
    prs = []
    page = 1

    while True:
        url = f"repos/{repo}/pulls?state=all&per_page=100&page={page}"
        result = run_gh_command(["api", url], silent=True)

        if not result or not isinstance(result, list):
            break

        for pr in result:
            # 작성자 필터
            if pr.get("user", {}).get("login") != author:
                continue

            # 날짜 필터
            created = pr["created_at"][:10]
            if created < since or created > until:
                continue

            prs.append({
                "repo": repo,
                "number": pr["number"],
                "title": pr["title"][:60],
                "state": "merged" if pr.get("merged_at") else pr["state"],
                "created_at": created,
                "url": pr["html_url"]
            })

        if len(result) < 100:
            break
        page += 1

    return prs


def get_repo_issues(repo: str, author: str, since: str, until: str) -> list[dict]:
    """레포지토리의 Issue 조회 (PR 제외)"""
    issues = []
    page = 1

    while True:
        url = f"repos/{repo}/issues?state=all&creator={author}&since={since}T00:00:00Z&per_page=100&page={page}"
        result = run_gh_command(["api", url], silent=True)

        if not result or not isinstance(result, list):
            break

        for issue in result:
            # PR은 제외
            if "pull_request" in issue:
                continue

            created = issue["created_at"][:10]
            if created > until:
                continue

            issues.append({
                "repo": repo,
                "number": issue["number"],
                "title": issue["title"][:60],
                "state": issue["state"],
                "created_at": created,
                "url": issue["html_url"]
            })

        if len(result) < 100:
            break
        page += 1

    return issues


def get_repo_reviews(repo: str, author: str, since: str, until: str) -> list[dict]:
    """레포지토리에서 리뷰한 PR 조회"""
    reviews = []

    # 모든 PR 조회
    url = f"repos/{repo}/pulls?state=all&per_page=100"
    result = run_gh_command(["api", url], silent=True)

    if not result or not isinstance(result, list):
        return reviews

    for pr in result:
        # 본인이 작성한 PR은 제외
        if pr.get("user", {}).get("login") == author:
            continue

        # 날짜 필터
        updated = pr.get("updated_at", "")[:10]
        if updated < since or updated > until:
            continue

        # 해당 PR의 리뷰 조회
        review_url = f"repos/{repo}/pulls/{pr['number']}/reviews"
        pr_reviews = run_gh_command(["api", review_url], silent=True)

        if pr_reviews and isinstance(pr_reviews, list):
            for review in pr_reviews:
                if review.get("user", {}).get("login") == author:
                    reviews.append({
                        "repo": repo,
                        "number": pr["number"],
                        "title": pr["title"][:60],
                        "url": pr["html_url"],
                        "state": review.get("state", "")
                    })
                    break  # 같은 PR은 한 번만 카운트

    return reviews


def generate_markdown_report(
    user: str,
    period_start: str,
    period_end: str,
    commits: list[dict],
    prs: list[dict],
    issues: list[dict],
    reviews: list[dict],
    org: str = None
) -> str:
    """Markdown 형식의 보고서 생성"""

    lines = []

    # 헤더
    lines.append(f"# GitHub 활동 보고서")
    lines.append("")
    lines.append(f"**작성자**: {user}")
    if org:
        lines.append(f"**조직**: {org}")
    lines.append(f"**기간**: {period_start} ~ {period_end}")
    lines.append(f"**생성일시**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    # 요약
    lines.append("---")
    lines.append("")
    lines.append("## 활동 요약")
    lines.append("")
    lines.append("| 항목 | 건수 |")
    lines.append("|------|------|")
    lines.append(f"| Commits | {len(commits)} |")
    lines.append(f"| Pull Requests | {len(prs)} |")
    lines.append(f"| Issues | {len(issues)} |")
    lines.append(f"| Code Reviews | {len(reviews)} |")
    lines.append(f"| **총 활동** | **{len(commits) + len(prs) + len(issues) + len(reviews)}** |")
    lines.append("")

    # 레포지토리별 통계
    repo_stats = defaultdict(lambda: {"commits": 0, "prs": 0, "issues": 0})
    for c in commits:
        repo_stats[c["repo"]]["commits"] += 1
    for p in prs:
        repo_stats[p["repo"]]["prs"] += 1
    for i in issues:
        repo_stats[i["repo"]]["issues"] += 1

    if repo_stats:
        lines.append("## 레포지토리별 활동")
        lines.append("")
        lines.append("| Repository | Commits | PRs | Issues |")
        lines.append("|------------|---------|-----|--------|")
        for repo, stats in sorted(repo_stats.items(), key=lambda x: sum(x[1].values()), reverse=True):
            lines.append(f"| {repo} | {stats['commits']} | {stats['prs']} | {stats['issues']} |")
        lines.append("")

    # Commits 상세
    if commits:
        lines.append("---")
        lines.append("")
        lines.append("## Commits")
        lines.append("")
        lines.append(f"총 **{len(commits)}**건의 커밋")
        lines.append("")

        # 레포지토리별로 그룹화
        commits_by_repo = defaultdict(list)
        for c in commits:
            commits_by_repo[c["repo"]].append(c)

        for repo, repo_commits in sorted(commits_by_repo.items()):
            lines.append(f"### {repo}")
            lines.append("")
            lines.append("| 날짜 | SHA | 메시지 |")
            lines.append("|------|-----|--------|")
            for c in sorted(repo_commits, key=lambda x: x["date"], reverse=True):
                # 메시지에서 특수문자 이스케이프
                msg = c['message'].replace('|', '\\|')
                lines.append(f"| {c['date']} | [{c['sha']}]({c['url']}) | {msg} |")
            lines.append("")

    # Pull Requests 상세
    if prs:
        lines.append("---")
        lines.append("")
        lines.append("## Pull Requests")
        lines.append("")

        merged_prs = [p for p in prs if p["state"] == "merged"]
        closed_prs = [p for p in prs if p["state"] == "closed"]
        open_prs = [p for p in prs if p["state"] == "open"]

        lines.append(f"총 **{len(prs)}**건 (Merged: {len(merged_prs)}, Closed: {len(closed_prs)}, Open: {len(open_prs)})")
        lines.append("")
        lines.append("| 날짜 | Repository | # | 제목 | 상태 |")
        lines.append("|------|------------|---|------|------|")
        for p in sorted(prs, key=lambda x: x["created_at"], reverse=True):
            state_icon = {"merged": "[M]", "closed": "[C]", "open": "[O]"}.get(p["state"], "[ ]")
            title = p['title'].replace('|', '\\|')
            lines.append(f"| {p['created_at']} | {p['repo']} | [#{p['number']}]({p['url']}) | {title} | {state_icon} {p['state']} |")
        lines.append("")

    # Issues 상세
    if issues:
        lines.append("---")
        lines.append("")
        lines.append("## Issues")
        lines.append("")

        closed_issues = [i for i in issues if i["state"] == "closed"]
        open_issues = [i for i in issues if i["state"] == "open"]

        lines.append(f"총 **{len(issues)}**건 (Closed: {len(closed_issues)}, Open: {len(open_issues)})")
        lines.append("")
        lines.append("| 날짜 | Repository | # | 제목 | 상태 |")
        lines.append("|------|------------|---|------|------|")
        for i in sorted(issues, key=lambda x: x["created_at"], reverse=True):
            state_icon = "[C]" if i["state"] == "closed" else "[O]"
            title = i['title'].replace('|', '\\|')
            lines.append(f"| {i['created_at']} | {i['repo']} | [#{i['number']}]({i['url']}) | {title} | {state_icon} {i['state']} |")
        lines.append("")

    # Code Reviews 상세
    if reviews:
        lines.append("---")
        lines.append("")
        lines.append("## Code Reviews")
        lines.append("")
        lines.append(f"총 **{len(reviews)}**건의 PR 리뷰")
        lines.append("")
        lines.append("| Repository | # | 제목 |")
        lines.append("|------------|---|------|")
        for r in reviews:
            title = r['title'].replace('|', '\\|')
            lines.append(f"| {r['repo']} | [#{r['number']}]({r['url']}) | {title} |")
        lines.append("")

    # 푸터
    lines.append("---")
    lines.append("")
    lines.append("*이 보고서는 GitHub API를 통해 자동 생성되었습니다.*")

    return "\n".join(lines)


def main():
    # Load .env file
    load_env()

    parser = argparse.ArgumentParser(
        description="GitHub 활동 통계 도구 - 인사평가 첨부자료용",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  # 최근 6개월 활동 조회
  python github_stats.py

  # 특정 기간 조회 (2024년 하반기)
  python github_stats.py --since 2024-07-01 --until 2024-12-31

  # 특정 사용자의 활동 조회
  python github_stats.py --user octocat

  # 특정 조직 내 활동만 조회
  python github_stats.py --org my-company

  # 파일로 저장
  python github_stats.py --output report.md

  # 2024년 전체 활동을 파일로 저장
  python github_stats.py -s 2024-01-01 -e 2024-12-31 -f 2024_활동보고서.md

환경변수:
  GITHUB_TOKEN  GitHub Personal Access Token (private repo 접근용)
                .env 파일에 설정하거나 환경변수로 설정
        """
    )

    parser.add_argument(
        "--user", "-u",
        help="GitHub 사용자명 (기본값: 현재 인증된 사용자)"
    )
    parser.add_argument(
        "--since", "-s",
        help="시작 날짜 (YYYY-MM-DD, 기본값: 6개월 전)"
    )
    parser.add_argument(
        "--until", "-e",
        help="종료 날짜 (YYYY-MM-DD, 기본값: 오늘)"
    )
    parser.add_argument(
        "--org", "-o",
        help="조직명 (특정 조직 내 활동만 조회)"
    )
    parser.add_argument(
        "--output", "-f",
        help="출력 파일 경로 (기본값: 터미널 출력)"
    )
    parser.add_argument(
        "--no-reviews",
        action="store_true",
        help="코드 리뷰 활동 제외 (속도 향상)"
    )
    parser.add_argument(
        "--branch", "-b",
        nargs="+",
        help="특정 브랜치만 조회 (예: --branch main develop)"
    )
    parser.add_argument(
        "--all-branches",
        action="store_true",
        help="모든 브랜치의 커밋 조회 (기본값: default branch만)"
    )
    parser.add_argument(
        "--token", "-t",
        help="GitHub Personal Access Token (또는 .env의 GITHUB_TOKEN 사용)"
    )

    args = parser.parse_args()

    # Token from CLI argument
    if args.token:
        os.environ["GITHUB_TOKEN"] = args.token

    # Check token
    token = get_token()
    if token:
        print(f"Token: {'*' * 10}{token[-4:]}", file=sys.stderr)
    else:
        print("Token: 없음 (public repo만 조회 가능)", file=sys.stderr)

    # 사용자 확인
    if args.user:
        user = args.user
    else:
        user_info = get_user_info()
        if not user_info:
            print("Error: GitHub CLI 인증이 필요합니다.", file=sys.stderr)
            print("  1. 'gh auth login' 실행, 또는", file=sys.stderr)
            print("  2. .env 파일에 GITHUB_TOKEN 설정", file=sys.stderr)
            sys.exit(1)
        user = user_info.get("login", "")

    print(f"사용자: {user}", file=sys.stderr)

    # 기간 설정
    if args.until:
        until_date = args.until
    else:
        until_date = datetime.now().strftime("%Y-%m-%d")

    if args.since:
        since_date = args.since
    else:
        since_date = (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d")

    print(f"기간: {since_date} ~ {until_date}", file=sys.stderr)

    # 레포지토리 목록 조회
    if args.org:
        print(f"조직 '{args.org}'의 레포지토리 조회 중...", file=sys.stderr)
        repos = get_org_repos(args.org)
    else:
        print(f"사용자 '{user}'의 레포지토리 조회 중...", file=sys.stderr)
        repos = get_user_repos(user)

    print(f"  -> {len(repos)}개 레포지토리", file=sys.stderr)

    if not repos:
        print("Error: 조회 가능한 레포지토리가 없습니다.", file=sys.stderr)
        sys.exit(1)

    # 데이터 수집
    all_commits = []
    all_prs = []
    all_issues = []
    all_reviews = []

    # 브랜치 설정 출력
    if args.all_branches:
        print("브랜치: 모든 브랜치", file=sys.stderr)
    elif args.branch:
        print(f"브랜치: {', '.join(args.branch)}", file=sys.stderr)
    else:
        print("브랜치: default branch만", file=sys.stderr)

    for i, repo in enumerate(repos, 1):
        print(f"\r[{i}/{len(repos)}] {repo} 조회 중...                    ", end="", file=sys.stderr)

        commits = get_repo_commits(repo, user, since_date, until_date, branches=args.branch, all_branches=args.all_branches)
        all_commits.extend(commits)

        prs = get_repo_prs(repo, user, since_date, until_date)
        all_prs.extend(prs)

        issues = get_repo_issues(repo, user, since_date, until_date)
        all_issues.extend(issues)

        if not args.no_reviews:
            reviews = get_repo_reviews(repo, user, since_date, until_date)
            all_reviews.extend(reviews)

    print(file=sys.stderr)
    print(f"수집 완료!", file=sys.stderr)
    print(f"  Commits: {len(all_commits)}건", file=sys.stderr)
    print(f"  PRs: {len(all_prs)}건", file=sys.stderr)
    print(f"  Issues: {len(all_issues)}건", file=sys.stderr)
    print(f"  Reviews: {len(all_reviews)}건", file=sys.stderr)

    # 보고서 생성
    report = generate_markdown_report(
        user=user,
        period_start=since_date,
        period_end=until_date,
        commits=all_commits,
        prs=all_prs,
        issues=all_issues,
        reviews=all_reviews,
        org=args.org
    )

    # 출력 파일명 결정
    if args.output:
        output_file = args.output
    else:
        # 자동 파일명 생성: github_report_{user/org}_{since}_{until}.md
        target_name = args.org if args.org else user
        output_file = f"github_report_{target_name}_{since_date}_{until_date}.md"

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"보고서 저장됨: {output_file}", file=sys.stderr)


if __name__ == "__main__":
    main()
