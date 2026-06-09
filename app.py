import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import json
import os
import re
import urllib.parse
from pathlib import Path
from datetime import datetime, timedelta
import requests
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env", override=True)

def _get_secret(key: str, default: str = "") -> str:
    try:
        return st.secrets[key]
    except Exception:
        return os.environ.get(key, default)

KAKAO_JS_KEY    = _get_secret("KAKAO_JS_KEY")
KMA_API_KEY     = _get_secret("KMA_API_KEY")
ENNOEIA_KEY     = _get_secret("ENNOEIA_API_KEY")
ENNOEIA_PROJECT = "KNTO-PROMPTON-2026-121"
ENNOEIA_HASH    = "da9313cd70180ac3cfc1b38f54973cc0d40628fee3a572e2eb6d9cf5a3e6a6dc"

st.set_page_config(page_title="🐾 댕댕맵", page_icon="🐾", layout="wide")

# ── 파스텔 테마 CSS ────────────────────────────────────────────────
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'Nunito', 'Malgun Gothic', sans-serif !important; }
[data-testid="stAppViewContainer"] > .main {
    background: linear-gradient(135deg, #FFF0F5 0%, #F8F0FF 50%, #F0F8FF 100%);
}
[data-testid="stSidebar"] > div:first-child {
    background: linear-gradient(180deg, #FFE8F2 0%, #EDE8FF 55%, #E8F2FF 100%);
}
[data-testid="metric-container"] {
    background: white !important;
    border-radius: 18px !important;
    border: 2px solid #FFD6E7 !important;
    box-shadow: 0 4px 16px rgba(255,143,171,0.18) !important;
}
[data-testid="stMetricLabel"] p { color: #C06080 !important; font-weight: 700 !important; font-size:0.85rem !important; }
[data-testid="stMetricValue"]   { color: #7B4F8A !important; font-weight: 800 !important; }
.stButton > button {
    border-radius: 22px !important; border: none !important;
    font-weight: 700 !important; font-size: 0.93rem !important;
    transition: transform 0.15s, box-shadow 0.15s !important;
}
.stButton > button:hover { transform: scale(1.04) !important; box-shadow: 0 6px 20px rgba(255,100,150,0.28) !important; }
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #FF8FAB 0%, #C084D4 100%) !important;
    color: white !important; box-shadow: 0 4px 15px rgba(255,100,150,0.30) !important;
}
.stButton > button[kind="secondary"] { background: #F0EAF8 !important; color: #8B6BB8 !important; }
[data-testid="stExpander"] { border-radius: 14px !important; border: 2px solid #E8D5F5 !important; background: white !important; }
hr { border-color: #FFD6E7 !important; border-width: 1.5px !important; }
[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 18px !important; border: 2px solid #FFE0ED !important; background: white !important;
}
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 { color: #C06080 !important; }
.stAlert { border-radius: 12px !important; }
</style>""", unsafe_allow_html=True)

# ── 상수 ────────────────────────────────────────────────────────────
SIZE_COMPAT = {
    "전체 (필터 없음)":    ["전견종", "소형견", "소형/중형견", "중형견이하", "안내견전용", "정보없음"],
    "소형견 (10kg 미만)":  ["전견종", "소형견", "소형/중형견", "중형견이하", "정보없음"],
    "중형견 (25kg 미만)":  ["전견종", "소형/중형견", "중형견이하", "정보없음"],
    "대형견":             ["전견종", "정보없음"],
}
SIZE_ICONS = {
    "전체 (필터 없음)":   "🐾 전체",
    "소형견 (10kg 미만)": "🐩 소형",
    "중형견 (25kg 미만)": "🐕 중형",
    "대형견":            "🦮 대형",
}
COURSE_ORDER = ["관광지", "애견카페", "카페", "음식점", "문화시설", "레포츠", "숙박", "쇼핑", "기타"]
CARD_STYLES  = [
    {"bg": "#FFF0F5", "border": "#FFB7C5", "num": "①"},
    {"bg": "#F0FFF8", "border": "#A8D5BA", "num": "②"},
    {"bg": "#F5F0FF", "border": "#C7CEEA", "num": "③"},
    {"bg": "#FFF8F0", "border": "#FFDAC1", "num": "④"},
]
CAT_COLORS = {
    "관광지": "#3B82F6", "문화시설": "#8B5CF6", "음식점": "#F97316",
    "숙박": "#10B981", "레포츠": "#EF4444", "쇼핑": "#EC4899",
    "애견카페": "#E879A0", "카페": "#F59E0B", "기타": "#6B7280",
}
SIZE_COLORS = {
    "전견종": "#059669", "소형견": "#0284C7", "소형/중형견": "#7C3AED",
    "중형견이하": "#B45309", "정보없음": "#9CA3AF", "안내견전용": "#6B7280", "입장불가": "#DC2626",
}

# ── 기상청 격자 좌표 (시도 대표점) ────────────────────────────────────
REGION_GRID = {
    "서울": (60, 127), "부산": (98, 76),  "대구": (89, 90),
    "인천": (55, 124), "광주": (58, 74),  "대전": (67, 100),
    "울산": (102, 84), "세종": (66, 103), "경기": (60, 121),
    "강원": (73, 134), "충북": (69, 107), "충남": (68, 100),
    "전북": (63, 89),  "전남": (51, 67),  "경북": (87, 106),
    "경남": (91, 77),  "제주": (52, 38),
}
SKY_LABEL = {"1": "맑음", "3": "구름많음", "4": "흐림"}
PTY_LABEL = {"0": "없음", "1": "비", "2": "비/눈", "3": "눈", "4": "소나기"}
SKY_ICON  = {"1": "☀️", "3": "⛅", "4": "☁️"}
PTY_ICON  = {"0": "", "1": "🌧️", "2": "🌨️", "3": "❄️", "4": "🌦️"}

@st.cache_data(ttl=1800, show_spinner=False)
def get_weather(nx: int, ny: int) -> dict | None:
    now = datetime.now()
    if now.minute < 30:
        now -= timedelta(hours=1)
    base_date = now.strftime("%Y%m%d")
    base_time = now.strftime("%H") + "30"
    try:
        resp = requests.get(
            "https://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtFcst",
            params={
                "serviceKey": KMA_API_KEY,
                "pageNo": 1, "numOfRows": 60,
                "dataType": "JSON",
                "base_date": base_date, "base_time": base_time,
                "nx": nx, "ny": ny,
            },
            timeout=10,
        )
        resp.raise_for_status()
        body = resp.json().get("response", {})
        result_code = body.get("header", {}).get("resultCode", "00")
        if result_code != "00":
            result_msg = body.get("header", {}).get("resultMsg", "알 수 없는 오류")
            st.session_state["_wx_error"] = f"기상청 API 오류 [{result_code}]: {result_msg}"
            return None
        items = body["body"]["items"]["item"]
    except Exception as e:
        st.session_state["_wx_error"] = str(e)
        return None
    result = {}
    for item in items:
        cat, val = item["category"], item["fcstValue"]
        if cat not in result:
            result[cat] = val
    st.session_state.pop("_wx_error", None)
    return result

def get_walk_suitability(weather: dict) -> tuple[str, str]:
    pty = weather.get("PTY", "0")
    tmp = float(weather.get("T1H", 20))
    wsd = float(weather.get("WSD", 0))
    if pty != "0":
        return "⛔ 산책 비추천", "#EF4444"
    if tmp <= 0 or tmp >= 33:
        return "⚠️ 온도 주의", "#F97316"
    if wsd >= 9:
        return "⚠️ 강풍 주의", "#F97316"
    if tmp >= 28:
        return "⚠️ 더위 주의", "#F97316"
    return "✅ 산책하기 좋아요", "#10B981"

# ── 데이터 로드 ────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def load_data() -> pd.DataFrame:
    df = pd.read_csv(BASE_DIR / "data" / "pet_tour_preprocessed.csv")
    df = df.dropna(subset=["mapx", "mapy"])
    str_cols = df.select_dtypes("object").columns
    df[str_cols] = df[str_cols].fillna("정보없음")
    df["tel"] = df["tel"].replace("nan", "정보없음")
    # 카페 서브 분류: 제목 기반으로 애견카페 / 카페 재분류
    _dog_cafe_pat = re.compile(
        r'애견.*카페|카페.*애견|도그.*카페|카페.*도그|펫.*카페|카페.*펫'
        r'|강아지.*카페|카페.*강아지|퍼피.*카페|반려.*카페',
        re.IGNORECASE,
    )
    _cafe_pat = re.compile(r'카페|cafe', re.IGNORECASE)
    def _reclassify_cafe(row):
        t = str(row["title"])
        if _dog_cafe_pat.search(t):
            return "애견카페"
        if _cafe_pat.search(t):
            return "카페"
        return row["content_type_name"]
    cafe_rows = df["title"].str.contains(r'카페|cafe', case=False, na=False, regex=True)
    df.loc[cafe_rows, "content_type_name"] = df[cafe_rows].apply(_reclassify_cafe, axis=1)

    if "province" not in df.columns:
        prov_map = {
            "서울특별시": "서울", "부산광역시": "부산", "대구광역시": "대구",
            "인천광역시": "인천", "광주광역시": "광주", "대전광역시": "대전",
            "울산광역시": "울산", "세종특별자치시": "세종", "경기도": "경기",
            "강원특별자치도": "강원", "강원도": "강원",
            "충청북도": "충북", "충청남도": "충남",
            "전북특별자치도": "전북", "전라북도": "전북",
            "전라남도": "전남", "경상북도": "경북",
            "경상남도": "경남", "제주특별자치도": "제주",
        }
        def _prov(addr):
            if pd.isna(addr): return "정보없음"
            for full, short in prov_map.items():
                if full in str(addr): return short
            return "정보없음"
        df["province"] = df["addr1"].apply(_prov)
    return df

# ── 카카오맵 HTML (클러스터링 + 범례 + 코스 마커 + 운영시간/홈페이지) ──
@st.cache_data(ttl=3600, show_spinner=False)
def load_kakao_sdk_script(key: str) -> str:
    try:
        resp = requests.get(
            "https://dapi.kakao.com/v2/maps/sdk.js",
            params={"appkey": key, "autoload": "false"},
            timeout=8,
        )
        resp.raise_for_status()
        sdk_script = resp.text.replace("http://t1.daumcdn.net", "https://t1.daumcdn.net")
        sdk_script = sdk_script.replace('s+"//t1.daumcdn.net', '"https://t1.daumcdn.net')
        return sdk_script.replace("</script", "<\\/script")
    except Exception:
        return ""

def build_map_html(places: list[dict], key: str, course_places: list[dict] = None) -> str:
    places_js = json.dumps(places,          ensure_ascii=False)
    course_js = json.dumps(course_places or [], ensure_ascii=False)
    cat_js    = json.dumps(CAT_COLORS,      ensure_ascii=False)
    size_js   = json.dumps(SIZE_COLORS,     ensure_ascii=False)
    sdk_script = load_kakao_sdk_script(key)
    sdk_url = (
        'https://dapi.kakao.com/v2/maps/sdk.js?'
        f'appkey={urllib.parse.quote(key)}&autoload=false'
    )
    sdk_loader = (
        '<script>'
        '  window.handleKakaoMapLoadError = window.handleKakaoMapLoadError || function(){};'
        '</script>'
        f'<script>{sdk_script}</script>'
        '<script>try { initKakaoMap(); } catch (err) { if (window.console && window.console.error) { console.error(err); } handleKakaoMapLoadError(); }</script>'
        if sdk_script
        else (
            f'<script src="{sdk_url}" onerror="handleKakaoMapLoadError()"></script>'
            '<script>window.addEventListener("load", function(){ initKakaoMap(); });</script>'
        )
    )

    if course_places:
        legend_html = (
            '<span style="display:inline-flex;align-items:center;margin:2px 10px 2px 0;font-size:11px;color:#7B4F8A;font-weight:700">'
            '<span style="width:16px;height:16px;border-radius:50%;background:linear-gradient(135deg,#FFB7C5,#C7CEEA);'
            'display:inline-block;margin-right:5px;flex-shrink:0;border:2px solid rgba(255,255,255,0.95);'
            'box-shadow:0 2px 8px rgba(192,132,212,0.22)"></span>추천 장소</span>'
            '<span style="display:inline-flex;align-items:center;margin:2px 10px 2px 0;font-size:11px;color:#4C6FAE;font-weight:700">'
            '<span style="width:10px;height:14px;border-radius:8px 8px 8px 2px;background:#4C86E8;'
            'display:inline-block;margin-right:5px;flex-shrink:0;border:2px solid white;'
            'box-shadow:0 2px 7px rgba(76,134,232,0.28);transform:rotate(-45deg)"></span>전체 장소</span>'
        )
    else:
        legend_items = [
            ("시도별 그룹 마커", "linear-gradient(135deg,#FFD6E7,#E9D5FF)", "12px"),
            ("500곳 미만", "#FFD6E7", "10px"),
            ("500-1,500곳", "#E9D5FF", "12px"),
            ("1,500곳 이상", "#C084D4", "14px"),
        ]
        legend_html = "".join(
            f'<span style="display:inline-flex;align-items:center;margin:2px 10px 2px 0;font-size:11px;color:#7B4F8A;font-weight:700">'
            f'<span style="width:{size};height:{size};border-radius:50%;background:{bg};'
            f'display:inline-block;margin-right:5px;flex-shrink:0;border:2px solid rgba(255,255,255,0.95);'
            f'box-shadow:0 2px 8px rgba(192,132,212,0.22)"></span>{label}</span>'
            for label, bg, size in legend_items
        )

    return f"""<!DOCTYPE html><html><head>
<meta charset="utf-8">
<style>
  body{{margin:0;padding:0;font-family:'Malgun Gothic',sans-serif;background:transparent}}
  #map{{width:100%;height:520px}}
  .legend{{
    position:absolute;bottom:24px;left:10px;
    background:rgba(255,255,255,0.95);
    padding:8px 12px;border-radius:12px;z-index:5;
    box-shadow:0 2px 12px rgba(180,100,140,0.18);
    display:flex;flex-wrap:wrap;max-width:calc(100% - 24px)
  }}
  .iw{{padding:12px;min-width:190px;max-width:240px;font-family:'Malgun Gothic',sans-serif}}
  .iw-title{{font-size:14px;font-weight:700;color:#222;margin-bottom:5px}}
  .iw-addr{{font-size:11px;color:#888;margin-bottom:7px;line-height:1.5}}
  .tag{{display:inline-block;padding:2px 8px;border-radius:10px;font-size:11px;margin-right:3px;margin-bottom:3px;color:#fff}}
  .iw-row{{font-size:11px;color:#666;margin-top:4px;line-height:1.5}}
  .iw-row a{{color:#8B5CF6;text-decoration:none}}
  .cp-wrap{{
    position:relative;display:flex;flex-direction:column;align-items:center;
    transform:translateY(-10px);cursor:pointer;user-select:none
  }}
  .cp{{
    width:46px;height:46px;border-radius:50%;
    background:radial-gradient(circle at 35% 28%,var(--cp-light),var(--cp-main) 52%,var(--cp-deep) 92%);
    color:var(--cp-text);font-weight:900;font-size:22px;
    display:flex;align-items:center;justify-content:center;
    border:3px solid rgba(255,255,255,0.96);
    box-shadow:0 10px 24px rgba(180,100,140,0.22),0 0 0 7px rgba(255,255,255,0.55)
  }}
  .cp-label{{
    margin-top:5px;max-width:116px;padding:4px 8px;border-radius:999px;
    background:rgba(255,255,255,0.94);color:var(--cp-text);
    font-size:11px;font-weight:800;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
    box-shadow:0 3px 10px rgba(180,100,140,0.16);
    border:1px solid var(--cp-deep)
  }}
  .prov-wrap{{
    position:relative;display:flex;flex-direction:column;align-items:center;
    transform:translateY(-8px);cursor:pointer;user-select:none
  }}
  .prov-bubble{{
    min-width:44px;height:44px;padding:0 10px;border-radius:999px;
    background:linear-gradient(135deg,#FFD6E7 0%,#E9D5FF 100%);
    color:#7B4F8A;font-size:15px;font-weight:900;
    display:flex;align-items:center;justify-content:center;
    border:3px solid rgba(255,255,255,0.96);
    box-shadow:0 8px 22px rgba(192,132,212,0.28),0 2px 8px rgba(255,143,171,0.2)
  }}
  .prov-label{{
    margin-top:5px;padding:3px 8px;border-radius:999px;
    background:rgba(255,255,255,0.92);color:#8B5CF6;
    font-size:11px;font-weight:800;white-space:nowrap;
    box-shadow:0 2px 8px rgba(180,100,140,0.16)
  }}
  .list-group{{
    min-width:24px;height:24px;padding:0 6px;border-radius:999px;
    background:#4C86E8;color:white;font-size:11px;font-weight:900;
    display:flex;align-items:center;justify-content:center;
    border:2px solid white;box-shadow:0 4px 12px rgba(76,134,232,0.28)
  }}
  .list-group-label{{
    margin-top:3px;padding:2px 6px;border-radius:999px;
    background:rgba(255,255,255,0.9);color:#4C6FAE;
    font-size:10px;font-weight:800;white-space:nowrap;
    box-shadow:0 2px 8px rgba(76,134,232,0.15)
  }}
  .mw{{position:relative;width:100%;height:520px}}
  .map-error{{
    position:absolute;inset:0;display:none;align-items:center;justify-content:center;
    text-align:center;color:#7B4F8A;background:#FFF7FB;border:2px dashed #FFD6E7;
    border-radius:16px;font-size:14px;font-weight:700;line-height:1.6;padding:24px
  }}
</style>
</head><body>
<div class="mw">
  <div id="map"></div>
  <div id="map-error" class="map-error"></div>
  <div class="legend">{legend_html}</div>
</div>
<script>
(function(){{
  function showMapError(message){{
    var err=document.getElementById('map-error');
    if(err){{
      err.style.display='flex';
      err.innerHTML=message;
    }}
  }}

  window.handleKakaoMapLoadError=function(){{
    showMapError('카카오 지도 SDK를 불러오지 못했습니다.<br>JavaScript 키와 도메인 등록을 확인해 주세요.');
  }};

  window.initKakaoMap=function(){{
    try{{
      if(!window.kakao||!kakao.maps){{
        throw new Error('Kakao Maps SDK is not available.');
      }}

      kakao.maps.load(function(){{
        var map=new kakao.maps.Map(document.getElementById('map'),{{center:new kakao.maps.LatLng(35.9,127.8),level:13}});
        var iw=new kakao.maps.InfoWindow({{zIndex:1}});
        var C={cat_js};
        var S={size_js};
        var places={places_js};
        var markers=[];
        var markerItems=[];
        var smallBlueMarkerSvg='<svg xmlns="http://www.w3.org/2000/svg" width="18" height="24" viewBox="0 0 18 24"><path d="M9 23s7-7.1 7-14A7 7 0 1 0 2 9c0 6.9 7 14 7 14z" fill="#4C86E8" stroke="white" stroke-width="2"/><circle cx="9" cy="9" r="3" fill="white" opacity=".95"/></svg>';
        var smallBlueMarkerImage=new kakao.maps.MarkerImage(
          'data:image/svg+xml;charset=UTF-8,'+encodeURIComponent(smallBlueMarkerSvg),
          new kakao.maps.Size(18,24),
          {{offset:new kakao.maps.Point(9,24)}}
        );
        places.forEach(function(p){{
          if(!p.mapy||!p.mapx)return;
          var pos=new kakao.maps.LatLng(p.mapy,p.mapx);
          var m=new kakao.maps.Marker({{position:pos,title:p.title}});
          m.setImage(smallBlueMarkerImage);
          var cc=C[p.content_type_name]||'#6B7280';
          var sc=S[p.dog_size_category]||'#9CA3AF';
          var html='<div class="iw">'
            +'<div class="iw-title">'+p.title+'</div>'
            +'<div class="iw-addr">'+(p.addr1||'')+'</div>'
            +'<div>'
            +'<span class="tag" style="background:'+cc+'">'+p.content_type_name+'</span>'
            +'<span class="tag" style="background:'+sc+'">'+p.dog_size_category+'</span>'
            +'</div>'
            +(p.acmpyTypeCd&&p.acmpyTypeCd!=='정보없음'?'<div class="iw-row">🐾 '+p.acmpyTypeCd+'</div>':'')
            +(p.opertime&&p.opertime!=='정보없음'?'<div class="iw-row">🕐 '+p.opertime+'</div>':'')
            +(p.tel&&p.tel!=='정보없음'?'<div class="iw-row">📞 '+p.tel+'</div>':'')
            +(p.homepage&&p.homepage!=='정보없음'?'<div class="iw-row"><a href="'+p.homepage+'" target="_blank">🔗 홈페이지</a></div>':'')
            +'<div class="iw-row"><a href="https://map.kakao.com/link/map/'+encodeURIComponent(p.title)+','+p.mapy+','+p.mapx+'" target="_blank">🗺️ 카카오맵에서 보기</a></div>'
            +'</div>';
          kakao.maps.event.addListener(m,'click',(function(mk,c){{return function(){{iw.setContent(c);iw.open(map,mk);}};}})(m,html));
          markers.push(m);
          markerItems.push({{marker:m,province:p.province||'정보없음',gu:p.gu_name||'정보없음',position:pos}});
        }});
        var listOverlays=[];
        function clearListOverlays(){{
          listOverlays.forEach(function(o){{o.setMap(null);}});
          listOverlays=[];
        }}
        function showListMarkers(selectedProvince, fitToBounds){{
          var bounds=new kakao.maps.LatLngBounds();
          var shown=0;
          var selected=[];
          clearListOverlays();
          markerItems.forEach(function(item){{item.marker.setMap(null);}});
          markerItems.forEach(function(item){{
            var visible=!selectedProvince||item.province===selectedProvince;
            if(visible){{
              selected.push(item);
              bounds.extend(item.position);
              shown++;
            }}
          }});
          if(selected.length<=180){{
            selected.forEach(function(item){{item.marker.setMap(map);}});
          }}else{{
            var groups={{}};
            selected.forEach(function(item){{
              var name=item.gu&&item.gu!=='정보없음'?item.gu:item.province;
              if(!groups[name]){{groups[name]={{count:0,lat:0,lng:0}};}}
              groups[name].count++;
              groups[name].lat+=item.position.getLat();
              groups[name].lng+=item.position.getLng();
            }});
            Object.keys(groups).forEach(function(name){{
              var g=groups[name];
              var pos=new kakao.maps.LatLng(g.lat/g.count,g.lng/g.count);
              var el=document.createElement('div');
              el.className='prov-wrap';
              el.innerHTML='<div class="list-group">'+formatCount(g.count)+'</div><div class="list-group-label">'+name+'</div>';
              var overlay=new kakao.maps.CustomOverlay({{position:pos,content:el,yAnchor:0.85,zIndex:6}});
              listOverlays.push(overlay);
              overlay.setMap(map);
            }});
          }}
          if(fitToBounds&&shown>0){{map.setBounds(bounds,60);}}
        }}
        var provinceOverlays=[];
        function hideProvinceOverlays(){{
          provinceOverlays.forEach(function(o){{o.setMap(null);}});
        }}
        function formatCount(count){{
          if(count>=1000){{
            var value=(count/1000).toFixed(1);
            return value.replace(/\\.0$/,'')+'k';
          }}
          return String(count);
        }}
        var cp={course_js};
        var nums=['①','②','③','④','⑤','⑥','⑦','⑧'];
        var cpPalette=[
          {{light:'#FFF0F5',main:'#FFB7C5',deep:'#E879A0',text:'#8A4E67'}},
          {{light:'#F0FFF8',main:'#A8D5BA',deep:'#6FB28A',text:'#4F7D61'}},
          {{light:'#F5F0FF',main:'#C7CEEA',deep:'#9B8BD3',text:'#66548E'}},
          {{light:'#FFF8F0',main:'#FFDAC1',deep:'#E9B57C',text:'#8A6540'}}
        ];
        if(cp.length>0){{
          showListMarkers(null,false);
          var courseBounds=new kakao.maps.LatLngBounds();
          var courseShown=0;
          cp.forEach(function(p,i){{
    if(!p.mapy||!p.mapx)return;
    var coursePos=new kakao.maps.LatLng(p.mapy,p.mapx);
    courseBounds.extend(coursePos);
    courseShown++;
    var el=document.createElement('div');
    el.className='cp-wrap';
    var color=cpPalette[i%cpPalette.length];
    el.style.setProperty('--cp-light',color.light);
    el.style.setProperty('--cp-main',color.main);
    el.style.setProperty('--cp-deep',color.deep);
    el.style.setProperty('--cp-text',color.text);
    var label=(p.title||'추천 장소');
    el.innerHTML='<div class="cp">'+(nums[i]||(i+1))+'</div><div class="cp-label">'+label+'</div>';
    new kakao.maps.CustomOverlay({{position:coursePos,content:el,yAnchor:1.15,zIndex:10}}).setMap(map);
  }});
  if(courseShown>1){{
    map.setBounds(courseBounds,80);
  }}else if(courseShown===1){{
    map.setCenter(new kakao.maps.LatLng(cp[0].mapy,cp[0].mapx));
    map.setLevel(8);
  }}
}}else if(markerItems.length>0){{
  var groups={{}};
  places.forEach(function(p){{
    var lat=parseFloat(p.mapy), lng=parseFloat(p.mapx);
    if(!lat||!lng)return;
    var prov=p.province||'정보없음';
    if(!groups[prov]){{groups[prov]={{province:prov,count:0,lat:0,lng:0}};}}
    groups[prov].count++;
    groups[prov].lat+=lat;
    groups[prov].lng+=lng;
  }});
  var provinceBounds=new kakao.maps.LatLngBounds();
  Object.keys(groups).forEach(function(name){{
    var g=groups[name];
    var pos=new kakao.maps.LatLng(g.lat/g.count,g.lng/g.count);
    var el=document.createElement('div');
    el.className='prov-wrap';
    el.innerHTML='<div class="prov-bubble">'+formatCount(g.count)+'</div><div class="prov-label">'+name+'</div>';
    el.addEventListener('click',(function(prov){{return function(){{
      hideProvinceOverlays();
      iw.close();
      showListMarkers(prov,true);
      map.setLevel(Math.min(map.getLevel(),9));
    }};}})(name));
    var overlay=new kakao.maps.CustomOverlay({{position:pos,content:el,yAnchor:0.85,zIndex:7}});
    provinceOverlays.push(overlay);
    overlay.setMap(map);
    provinceBounds.extend(pos);
  }});
  if(provinceOverlays.length>0){{map.setBounds(provinceBounds,80);}}
}}
      }});
    }}catch(e){{
      showMapError('카카오 지도를 초기화하지 못했습니다.<br>'+String(e.message||e));
      console.error(e);
    }}
  }};
}})();
</script>
{sdk_loader}
</body></html>"""

# ── 규칙 기반 코스 추천 ────────────────────────────────────────────
def recommend_course(df: pd.DataFrame) -> list[dict]:
    if len(df) == 0:
        return []
    valid    = df[df["province"] != "정보없음"]
    top_prov = valid["province"].value_counts().index[0] if len(valid) > 0 \
               else df["province"].value_counts().index[0]
    result   = []
    used_titles = set()

    def _course_item(place, cat=None):
        return {
            "cat":      cat or place["content_type_name"],
            "title":    place["title"],
            "addr":     place["addr1"],
            "prov":     place["province"],
            "size":     place["dog_size_category"],
            "info":     place["acmpyTypeCd"],
            "mapx":     float(place["mapx"]) if pd.notna(place["mapx"]) else None,
            "mapy":     float(place["mapy"]) if pd.notna(place["mapy"]) else None,
            "homepage": str(place.get("homepage", "정보없음")),
            "time":     "",
            "reason":   "",
        }

    for cat in COURSE_ORDER:
        cat_df = df[df["content_type_name"] == cat]
        if cat_df.empty:
            continue
        cat_df = cat_df[~cat_df["title"].isin(used_titles)]
        if cat_df.empty:
            continue
        same_prov = cat_df[cat_df["province"] == top_prov]
        pool  = same_prov if len(same_prov) > 0 else cat_df
        place = pool.sample(1).iloc[0]
        result.append(_course_item(place, cat))
        used_titles.add(place["title"])
        if len(result) >= 4:
            break
    if len(result) < min(4, len(df)):
        fill_pool = df[~df["title"].isin(used_titles)]
        same_prov = fill_pool[fill_pool["province"] == top_prov]
        fill_pool = same_prov if len(same_prov) > 0 else fill_pool
        for _, place in fill_pool.sample(min(4 - len(result), len(fill_pool))).iterrows():
            result.append(_course_item(place))
            used_titles.add(place["title"])
    return result

# ── AI 코스 추천 ───────────────────────────────────────────────────
def ai_recommend_course(dog_name: str, dog_size: str, places: list[dict],
                        weather_ctx: str = "") -> list[dict]:
    sample = places[:20]
    places_text = "\n".join(
        f"- {p['title']} | 유형: {p['content_type_name']} | 자치구: {p['gu_name']}"
        f" | 주소: {p.get('addr1') or '정보없음'}"
        f" | 동반형태: {p.get('acmpyTypeCd') or '정보없음'}"
        f" | 입장가능견종: {p['dog_size_category']}"
        for p in sample
    )
    n_courses = min(4, len(sample))
    time_labels = ["오전", "점심", "오후1", "오후2"][:n_courses]
    example_items = "\n".join(
        f'  {{"title": "목록에 있는 장소명 그대로", "time": "{t}", "reason": "선정 이유 1~2줄"}}{"," if i < n_courses - 1 else ""}'
        for i, t in enumerate(time_labels)
    )
    weather_line = f"\n날씨 정보: {weather_ctx}" if weather_ctx else ""
    prompt = (
        f"강아지 이름: {dog_name} | 크기: {dog_size}{weather_line}\n\n"
        f"[반려동물 동반 가능 장소 목록]\n{places_text}\n\n"
        f"[규칙]\n"
        f"- 위 목록에서 서로 다른 {n_courses}곳을 골라 오전→점심→오후 순서로 자연스러운 코스를 구성하세요.\n"
        f"- 유형(content_type_name)이 같거나 유사한 장소(예: 박물관+미술관, 카페+카페)는 2곳 이상 선택하지 마세요.\n"
        f"- reason에 {dog_name}의 이름을 부르며 친근한 말투로, 1~2줄 이내로 작성하세요.\n"
        f"- 좌표·URL·링크는 절대 생성하지 마세요.\n\n"
        f"반드시 아래 JSON 배열 형식으로만 응답하세요 (JSON 외 텍스트 없음, 항목 수 정확히 {n_courses}개):\n"
        f'[\n{example_items}\n]'
    )
    resp = requests.post(
        "https://api.ennoia.so/api/preset/v2/chat/completions",
        headers={"project": ENNOEIA_PROJECT, "apiKey": ENNOEIA_KEY,
                 "Content-Type": "application/json; charset=utf-8"},
        json={"hash": ENNOEIA_HASH, "params": {},
              "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}]},
        timeout=90,
    )
    resp.raise_for_status()
    result = resp.json()
    content = ""
    if "choices" in result:
        raw = result["choices"][0]["message"]["content"]
        content = raw[0].get("text", str(raw)) if isinstance(raw, list) else str(raw)
    else:
        content = str(result)
    content = content.strip()
    if content.startswith("```"):
        start = content.index("[")
        end   = content.rindex("]") + 1
        content = content[start:end]
    return json.loads(content)


def enrich_ai_course(ai_items: list[dict], df: pd.DataFrame) -> list[dict]:
    result = []
    for item in ai_items:
        title = item.get("title", "")
        match = df[df["title"] == title]
        if match.empty:
            match = df[df["title"].str.contains(title[:min(6, len(title))], na=False, regex=False)]
        if not match.empty:
            row = match.iloc[0]
            mapx = row["mapx"] if "mapx" in row.index else None
            mapy = row["mapy"] if "mapy" in row.index else None
            result.append({
                "cat":      row.get("content_type_name", "기타"),
                "title":    row["title"],
                "addr":     row.get("addr1", "정보없음"),
                "prov":     row.get("province", ""),
                "size":     row.get("dog_size_category", "정보없음"),
                "info":     row.get("acmpyTypeCd", "정보없음"),
                "mapx":     float(mapx) if mapx is not None and pd.notna(mapx) else None,
                "mapy":     float(mapy) if mapy is not None and pd.notna(mapy) else None,
                "homepage": str(row.get("homepage", "정보없음")),
                "time":     item.get("time", ""),
                "reason":   item.get("reason", ""),
            })
        else:
            result.append({
                "cat": "기타", "title": title, "addr": "정보없음", "prov": "",
                "size": "정보없음", "info": "정보없음",
                "mapx": None, "mapy": None, "homepage": "정보없음",
                "time": item.get("time", ""), "reason": item.get("reason", ""),
            })
    return result

def build_filter_map_picks(df: pd.DataFrame, limit: int = 4) -> list[dict]:
    if df.empty:
        return []
    picks = df.copy()
    if "content_type_name" in picks.columns:
        picks["_cat_rank"] = picks["content_type_name"].map(
            {cat: idx for idx, cat in enumerate(COURSE_ORDER)}
        ).fillna(len(COURSE_ORDER))
    else:
        picks["_cat_rank"] = len(COURSE_ORDER)
    picks = picks.sort_values(["_cat_rank", "title"], kind="stable").head(limit)
    return [
        {
            "title": row["title"],
            "cat": row.get("content_type_name", "기타"),
            "addr": row.get("addr1", "정보없음"),
            "prov": row.get("province", ""),
            "size": row.get("dog_size_category", "정보없음"),
            "info": row.get("acmpyTypeCd", "정보없음"),
            "mapx": float(row["mapx"]),
            "mapy": float(row["mapy"]),
            "homepage": str(row.get("homepage", "정보없음")),
            "time": "",
            "reason": "",
        }
        for _, row in picks.iterrows()
        if pd.notna(row.get("mapx")) and pd.notna(row.get("mapy"))
    ]

# ── 세션 상태 초기화 ───────────────────────────────────────────────
for _k, _v in [("course_cards", []), ("course_ai_text", ""),
               ("course_map_places", []), ("course_name", ""), ("course_is_ai", False)]:
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ── 데이터 로드 ────────────────────────────────────────────────────
df_raw = load_data()

# ── 사이드바 ───────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="text-align:center;padding:10px 0 4px 0">
      <span style="font-size:1.9rem;font-weight:800;
           background:linear-gradient(135deg,#FF8FAB,#C084D4);
           -webkit-background-clip:text;-webkit-text-fill-color:transparent;
           background-clip:text;color:transparent">🐾 댕댕맵</span>
    </div>""", unsafe_allow_html=True)

    st.header("🐶 우리 강아지")
    dog_name    = st.text_input("이름", placeholder="예: 초코, 댕댕이, 뭉치")
    _icon_labels = list(SIZE_ICONS.values())
    _size_label  = st.radio("크기", _icon_labels, horizontal=True)
    dog_size     = {v: k for k, v in SIZE_ICONS.items()}[_size_label]

    st.divider()
    st.header("🔍 필터")

    all_cats  = sorted(df_raw["content_type_name"].unique().tolist())
    sel_cats  = st.multiselect("카테고리", all_cats,  key="sel_cats")

    all_provs = sorted(df_raw["province"].dropna().unique().tolist())
    sel_provs = st.multiselect("시도",     all_provs, key="sel_provs")

    _gu_base  = df_raw[df_raw["province"].isin(sel_provs)] if sel_provs else df_raw
    all_gus   = sorted(_gu_base["gu_name"].dropna().unique().tolist())
    sel_gus   = st.multiselect("자치구",   all_gus,   key="sel_gus")

    def _reset_filters():
        st.session_state["sel_cats"] = []
        st.session_state["sel_provs"] = []
        st.session_state["sel_gus"] = []
        st.session_state.course_cards      = []
        st.session_state.course_ai_text    = ""
        st.session_state.course_map_places = []
        st.session_state.course_name       = ""
        st.session_state.course_is_ai      = False
    st.button("🔄 필터 초기화", on_click=_reset_filters, use_container_width=True, type="secondary")

    st.divider()
    st.header("🌤️ 날씨")
    _wx_region = sel_provs[0] if sel_provs else "서울"
    _nx, _ny   = REGION_GRID.get(_wx_region, (60, 127))
    if KMA_API_KEY:
        _wx = get_weather(_nx, _ny)
        if _wx:
            _sky      = _wx.get("SKY", "1")
            _pty      = _wx.get("PTY", "0")
            _tmp      = _wx.get("T1H", "--")
            _reh      = _wx.get("REH", "--")
            _wsd      = _wx.get("WSD", "--")
            _icon     = PTY_ICON.get(_pty, "") or SKY_ICON.get(_sky, "🌤️")
            _sky_text = PTY_LABEL.get(_pty, "없음") if _pty != "0" else SKY_LABEL.get(_sky, "맑음")
            _wt, _wc  = get_walk_suitability(_wx)
            st.markdown(f"""
            <div style="background:white;border-radius:16px;border:2px solid #FFD6E7;
                        padding:14px 16px;margin-bottom:4px">
              <div style="font-size:0.76rem;color:#999;margin-bottom:6px">
                📍 {_wx_region} 현재 날씨
              </div>
              <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">
                <span style="font-size:2rem">{_icon}</span>
                <div>
                  <span style="font-size:1.5rem;font-weight:800;color:#333">{_tmp}°C</span>
                  <span style="font-size:0.8rem;color:#888;margin-left:6px">{_sky_text}</span>
                </div>
              </div>
              <div style="font-size:0.78rem;color:#777;margin-bottom:8px">
                💧 습도 {_reh}% &nbsp;|&nbsp; 💨 풍속 {_wsd}m/s
              </div>
              <div style="background:{_wc}22;border:1.5px solid {_wc}66;
                          border-radius:10px;padding:5px 10px;
                          font-size:0.82rem;font-weight:700;color:{_wc}">
                {_wt}
              </div>
            </div>""", unsafe_allow_html=True)
        else:
            _wx_err = st.session_state.get("_wx_error", "")
            st.caption(f"날씨 정보를 불러올 수 없습니다.")
            if _wx_err:
                st.caption(f"⚠️ {_wx_err}")
    else:
        st.caption("⚠️ .env에 KMA_API_KEY를 추가해주세요.")

    st.divider()
    use_ai    = st.toggle("🤖 AI 코스 추천 사용",
                          value=bool(ENNOEIA_KEY), disabled=not bool(ENNOEIA_KEY),
                          help="ENNOEIA_API_KEY가 없으면 규칙 기반으로 추천됩니다.")
    do_course = st.button("✨ 코스 추천", type="primary", use_container_width=True)

# ── 데이터 필터링 ──────────────────────────────────────────────────
df = df_raw.copy()
df = df[df["dog_size_category"].isin(SIZE_COMPAT[dog_size])]
if sel_cats:  df = df[df["content_type_name"].isin(sel_cats)]
if sel_provs: df = df[df["province"].isin(sel_provs)]
if sel_gus:   df = df[df["gu_name"].isin(sel_gus)]

display_name = dog_name.strip() if dog_name.strip() else "반려견"
filters_active = bool(sel_cats or sel_provs or sel_gus)

# ── 코스 추천 처리 ─────────────────────────────────────────────────
if do_course:
    if len(df) == 0:
        st.sidebar.warning("조건에 맞는 장소가 없습니다.")
    elif use_ai:
        with st.spinner(f"🤖 댕댕맵이 {display_name}를 위한 코스를 추천 중... 잠시만 기다려 주세요!"):
            ai_cols = [c for c in ["title","content_type_name","province","gu_name",
                                   "addr1","acmpyTypeCd","dog_size_category"] if c in df.columns]
            # 날씨 컨텍스트 생성
            _weather_ctx = ""
            if KMA_API_KEY and sel_provs:
                _wx = get_weather(*REGION_GRID.get(sel_provs[0], (60, 127)))
                if _wx:
                    _pty = _wx.get("PTY", "0")
                    _sky = _wx.get("SKY", "1")
                    _tmp = _wx.get("T1H", "--")
                    _desc = PTY_LABEL.get(_pty, "") if _pty != "0" else SKY_LABEL.get(_sky, "맑음")
                    _weather_ctx = f"{_tmp}°C, {_desc}"
                    if _pty != "0":
                        _weather_ctx += " → 실내 위주 코스 권장"
                    elif float(_tmp) >= 28:
                        _weather_ctx += " → 그늘·실내 장소 우선 권장"
            try:
                ai_items = ai_recommend_course(display_name, dog_size,
                                               df[ai_cols].to_dict("records"), _weather_ctx)
                course   = enrich_ai_course(ai_items, df)
            except Exception as e:
                course = []
                st.sidebar.error(f"AI 추천 오류: {e}")
        st.session_state.course_cards      = course
        st.session_state.course_map_places = [
            {"title": p["title"], "mapx": p["mapx"], "mapy": p["mapy"]}
            for p in course if p.get("mapx") and p.get("mapy")
        ]
        st.session_state.course_ai_text    = ""
        st.session_state.course_name       = display_name
        st.session_state.course_is_ai      = True
    else:
        course = recommend_course(df)
        st.session_state.course_cards      = course
        st.session_state.course_map_places = [
            {"title": p["title"], "mapx": p["mapx"], "mapy": p["mapy"]}
            for p in course if p.get("mapx") and p.get("mapy")
        ]
        st.session_state.course_ai_text    = ""
        st.session_state.course_name       = display_name
        st.session_state.course_is_ai      = False

# ── 타이틀 ────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;padding:6px 0 18px 0">
  <div style="font-size:2.8rem;font-weight:800;line-height:1.2;
       background:linear-gradient(135deg,#FF8FAB 0%,#C084D4 50%,#7BA7E8 100%);
       -webkit-background-clip:text;-webkit-text-fill-color:transparent;
       background-clip:text;color:transparent">
    🐾 댕댕맵
  </div>
  <div style="color:#C06080;font-size:0.9rem;margin-top:6px;font-weight:600;letter-spacing:0.3px">
    전국 반려견 동반 관광 맞춤 추천 플랫폼 &nbsp;✦&nbsp; 2026 한국관광공사 공모전
  </div>
</div>""", unsafe_allow_html=True)

# ── 통계 ──────────────────────────────────────────────────────────
c1, c2, c3 = st.columns(3)
c1.metric("🗺️ 검색된 장소", f"{len(df)}곳")
c2.metric("📍 시도",        f"{df['province'].nunique()}개")
c3.metric("🏷️ 카테고리",    f"{df['content_type_name'].nunique()}개")

# ── 결과 없음 안내 ─────────────────────────────────────────────────
if len(df) == 0:
    st.warning("🔍 조건에 맞는 장소가 없습니다.")
    base = df_raw[df_raw["dog_size_category"].isin(SIZE_COMPAT[dog_size])]
    if sel_gus:
        tmp = base.copy()
        if sel_cats:  tmp = tmp[tmp["content_type_name"].isin(sel_cats)]
        if sel_provs: tmp = tmp[tmp["province"].isin(sel_provs)]
        if len(tmp) > 0:
            st.info(f"💡 자치구 필터를 해제하면 **{len(tmp)}곳** 검색됩니다.")
    elif sel_provs:
        tmp = base[base["content_type_name"].isin(sel_cats)] if sel_cats else base.copy()
        if len(tmp) > 0:
            st.info(f"💡 시도 필터를 해제하면 **{len(tmp)}곳** 검색됩니다.")
    elif sel_cats:
        if len(base) > 0:
            st.info(f"💡 카테고리 필터를 해제하면 **{len(base)}곳** 검색됩니다.")

# ── 지도 (클러스터링 + 코스 마커 + 범례) ──────────────────────────
filter_map_picks = []
if not KAKAO_JS_KEY:
    st.warning("⚠️ .env 파일에 KAKAO_JS_KEY를 추가해주세요.")
else:
    map_cols   = [c for c in ["title","addr1","mapx","mapy","province","content_type_name",
                               "gu_name","dog_size_category","acmpyTypeCd",
                               "tel","opertime","homepage"] if c in df.columns]
    places_df  = df[map_cols].copy()
    places_df["tel"] = places_df["tel"].replace("nan", "정보없음").fillna("정보없음")
    filter_map_picks = build_filter_map_picks(places_df) if filters_active else []
    map_focus_places = (
        st.session_state.course_map_places
        if st.session_state.course_map_places
        else filter_map_picks
    )
    components.html(
        build_map_html(places_df.to_dict("records"), KAKAO_JS_KEY,
                       map_focus_places),
        height=550,
    )

# ── 코스 추천 결과 ─────────────────────────────────────────────────
recommendation_cards = st.session_state.course_cards or filter_map_picks
if recommendation_cards:
    ai_label = "🤖 AI " if st.session_state.course_is_ai else ""
    _num_labels = ["①", "②", "③", "④", "⑤", "⑥", "⑦", "⑧"]
    _marker_str = "".join(_num_labels[:len(recommendation_cards)])
    _heading = "🗺️ 오늘의 추천 코스" if st.session_state.course_cards else "💗 추천 장소"
    st.markdown(f"""
    <div style="margin:20px 0 10px 0">
      <span style="font-size:1.1rem;font-weight:800;color:#8B5CF6">
        {_heading}
      </span>
      <span style="font-size:0.8rem;color:#AAA;margin-left:10px">
        지도의 {_marker_str} 마커를 확인하세요
      </span>
    </div>""", unsafe_allow_html=True)

    cols = st.columns(min(4, len(recommendation_cards)))
    for i, p in enumerate(recommendation_cards):
        col = cols[i % len(cols)]
        cs = CARD_STYLES[i % len(CARD_STYLES)]
        addr_short   = p["addr"][:35] + ("…" if len(p["addr"]) > 35 else "")
        reason_text  = p.get("reason") or (p["info"] if p["info"] != "정보없음" else "")
        info_line    = (f'<div style="font-size:0.72rem;color:#666;margin-top:6px;line-height:1.5">'
                        f'{reason_text[:60]}</div>') if reason_text else ""
        time_badge   = (f'<span style="background:#E8D5F5;color:#7B4F8A;padding:2px 8px;'
                        f'border-radius:10px;font-size:0.7rem;margin-left:4px">{p["time"]}</span>') \
                       if p.get("time") else ""
        map_link     = (
            f'https://map.kakao.com/link/map/{urllib.parse.quote(p["title"])},{p["mapy"]},{p["mapx"]}'
            if p.get("mapx") and p.get("mapy") else ""
        )
        _ls = 'font-size:0.7rem;text-decoration:none;border-radius:8px;padding:2px 8px;white-space:nowrap;'
        map_btn  = (f'<a href="{map_link}" target="_blank" '
                    f'style="{_ls}color:#8B5CF6;border:1px solid #C4B5FD">🗺️ 카카오맵</a>') \
                   if map_link else ""
        homepage = p.get("homepage", "정보없음")
        home_btn = (f'<a href="{homepage}" target="_blank" '
                    f'style="{_ls}color:#059669;border:1px solid #A7F3D0">🔗 홈페이지</a>') \
                   if homepage and homepage not in ("정보없음", "nan") else ""
        links_row = (f'<div style="margin-top:8px;display:flex;gap:6px;flex-wrap:wrap">'
                     f'{map_btn}{home_btn}</div>') if (map_btn or home_btn) else ""
        with col:
            st.markdown(f"""
            <div style="background:{cs['bg']};border:2px solid {cs['border']};
                        border-radius:18px;padding:16px;min-height:158px">
              <div style="font-size:1.6rem;margin-bottom:6px">{cs['num']}</div>
              <div style="font-weight:800;font-size:0.92rem;color:#333;margin-bottom:4px;line-height:1.3">
                {p['title']}
              </div>
              <div style="font-size:0.74rem;color:#888;margin-bottom:9px;line-height:1.4">
                📍 {addr_short}
              </div>
              <span style="background:{cs['border']};color:white;padding:2px 9px;
                           border-radius:10px;font-size:0.7rem;font-weight:700">{p['cat']}</span>
              <span style="background:#EEE;color:#666;padding:2px 8px;
                           border-radius:10px;font-size:0.7rem;margin-left:4px">{p['size']}</span>
              {time_badge}
              {info_line}
              {links_row}
            </div>""", unsafe_allow_html=True)

    st.markdown(
        '<div style="margin-top:10px;font-size:0.78rem;color:#999;text-align:center">'
        '⚠️ 폐업한 장소가 존재할 수 있으니, 방문 전 반드시 링크를 통해 영업 여부를 확인해 주세요.'
        '</div>',
        unsafe_allow_html=True,
    )

# ── 전체 장소 목록 ──────────────────────────────────────────────────
with st.expander("📋 전체 장소 목록 보기"):
    if len(df) > 0:
        show_cols = [c for c in ["title","province","gu_name","content_type_name",
                                  "dog_size_category","acmpyTypeCd","addr1"] if c in df.columns]
        st.dataframe(
            df[show_cols].rename(columns={
                "title": "장소명", "province": "시도", "gu_name": "자치구",
                "content_type_name": "카테고리", "dog_size_category": "견종크기",
                "acmpyTypeCd": "동반형태", "addr1": "주소",
            }),
            use_container_width=True,
            height=320,
            column_config={
                "장소명":  st.column_config.TextColumn("🏠 장소명",   width="medium"),
                "시도":    st.column_config.TextColumn("📍 시도",     width="small"),
                "자치구":  st.column_config.TextColumn("🏘️ 자치구",   width="small"),
                "카테고리":st.column_config.TextColumn("🏷️ 카테고리", width="small"),
                "견종크기":st.column_config.TextColumn("🐾 견종크기", width="small"),
                "동반형태":st.column_config.TextColumn("ℹ️ 동반형태", width="medium"),
                "주소":    st.column_config.TextColumn("📌 주소",     width="large"),
            },
        )
    else:
        st.info("검색 조건에 맞는 장소가 없습니다.")
