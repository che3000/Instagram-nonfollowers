#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import os, csv, time, traceback, json
from datetime import datetime
from typing import Iterable, Tuple, Optional, List, Set, Dict

from flask import (
    Flask, request, Response, render_template_string,
    send_from_directory, url_for, stream_with_context
)
from instaloader import Instaloader, Profile, exceptions

APP = Flask(__name__)

DATA_DIR = os.path.abspath(os.environ.get("DATA_DIR", "./data"))
os.makedirs(DATA_DIR, exist_ok=True)

def generate_plotly_charts(following_count, followers_count, following_only_count, fans_only_count):
    """使用 Plotly 生成互動式圓餅圖並返回 JSON 數據"""
    try:
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
        import plotly.io as pio
        
        # 創建子圖
        fig = make_subplots(
            rows=1, cols=2,
            specs=[[{"type": "pie"}, {"type": "pie"}]],
            subplot_titles=("你追蹤的人", "追蹤你的人"),
            horizontal_spacing=0.05
        )
        
        # 第一個圓餅圖：你追蹤的人
        following_mutual = following_count - following_only_count
        following_data = [following_mutual, following_only_count]
        following_labels = ['有回追', '沒回追']
        following_colors = ['#22c55e', '#ef4444']
        
        if sum(following_data) > 0:
            fig.add_trace(go.Pie(
                values=following_data,
                labels=following_labels,
                marker_colors=following_colors,
                hole=0.3,
                textinfo='label+percent+value',
                textposition='auto',
                showlegend=False,
                domain=dict(x=[0.05, 0.45], y=[0.1, 0.9])
            ), row=1, col=1)
        
        # 第二個圓餅圖：追蹤你的人
        followers_mutual = followers_count - fans_only_count
        followers_data = [followers_mutual, fans_only_count]
        followers_labels = ['你也追蹤', '你沒追蹤']
        followers_colors = ['#22c55e', '#3b82f6']
        
        if sum(followers_data) > 0:
            fig.add_trace(go.Pie(
                values=followers_data,
                labels=followers_labels,
                marker_colors=followers_colors,
                hole=0.3,
                textinfo='label+percent+value',
                textposition='auto',
                showlegend=False,
                domain=dict(x=[0.55, 0.95], y=[0.1, 0.9])
            ), row=1, col=2)
        
        # 設定整體佈局
        fig.update_layout(
            font=dict(color='white', size=12),
            paper_bgcolor='rgba(11, 16, 32, 1)',
            plot_bgcolor='rgba(11, 16, 32, 1)',
            height=450,
            margin=dict(t=20, b=80, l=20, r=20),
            annotations=[
                dict(text="你追蹤的人", x=0.24, y=-0.15, font_size=16, showarrow=False, font_color='white'),
                dict(text="追蹤你的人", x=0.76, y=-0.15, font_size=16, showarrow=False, font_color='white')
            ]
        )
        
        # 轉換為 JSON
        chart_json = pio.to_json(fig)
        return chart_json
        
    except ImportError:
        print("[WARN] Plotly not available, using fallback")
        return None
    except Exception as e:
        print(f"[ERROR] Error generating Plotly charts: {e}")
        return None

# ---------------------------
# 前端：一頁式簡單 UI
# ---------------------------
HTML = """
<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <title>IG Non-Followers（本機網頁介面）</title>
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
  <meta http-equiv="Pragma" content="no-cache">
  <meta http-equiv="Expires" content="0">
  <script src="https://cdn.plot.ly/plotly-2.26.2.min.js"></script>
  <style>
    :root{--bg:#0b1020;--fg:#e6f1ff;--muted:#8aa0bf;--card:#111836;--accent:#4f8cff;}
    body { font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Ubuntu,"Helvetica Neue",Arial; margin: 0;
           color: var(--fg); background: linear-gradient(180deg,#020617,#0b1020); }
    .wrap { max-width: 1100px; margin: 32px auto; padding: 0 16px; }
    .card { background: rgba(17,24,54,.8); border:1px solid #1f2a44; border-radius:16px; padding:16px; }
    .row{ margin-bottom:12px;}
    label{ display:block; margin-bottom:6px; color: var(--muted); }
    input[type=text], input[type=password]{
      width:100%; padding:12px; border:1px solid #2b3b63; background:#0f1730; color:var(--fg); border-radius:10px;
    }
    input[disabled]{ opacity:.6; }
    button{
      padding:10px 16px; border:0; border-radius:10px; background:var(--accent); color:#fff; cursor:pointer; font-weight:600;
    }
    button:disabled{ opacity:.5; cursor:not-allowed; }
    pre{ background:#060a17; color:#cfe8ff; padding:12px; border-radius:10px; max-height:260px; overflow:auto; white-space:pre-wrap; border:1px solid #1c2846;}
    .muted{color:var(--muted)}
    .pill{display:inline-block;background:#16274d; color:#9db9ff; padding:4px 8px; border-radius:999px; margin-left:8px; font-size:12px;}
    a{color:#7aa2ff}
    .grid{ display:grid; gap:12px; grid-template-columns: repeat(auto-fill, minmax(180px,1fr)); }
    .user{ background:#0f1730; border:1px solid #1f2a44; border-radius:12px; padding:12px; display:flex; gap:10px; align-items:center;}
    .avatar{ width:44px; height:44px; border-radius:999px; border:1px solid #2f3f6b; background:#0b1020; object-fit:cover;}
    .uname{ font-weight:700; }
    .id{ color:#9db9ff; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, "Cascadia Mono", Consolas, "Liberation Mono", "Courier New", monospace; }
    .cols{ display:grid; gap:18px; grid-template-columns: 1fr; }
    @media (min-width: 900px){ .cols{ grid-template-columns: repeat(2,1fr);} }
    h2,h3{ margin: 12px 0;}
    .section{ background: rgba(17,24,54,.6); border:1px solid #1f2a44; border-radius:16px; padding:14px;}
    
    /* 統計樣式 */
    .stats-grid{ display:grid; grid-template-columns: repeat(2,1fr); gap:16px; }
    .stat-item{ text-align:center; padding:12px; background:rgba(79,140,255,.1); border-radius:12px; border:1px solid rgba(79,140,255,.3); }
    .stat-number{ font-size:24px; font-weight:700; color:var(--accent); }
    .stat-label{ font-size:12px; color:var(--muted); margin-top:4px; }
    
    /* 標籤頁樣式 */
    .tabs-container{ margin-top:16px; }
    .tabs-nav{ display:flex; gap:4px; margin-bottom:16px; border-bottom:1px solid #1f2a44; overflow-x:auto; }
    .tab-btn{ 
      background:transparent; border:none; padding:12px 16px; color:var(--muted); cursor:pointer; 
      border-radius:8px 8px 0 0; transition:all 0.2s; white-space:nowrap; display:flex; align-items:center; gap:8px;
    }
    
    /* 資料夾選擇樣式 */
    .folder-item{ 
      background:rgba(79,140,255,.1); border:1px solid rgba(79,140,255,.3); 
      border-radius:12px; padding:12px; cursor:pointer; transition:all 0.2s;
      display:flex; justify-content:space-between; align-items:center;
    }
    .folder-item:hover{ background:rgba(79,140,255,.2); border-color:rgba(79,140,255,.5); }
    .folder-info{ flex:1; }
    .folder-igid{ font-weight:700; color:var(--fg); }
    .folder-date{ color:var(--muted); font-size:14px; margin-top:2px; }
    .folder-btn{ background:var(--accent); color:white; border:none; padding:6px 12px; border-radius:6px; cursor:pointer; }
    
    /* Session 選擇樣式 */
    .session-item{ 
      background:rgba(45,128,63,.1); border:1px solid rgba(45,128,63,.3); 
      border-radius:12px; padding:12px; cursor:pointer; transition:all 0.2s;
      display:flex; justify-content:space-between; align-items:center;
    }
    .session-item:hover{ background:rgba(45,128,63,.2); border-color:rgba(45,128,63,.5); }
    .session-info{ flex:1; }
    .session-username{ font-weight:700; color:var(--fg); }
    .session-lastused{ color:var(--muted); font-size:14px; margin-top:2px; }
    .session-btn{ background:#2d803f; color:white; border:none; padding:6px 12px; border-radius:6px; cursor:pointer; }
    .tab-btn:hover{ background:rgba(79,140,255,.1); color:var(--fg); }
    .tab-btn.active{ background:var(--accent); color:#fff; }
    .tab-icon{ font-size:16px; }
    .tab-content{ background:rgba(17,24,54,.6); border:1px solid #1f2a44; border-radius:0 16px 16px 16px; padding:16px; }
    .tab-pane{ display:none; }
    .tab-pane.active{ display:block; }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card">
      <h2>IG Non-Followers（本機網頁介面）
        <span id="status" class="pill"></span>
      </h2>
      <div id="folder-prompt" class="card" style="margin-bottom: 16px; display: none;">
        <h3>發現已存在的分析結果</h3>
        <div id="single-folder" style="display: none;">
          <p>找到資料夾：<strong id="existing-folder"></strong></p>
          <p>帳號：<strong id="folder-username"></strong> | 日期：<strong id="folder-date"></strong></p>
          <div style="display:flex;gap:8px;flex-wrap:wrap;">
            <button onclick="loadExistingData()" style="background:#2d803f">載入此結果</button>
            <button onclick="hideFolderPrompt()" style="background:#2b3b63">重新分析</button>
          </div>
        </div>
        <div id="multiple-folders" style="display: none;">
          <p>找到多個分析結果，請選擇要載入的資料：</p>
          <div style="max-height: 300px; overflow-y: auto; margin: 12px 0;">
            <div id="folder-list" style="display: flex; flex-direction: column; gap: 8px;">
              <!-- 資料夾清單將在這裡動態生成 -->
            </div>
          </div>
          <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:12px;">
            <button onclick="hideFolderPrompt()" style="background:#2b3b63">重新分析</button>
          </div>
        </div>
      </div>
      
      <div id="session-prompt" class="card" style="margin-bottom: 16px; display: none;">
        <h3>發現已存在的登入資訊</h3>
        
        <div id="single-session" style="display: none;">
          <p>要使用已存在的登入資訊嗎？帳號：<strong id="existing-username"></strong></p>
          <div class="row" style="display:flex;align-items:center;gap:8px;margin:12px 0;">
            <input id="session_fetch_avatar" name="session_fetch_avatar" type="checkbox" checked>
            <label for="session_fetch_avatar" style="margin:0;">下載頭像（小尺寸版本，可能增加耗時與 API 次數）</label>
          </div>
          <div style="display:flex;gap:8px;flex-wrap:wrap;">
            <button onclick="useExistingSession()">使用此帳號重新抓取</button>
            <button onclick="hideSessionPrompt()" style="background:#2b3b63">使用其他帳號</button>
          </div>
        </div>
        
        <div id="multiple-sessions" style="display: none;">
          <p>找到多個已登入帳號，請選擇要使用的帳號：</p>
          <div class="row" style="display:flex;align-items:center;gap:8px;margin:12px 0;">
            <input id="multi_session_fetch_avatar" name="multi_session_fetch_avatar" type="checkbox" checked>
            <label for="multi_session_fetch_avatar" style="margin:0;">下載頭像（小尺寸版本，可能增加耗時與 API 次數）</label>
          </div>
          <div style="max-height: 250px; overflow-y: auto; margin: 12px 0;">
            <div id="session-list" style="display: flex; flex-direction: column; gap: 8px;">
              <!-- session 清單將在這裡動態生成 -->
            </div>
          </div>
          <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:12px;">
            <button onclick="hideSessionPrompt()" style="background:#2b3b63">使用其他帳號</button>
          </div>
        </div>
      </div>
      <div id="login-form">
        <p class="muted">輸入 Instagram 帳密（只用於本機登入；完成後會把 session 存到 <code>data/</code>）。</p>
        <form id="form" onsubmit="start(); return false;">
        <div class="row">
          <label>Instagram 使用者名稱</label>
          <input id="username" name="username" type="text" placeholder="your_ig_username" required>
        </div>
        <div class="row">
          <label>Instagram 密碼</label>
          <input id="password" name="password" type="password" placeholder="••••••••" required>
        </div>
        <div class="row" style="display:flex;align-items:center;gap:8px;">
          <input id="fetch_avatar" name="fetch_avatar" type="checkbox" checked>
          <label for="fetch_avatar" style="margin:0;">下載頭像（小尺寸版本，可能增加耗時與 API 次數）</label>
        </div>
        <div class="row">
          <small class="muted">若帳號需要 2FA，畫面會提示輸入 <b>備用驗證碼</b>。頭像使用小尺寸版本以減少 API 負擔。</small>
        </div>
        <div class="row">
          <button id="btn" type="submit">開始分析</button>
        </div>
      </form>
      <h3>即時進度</h3>
      <pre id="log">(等待開始)</pre>

      <div id="downloads" style="display:none; margin-top:10px;">
        <h3>下載結果</h3>
        <ul>
          <li><a id="following" href="#" download>追蹤中的使用者清單</a></li>
          <li><a id="followers" href="#" download>追蹤你的使用者清單</a></li>
          <li><a id="nf" href="#" download>沒回追的使用者清單</a></li>
          <li><a id="fy" href="#" download>沒追蹤回的使用者清單</a></li>
        </ul>
      </div>
    </div>

    <div id="results" style="display:none; margin-top:16px;">
      <!-- 統計圖表區域 -->
      <div class="card">
        <h3>分析結果統計</h3>
        <div style="display:flex; align-items:center; gap:24px; flex-wrap:wrap;">
          <div style="flex: 1; min-width:600px;">
            <div id="plotlyChart" style="width:100%; height:450px; background: rgba(11, 16, 32, 1); border-radius:8px;">
              <!-- Plotly 圖表將在這裡顯示 -->
            </div>
          </div>
          <div style="flex: 1; min-width:200px;">
            <div class="stats-grid">
              <div class="stat-item">
                <div class="stat-number" id="stat-following">0</div>
                <div class="stat-label">追蹤中</div>
              </div>
              <div class="stat-item">
                <div class="stat-number" id="stat-followers">0</div>
                <div class="stat-label">追蹤者</div>
              </div>
              <div class="stat-item">
                <div class="stat-number" id="stat-following-only">0</div>
                <div class="stat-label">沒回追你</div>
              </div>
              <div class="stat-item">
                <div class="stat-number" id="stat-fans-only">0</div>
                <div class="stat-label">你沒回追</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 標籤頁導航 -->
      <div class="tabs-container">
        <div class="tabs-nav">
          <button class="tab-btn active" onclick="showTab('following')">
            <span class="tab-icon">👥</span>
            追蹤中 (<span id="count-following">0</span>)
          </button>
          <button class="tab-btn" onclick="showTab('followers')">
            <span class="tab-icon">👤</span>
            追蹤者 (<span id="count-followers">0</span>)
          </button>
          <button class="tab-btn" onclick="showTab('following-only')">
            <span class="tab-icon">💔</span>
            沒回追你 (<span id="count-following-only">0</span>)
          </button>
          <button class="tab-btn" onclick="showTab('fans-only')">
            <span class="tab-icon">❤️</span>
            你沒回追 (<span id="count-fans-only">0</span>)
          </button>
        </div>

        <!-- 標籤頁內容 -->
        <div class="tab-content">
          <div id="tab-following" class="tab-pane active">
            <h3>追蹤中（你追蹤的人）</h3>
            <div id="list_following" class="grid"></div>
          </div>
          <div id="tab-followers" class="tab-pane">
            <h3>追蹤者（追蹤你的人）</h3>
            <div id="list_followers" class="grid"></div>
          </div>
          <div id="tab-following-only" class="tab-pane">
            <h3>沒回追你（你追他、他沒追你）</h3>
            <div id="list_following_only" class="grid"></div>
          </div>
          <div id="tab-fans-only" class="tab-pane">
            <h3>你沒回追（他追你、你沒追他）</h3>
            <div id="list_fans_only" class="grid"></div>
          </div>
        </div>
      </div>
    </div>
  </div>

<script>
let es = null;

// 全局錯誤處理
window.onerror = function(msg, url, lineNo, columnNo, error) {
  console.error('Global error:', msg, 'at', url + ':' + lineNo + ':' + columnNo);
  console.error('Error object:', error);
  return false;
};

window.addEventListener('unhandledrejection', function(event) {
  console.error('Unhandled promise rejection:', event.reason);
});

function appendLog(t){
  const log = document.getElementById('log');
  if(log.textContent === '(等待開始)'){ 
    log.textContent = ''; 
  }
  
  // 更新進度條（following / followers）
  const progressLabels = ['following:', 'followers:'];
  const label = progressLabels.find(l => t.includes(l));
  if(label && t.includes('%')){
    // 如果是進度行，就更新最後一個同標籤的進度
    const newlineChar = String.fromCharCode(10); // 使用字符代碼避免直接寫換行符
    const lines = log.textContent.split(newlineChar);
    let lastProgressIndex = lines.length - 1;
    while(lastProgressIndex >= 0 && !lines[lastProgressIndex].includes(label)) {
      lastProgressIndex--;
    }
    if(lastProgressIndex >= 0){
      lines[lastProgressIndex] = t;
      log.textContent = lines.join(newlineChar);
    } else {
      log.textContent += t + newlineChar;
    }
  } else {
    // 不是進度更新，直接附加
    log.textContent += t + String.fromCharCode(10);
  }
  log.scrollTop = log.scrollHeight;
}

function lockForm(locked){
  const u = document.getElementById('username');
  const p = document.getElementById('password');
  const b = document.getElementById('btn');
  const avatarOpt = document.getElementById('fetch_avatar');
  u.disabled = locked; p.disabled = locked; b.disabled = locked;
  if (avatarOpt) avatarOpt.disabled = locked;
}

function renderUsers(containerId, items){
  const el = document.getElementById(containerId);
  el.innerHTML = '';
  for(const it of items){
    const card = document.createElement('div');
    card.className = 'user';
    const img = document.createElement('img');
    img.className = 'avatar';
    img.src = it.avatar_url || '';
    img.alt = it.username;
    const box = document.createElement('div');
    const name = document.createElement('div');
    name.className = 'uname';
    name.textContent = it.full_name || '(無名稱)';
    const id = document.createElement('div');
    id.className = 'id';
    const a = document.createElement('a');
    a.href = 'https://instagram.com/' + it.username;
    a.target = '_blank';
    a.textContent = '@' + it.username;
    id.appendChild(a);
    box.appendChild(name); box.appendChild(id);
    card.appendChild(img); card.appendChild(box);
    el.appendChild(card);
  }
}

// 標籤頁切換功能
function showTab(tabName) {
  // 移除所有 active 類
  document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
  document.querySelectorAll('.tab-pane').forEach(pane => pane.classList.remove('active'));
  
  // 添加 active 類到對應的標籤
  event.target.classList.add('active');
  document.getElementById('tab-' + tabName).classList.add('active');
}

// 繪製高清晰度圓餅圖
// 使用 Plotly 繪製互動式圓餅圖
function drawPlotlyCharts(data) {
  try {
    // 從伺服器獲取 Plotly 圖表數據
    const params = new URLSearchParams({
      following: data.following,
      followers: data.followers,
      following_only: data.following_only,
      fans_only: data.fans_only
    });
    
    fetch(`/generate-chart?${params}`)
      .then(response => response.json())
      .then(result => {
        if (result.ok && result.chart) {
          const plotlyData = JSON.parse(result.chart);
          
          // 在指定的 div 中顯示 Plotly 圖表
          Plotly.newPlot('plotlyChart', plotlyData.data, plotlyData.layout, {
            responsive: true,
            displayModeBar: false,
            staticPlot: false
          });
        } else {
          document.getElementById('plotlyChart').innerHTML = 
            '<div style="display:flex;align-items:center;justify-content:center;height:400px;color:#9ca3af;font-size:16px;">圖表載入失敗</div>';
        }
      })
      .catch(error => {
        console.error('載入圖表時發生錯誤:', error);
        document.getElementById('plotlyChart').innerHTML = 
          '<div style="display:flex;align-items:center;justify-content:center;height:400px;color:#ef4444;font-size:16px;">載入圖表時發生錯誤</div>';
      });
  } catch (error) {
    console.error('Plotly 圖表錯誤:', error);
    document.getElementById('plotlyChart').innerHTML = 
      '<div style="display:flex;align-items:center;justify-content:center;height:400px;color:#ef4444;font-size:16px;">Plotly 不可用</div>';
  }
}

// Plotly 圖表全局設定
let plotFirstLoad = true;

// 切換圖表類型


// 更新統計數據和圖表
function updateStats(data) {
  // 更新數字統計
  document.getElementById('stat-following').textContent = data.following.length;
  document.getElementById('stat-followers').textContent = data.followers.length;
  document.getElementById('stat-following-only').textContent = data.following_only.length;
  document.getElementById('stat-fans-only').textContent = data.fans_only.length;
  
  // 更新標籤頁計數
  document.getElementById('count-following').textContent = data.following.length;
  document.getElementById('count-followers').textContent = data.followers.length;
  document.getElementById('count-following-only').textContent = data.following_only.length;
  document.getElementById('count-fans-only').textContent = data.fans_only.length;
  
  // 顯示 Plotly 圖表
  const chartData = {
    following: data.following.length,
    followers: data.followers.length, 
    following_only: data.following_only.length,
    fans_only: data.fans_only.length
  };
  
  drawPlotlyCharts(chartData);
}

function displayFolderOptions(latestFolder, allFolders, hasSession = false) {
  console.log('displayFolderOptions called with:', { latestFolder, allFolders, hasSession });
  if (!allFolders || allFolders.length === 0) {
    console.log('allFolders is empty or null');
    return;
  }
  
  // 儲存 hasSession 狀態供後續使用
  window.hasSession = hasSession;
  
  if (allFolders.length === 1) {
    // 只有一個資料夾，顯示簡單模式
    console.log('Single folder mode');
    const folderInfo = allFolders[0];
    document.getElementById('existing-folder').textContent = folderInfo.folder;
    document.getElementById('folder-username').textContent = folderInfo.igid;
    document.getElementById('folder-date').textContent = folderInfo.date_formatted;
    document.getElementById('single-folder').style.display = 'block';
    document.getElementById('multiple-folders').style.display = 'none';
    
    // 儲存 folder_info 供後續使用
    window.currentFolderInfo = folderInfo;
  } else {
    // 多個資料夾，顯示選擇列表
    console.log('Multiple folders mode, count:', allFolders.length);
    document.getElementById('single-folder').style.display = 'none';
    document.getElementById('multiple-folders').style.display = 'block';
    
    const folderList = document.getElementById('folder-list');
    folderList.innerHTML = '';
    
    allFolders.forEach(folder => {
      const folderItem = document.createElement('div');
      folderItem.className = 'folder-item';
      folderItem.innerHTML = `
        <div class="folder-info">
          <div class="folder-igid">${folder.igid}</div>
          <div class="folder-date">${folder.date_formatted}</div>
        </div>
        <button class="folder-btn" data-folder="${folder.folder}">載入此結果</button>
      `;
      
      // 為按鈕添加點擊事件監聽器
      const button = folderItem.querySelector('.folder-btn');
      button.addEventListener('click', () => {
        console.log('選擇資料夾:', folder.folder);
        selectFolder(folder.folder);
      });
      
      folderList.appendChild(folderItem);
    });
  }
  
  console.log('Setting folder-prompt to display: block');
  document.getElementById('folder-prompt').style.display = 'block';
  lockForm(false);
}

function selectFolder(folderName) {
  // 從 fetch 的結果中找到對應的資料夾資訊
  fetch('/get-folders')
    .then(r => r.json())
    .then(data => {
      if (data.ok) {
        const selectedFolder = data.folders.find(f => f.folder === folderName);
        if (selectedFolder) {
          window.currentFolderInfo = selectedFolder;
          loadExistingData();
        }
      }
    })
    .catch(err => {
      console.error('獲取資料夾資訊時發生錯誤:', err);
      alert('載入失敗，請重試');
    });
}

function displaySessionOptions(latestUsername, allSessions) {
  console.log('displaySessionOptions called with:', { latestUsername, allSessions });
  if (!allSessions || allSessions.length === 0) {
    console.log('allSessions is empty or null');
    return;
  }
  
  if (allSessions.length === 1) {
    // 只有一個 session，顯示簡單模式
    console.log('Single session mode');
    const session = allSessions[0];
    document.getElementById('existing-username').textContent = session.username;
    document.getElementById('single-session').style.display = 'block';
    document.getElementById('multiple-sessions').style.display = 'none';
    
    // 儲存 session 資訊供後續使用
    window.currentSession = session;
  } else {
    // 多個 session，顯示選擇列表
    console.log('Multiple sessions mode, count:', allSessions.length);
    document.getElementById('single-session').style.display = 'none';
    document.getElementById('multiple-sessions').style.display = 'block';
    
    const sessionList = document.getElementById('session-list');
    sessionList.innerHTML = '';
    
    allSessions.forEach(session => {
      const sessionItem = document.createElement('div');
      sessionItem.className = 'session-item';
      sessionItem.innerHTML = `
        <div class="session-info">
          <div class="session-username">${session.username}</div>
          <div class="session-lastused">最後使用：${session.last_used}</div>
        </div>
        <button class="session-btn" data-username="${session.username}">使用此帳號</button>
      `;
      
      // 為按鈕添加點擊事件監聽器
      const button = sessionItem.querySelector('.session-btn');
      button.addEventListener('click', () => {
        console.log('選擇 session:', session.username);
        selectSession(session.username);
      });
      
      sessionList.appendChild(sessionItem);
    });
  }
  
  console.log('Setting session-prompt to display: block');
  document.getElementById('session-prompt').style.display = 'block';
  lockForm(false);
}

function selectSession(username) {
  // 找到選中的 session 資訊
  fetch('/check_session?skip_folders=true')
    .then(r => r.json())
    .then(data => {
      if (data.stage === 'sessions' && data.all_sessions) {
        const selectedSession = data.all_sessions.find(s => s.username === username);
        if (selectedSession) {
          window.currentSession = selectedSession;
          // 設定使用者名稱並啟動
          document.getElementById('existing-username').textContent = username;
          useExistingSession();
        }
      }
    })
    .catch(err => {
      console.error('獲取 session 資訊時發生錯誤:', err);
      alert('載入失敗，請重試');
    });
}

function hideFolderPrompt() {
  document.getElementById('folder-prompt').style.display = 'none';
  // 隱藏資料夾提示後，繼續檢查 session
  checkForSession();
}

function checkForSession() {
  // 檢查第二階段：session 檔案（跳過資料夾檢查）
  console.log('Checking for sessions, hasSession:', window.hasSession);
  
  if (window.hasSession) {
    // 我們知道有 session，直接請求跳過資料夾檢查
    fetch('/check_session?skip_folders=true')
      .then(r => r.json())
      .then(data => {
        console.log('Session check result:', data);
        if (data.stage === 'sessions' && data.all_sessions) {
          displaySessionOptions(data.username, data.all_sessions);
        } else {
          // 沒有有效的 session，直接顯示登入表單
          document.getElementById('login-form').style.display = 'block';
          lockForm(false);
        }
      })
      .catch(err => {
        console.error('檢查 session 時發生錯誤:', err);
        document.getElementById('login-form').style.display = 'block';
        lockForm(false);
      });
  } else {
    // 沒有 session，直接顯示登入表單
    document.getElementById('login-form').style.display = 'block';
    lockForm(false);
  }
}

function hideSessionPrompt() {
  document.getElementById('session-prompt').style.display = 'none';
  document.getElementById('login-form').style.display = 'block';
}

function useExistingSession() {
  const username = document.getElementById('existing-username').textContent;
  
  // 根據顯示的模式選擇正確的 avatar 設定
  let fetchAvatar = true;
  const singleSessionOpt = document.getElementById('session_fetch_avatar');
  const multiSessionOpt = document.getElementById('multi_session_fetch_avatar');
  
  if (singleSessionOpt && singleSessionOpt.style.display !== 'none') {
    fetchAvatar = singleSessionOpt.checked;
  } else if (multiSessionOpt && multiSessionOpt.style.display !== 'none') {
    fetchAvatar = multiSessionOpt.checked;
  }
  const status = document.getElementById('status');
  const loginForm = document.getElementById('login-form');
  
  // 先清理舊的顯示狀態
  document.getElementById('downloads').style.display = 'none';
  document.getElementById('results').style.display = 'none';
  document.getElementById('status').textContent = '執行中…';
  
  // 隱藏 session 提示，顯示 log 區域
  document.getElementById('session-prompt').style.display = 'none';
  loginForm.style.display = 'block';
  
  // 隱藏輸入區域，但保持 log 區域可見
  const formInputs = loginForm.querySelector('form');
  if (formInputs) formInputs.style.display = 'none';
  
  // 重置 log 並清除舊內容
  const log = document.getElementById('log');
  log.textContent = '';  // 清空 log 內容
  appendLog('---');
  appendLog('使用現有 session 重新開始分析...');
  
  // 確保 log 區域可見
  log.parentElement.style.display = 'block';
  
  // 確保之前的連接已關閉
  if(es){ 
    es.onmessage = null;
    es.onerror = null;
    es.close(); 
    es = null;
  }

  // 建立新的連接
  const fetchParam = fetchAvatar ? '1' : '0';
  const streamUrl = '/stream?username='+encodeURIComponent(username)+'&use_existing=true&fetch_avatar='+fetchParam;
  console.log('Creating EventSource for existing session with URL:', streamUrl);
  es = new EventSource(streamUrl);
  es.onmessage = handleEvent;
  
  // 監聽連接狀態
  es.onopen = function(event) {
    console.log('EventSource 連接成功 (existing session):', event);
    appendLog('[INFO] 已建立連接，開始處理...');
  };
  
  // 監聽連接錯誤
  es.onerror = function(err) {
    console.error('EventSource 錯誤 (existing session):', err);
    console.error('ReadyState:', es.readyState);
    appendLog('[錯誤] 連接中斷，請重新整理頁面重試');
    status.textContent = '失敗 ✖';
    document.getElementById('session-prompt').style.display = 'none';
    document.getElementById('login-form').style.display = 'block';
    
    // 清理連接
    if(es){
      es.onmessage = null;
      es.onerror = null;
      es.close();
      es = null;
    }
  };
}

// 檢查是否有可用的 session
function checkSession() {
  console.log('檢查三階段狀態...');
  // 先確保其他 UI 元素處於正確的初始狀態
  document.getElementById('downloads').style.display = 'none';
  document.getElementById('results').style.display = 'none';
  document.getElementById('status').textContent = '';
  document.getElementById('log').textContent = '(等待開始)';
  
  // 先隱藏所有提示元素
  document.getElementById('folder-prompt').style.display = 'none';
  document.getElementById('session-prompt').style.display = 'none';
  document.getElementById('login-form').style.display = 'none';
  
  fetch('/check_session')
    .then(r => {
      console.log('check_session response status:', r.status);
      return r.json();
    })
    .then(data => {
      console.log('檢查結果:', data);
      console.log('data.stage:', data.stage);
      console.log('data.all_folders:', data.all_folders);
      console.log('data.all_sessions:', data.all_sessions);
      
      if (data.stage === 'folders') {
        // 第一階段：顯示結果資料夾選擇
        displayFolderOptions(data.folder_info, data.all_folders, data.has_session);
        
      } else if (data.stage === 'sessions') {
        // 第二階段：顯示 session 選擇
        displaySessionOptions(data.username, data.all_sessions);
        
      } else {
        // 第三階段：正常登入流程
        document.getElementById('login-form').style.display = 'block';
        lockForm(false);
      }
    })
    .catch(err => {
      console.error('檢查狀態時發生錯誤:', err);
      document.getElementById('login-form').style.display = 'block';
      lockForm(false);
    });
}

// 載入現有的數據
function loadExistingData() {
  const status = document.getElementById('status');
  status.textContent = '載入中...';
  
  // 隱藏所有提示，但保持 log 區域
  document.getElementById('folder-prompt').style.display = 'none';
  document.getElementById('session-prompt').style.display = 'none';
  document.getElementById('login-form').style.display = 'block';
  
  // 隱藏輸入表單
  const formInputs = document.getElementById('form');
  if (formInputs) formInputs.style.display = 'none';
  
  // 清理顯示
  document.getElementById('downloads').style.display = 'none';
  document.getElementById('results').style.display = 'none';
  
  // 準備載入參數
  let loadUrl = '/load-existing';
  if (window.currentFolderInfo) {
    const params = new URLSearchParams({
      folder: window.currentFolderInfo.folder,
      igid: window.currentFolderInfo.igid,
      date: window.currentFolderInfo.date
    });
    loadUrl += '?' + params.toString();
  }
  
  fetch(loadUrl)
    .then(r => r.json())
      .then(resp => {
      if (resp.ok) {
        const data = resp.data;
        const setLink = (id, url) => {
          const el = document.getElementById(id);
          if (!el) return;
          if (url) {
            el.href = url;
          } else {
            el.removeAttribute('href');
          }
        };

        setLink('following', data.following_url);
        setLink('followers', data.followers_url);
        setLink('nf', data.non_followers_url);
        setLink('fy', data.fans_you_dont_follow_url);
        document.getElementById('downloads').style.display = 'block';
        
        // 顯示用戶列表
        renderUsers('list_following', data.following);
        renderUsers('list_followers', data.followers);
        renderUsers('list_fans_only', data.fans_only);
        renderUsers('list_following_only', data.following_only);
        
        // 更新統計和圖表
        updateStats(data);
        
        document.getElementById('results').style.display = 'block';
        
        // 更新狀態
        status.textContent = '已載入 ✔';
        appendLog('已載入上次的分析結果');
      } else {
        status.textContent = '載入失敗 ✖';
        appendLog('[錯誤] ' + (resp.error || '無法載入數據'));
      }
    })
    .catch(err => {
      console.error('載入數據時發生錯誤:', err);
      status.textContent = '載入失敗 ✖';
      appendLog('[錯誤] 載入數據時發生錯誤');
    });
}

// 頁面載入時檢查 session
checkSession();

function handleEvent(e) {
  const d = e.data;
  if(d.startsWith('LOG:')){
    appendLog(d.slice(4));
    return;
  }
  if(d==='LOCK_FORM'){
    lockForm(true);
    return;
  }
  if(d==='UNLOCK_FORM'){
    lockForm(false);
    return;
  }
  if(d==='NEED_2FA'){
    const code = prompt('請輸入 2FA 備用驗證碼（中間不需空格）');
    if(code){
      fetch('/twofactor', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({username:document.getElementById('username').value.trim(), code:code})
      });
    }
    return;
  }
  if(d.startsWith('DONE:')){
    const payload = JSON.parse(d.slice(5));
    document.getElementById('following').href = payload.following_url;
    document.getElementById('followers').href = payload.followers_url;
    document.getElementById('nf').href = payload.non_followers_url;
    document.getElementById('fy').href = payload.fans_you_dont_follow_url;
    document.getElementById('downloads').style.display = 'block';
    
    // render lists
    renderUsers('list_following', payload.following);
    renderUsers('list_followers', payload.followers);
    renderUsers('list_fans_only', payload.fans_only);
    renderUsers('list_following_only', payload.following_only);
    
    // 更新統計和圖表
    updateStats(payload);
    
    document.getElementById('results').style.display = 'block';
    document.getElementById('status').textContent = '完成 ✔';
    es.close();
    return;
  }
  if(d.startsWith('ERROR:')){
    appendLog(d);
    document.getElementById('status').textContent = '失敗 ✖';
    hideSessionPrompt(); // 顯示登入表單
    es.close();
    return;
  }
  appendLog(d);
}

function start(){
  const u = document.getElementById('username').value.trim();
  const p = document.getElementById('password').value;
  const avatarOpt = document.getElementById('fetch_avatar');
  const fetchAvatar = avatarOpt ? avatarOpt.checked : true;
  const status = document.getElementById('status');
  document.getElementById('downloads').style.display = 'none';
  document.getElementById('results').style.display = 'none';
  appendLog('---');
  status.textContent = '執行中…';
  lockForm(true);

  fetch('/start', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({username:u, password:p, fetch_avatar: fetchAvatar})
  }).then(r=>{
    console.log('Start response status:', r.status);
    if(!r.ok){ 
      return r.json().then(data => {
        throw new Error(data.error || '啟動失敗');
      });
    }
    return r.json();
  }).then(data => {
    console.log('Start response data:', data);
    
    // 確保之前的連接已關閉
    if(es){ 
      es.onmessage = null;
      es.onerror = null;
      es.close(); 
      es = null;
    }

    // 建立新的連接
    const fetchParam = fetchAvatar ? '1' : '0';
    const streamUrl = '/stream?username='+encodeURIComponent(u)+'&fetch_avatar='+fetchParam;
    console.log('Creating EventSource with URL:', streamUrl);
    es = new EventSource(streamUrl);
    es.onmessage = handleEvent;
    
    // 監聽連接狀態
    es.onopen = function(event) {
      console.log('EventSource 連接成功:', event);
      appendLog('[INFO] 已建立連接，開始處理...');
    };
    
    // 監聽連接錯誤
    es.onerror = function(err) {
      console.error('EventSource 錯誤:', err);
      console.error('ReadyState:', es.readyState);
      appendLog('[錯誤] 連接中斷，請重新整理頁面重試');
      document.getElementById('status').textContent = '失敗 ✖';
      lockForm(false);
      
      // 清理連接
      if(es){
        es.onmessage = null;
        es.onerror = null;
        es.close();
        es = null;
      }
    };
  }).catch(err=>{
    alert(err.message);
    document.getElementById('status').textContent = '失敗 ✖';
    lockForm(false);
  });
}
</script>
</body>
</html>
"""

def sse(data:str):
    return f"data: {data}\n\n"

def log_emit(msg: str, same_line: bool = False):
    # 同步打到伺服器終端機（便於你在 Docker/主機端看進度）
    if same_line:
        # 使用 \r 來覆蓋同一行，並且清除該行（避免舊內容殘留）
        print(f"\r{msg:<80}", end="", flush=True)  # 使用格式化確保清除舊內容
    else:
        # 如果前一行是同行更新，先換行
        if hasattr(log_emit, '_last_same_line') and log_emit._last_same_line:
            print()  # 換行
        print(msg, flush=True)
    
    log_emit._last_same_line = same_line
    
    # 同步推給前端
    return sse("LOG:" + msg)

# 初始化 log_emit 的狀態
log_emit._last_same_line = False

def write_csv(path: str, rows: List[Dict[str, str]], ig_username: str) -> str:
    """寫入 CSV 檔案到 IGID_YYYYMMDDHHMMSS 資料夾中，並返回實際寫入的檔案名稱"""
    from datetime import datetime
    # 生成精確到秒的日期標籤
    date_tag = datetime.now().strftime("%Y%m%d%H%M%S")
    
    # 建立以 IGID_YYYYMMDDHHMMSS 命名的資料夾
    folder_name = f"{ig_username}_{date_tag}"
    result_dir = os.path.join(DATA_DIR, folder_name)
    os.makedirs(result_dir, exist_ok=True)
    
    # 取得檔案名稱部分
    base_name = os.path.basename(path)
    name_without_ext = os.path.splitext(base_name)[0]
    ext = os.path.splitext(base_name)[1]
    
    # 建立新檔案名稱：原檔名_YYYYMMDDHHMMSS.csv
    new_filename = f"{name_without_ext}_{date_tag}{ext}"
    new_path = os.path.join(result_dir, new_filename)
    
    # Excel 用 utf-8-sig 避免中文亂碼
    with open(new_path, "w", newline="", encoding="utf-8-sig", errors="replace") as f:
        w = csv.writer(f)
        w.writerow(["username", "full_name", "profile_url"])
        for user in rows:
            w.writerow([
                user["username"],
                user["full_name"],
                f"https://instagram.com/{user['username']}"
            ])
            
    return os.path.join(folder_name, new_filename)  # 返回相對於 DATA_DIR 的路徑

def to_user_obj(user, include_avatar: bool = True) -> Dict[str,str]:
    # 從 instaloader 的 user node 取資訊（避免逐一拉 Profile，省時省流量）
    username = getattr(user, "username", "")
    full_name = getattr(user, "full_name", "") or ""
    if include_avatar:
        # 優先使用標準畫質頭像，避免高畫質版本增加請求負擔
        avatar = getattr(user, "profile_pic_url", None)
        if avatar:
            avatar_s = str(avatar)
            # 如果是高畫質 URL，嘗試轉換為標準畫質
            if "/s150x150/" in avatar_s:
                avatar_s = avatar_s.replace("/s150x150/", "/s100x100/")
            elif "/s320x320/" in avatar_s:
                avatar_s = avatar_s.replace("/s320x320/", "/s100x100/")
        else:
            avatar_s = ""
    else:
        avatar_s = ""
    return {"username": username, "full_name": full_name, "avatar_url": avatar_s}

def fetch_users_with_progress(iterable, total: Optional[int], label: str, yielder, include_avatar: bool = True):
    users_pairs: List[Tuple[str, str]] = []
    users_objs: List[Dict[str, str]] = []
    count = 0

    # 確保 total 是整數或 None
    try:
        if total is not None:
            if callable(total):
                # 如果 total 是可呼叫的函數，先呼叫它
                total = total()
            total = int(total)
        else:
            total = None
    except (ValueError, TypeError, AttributeError) as e:
        # 如果轉換失敗，設為 None 並記錄警告
        print(f"[WARN] 無法處理 total 參數 {total} (類型: {type(total)}): {e}")
        total = None

    # 起始訊息（只透過 SSE；不再直接 print，避免重複）
    yield log_emit(f"{label} 準備抓取中...{f'（總數：{total}）' if total else ''}")

    def create_progress_bar(current, total, width=30):
        if total is None or total <= 0:
            return ""
        progress = float(current) / float(total)
        filled_length = int(round(width * progress))
        filled_blocks = "█" * filled_length
        empty_blocks = "_" * (width - filled_length)
        percent = int(round(progress * 100))
        return f"[{filled_blocks}{empty_blocks}] {percent}%"

    # 顯式迭代以攔截例外並重試
    iterator = iter(iterable)
    retry = 0
    backoff_cap = 60
    rate_sleep = 180  # 秒（增加到 3 分鐘）
    while True:
        try:
            user = next(iterator)
            users_pairs.append((user.username, (getattr(user, "full_name", "") or "")))
            users_objs.append(to_user_obj(user, include_avatar))
            count += 1

            if count % 10 == 0:
                progress = create_progress_bar(count, total)
                status = f"{label}: {count}/{total}" if total else f"{label}: {count} 筆"
                if progress:
                    status = f"{status} {progress}"
                yield log_emit(status, same_line=True)
            retry = 0  # 成功則重置重試計數

        except StopIteration:
            break
        except exceptions.TooManyRequestsException as e:
            msg = str(e) or "Too many requests"
            # 動態調整等待時間，如果持續收到 429，增加等待時間
            if retry > 3:
                rate_sleep = min(300, rate_sleep * 1.5)  # 最多等待 5 分鐘
            yield log_emit(f"[RATE-LIMIT] {msg}；將等待 {int(rate_sleep)}s 後重試…（第 {retry + 1} 次）")
            time.sleep(rate_sleep)
            retry += 1
            continue
        except exceptions.ConnectionException as e:
            # 指數退避，最多 backoff_cap 秒
            wait = min(backoff_cap, (2 ** retry) * 3 if retry > 0 else 3)
            yield log_emit(f"[WARN] 連線錯誤：{e}；{wait}s 後重試（第 {retry + 1} 次）…")
            time.sleep(wait)
            retry += 1
            continue
        except Exception as e:
            # 檢查是否為可跳過的錯誤（如私人帳號、已刪除帳號等）
            error_msg = str(e).lower()
            if any(keyword in error_msg for keyword in [
                'private', 'not found', 'does not exist', 'unavailable', 
                'deleted', 'suspended', 'blocked', 'invalid'
            ]):
                # 可跳過的錯誤，記錄並繼續
                yield log_emit(f"[SKIP] 跳過無法存取的帳號：{error_msg}")
                continue
            else:
                # 嚴重錯誤 → 傳回前端並中止此階段
                yield sse("ERROR:" + str(e))
                traceback.print_exc()
                return users_pairs, users_objs

    # 完成時先顯示100%進度，再顯示完成訊息
    if total and count < total:
        # 確保最後顯示100%
        final_progress = create_progress_bar(total, total)
        status = f"{label}: {total}/{total} {final_progress}"
        yield log_emit(status, same_line=True)
    
    # 然後顯示完成訊息（不再重複顯示100%）
    if total:
        if count < total:
            skipped = total - count
            completion_msg = f"{label} 完成：{count}/{total} 筆（跳過 {skipped} 個無法存取的帳號）"
        else:
            completion_msg = f"{label} 完成：{count}/{total} 筆"
    else:
        completion_msg = f"{label} 完成：共 {count} 筆"
    yield log_emit(completion_msg, same_line=False)  # 完成訊息另起新行
    return users_pairs, users_objs

RUNS = {}  # username -> {"password":..., "twofa_code":...}

@APP.get("/")

def index():
    return render_template_string(HTML)

@APP.post("/start")
def start():
    data = request.get_json(force=True)
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    fetch_avatar_raw = data.get("fetch_avatar", True)
    if isinstance(fetch_avatar_raw, str):
        fetch_avatar = fetch_avatar_raw.lower() in ("1", "true", "yes", "on")
    else:
        fetch_avatar = bool(fetch_avatar_raw)
    
    print(f"[DEBUG] Start request - username: {username}, has_password: {bool(password)}", flush=True)
    
    if not username or not password:
        return {"error":"缺少帳號或密碼"}, 400
    if username in RUNS and RUNS[username].get("running"):
        return {"error": "此帳號已經在執行中"}, 400
    
    RUNS[username] = {"password": password, "twofa_code": None, "running": False, "fetch_avatar": fetch_avatar}
    print(f"[DEBUG] Added {username} to RUNS. Current RUNS: {list(RUNS.keys())}", flush=True)
    return {"ok":True}

@APP.post("/twofactor")
def twofactor():
    data = request.get_json(force=True)
    username = data.get("username")
    code = (data.get("code") or "").strip()
    if username not in RUNS:
        return {"error":"not running"}, 400
    RUNS[username]["twofa_code"] = code
    return {"ok": True}

def find_all_result_folders() -> List[Dict[str, str]]:
    """尋找所有有效的結果資料夾（格式：IGID_YYYYMMDDHHMMSS）並驗證包含完整的 CSV 檔案"""
    try:
        valid_folders = []
        
        for item in os.listdir(DATA_DIR):
            item_path = os.path.join(DATA_DIR, item)
            if os.path.isdir(item_path) and '_' in item:
                # 檢查是否符合 IGID_YYYYMMDDHHMMSS 格式
                parts = item.split('_')
                if len(parts) >= 2:
                    # 最後一個部分應該是日期時間
                    datetime_str = parts[-1]  # YYYYMMDDHHMMSS
                    # 其餘部分組成 IGID
                    igid = '_'.join(parts[:-1])
                    
                    # 驗證日期時間格式（14位數字）
                    if len(datetime_str) == 14 and datetime_str.isdigit():
                        try:
                            # 驗證完整的日期時間格式
                            date_obj = datetime.strptime(datetime_str, '%Y%m%d%H%M%S')
                            
                            # 檢查資料夾內是否包含四份必要的 CSV 檔案
                            required_files = [
                                f"following_users_{datetime_str}.csv",
                                f"followers_users_{datetime_str}.csv", 
                                f"non_followers_{datetime_str}.csv",
                                f"fans_you_dont_follow_{datetime_str}.csv"
                            ]
                            
                            all_files_exist = True
                            for filename in required_files:
                                file_path = os.path.join(item_path, filename)
                                if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
                                    all_files_exist = False
                                    break
                            
                            if all_files_exist:
                                valid_folders.append({
                                    "folder": item,
                                    "igid": igid,
                                    "date": datetime_str,
                                    "date_formatted": date_obj.strftime('%Y年%m月%d日 %H:%M:%S'),
                                    "sort_date": datetime_str
                                })
                                print(f"[DEBUG] 找到有效的結果資料夾: {item} (IGID: {igid}, 日期時間: {datetime_str})", flush=True)
                            else:
                                print(f"[DEBUG] 資料夾 {item} 缺少必要的 CSV 檔案", flush=True)
                                
                        except ValueError:
                            continue
        
        # 按日期時間排序，最新的在前面
        valid_folders.sort(key=lambda x: x['sort_date'], reverse=True)
        return valid_folders
        
    except Exception as e:
        print(f"尋找結果資料夾時發生錯誤: {e}")
        return []

def find_latest_result_folder() -> Optional[Dict[str, str]]:
    """尋找最新的結果資料夾（格式：IGID_YYYYMMDDHHMMSS）並驗證包含完整的 CSV 檔案"""
    folders = find_all_result_folders()
    if folders:
        return folders[0]  # 返回最新的資料夾
    return None

def read_existing_csv(folder_info: Optional[Dict[str, str]] = None) -> Optional[Dict[str, List[Dict[str, str]]]]:
    """從現有的 CSV 檔案載入資料（支援新的資料夾結構）。"""
    print("開始讀取 CSV 檔案...")  # 偵錯日誌
    try:
        if not folder_info:
            folder_info = find_latest_result_folder()
        
        if not folder_info:
            print("未找到符合格式的結果資料夾")
            return None
            
        folder_name = folder_info["folder"]
        date_str = folder_info["date"]
        result_dir = os.path.join(DATA_DIR, folder_name)
        
        if not os.path.exists(result_dir):
            print(f"結果資料夾不存在: {result_dir}")
            return None

        result: Dict[str, List[Dict[str, str]]] = {
            "following": [],
            "followers": [],
            "following_only": [],
            "fans_only": [],
        }
        
        # 定義檔案對應關係
        file_mapping = {
            "following": f"following_users_{date_str}.csv",
            "followers": f"followers_users_{date_str}.csv",
            "non_followers": f"non_followers_{date_str}.csv",
            "fans_you_dont_follow": f"fans_you_dont_follow_{date_str}.csv",
        }

        chosen_files: Dict[str, Optional[str]] = {}
        
        # 檢查並讀取檔案
        def read_into(result_key: str, file_key: str) -> None:
            filename = file_mapping.get(file_key)
            if not filename:
                return
                
            file_path = os.path.join(result_dir, filename)
            if not os.path.exists(file_path):
                print(f"檔案不存在: {file_path}")
                return
                
            chosen_files[file_key] = os.path.join(folder_name, filename)
            
            with open(file_path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    result[result_key].append({
                        "username": row.get("username", ""),
                        "full_name": row.get("full_name", ""),
                        "avatar_url": "",
                    })

        read_into("following", "following")
        read_into("followers", "followers")
        read_into("following_only", "non_followers")
        read_into("fans_only", "fans_you_dont_follow")

        result["files"] = chosen_files  # type: ignore
        result["folder_info"] = folder_info  # type: ignore
        return result
    except Exception as e:
        print(f"讀取 CSV 時發生錯誤: {e}")
        return None


def check_session(skip_folders: bool = False):
    """
    三階段檢查邏輯：
    1. 先檢查是否有符合格式的結果資料夾 (IGID_YYYYMMDDHHMMSS)
    2. 再檢查是否有 session 檔案
    3. 最後才是正常登入流程
    """
    print(f"[DEBUG] check_session called with skip_folders={skip_folders}", flush=True)
    
    # 確保 data 目錄存在
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR, exist_ok=True)
        print(f"[DEBUG] DATA_DIR 不存在，已創建: {DATA_DIR}", flush=True)
        return {"has_folders": False, "has_session": False, "stage": "login"}
        
    # 清除所有舊的執行狀態
    global RUNS
    RUNS.clear()
    
    print(f"[DEBUG] DATA_DIR 內容: {os.listdir(DATA_DIR)}", flush=True)

    try:
        # 同時檢查資料夾和 sessions
        all_folders = []
        sessions = []
        
        # 檢查結果資料夾（除非被跳過）
        if not skip_folders:
            print("[DEBUG] 開始檢查結果資料夾", flush=True)
            all_folders = find_all_result_folders()
            if all_folders:
                print(f"[DEBUG] 找到 {len(all_folders)} 個結果資料夾", flush=True)
            else:
                print("[DEBUG] 未找到有效的結果資料夾", flush=True)
        else:
            print("[DEBUG] 跳過資料夾檢查", flush=True)
        
        # 檢查 session 檔案
        print("[DEBUG] 開始檢查 session 檔案", flush=True)
        for f in os.listdir(DATA_DIR):
            if f.startswith("session-"):
                session_path = os.path.join(DATA_DIR, f)
                # 確認檔案真的存在且不是空的
                if os.path.isfile(session_path) and os.path.getsize(session_path) > 0:
                    username = f[8:]  # 移除 "session-" 前綴
                    # 獲取檔案修改時間
                    mtime = os.path.getmtime(session_path)
                    sessions.append({
                        "username": username,
                        "file": f,
                        "mtime": mtime,
                        "last_used": datetime.fromtimestamp(mtime).strftime('%Y年%m月%d日 %H:%M')
                    })
        
        if sessions:
            # 按修改時間排序，最新的在前面
            sessions.sort(key=lambda x: x['mtime'], reverse=True)
            print(f"[DEBUG] 找到 {len(sessions)} 個 session 檔案", flush=True)
        else:
            print("[DEBUG] 未找到有效的 session 檔案", flush=True)
        
        # 決定要顯示什麼（恢復三階段邏輯）
        if all_folders:
            # 第一階段：優先顯示資料夾選擇
            latest_folder = all_folders[0]
            return {
                "has_folders": True,
                "has_session": len(sessions) > 0,  # 記錄是否有 session，但不在此階段顯示
                "stage": "folders",
                "folder_info": latest_folder,
                "all_folders": all_folders,
                "all_sessions": sessions if len(sessions) > 0 else None  # 備用資料
            }
        elif sessions:
            # 第二階段：如果沒有資料夾，顯示 session 選擇
            latest_session = sessions[0]
            return {
                "has_folders": False,
                "has_session": True, 
                "stage": "sessions",
                "username": latest_session['username'],
                "all_sessions": sessions
            }
        
        # 第三階段：正常登入流程
        return {
            "has_folders": False,
            "has_session": False,
            "stage": "login"
        }
        
    except (OSError, IOError) as e:
        print(f"檢查時發生錯誤: {e}", flush=True)
        
    return {"has_folders": False, "has_session": False, "stage": "login"}

@APP.get("/check_session")
def handle_check_session():
    skip_folders = request.args.get("skip_folders", "false").lower() == "true"
    return check_session(skip_folders)

@APP.get("/stream")
def stream():
    username = request.args.get("username","")
    use_existing = request.args.get("use_existing", "false") == "true"
    fetch_param = request.args.get("fetch_avatar")
    fetch_avatar_override = None
    if fetch_param is not None:
        fetch_avatar_override = fetch_param.lower() in ("1", "true", "yes", "on")
    
    print(f"[DEBUG] Stream request - username: {username}, use_existing: {use_existing}", flush=True)
    print(f"[DEBUG] Current RUNS: {list(RUNS.keys())}", flush=True)
    
    # 檢查是否已經在執行中
    if username in RUNS and RUNS[username].get("running"):
        print(f"[DEBUG] Username {username} already running", flush=True)
        return Response(sse("ERROR:此帳號已經在執行中"), mimetype="text/event-stream")
    
    if use_existing:
        # 如果使用現有 session，創建一個臨時的 RUNS 條目
        print(f"[DEBUG] Using existing session for {username}", flush=True)
        RUNS[username] = {"password": None, "twofa_code": None, "running": True, "fetch_avatar": fetch_avatar_override if fetch_avatar_override is not None else True}
    elif username not in RUNS:
        print(f"[DEBUG] Username {username} not in RUNS, returning error", flush=True)
        return Response(sse("ERROR:沒有此任務"), mimetype="text/event-stream")
    else:
        # 標記為執行中
        print(f"[DEBUG] Marking {username} as running", flush=True)
        RUNS[username]["running"] = True
        if fetch_avatar_override is not None:
            RUNS[username]["fetch_avatar"] = fetch_avatar_override

    @stream_with_context
    def run_and_stream():
        state = RUNS[username]
        fetch_avatar = state.get("fetch_avatar", True)
        pwd = state["password"]
        nf_path = os.path.join(DATA_DIR, "non_followers.csv")
        fy_path = os.path.join(DATA_DIR, "fans_you_dont_follow.csv")

        try:
            yield log_emit("=== IG Non-Followers（Web）===")
            
            # 顯示當前時區資訊
            tz_info = os.environ.get('TZ', '未設定')
            current_time = datetime.now()
            yield log_emit(f"[INFO] 當前時區: {tz_info}, 本機時間: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")

            L = Instaloader()
            L.context.iphone_support = False
            if not fetch_avatar:
                yield log_emit("[INFO] 跳過頭像下載以縮短時間")
            else:
                yield log_emit("[INFO] 將下載標準畫質頭像")
            
            # 設定更保守的請求參數以避免 429 錯誤
            L.context.sleep = True
            L.context.request_timeout = 120  # 增加超時時間
            
            # 安全地設定速率控制參數
            try:
                if hasattr(L.context, '_rate_controller') and L.context._rate_controller:
                    # 保存原始方法
                    original_query_waittime = L.context._rate_controller.query_waittime
                    
                    # 創建新的方法來覆蓋原始等待時間
                    def custom_query_waittime(query_type, current_time, untracked_queries):
                        if callable(original_query_waittime):
                            base_wait = original_query_waittime(query_type, current_time, untracked_queries)
                        else:
                            base_wait = 1.0  # 預設值
                        
                        # 根據查詢類型增加等待時間（更保守的設定）
                        if query_type == 'iphone':
                            return max(base_wait, 10.0)  # iPhone 查詢至少等待 10 秒
                        else:
                            return max(base_wait, 8.0)  # 其他查詢至少等待 8 秒
                    
                    # 替換方法
                    L.context._rate_controller.query_waittime = custom_query_waittime
                    yield log_emit("[INFO] 已設定保守的請求間隔以避免 API 限制")
                else:
                    yield log_emit("[WARN] 無法設定自訂請求間隔，使用預設值")
            except Exception as e:
                yield log_emit(f"[WARN] 設定請求間隔時發生錯誤: {e}")
                # 繼續執行，使用預設的速率控制

            sess_path = os.path.join(DATA_DIR, f"session-{username}")
            # 先試 session
            if os.path.exists(sess_path):
                L.load_session_from_file(username, sess_path)
                yield sse("LOCK_FORM")  # 有 session 視為已授權 → 鎖起表單
                yield log_emit(f"[OK] 已載入 session：{sess_path}")
                yield log_emit("[INFO] 等待 10 秒後開始抓取，避免 API 限制...")
                time.sleep(10)  # 載入 session 後較長等待
            else:
                # 沒 session → 登入流程
                while True:
                    try:
                        yield log_emit("[INFO] 嘗試登入…")
                        L.login(username, pwd)
                        L.save_session_to_file(sess_path)
                        yield sse("LOCK_FORM")  # 登入成功 → 鎖表單
                        yield log_emit(f"[OK] 已登入並儲存 session：{sess_path}")
                        yield log_emit("[INFO] 等待 10 秒後開始抓取，避免 API 限制...")
                        time.sleep(10)  # 登入後較長等待
                        break
                    except exceptions.TwoFactorAuthRequiredException:
                        # 要求 2FA
                        yield sse("NEED_2FA")
                        yield log_emit("[INFO] 需要 2FA 驗證碼…")
                        # 等待 2FA
                        yield log_emit("等待輸入 2FA 驗證碼...")
                        while RUNS[username].get("twofa_code") in (None, ""):
                            time.sleep(0.5)  # 減少檢查頻率，避免過多日誌
                        code = RUNS[username].pop("twofa_code")
                        try:
                            L.two_factor_login(code)
                            L.save_session_to_file(sess_path)
                            yield sse("LOCK_FORM")
                            yield log_emit(f"[OK] 2FA 成功，已儲存 session：{sess_path}")
                            break
                        except exceptions.LoginException as e2:
                            # 2FA 錯誤 → 不解鎖帳號（通常重輸 2FA）
                            yield log_emit(f"[WARN] 2FA 驗證失敗：{e2}，請重新輸入。")
                            continue
                    except exceptions.BadCredentialsException as e:
                        # 密碼錯誤 → 解鎖表單讓使用者重填
                        yield sse("UNLOCK_FORM")
                        yield sse("ERROR:密碼錯誤，請重新輸入。")
                        yield log_emit(f"[ERROR] 密碼錯誤：{e}")
                        return
                    except exceptions.LoginException as e:
                        msg = (str(e) or "").lower();
                        yield log_emit(f"[WARN] 登入被 IG 擋下：{e}")
                        if any(k in msg for k in ("challenge", "checkpoint", "fail")):
                            # 解鎖表單讓使用者重新輸入
                            yield sse("UNLOCK_FORM")
                            yield log_emit("[INFO] 請重新檢查帳號密碼是否正確，或到 Instagram App → 安全性 / 登入活動 → 允許這次登入")
                            yield sse("ERROR:登入失敗，請重新檢查帳號密碼或允許新的登入活動")
                            return
                        # 其他狀況視為錯誤 → 解鎖
                        yield sse("UNLOCK_FORM")
                        yield sse("ERROR:" + str(e))
                        return

            # 取得 Profile 與名單
            try:
                yield log_emit(f"[INFO] 正在取得用戶 {username} 的資料...")
                
                # 設定一個簡單的監控機制，不使用輸出重定向避免死鎖
                import threading
                import queue
                
                result_queue = queue.Queue()
                
                def get_profile_thread():
                    try:
                        profile = Profile.from_username(L.context, username)
                        result_queue.put(('success', profile))
                    except Exception as e:
                        result_queue.put(('error', e))
                
                # 啟動線程
                thread = threading.Thread(target=get_profile_thread)
                thread.daemon = True
                thread.start()
                
                # 等待結果，每 10 秒檢查一次（更頻繁的更新）
                wait_time = 0
                max_wait = 300  # 最多等待 5 分鐘
                check_interval = 10  # 每 10 秒檢查一次
                
                profile = None
                
                while wait_time < max_wait:
                    if not result_queue.empty():
                        result_type, result_data = result_queue.get()
                        
                        if result_type == 'success':
                            profile = result_data
                        else:
                            raise result_data
                        break
                    elif not thread.is_alive():
                        # 線程已結束但沒有結果，可能發生未預期的錯誤
                        yield log_emit("[WARN] 處理線程已結束，但沒有收到結果")
                        break
                    else:
                        # 線程還在運行，可能在等待重試
                        wait_time += check_interval
                        if wait_time == 10:
                            yield log_emit("[INFO] 正在處理中，請耐心等待...")
                        elif wait_time == 30:
                            yield log_emit("[INFO] 處理時間較長，可能遇到網路問題...")
                        elif wait_time == 60:
                            yield log_emit("[RATE-LIMIT] 檢測到 API 限制 (429 Too Many Requests)")
                            yield log_emit("[INFO] Instagram 要求等待後重試，通常為 15-30 分鐘")
                            from datetime import timedelta
                            estimated_retry_time = datetime.now() + timedelta(minutes=30)
                            yield log_emit(f"[INFO] 預估重試時間：{estimated_retry_time.strftime('%H:%M')} (台北時間)")
                        elif wait_time == 120:
                            yield log_emit("[INFO] Instaloader 正在背景等待重試時間...")
                            yield log_emit("[INFO] 這是正常行為，程式會自動在指定時間重試")
                            yield log_emit("[建議] 您可以:")
                            yield log_emit("  1. 繼續等待（推薦，程式會自動處理）")
                            yield log_emit("  2. 重新整理頁面並稍後再試")
                            yield log_emit("  3. 確保已關閉所有 Instagram App 以避免額外的 API 請求")
                        elif wait_time == 180:
                            yield log_emit("[INFO] 已等待 3 分鐘，程式仍在運行中")
                            yield log_emit("[提示] 根據終端機顯示，Instagram 通常要求等待 30 分鐘")
                            yield log_emit("[提示] 您可以查看終端機輸出以獲得更詳細的資訊")
                        elif wait_time % 60 == 0 and wait_time >= 240:
                            yield log_emit(f"[INFO] 已等待 {wait_time//60} 分鐘，Instaloader 仍在處理中...")
                            if wait_time == 240:
                                yield log_emit("[提示] 如果終端機顯示等待時間（如 'at 02:31'），程式會在該時間自動重試")
                        
                        time.sleep(check_interval)
                
                if profile is None:
                    if wait_time >= max_wait:
                        yield log_emit(f"[TIMEOUT] 等待超過 {max_wait//60} 分鐘，停止等待")
                        yield log_emit("[建議] Instagram 可能正在限制 API 請求")
                        yield log_emit("[建議] 請等待 15-30 分鐘後再試，並確保關閉 Instagram App")
                        yield sse("ERROR:請求超時，請稍後再試")
                    else:
                        yield log_emit("[ERROR] 無法取得用戶資料，處理過程中發生未知錯誤")
                        yield sse("ERROR:無法取得用戶資料")
                    return
                
                yield log_emit(f"[OK] 成功取得用戶資料：{profile.username}")
                yield log_emit(f"[INFO] 追蹤中：{profile.followees} 人，追蹤者：{profile.followers} 人")
                    
            except exceptions.TooManyRequestsException as e:
                error_msg = str(e) if str(e) else "Instagram API 請求限制"
                yield log_emit(f"[RATE-LIMIT] {error_msg}")
                
                # 嘗試從錯誤訊息中提取等待時間
                import re
                wait_match = re.search(r'retry.+?(\d+)\s*minutes?', error_msg, re.IGNORECASE)
                if wait_match:
                    wait_minutes = int(wait_match.group(1))
                    from datetime import timedelta
                    retry_time = datetime.now() + timedelta(minutes=wait_minutes)
                    yield log_emit(f"[INFO] Instagram 要求等待 {wait_minutes} 分鐘")
                    yield log_emit(f"[INFO] 預計重試時間：{retry_time.strftime('%H:%M')} (台北時間)")
                    yield log_emit(f"[建議] 請關閉所有 Instagram App，並等待指定時間後再試")
                else:
                    yield log_emit("[建議] 請等待 10-15 分鐘後再試，並避免同時使用 Instagram App")
                
                yield log_emit("[INFO] 由於 API 限制，分析將暫停。請等待指定時間後重新嘗試。")
                yield sse("ERROR:Instagram API 請求限制，請稍後再試")
                return
                
            except exceptions.ConnectionException as e:
                yield log_emit(f"[WARN] 連線錯誤：{e}")
                yield log_emit("[建議] 請檢查網路連線或稍後再試")
                yield sse("ERROR:網路連線錯誤，請稍後再試")
                return
                
            except exceptions.LoginException as e:
                yield log_emit(f"[ERROR] 登入問題：{e}")
                yield log_emit("[建議] Session 可能已過期，請重新登入")
                yield sse("ERROR:登入問題，請重新登入")
                return
                
            except Exception as e:
                yield log_emit(f"[ERROR] 無法取得用戶資料：{e}")
                yield log_emit(f"[DEBUG] 錯誤類型：{type(e).__name__}")
                
                # 檢查錯誤訊息中是否包含 429 相關資訊
                error_str = str(e).lower()
                if '429' in error_str or 'too many requests' in error_str:
                    yield log_emit("[INFO] 檢測到 API 限制錯誤")
                    yield log_emit("[建議] 請等待 15-30 分鐘後再試，並確保沒有同時使用 Instagram App")
                    yield sse("ERROR:Instagram API 請求限制，請稍後再試")
                else:
                    yield log_emit(f"[DEBUG] 詳細錯誤：{traceback.format_exc()}")
                    yield sse("ERROR:" + str(e))
                return

            # following
            try:
                following_count = profile.followees if hasattr(profile, 'followees') else None
                following_pairs, following_objs = yield from fetch_users_with_progress(
                    profile.get_followees(), following_count, "following", log_emit, include_avatar=fetch_avatar
                )
            except Exception as e:
                yield log_emit(f"[ERROR] 取得追蹤中列表時發生錯誤：{e}")
                yield sse("ERROR:" + str(e))
                return
                
            # followers
            try:
                followers_count = profile.followers if hasattr(profile, 'followers') else None
                followers_pairs, followers_objs = yield from fetch_users_with_progress(
                    profile.get_followers(), followers_count, "followers", log_emit, include_avatar=fetch_avatar
                )
            except Exception as e:
                yield log_emit(f"[ERROR] 取得追蹤者列表時發生錯誤：{e}")
                yield sse("ERROR:" + str(e))
                return

            following_set: Set[str] = {u for u,_ in following_pairs}
            followers_set: Set[str] = {u for u,_ in followers_pairs}

            # 分類（物件版也要分）
            following_only_set = following_set - followers_set
            fans_only_set      = followers_set - following_set

            def filter_objs(objs: List[Dict[str,str]], keep: Set[str]) -> List[Dict[str,str]]:
                return [o for o in objs if o.get("username") in keep]

            following_only_objs = filter_objs(following_objs, following_only_set)
            fans_only_objs      = filter_objs(followers_objs, fans_only_set)

            # CSV
            yield log_emit("[INFO] 輸出 CSV 檔案...")
            
            # 產生資料夾路徑（用於顯示訊息）
            date_tag = datetime.now().strftime("%Y%m%d%H%M%S")
            folder_name = f"{username}_{date_tag}"
            result_folder_path = os.path.join(DATA_DIR, folder_name)
            
            # 1. 追蹤中的使用者
            following_filename = write_csv(
                os.path.join(DATA_DIR, "following_users.csv"),
                following_objs,
                username
            )
            
            # 2. 追蹤你的使用者
            followers_filename = write_csv(
                os.path.join(DATA_DIR, "followers_users.csv"),
                followers_objs,
                username
            )
            
            # 3. 沒回追的使用者
            nf_filename = write_csv(
                os.path.join(DATA_DIR, "non_followers.csv"),
                following_only_objs,
                username
            )
            
            # 4. 沒追蹤回的使用者
            fy_filename = write_csv(
                os.path.join(DATA_DIR, "fans_you_dont_follow.csv"),
                fans_only_objs,
                username
            )

            yield log_emit(f"[OK] 已儲存所有 CSV 檔案到 {result_folder_path}")

            # 回傳完成 payload：含四類清單（for UI）與下載連結
            payload = {
                "following": following_objs,
                "followers": followers_objs,
                "following_only": following_only_objs,
                "fans_only": fans_only_objs,
                # CSV 下載連結
                "following_url": f"/download/{following_filename}",
                "followers_url": f"/download/{followers_filename}",
                "non_followers_url": f"/download/{nf_filename}",
                "fans_you_dont_follow_url": f"/download/{fy_filename}"
            }
            yield sse("DONE:" + json.dumps(payload, ensure_ascii=False))

        except Exception as e:
            # 未預期錯誤 → 解鎖表單
            yield sse("UNLOCK_FORM")
            yield sse("ERROR:" + str(e))
            traceback.print_exc()

    return Response(run_and_stream(), mimetype="text/event-stream")

@APP.get("/download/<path:filename>")
def download(filename):
    # 支援資料夾結構的檔案下載
    # filename 可能是 "folder_name/file.csv" 格式
    file_path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(file_path):
        return {"error": "檔案不存在"}, 404
    
    # 確保檔案在 DATA_DIR 內（安全性檢查）
    if not os.path.abspath(file_path).startswith(os.path.abspath(DATA_DIR)):
        return {"error": "檔案路徑無效"}, 403
        
    directory = os.path.dirname(file_path)
    filename_only = os.path.basename(file_path)
    return send_from_directory(directory, filename_only, as_attachment=True)

@APP.get("/generate-chart")
def generate_chart():
    """生成圓餅圖"""
    following = int(request.args.get("following", 0))
    followers = int(request.args.get("followers", 0))
    following_only = int(request.args.get("following_only", 0))
    fans_only = int(request.args.get("fans_only", 0))
    
    chart_data = generate_plotly_charts(following, followers, following_only, fans_only)
    
    if chart_data:
        return {"ok": True, "chart": chart_data}
    else:
        return {"ok": False, "error": "無法生成圖表"}

@APP.get("/get-folders")
def get_folders():
    """獲取所有可用的結果資料夾"""
    try:
        folders = find_all_result_folders()
        return {"ok": True, "folders": folders}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@APP.get("/load-existing")
def load_existing():
    """載入既有 CSV 資料"""
    # 檢查是否指定了特定資料夾
    folder = request.args.get("folder")
    igid = request.args.get("igid")
    date = request.args.get("date")
    
    folder_info = None
    if folder and igid and date:
        folder_info = {"folder": folder, "igid": igid, "date": date}
    
    data = read_existing_csv(folder_info)
    if not data:
        return {"ok": False, "error": "無法讀取現有資料"}, 400

    files = data.get("files") or {};
    urls: Dict[str, str] = {};
    if files.get("following"):
        urls["following_url"] = f"/download/{files['following']}"
    if files.get("followers"):
        urls["followers_url"] = f"/download/{files['followers']}"
    if files.get("non_followers"):
        urls["non_followers_url"] = f"/download/{files['non_followers']}"
    if files.get("fans_you_dont_follow"):
        urls["fans_you_dont_follow_url"] = f"/download/{files['fans_you_dont_follow']}"

    return {
        "ok": True,
        "data": {
            **data,
            **urls,
        }
    }

if __name__ == "__main__":
    # 建議仍用 docker 跑；本機時也可直接 python app.py
    APP.run(host="0.0.0.0", port=int(os.environ.get("PORT", "7860")), debug=False, threaded=True)
