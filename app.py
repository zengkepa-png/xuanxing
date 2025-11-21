import streamlit as st
import pandas as pd
import io
import os

# -----------------------------------------------------------------------------
# 1. 依赖库检查 (防止因缺少 reportlab 而报错)
# -----------------------------------------------------------------------------
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False

# -----------------------------------------------------------------------------
# 2. 页面配置与 CSS 样式
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="模组选型对比专家 Pro",
    page_icon="📡",
    layout="wide"
)

st.markdown("""
    <style>
    /* 整体背景 */
    .stApp {
        background-color: #f4f6f9;
    }
    /* 标题栏 */
    .main-header {
        background: linear-gradient(135deg, #0062E6, #33AEFF);
        padding: 2rem;
        border-radius: 0 0 15px 15px;
        color: white;
        margin-bottom: 2rem;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    h1 { color: white !important; }
    
    /* 选项卡优化 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background-color: white;
        padding: 10px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .stTabs [data-baseweb="tab"] {
        height: 45px;
        background-color: #f0f2f6;
        border-radius: 5px;
        color: #333;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background-color: #0062E6;
        color: white;
    }
    /* 表格容器样式 */
    div[data-testid="stDataFrame"] {
        background: white;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    /* 按钮样式 */
    .stButton>button {
        border-radius: 5px;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 3. 功能函数定义
# -----------------------------------------------------------------------------

def create_pdf(dataframe, title="对比报告"):
    """生成 PDF 报告，包含基本的中文支持尝试"""
    if not HAS_REPORTLAB:
        return None
        
    buffer = io.BytesIO()
    # 设置页面为横向 A4
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), 
                            rightMargin=30, leftMargin=30, 
                            topMargin=30, bottomMargin=18)
    elements = []
    
    # --- 字体处理逻辑 ---
    font_name = "Helvetica" # 默认回退字体
    
    # 尝试查找系统中的常见中文字体路径
    system_fonts = [
        "SimHei.ttf", # 优先查找当前目录下是否有字体文件
        "arialuni.ttf",
        "C:/Windows/Fonts/simhei.ttf", 
        "C:/Windows/Fonts/msyh.ttf",
        "/System/Library/Fonts/PingFang.ttc",
        "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf"
    ]
    
    for f in system_fonts:
        if os.path.exists(f):
            try:
                # 注册字体
                pdfmetrics.registerFont(TTFont('CustomChinese', f))
                font_name = 'CustomChinese'
                break
            except:
                continue
                
    styles = getSampleStyleSheet()
    
    # 自定义样式
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Title'],
        fontName=font_name,
        fontSize=18,
        spaceAfter=20,
        textColor=colors.HexColor("#0062E6")
    )
    normal_style = ParagraphStyle(
        'NormalStyle',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=8,
        leading=10
    )

    # 添加标题
    elements.append(Paragraph(title, title_style))

    # 准备表格数据
    cols = dataframe.columns.tolist()
    # 表头
    data = [[Paragraph(str(c), normal_style) for c in cols]]
    
    # 表内容
    for index, row in dataframe.iterrows():
        row_data = []
        for item in row:
            text = str(item) if pd.notnull(item) else "-"
            # 简单清洗 html 敏感字符
            text = text.replace('\n', '<br/>').replace('<', '&lt;').replace('>', '&gt;')
            row_data.append(Paragraph(text, normal_style))
        data.append(row_data)

    # 动态计算列宽
    page_width = landscape(A4)[0] - 60
    col_width = page_width / len(cols) if len(cols) > 0 else 0
    
    t = Table(data, colWidths=[col_width] * len(cols))
    
    # 表格样式设计
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0062E6")), # 表头背景蓝
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),           # 表头文字白
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),              # 内容背景白
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),                # 网格线
    ]))
    
    elements.append(t)
    
    try:
        doc.build(elements)
    except Exception as e:
        print(f"PDF生成错误: {e}")
        return None
        
    buffer.seek(0)
    return buffer

@st.cache_data
def load_data():
    """智能加载目录下唯一的 CSV 文件"""
    target_file = None
    
    # 1. 优先查找名为 data.csv 的文件
    if os.path.exists("data.csv"):
        target_file = "data.csv"
    else:
        # 2. 否则查找目录下任何一个 csv 文件
        files = [f for f in os.listdir('.') if f.lower().endswith('.csv')]
        if files:
            target_file = files[0] # 取第一个找到的CSV
    
    if not target_file:
        return None

    try:
        df = pd.read_csv(target_file)
        
        # 清理列名空格
        df.columns = [c.strip() for c in df.columns]
        
        # 智能识别“型号”列
        model_col = None
        possible_names = ["参数 / 型号", "型号", "Model", "Product"]
        
        for name in possible_names:
            if name in df.columns:
                model_col = name
                break
        
        if not model_col:
            model_col = df.columns[0] # 没找到就默认第一列
            
        df.rename(columns={model_col: "Model"}, inplace=True)
        df.fillna("-", inplace=True)
        return df
    except Exception as e:
        st.error(f"读取文件 {target_file} 失败: {e}")
        return None

# -----------------------------------------------------------------------------
# 4. 主程序逻辑
# -----------------------------------------------------------------------------

# 标题区
st.markdown('<div class="main-header"><h1>📡 智能模组参数对比系统 Pro</h1><p>专业版 · 差异高亮 · 智能筛选 · 报告导出</p></div>', unsafe_allow_html=True)

# 加载数据
df = load_data()

if df is None:
    st.warning("⚠️ 未找到 CSV 数据文件。请将 CSV 文件上传或放入该目录。")
    st.stop()

# 检查 ReportLab
if not HAS_REPORTLAB:
    st.warning("⚠️ 提示: 未检测到 `reportlab` 库，PDF 导出功能不可用。建议安装: `pip install reportlab`")

# 选项卡
tab1, tab2 = st.tabs(["📊 方案一：型号 PK (差异高亮)", "⚙️ 方案二：参数筛选"])

# ========================================================
# Tab 1: 型号 PK
# ========================================================
with tab1:
    col_ctrl1, col_ctrl2 = st.columns([3, 1])
    with col_ctrl1:
        all_models = df['Model'].unique().tolist()
        # 默认选中前两个
        default_sel = all_models[:2] if len(all_models) >=2 else all_models
        
        selected_models = st.multiselect(
            "请选择参与对比的型号:",
            options=all_models,
            default=default_sel
        )
    
    with col_ctrl2:
        st.write("") 
        st.write("") 
        # 功能开关
        hide_same = st.checkbox("隐藏相同项", value=False, help="勾选后，如果某行参数所有型号都一样，则不显示。")

    if selected_models:
        # 1. 数据过滤与转置
        subset = df[df['Model'].isin(selected_models)].copy()
        # 转置: Index变成参数名，Columns变成型号名
        df_display = subset.set_index('Model').T
        
        # 2. 逻辑处理：隐藏相同项
        if hide_same:
            # 判断每行去重后的数量是否 > 1
            diff_mask = df_display.apply(lambda x: x.nunique() > 1, axis=1)
            df_display = df_display[diff_mask]
        
        st.markdown(f"### 📋 对比详情 ({len(df_display)} 项参数)")
        
        # 3. 样式处理：高亮差异 (带容错保护)
        # 定义高亮函数
        def highlight_rows(row):
            try:
                # 这一行的唯一值数量
                n_unique = len(set(row))
                if n_unique > 1:
                    # 有差异：浅黄背景，深色文字
                    return ['background-color: #fffbe6; color: #5c3a00; font-weight: bold'] * len(row)
                return [''] * len(row)
            except:
                return [''] * len(row)

        try:
            # 尝试应用 Pandas Styler
            st.dataframe(df_display.style.apply(highlight_rows, axis=1), use_container_width=True, height=600)
        except Exception:
            # 如果报错 (如 pandas 版本太低)，降级显示普通表格
            st.caption("注：当前环境不支持颜色高亮，显示标准表格。")
            st.dataframe(df_display, use_container_width=True, height=600)
            
        # 4. 导出区域
        st.divider()
        st.subheader("📥 导出数据")
        
        # 准备导出用的 DataFrame (把索引变成列)
        export_df = df_display.reset_index().rename(columns={'index': '参数项'})
        
        c1, c2 = st.columns([1, 5])
        with c1:
            # CSV 下载
            st.download_button(
                label="📄 下载 CSV",
                data=export_df.to_csv(index=False).encode('utf-8-sig'),
                file_name="comparison_result.csv",
                mime="text/csv"
            )
        with c2:
            # PDF 下载
            if HAS_REPORTLAB:
                pdf_data = create_pdf(export_df, title="模组参数对比报告")
                if pdf_data:
                    st.download_button(
                        label="📕 下载 PDF 报告",
                        data=pdf_data,
                        file_name="comparison_report.pdf",
                        mime="application/pdf"
                    )
                else:
                    st.info("PDF生成失败 (可能缺少中文字体)，请使用 CSV 下载。")

    else:
        st.info("👈 请在左侧至少选择一个型号开始对比。")

# ========================================================
# Tab 2: 参数筛选
# ========================================================
with tab2:
    st.markdown("### 🛠️ 自定义报表生成器")
    st.info("在此模式下，您可以指定只需查看的参数列，生成精简的对比表。")
    
    # 排除 'Model' 列的其他所有列
    param_options = [c for c in df.columns if c != 'Model']
    
    # 默认选前 5 个，防止列表为空
    default_params = param_options[:5] if len(param_options) >=5 else param_options
    
    # 步骤 1: 选参数
    selected_params = st.multiselect(
        "Step 1: 选择您关心的参数维度 (支持搜索)",
        options=param_options,
        default=default_params
    )
    
    # 步骤 2: 选型号
    selected_models_tab2 = st.multiselect(
        "Step 2: 选择包含的型号",
        options=df['Model'].unique(),
        default=df['Model'].unique()[:3] if len(df['Model'].unique()) >=3 else df['Model'].unique()
    )
    
    if selected_params and selected_models_tab2:
        # 筛选数据
        filtered = df[df['Model'].isin(selected_models_tab2)]
        # 只取 [Model, 参数1, 参数2...]
        final_view = filtered[['Model'] + selected_params]
        
        st.divider()
        st.markdown("### 🎯 筛选结果")
        st.dataframe(final_view, use_container_width=True)
        
        # 导出
        st.markdown("#### 导出当前视图")
        ce1, ce2 = st.columns([1, 5])
        with ce1:
             st.download_button(
                label="📄 下载 CSV",
                data=final_view.to_csv(index=False).encode('utf-8-sig'),
                file_name="custom_selection.csv",
                mime="text/csv",
                key="csv_tab2"
            )
        with ce2:
            if HAS_REPORTLAB:
                pdf_data_2 = create_pdf(final_view, title="自定义参数选型表")
                if pdf_data_2:
                    st.download_button(
                        label="📕 下载 PDF",
                        data=pdf_data_2,
                        file_name="custom_selection.pdf",
                        mime="application/pdf",
                        key="pdf_tab2"
                    )
    else:
        st.warning("请在上方完成参数和型号的选择。")

# -----------------------------------------------------------------------------
# 页脚
# -----------------------------------------------------------------------------
st.markdown("---")
st.caption("© 2025 模组选型中心 | Powered by Streamlit & Python")