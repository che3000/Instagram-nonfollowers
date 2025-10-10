#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IG Non-Followers – 互動版（含登入自動重試，CSV 含 full_name）
- 互動式詢問帳號 / 密碼（不顯示），若需要 備用驗證碼 會再詢問。
- 登入被 IG 擋下（fail / challenge / checkpoint）時，提示你到 App 允許，按 Enter 直接重試。
- Session 與 CSV 儲存在 data/（或 /app/data）。
- 進度條 + 節流/連線重試。
- CSV 欄位：username, full_name, profile_url
"""
from __future__ import annotations
import os
import sys
import csv
import time
import getpass
import traceback
from typing import Iterable, List, Tuple, Set, Optional
from datetime import datetime

from instaloader import Instaloader, Profile, exceptions
from tqdm import tqdm

# === 可調參數 ===
PROGRESS_STEP = 1
RATE_LIMIT_SLEEP = 90
CONNECTION_MAX_RETRIES = 5
OUTPUT_NON_FOLLOWERS = "non_followers.csv"
OUTPUT_FANS_NOT_FOLLOWED = "fans_you_dont_follow.csv"


def is_tty() -> bool:
    """檢查當前是否在互動式終端環境中。"""
    try:
        return sys.stdin.isatty()
    except (AttributeError, OSError):
        return False


def get_project_root() -> str:
    """取得專案根目錄路徑。"""
    return os.path.dirname(os.path.abspath(__file__))


def resolve_data_dir() -> str:
    """優先 /app/data（Docker 掛載），其次 ./data，否則建立 ./data。"""
    candidates = ["/app/data", os.path.join(get_project_root(), "data")]
    for path in candidates:
        if os.path.isdir(path):
            return path
    path = os.path.join(get_project_root(), "data")
    os.makedirs(path, exist_ok=True)
    return path


def session_path_for(username: str, data_dir: str) -> str:
    """為指定使用者名稱建立 session 檔案路徑。"""
    return os.path.join(data_dir, f"session-{username}")


def find_existing_sessions(data_dir: str) -> List[Tuple[str, str, str]]:
    """
    尋找現有的 session 檔案
    回傳: [(username, session_file, last_used_time)]
    """
    sessions = []

    if not os.path.exists(data_dir):
        return sessions

    for filename in os.listdir(data_dir):
        if filename.startswith("session-") and os.path.isfile(os.path.join(data_dir, filename)):
            username = filename[8:]  # 移除 "session-" 前綴
            session_path = os.path.join(data_dir, filename)

            # 檢查檔案大小，確保不是空檔案
            if os.path.getsize(session_path) > 0:
                # 獲取最後修改時間
                mtime = os.path.getmtime(session_path)
                last_used = datetime.fromtimestamp(
                    mtime).strftime('%Y年%m月%d日 %H:%M')
                sessions.append((username, filename, last_used))

    # 按最後使用時間排序，最新的在前面
    sessions.sort(key=lambda x: os.path.getmtime(
        os.path.join(data_dir, x[1])), reverse=True)
    return sessions


def choose_session(sessions: List[Tuple[str, str, str]]) -> Optional[str]:
    """
    讓用戶選擇現有的 session
    回傳: 選中的 username，或 None 表示不使用現有 session
    """
    print("\n=== 發現已存在的登入狀態 ===", flush=True)
    print("0. 不使用現有登入狀態（重新登入）", flush=True)

    for i, (username, _, last_used) in enumerate(sessions, 1):
        print(f"{i}. {username} (最後使用：{last_used})", flush=True)

    while True:
        try:
            choice = input(f"\n請選擇 (0-{len(sessions)}): ").strip()
            if not choice:
                continue

            choice_num = int(choice)
            if choice_num == 0:
                return None
            elif 1 <= choice_num <= len(sessions):
                return sessions[choice_num - 1][0]
            else:
                print(f"請輸入 0 到 {len(sessions)} 之間的數字", flush=True)
        except ValueError:
            print("請輸入有效的數字", flush=True)


def ensure_session(loader: Instaloader) -> tuple[str, str]:
    """
    互動式建立或載入 session（含登入自動重試）。
    回傳: (username, data_dir)
    """
    if not is_tty():
        print(
            "[ERROR] 目前不是互動式終端機，無法輸入帳密。\n"
            "請使用：docker compose run --rm --build ig-nonfollowers  或  docker run -it ...",
            flush=True
        )
        sys.exit(1)

    print("=== IG Non-Followers (interactive, auto-retry) ===", flush=True)

    data_dir = resolve_data_dir()

    # 檢查是否有現有的 sessions
    existing_sessions = find_existing_sessions(data_dir)

    username = None
    if existing_sessions:
        # 有現有 sessions，讓用戶選擇
        selected_username = choose_session(existing_sessions)
        if selected_username:
            username = selected_username
            sess_path = session_path_for(username, data_dir)
            loader.load_session_from_file(username, sess_path)
            print(f"[OK] 已載入 session：{sess_path}", flush=True)
            return username, data_dir

    # 沒有選擇現有 session，進入登入流程
    if not username:
        username = input("Instagram 使用者名稱：").strip()
        if not username:
            print("[ERROR] 使用者名稱不可空白。", flush=True)
            sys.exit(1)

    sess_path = session_path_for(username, data_dir)

    # 檢查是否已經有這個用戶的 session（如果是新輸入的用戶名）
    if os.path.exists(sess_path):
        loader.load_session_from_file(username, sess_path)
        print(f"[OK] 已載入 session：{sess_path}", flush=True)
        return username, data_dir

    # 無 session → 登入流程（自動重試）
    while True:
        print("[INFO] 首次使用：將建立新 session（之後免輸密碼）。", flush=True)
        password = getpass.getpass("Instagram 密碼（輸入不會顯示）：")

        try:
            loader.login(username, password)
            os.makedirs(data_dir, exist_ok=True)
            loader.save_session_to_file(sess_path)
            print(f"[OK] 已登入並儲存 session：{sess_path}", flush=True)
            return username, data_dir

        except exceptions.TwoFactorAuthRequiredException:
            # 2FA 最多 3 次（依你的指示，引導使用備用驗證碼）
            for attempt in range(1, 4):
                print(
                    "\n需要 2FA 打開Instagram → 右下角頭貼 → 右上角三條線 → 帳號管理中心 → 密碼和帳號安全\n"
                    "→ 雙重驗證 → Instagram → 其他方式 → 備用驗證碼 → 選一組輸入（中間不需空格）",
                    flush=True
                )
                code = input(f"請輸入備用驗證碼（第 {attempt}/3 次）：").strip()
                try:
                    loader.two_factor_login(code)
                    os.makedirs(data_dir, exist_ok=True)
                    loader.save_session_to_file(sess_path)
                    print(f"[OK] 2FA 成功，已儲存 session：{sess_path}", flush=True)
                    return username, data_dir
                except exceptions.LoginException as e2:
                    print(f"[WARN] 2FA 驗證失敗：{e2}", flush=True)
            print("[ERROR] 2FA 多次失敗，請稍後再試。", flush=True)
            sys.exit(1)

        except exceptions.LoginException as e:
            # 常見：'fail'（空訊息）、'challenge'、'checkpoint'
            msg = (str(e) or "").lower()
            print(f"[WARN] 登入被 Meta 擋下：{e}", flush=True)
            if any(k in msg for k in ("challenge", "checkpoint", "fail")):
                print(
                    "密碼錯誤或活動被攔截，請在 App 允許/再試一次。\n"
                    "允許或確認後，按 Enter 重試（或輸入 q 離開）。",
                    flush=True
                )
                resp = input("繼續？(Enter 重試 / q 離開) ").strip().lower()
                if resp == "q":
                    sys.exit(1)
                time.sleep(5)
                continue
            else:
                print("[ERROR] 非預期的登入錯誤，無法自動處理。", flush=True)
                sys.exit(1)


def fetch_users_with_progress(
    it: Iterable, total: Optional[int], label: str
) -> List[Tuple[str, str]]:
    """
    逐步迭代名單，顯示進度條，並回傳 [(username, full_name)]。
    """
    users: List[Tuple[str, str]] = []
    pbar = tqdm(total=total, desc=label, unit="user")

    iterator = iter(it)
    retry = 0
    while True:
        try:
            user = next(iterator)
            users.append((user.username, (user.full_name or "")))
            pbar.update(PROGRESS_STEP)
            retry = 0
        except StopIteration:
            break
        except exceptions.TooManyRequestsException:
            pbar.set_postfix_str("rate-limited; sleeping…")
            time.sleep(RATE_LIMIT_SLEEP)
            continue
        except exceptions.ConnectionException as e:
            if retry < CONNECTION_MAX_RETRIES:
                wait = min(60, 2 ** retry * 3)
                pbar.set_postfix_str(f"conn err; retry in {wait}s")
                time.sleep(wait)
                retry += 1
                continue
            else:
                pbar.close()
                raise RuntimeError(
                    f"Reach max retries due to connection errors: {e}"
                ) from e
        except Exception:
            pbar.close()
            raise

    pbar.close()
    return users


def write_csv(path: str, rows: Iterable[Tuple[str, str]]) -> None:
    """
    Writes Instagram user data to a CSV file with UTF-8 BOM encoding for Excel compatibility.

    Args:
        path (str): The file path to write the CSV to.
        rows (Iterable[Tuple[str, str]]): An iterable of tuples containing (username, full_name).

    The CSV will have columns: 'username', 'full_name', and 'profile_url'.
    """
    # 重點：用 utf-8-sig（含 BOM）讓 Windows Excel 正確辨識中文
    with open(path, "w", newline="", encoding="utf-8-sig", errors="replace") as f:
        w = csv.writer(f)
        w.writerow(["username", "full_name", "profile_url"])
        for username, full_name in rows:
            w.writerow(
                [username, full_name, f"https://instagram.com/{username}"])


def build_ts_csv_path(data_dir: str, base: str, username: str) -> str:
    """建立含帳號與時間戳的 CSV 路徑，放在 IGID_YYYYMMDDHHMMSS 資料夾中"""
    ts = datetime.now().strftime("%Y%m%d%H%M%S")

    # 建立以 IGID_YYYYMMDDHHMMSS 命名的資料夾
    folder_name = f"{username}_{ts}"
    result_dir = os.path.join(data_dir, folder_name)
    os.makedirs(result_dir, exist_ok=True)

    # CSV 檔案名稱：base_YYYYMMDDHHMMSS.csv
    filename = f"{base}_{ts}.csv"
    return os.path.join(result_dir, filename)


def main() -> None:
    """
    Main entry point for the Instagram follower analysis tool.
    This function performs the following operations:
    1. Initializes an Instaloader instance with session management
    2. Retrieves the user's following list (people the user follows)
    3. Retrieves the user's followers list (people who follow the user)
    4. Calculates the difference between following and followers to identify:
        - Non-followers: users you follow but who don't follow you back
        - Fans you don't follow: users who follow you but you don't follow back
    5. Outputs results to CSV files in two formats:
        - Fixed filename CSVs for backward compatibility
        - Timestamped CSVs with username for historical tracking
    Returns:
         None
    Raises:
         InstaloaderException: If there are issues with Instagram API requests
         IOError: If there are problems writing CSV files
    Note:
         This function requires an authenticated Instagram session managed by ensure_session().
         All CSV outputs are saved to the data directory associated with the session.
    """
    loader = Instaloader()
    loader.context.sleep = True
    loader.context.request_timeout = 90

    username, data_dir = ensure_session(loader)
    profile = Profile.from_username(loader.context, username)

    total_following = getattr(profile, "followees", None)
    total_followers = getattr(profile, "followers", None)

    print("[1/4] 取得 following（你追的人）…", flush=True)
    following_users = fetch_users_with_progress(
        profile.get_followees(), total_following, "following")

    print("[2/4] 取得 followers（追你的人）…", flush=True)
    followers_users = fetch_users_with_progress(
        profile.get_followers(), total_followers, "followers")

    print("[3/4] 計算集合差集…", flush=True)
    following_usernames: Set[str] = {u for u, _ in following_users}
    followers_usernames: Set[str] = {u for u, _ in followers_users}

    # 你追但對方沒回追
    non_followers = [(u, n)
                     for (u, n) in following_users if u not in followers_usernames]
    # 對方追你但你沒回追
    fans_you_dont_follow = [(u, n) for (
        u, n) in followers_users if u not in following_usernames]

    # 原固定檔名（相容）
    nf_path = os.path.join(data_dir, OUTPUT_NON_FOLLOWERS)
    fnf_path = os.path.join(data_dir, OUTPUT_FANS_NOT_FOLLOWED)

    print("[4/4] 輸出 CSV…", flush=True)
    write_csv(nf_path, non_followers)
    write_csv(fnf_path, fans_you_dont_follow)

    # 另外輸出四份含帳號與時間戳的 CSV
    following_ts_path = build_ts_csv_path(
        data_dir, "following_users", username)
    followers_ts_path = build_ts_csv_path(
        data_dir, "followers_users", username)
    nf_ts_path = build_ts_csv_path(data_dir, "non_followers", username)
    fy_ts_path = build_ts_csv_path(data_dir, "fans_you_dont_follow", username)

    write_csv(following_ts_path, following_users)
    write_csv(followers_ts_path, followers_users)
    write_csv(nf_ts_path, non_followers)
    write_csv(fy_ts_path, fans_you_dont_follow)

    print("\n=== 完成！===", flush=True)
    print(f"使用者：{username}", flush=True)
    print(f"following 總數：{len(following_usernames)}", flush=True)
    print(f"followers 總數：{len(followers_usernames)}", flush=True)
    print(f"你追但沒回追：{len(non_followers)} → {nf_path}", flush=True)
    print(f"他人追你但你沒回追：{len(fans_you_dont_follow)} → {fnf_path}", flush=True)
    print("— 另已輸出含帳號與時間戳的四份 CSV：", flush=True)
    print(f"following_users → {following_ts_path}", flush=True)
    print(f"followers_users → {followers_ts_path}", flush=True)
    print(f"non_followers → {nf_ts_path}", flush=True)
    print(f"fans_you_dont_follow → {fy_ts_path}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[INFO] 使用者中斷。", flush=True)
    except (OSError, IOError) as e:
        print(f"\n[ERROR] 檔案系統錯誤：{e}", flush=True)
        sys.exit(1)
    except ImportError as e:
        print(f"\n[ERROR] 模組導入錯誤：{e}", flush=True)
        print("請確認已安裝所需的套件：pip install -r requirements.txt", flush=True)
        sys.exit(1)
    except Exception as e:  # pylint: disable=broad-except
        print(f"\n[ERROR] 發生未預期錯誤：{e}", flush=True)
        traceback.print_exc()
        sys.exit(1)
