import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import json
import os
from pathlib import Path
from datetime import datetime, timedelta
import requests
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR.parent / ".env", override=True)
KAKAO_JS_KEY    = os.environ.get("KAKAO_JS_KEY", "")
KMA_API_KEY     = os.environ.get("KMA_API_KEY", "")
ENNOEIA_KEY     = os.environ.get("ENNOEIA_API_KEY", "")
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
COURSE_ORDER = ["관광지", "음식점", "문화시설", "레포츠", "숙박", "쇼핑", "기타"]
CARD_STYLES  = [
    {"bg": "#FFF0F5", "border": "#FFB7C5", "num": "①"},
    {"bg": "#F0FFF8", "border": "#A8D5BA", "num": "②"},
    {"bg": "#F5F0FF", "border": "#C7CEEA", "num": "③"},
    {"bg": "#FFF8F0", "border": "#FFDAC1", "num": "④"},
]
CAT_COLORS = {
    "관광지": "#3B82F6", "문화시설": "#8B5CF6", "음식점": "#F97316",
    "숙박": "#10B981", "레포츠": "#EF4444", "쇼핑": "#EC4899", "기타": "#6B7280",
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
        items = resp.json()["response"]["body"]["items"]["item"]
    except Exception:
        return None
    result = {}
    for item in items:
        cat, val = item["category"], item["fcstValue"]
        if cat not in result:
            result[cat] = val
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
def build_map_html(places: list[dict], key: str, course_places: list[dict] = None) -> str:
    places_js = json.dumps(places,          ensure_ascii=False)
    course_js = json.dumps(course_places or [], ensure_ascii=False)
    cat_js    = json.dumps(CAT_COLORS,      ensure_ascii=False)
    size_js   = json.dumps(SIZE_COLORS,     ensure_ascii=False)

    legend_html = "".join(
        f'<span style="display:inline-flex;align-items:center;margin:2px 8px 2px 0;font-size:11px">'
        f'<span style="width:10px;height:10px;border-radius:50%;background:{c};'
        f'display:inline-block;margin-right:4px;flex-shrink:0"></span>{n}</span>'
        for n, c in CAT_COLORS.items()
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
  .cp{{
    width:34px;height:34px;border-radius:50%;
    background:linear-gradient(135deg,#FF8FAB,#C084D4);
    color:white;font-weight:800;font-size:15px;
    display:flex;align-items:center;justify-content:center;
    border:3px solid white;box-shadow:0 3px 10px rgba(0,0,0,0.35);
    cursor:pointer;user-select:none
  }}
  .mw{{position:relative;width:100%;height:520px}}
</style>
</head><body>
<div class="mw">
  <div id="map"></div>
  <div class="legend">{legend_html}</div>
</div>
<script src="//dapi.kakao.com/v2/maps/sdk.js?appkey={key}&libraries=clusterer"></script>
<script>
var map=new kakao.maps.Map(document.getElementById('map'),{{center:new kakao.maps.LatLng(35.9,127.8),level:13}});
var iw=new kakao.maps.InfoWindow({{zIndex:1}});
var C={cat_js};
var S={size_js};
var places={places_js};
var markers=[];
places.forEach(function(p){{
  if(!p.mapy||!p.mapx)return;
  var m=new kakao.maps.Marker({{position:new kakao.maps.LatLng(p.mapy,p.mapx),title:p.title}});
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
    +'<div class="iw-row"><a href="https://map.kakao.com/link/map/"+encodeURIComponent(p.title)+","+p.mapy+","+p.mapx+'" target="_blank">🗺️ 카카오맵에서 보기</a></div>'
    +'</div>';
  kakao.maps.event.addListener(m,'click',(function(mk,c){{return function(){{iw.setContent(c);iw.open(map,mk);}};}})(m,html));
  markers.push(m);
}});
new kakao.maps.MarkerClusterer({{
  map:map,markers:markers,averageCenter:true,minLevel:5,
  styles:[
    {{width:'38px',height:'38px',background:'rgba(255,143,171,0.9)',borderRadius:'19px',color:'#fff',textAlign:'center',fontWeight:'700',lineHeight:'38px',fontSize:'13px',border:'2px solid #FF8FAB'}},
    {{width:'46px',height:'46px',background:'rgba(192,132,212,0.9)',borderRadius:'23px',color:'#fff',textAlign:'center',fontWeight:'700',lineHeight:'46px',fontSize:'14px',border:'2px solid #C084D4'}},
    {{width:'54px',height:'54px',background:'rgba(123,79,138,0.9)',borderRadius:'27px',color:'#fff',textAlign:'center',fontWeight:'700',lineHeight:'54px',fontSize:'15px',border:'2px solid #7B4F8A'}}
  ]
}});
var cp={course_js};
var nums=['①','②','③','④'];
if(cp.length>0){{
  cp.forEach(function(p,i){{
    if(!p.mapy||!p.mapx)return;
    var el=document.createElement('div');
    el.className='cp';el.innerText=nums[i]||(i+1);
    new kakao.maps.CustomOverlay({{position:new kakao.maps.LatLng(p.mapy,p.mapx),content:el,yAnchor:1.15,zIndex:10}}).setMap(map);
  }});
  map.setCenter(new kakao.maps.LatLng(cp[0].mapy,cp[0].mapx));
  map.setLevel(10);
}}
</script></body></html>"""

# ── 규칙 기반 코스 추천 ────────────────────────────────────────────
def recommend_course(df: pd.DataFrame) -> list[dict]:
    if len(df) == 0:
        return []
    valid    = df[df["province"] != "정보없음"]
    top_prov = valid["province"].value_counts().index[0] if len(valid) > 0 \
               else df["province"].value_counts().index[0]
    result   = []
    for cat in COURSE_ORDER:
        cat_df = df[df["content_type_name"] == cat]
        if cat_df.empty:
            continue
        same_prov = cat_df[cat_df["province"] == top_prov]
        pool  = same_prov if len(same_prov) > 0 else cat_df
        place = pool.sample(1).iloc[0]
        result.append({
            "cat":   cat,
            "title": place["title"],
            "addr":  place["addr1"],
            "prov":  place["province"],
            "size":  place["dog_size_category"],
            "info":  place["acmpyTypeCd"],
            "mapx":  float(place["mapx"]) if pd.notna(place["mapx"]) else None,
            "mapy":  float(place["mapy"]) if pd.notna(place["mapy"]) else None,
        })
        if len(result) >= 4:
            break
    return result

# ── AI 코스 추천 ───────────────────────────────────────────────────
def ai_recommend_course(dog_name: str, dog_size: str, places: list[dict]) -> str:
    sample = places[:20]
    places_text = "\n".join(
        f"- {p['title']} | 유형: {p['content_type_name']} | 자치구: {p['gu_name']}"
        f" | 주소: {p.get('addr1') or '정보없음'}"
        f" | 동반형태: {p.get('acmpyTypeCd') or '정보없음'}"
        f" | 입장가능견종: {p['dog_size_category']}"
        for p in sample
    )
    prompt = (
        f"아래 장소 목록은 한국관광공사 TourAPI와 공식 문화시설 데이터에서 검증된 반려동물 동반 가능 장소입니다.\n"
        f"코스 추천 시 반드시 이 목록에 있는 장소를 우선 활용해주세요.\n\n"
        f"강아지 정보: {dog_name} ({dog_size})\n\n"
        f"[검증된 반려동물 동반 가능 장소 목록]\n{places_text}\n\n"
        f"위 목록을 참고해 오전·점심·오후 3~4곳의 하루 코스를 짜주세요.\n"
        f"각 장소마다 ① 장소명 ② 주소 ③ 동반 조건 ④ 선정 이유(1줄)를 포함하고,\n"
        f"이동 순서와 동선이 자연스럽도록 구성해 한국어로 답변해주세요."
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
    if "choices" in result:
        content = result["choices"][0]["message"]["content"]
        if isinstance(content, list):
            return content[0].get("text", str(content))
        return str(content)
    return str(result)

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

    if st.button("🔄 필터 초기화", use_container_width=True, type="secondary"):
        for _k in ("sel_cats", "sel_provs", "sel_gus"):
            st.session_state.pop(_k, None)
        st.session_state.course_cards      = []
        st.session_state.course_ai_text    = ""
        st.session_state.course_map_places = []
        st.session_state.course_name       = ""
        st.rerun()

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
            st.caption("날씨 정보를 불러올 수 없습니다.")
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

# ── 코스 추천 처리 ─────────────────────────────────────────────────
if do_course:
    if len(df) == 0:
        st.sidebar.warning("조건에 맞는 장소가 없습니다.")
    elif use_ai:
        with st.spinner(f"🤖 AI가 {display_name}를 위한 코스를 추천 중..."):
            ai_cols = [c for c in ["title","content_type_name","province","gu_name",
                                   "addr1","acmpyTypeCd","dog_size_category"] if c in df.columns]
            try:
                ai_text = ai_recommend_course(display_name, dog_size, df[ai_cols].to_dict("records"))
            except Exception as e:
                ai_text = f"AI 추천 중 오류가 발생했습니다: {e}"
        st.session_state.course_ai_text    = ai_text
        st.session_state.course_cards      = []
        st.session_state.course_map_places = []
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
if not KAKAO_JS_KEY:
    st.warning("⚠️ .env 파일에 KAKAO_JS_KEY를 추가해주세요.")
else:
    map_cols   = [c for c in ["title","addr1","mapx","mapy","content_type_name",
                               "gu_name","dog_size_category","acmpyTypeCd",
                               "tel","opertime","homepage"] if c in df.columns]
    places_df  = df[map_cols].copy()
    places_df["tel"] = places_df["tel"].replace("nan", "정보없음").fillna("정보없음")
    components.html(
        build_map_html(places_df.to_dict("records"), KAKAO_JS_KEY,
                       st.session_state.course_map_places),
        height=550,
    )

# ── 코스 추천 결과 ─────────────────────────────────────────────────
if st.session_state.course_cards:
    st.markdown(f"""
    <div style="margin:20px 0 10px 0">
      <span style="font-size:1.1rem;font-weight:800;color:#8B5CF6">
        🗺️ {st.session_state.course_name}를 위한 추천 코스
      </span>
      <span style="font-size:0.8rem;color:#AAA;margin-left:10px">
        지도의 ①②③④ 마커를 확인하세요
      </span>
    </div>""", unsafe_allow_html=True)

    cols = st.columns(len(st.session_state.course_cards))
    for i, (p, col) in enumerate(zip(st.session_state.course_cards, cols)):
        cs = CARD_STYLES[i % len(CARD_STYLES)]
        addr_short = p["addr"][:35] + ("…" if len(p["addr"]) > 35 else "")
        info_line  = (f'<div style="font-size:0.72rem;color:#999;margin-top:6px;line-height:1.4">'
                      f'{p["info"][:45]}</div>') if p["info"] != "정보없음" else ""
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
              {info_line}
            </div>""", unsafe_allow_html=True)

elif st.session_state.course_ai_text:
    st.markdown(f"""
    <div style="margin:20px 0 10px 0;font-size:1.1rem;font-weight:800;color:#8B5CF6">
      🤖 AI 추천 코스 — {st.session_state.course_name}
    </div>""", unsafe_allow_html=True)
    st.markdown(
        f'<div style="background:white;border:2px solid #E8D5F5;border-radius:18px;'
        f'padding:20px;line-height:1.8;color:#444">'
        f'{st.session_state.course_ai_text}</div>',
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
