from fpdf import FPDF

class TakeawaysPDF(FPDF):
    def header_block(self, text, y, w=170, h=10, color=(41, 128, 185), text_color=(255, 255, 255)):
        self.set_xy((210 - w) / 2, y)
        self.set_fill_color(*color)
        self.set_text_color(*text_color)
        self.set_font("Helvetica", "B", 12)
        self.cell(w, h, text, fill=True, align="C")
        self.ln()
        return y + h + 2

    def body_text(self, text, y, x=20, size=10, bold=False):
        self.set_xy(x, y)
        self.set_text_color(33, 37, 41)
        style = "B" if bold else ""
        self.set_font("Helvetica", style, size)
        self.multi_cell(170, 5.5, text)
        return self.get_y()

    def add_icon_box(self, x, y, icon, title, desc):
        self.set_fill_color(248, 249, 250)
        self.set_draw_color(41, 128, 185)
        self.rect(x, y, 52, 30, style="DF")
        self.set_xy(x, y + 2)
        self.set_text_color(41, 128, 185)
        self.set_font("Helvetica", "B", 22)
        self.cell(52, 12, icon, align="C")
        self.ln()
        self.set_xy(x, y + 14)
        self.set_font("Helvetica", "B", 9)
        self.cell(52, 5, title, align="C")
        self.ln()
        self.set_xy(x, y + 20)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(108, 117, 125)
        self.cell(52, 5, desc, align="C")

    def draw_browser_frame(self, x, y, w, h, title_text="Browser"):
        # Outer frame
        self.set_draw_color(180, 180, 180)
        self.set_line_width(0.5)
        self.rect(x, y, w, h, style="D")
        # Title bar
        self.set_fill_color(230, 230, 230)
        self.rect(x + 1, y + 1, w - 2, 9, style="F")
        self.set_xy(x + 6, y + 2)
        self.set_text_color(100, 100, 100)
        self.set_font("Helvetica", "", 7)
        self.cell(20, 5, title_text)

    def draw_panel_label(self, x, y, w, text, color=(41, 128, 185)):
        self.set_fill_color(*color)
        self.rect(x, y, w, 7, style="F")
        self.set_xy(x, y + 1)
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 7)
        self.cell(w, 5, text, align="C")

    def draw_chat_bubble(self, x, y, w, text, is_user=True, size=7):
        if is_user:
            bg = (225, 245, 255)
            label = "You"
            label_color = (41, 128, 185)
        else:
            bg = (240, 240, 240)
            label = "AI"
            label_color = (100, 100, 100)
        # Calculate height
        self.set_font("Helvetica", "", size)
        lines = self.multi_cell(w - 8, 4, text, split_only=True)
        h = max(12, len(lines) * 4 + 10)
        self.set_fill_color(*bg)
        self.set_draw_color(200, 200, 200)
        self.rect(x, y, w, h, style="DF")
        self.set_xy(x + 2, y + 1)
        self.set_text_color(*label_color)
        self.set_font("Helvetica", "B", 6)
        self.cell(8, 3, label)
        self.set_xy(x + 3, y + 5)
        self.set_text_color(33, 37, 41)
        self.set_font("Helvetica", "", size)
        self.multi_cell(w - 6, 4, text)
        return h


pdf = TakeawaysPDF()
pdf.set_auto_page_break(auto=False)

# ═══════════════════════════════════════════
# PAGE 1: Overview + AI
# ═══════════════════════════════════════════
pdf.add_page()

# -- Title --
pdf.set_text_color(41, 128, 185)
pdf.set_font("Helvetica", "B", 26)
pdf.set_xy(0, 12)
pdf.cell(210, 10, "Expense Tracker", align="C")
pdf.ln()
pdf.set_font("Helvetica", "", 13)
pdf.set_text_color(108, 117, 125)
pdf.cell(210, 7, "AI-Built Personal Finance Tracker  |  AI Champion Showcase  |  May 2026", align="C")

pdf.set_draw_color(41, 128, 185)
pdf.set_line_width(0.5)
pdf.line(20, 34, 190, 34)

# -- Why I Built This --
y = pdf.header_block("Why I Built This", 40)
y = pdf.body_text(
    "I wanted to visualize where my money goes each month. A Google Sheet works for "
    "data entry but can't spot trends, compare months, or track budgets. The bigger "
    "insight: if I struggle with this as a data person, how do small business owners "
    "(restaurants, retail shops) manage? They don't have data teams.", y, size=9
)

# -- Stack --
y = pdf.header_block("The Stack (Built Entirely with Claude AI)", y + 3)
pdf.add_icon_box(22, y + 2, "[DB]", "Supabase", "PostgreSQL Cloud DB")
pdf.add_icon_box(79, y + 2, "[API]", "FastAPI", "Python REST API")
pdf.add_icon_box(136, y + 2, "[T]", "dbt", "Data Transforms")
y += 35

# -- AI Involvement --
y = pdf.header_block("Where AI Fits In", y + 3)

pdf.set_fill_color(248, 249, 250)
pdf.set_draw_color(200, 200, 200)
pdf.rect(20, y + 2, 83, 38, style="DF")
pdf.set_xy(23, y + 4)
pdf.set_text_color(41, 128, 185)
pdf.set_font("Helvetica", "B", 10)
pdf.cell(77, 6, "AI in HOW it was built", align="C")
pdf.set_text_color(33, 37, 41)
pdf.set_font("Helvetica", "", 8)
items = [
    "Schema + 4 tables designed by AI",
    "14 API endpoints auto-generated",
    "5 dbt models with AEST timezone",
    "6+ errors debugged live by AI",
    "Zero manual coding required",
]
yy2 = y + 12
for item in items:
    pdf.set_xy(25, yy2)
    pdf.cell(75, 5, f"  -  {item}")
    yy2 += 4.8

pdf.set_fill_color(41, 128, 185)
pdf.set_text_color(255, 255, 255)
pdf.rect(106, y + 2, 83, 38, style="DF")
pdf.set_xy(109, y + 4)
pdf.set_font("Helvetica", "B", 10)
pdf.cell(77, 6, "AI in the PRODUCT (Vision)", align="C")
pdf.set_font("Helvetica", "", 8)
items2 = [
    "Phase 2: AI CSV cleaner",
    "  -  Auto-map columns to schema",
    "  -  Detect categories from desc",
    "Phase 3: AI dashboard builder",
    "  -  Customer uploads Excel -> BI",
    "  -  No data engineer needed",
]
yy2 = y + 12
for item in items2:
    pdf.set_xy(108, yy2)
    if item.startswith("Phase"):
        pdf.set_font("Helvetica", "B", 8)
    else:
        pdf.set_font("Helvetica", "", 8)
    pdf.cell(79, 5, f"  {item}")
    yy2 += 4.8

y += 44

# -- My Background --
y = pdf.header_block("My Data Engineering & AI Journey", y + 3)
pdf.set_text_color(33, 37, 41)
pdf.set_draw_color(200, 200, 200)

# Box 1: Microsoft Fabric
pdf.set_fill_color(248, 249, 250)
pdf.rect(20, y + 2, 83, 36, style="DF")
pdf.set_xy(22, y + 4)
pdf.set_text_color(41, 128, 185)
pdf.set_font("Helvetica", "B", 9)
pdf.cell(79, 5, "[MS] Microsoft Fabric / Synapse", align="C")
pdf.set_text_color(33, 37, 41)
pdf.set_font("Helvetica", "", 8)
bg1 = [
    "TEEG CID project: production data",
    "60+ Synapse notebooks",
    "Bronze -> Silver Lakehouses",
    "CI/CD pipelines (Azure DevOps)",
    "Power BI semantic models",
    "AEST timezone conversions",
]
yy2 = y + 11
for b in bg1:
    pdf.set_xy(23, yy2)
    pdf.cell(77, 4.5, f"  -  {b}")
    yy2 += 4.5

# Box 2: Databricks
pdf.set_fill_color(248, 249, 250)
pdf.rect(106, y + 2, 83, 36, style="DF")
pdf.set_xy(108, y + 4)
pdf.set_text_color(41, 128, 185)
pdf.set_font("Helvetica", "B", 9)
pdf.cell(79, 5, "[AI] Databricks AI Agents", align="C")
pdf.set_text_color(33, 37, 41)
pdf.set_font("Helvetica", "", 8)
bg2 = [
    "Databricks AI Days conference",
    "Built RAG agents (tool-calling)",
    "MLflow ResponsesAgent + UC funcs",
    "Vector search for documents",
    "Agent evaluation + deployment",
    "Agent Bricks (no-code UI)",
]
yy2 = y + 11
for b in bg2:
    pdf.set_xy(108, yy2)
    pdf.cell(77, 4.5, f"  -  {b}")
    yy2 += 4.5

y += 42

# -- Key Takeaways --
y = pdf.header_block("Key Takeaways", y + 2)
y = pdf.body_text(
    "1. AI democratizes data engineering -- non-developers can build production-grade data stacks.", y, size=9, bold=True)
y = pdf.body_text(
    "2. Real tools, real stack -- Supabase, dbt, FastAPI, Power BI. Same tools enterprises use.", y, size=9)
y = pdf.body_text(
    "3. Start with personal pain, scale to product -- best SaaS ideas come from solving your own problem.", y, size=9)
y = pdf.body_text(
    "4. AI is the co-builder -- Claude designed, coded, debugged, and explained every layer.", y, size=9)

# Footnote
pdf.set_text_color(108, 117, 125)
pdf.set_font("Helvetica", "I", 8)
pdf.set_xy(0, 286)
pdf.cell(210, 5, "github.com/xinxu-work/DS  |  Built with Claude AI  |  Supabase + FastAPI + dbt + Power BI", align="C")

# ═══════════════════════════════════════════
# PAGE 2: Web UI + Architecture
# ═══════════════════════════════════════════
pdf.add_page()

pdf.set_text_color(41, 128, 185)
pdf.set_font("Helvetica", "B", 22)
pdf.set_xy(0, 10)
pdf.cell(210, 8, "The Product Vision", align="C")
pdf.set_font("Helvetica", "", 11)
pdf.set_text_color(108, 117, 125)
pdf.set_xy(0, 20)
pdf.cell(210, 5, "What the customer sees -- and what powers it behind the scenes", align="C")

pdf.set_draw_color(41, 128, 185)
pdf.set_line_width(0.5)
pdf.line(20, 30, 190, 30)

# ── WEB UI MOCKUP ──
y_start = 36
pdf.draw_browser_frame(12, y_start, 186, 112, "finflow.ai -- Your Personal Finance Dashboard")

# URL bar
pdf.set_fill_color(248, 249, 250)
pdf.rect(13, y_start + 11, 184, 7, style="F")
pdf.set_xy(18, y_start + 12)
pdf.set_text_color(41, 128, 185)
pdf.set_font("Helvetica", "", 7)
pdf.cell(30, 4, "finflow.ai/dashboard")

# Main area
main_top = y_start + 19

# === LEFT PANEL: Upload + Dashboard ===
left_w = 110
pdf.set_draw_color(200, 200, 200)
pdf.set_line_width(0.3)
pdf.rect(14, main_top, left_w, 92, style="D")

# Upload area
upload_top = main_top + 2
pdf.set_fill_color(225, 245, 255)
pdf.set_draw_color(41, 128, 185)
pdf.set_line_width(0.6)
pdf.set_dash_pattern(2, 1)
pdf.rect(17, upload_top, left_w - 5, 25, style="D")
pdf.set_dash_pattern(0, 0)  # reset to solid
pdf.set_line_width(0.3)
pdf.set_xy(20, upload_top + 4)
pdf.set_text_color(41, 128, 185)
pdf.set_font("Helvetica", "B", 10)
pdf.cell(left_w - 8, 5, "Drop CSV/Excel file here or click to upload", align="C")
pdf.set_xy(20, upload_top + 11)
pdf.set_text_color(108, 117, 125)
pdf.set_font("Helvetica", "", 8)
pdf.cell(left_w - 8, 5, "AI auto-detects columns, maps categories, flags anomalies", align="C")

# AI processing indicator
pdf.set_xy(60, upload_top + 19)
pdf.set_fill_color(41, 128, 185)
pdf.set_text_color(255, 255, 255)
pdf.set_font("Helvetica", "B", 7)
pdf.cell(30, 4, "AI PROCESSING...", fill=True, align="C")

# Dashboard preview area
dash_top = upload_top + 28
pdf.set_fill_color(255, 255, 255)
pdf.set_draw_color(220, 220, 220)
pdf.rect(17, dash_top, left_w - 5, 57, style="DF")

# Fake mini charts in dashboard
pdf.set_xy(20, dash_top + 3)
pdf.set_text_color(33, 37, 41)
pdf.set_font("Helvetica", "B", 9)
pdf.cell(40, 5, "Monthly Spending")

# Mini bar chart (text-based bars)
bar_y = dash_top + 10
months = [("Jan", 25), ("Feb", 32), ("Mar", 28), ("Apr", 35), ("May", 22)]
bx = 22
for m, h in months:
    pdf.set_fill_color(41, 128, 185)
    pdf.rect(bx, bar_y + 25 - h, 10, h, style="F")
    pdf.set_xy(bx, bar_y + 26)
    pdf.set_font("Helvetica", "", 6)
    pdf.set_text_color(108, 117, 125)
    pdf.cell(10, 3, m, align="C")
    bx += 16

# Budget gauge
pdf.set_xy(100, dash_top + 3)
pdf.set_text_color(33, 37, 41)
pdf.set_font("Helvetica", "B", 8)
pdf.cell(30, 4, "Budget")

pdf.set_fill_color(230, 230, 230)
pdf.rect(100, dash_top + 8, 18, 14, style="F")
pdf.set_fill_color(41, 128, 185)
pdf.rect(100, dash_top + 18, 18, 4, style="F")  # 78% fill
pdf.set_xy(100, dash_top + 9)
pdf.set_text_color(41, 128, 185)
pdf.set_font("Helvetica", "B", 10)
pdf.cell(18, 5, "78%", align="C")
pdf.set_xy(100, dash_top + 15)
pdf.set_text_color(108, 117, 125)
pdf.set_font("Helvetica", "", 6)
pdf.cell(18, 3, "used", align="C")

# Mini line chart (dots connected)
pdf.set_xy(20, dash_top + 32)
pdf.set_font("Helvetica", "B", 8)
pdf.set_text_color(33, 37, 41)
pdf.cell(40, 4, "Savings Rate Trend")

lx = 22
dots_y = [dash_top + 49, dash_top + 46, dash_top + 48, dash_top + 43, dash_top + 41]
pdf.set_draw_color(41, 128, 185)
pdf.set_line_width(1.2)
for i in range(len(dots_y) - 1):
    pdf.line(lx + i * 14, dots_y[i], lx + (i+1) * 14, dots_y[i+1])
# Dots as tiny filled rectangles
for i, dy in enumerate(dots_y):
    pdf.set_fill_color(41, 128, 185)
    pdf.rect(lx + i * 14 - 1.5, dy - 1.5, 3, 3, style="F")
pdf.set_draw_color(200, 200, 200)
pdf.set_line_width(0.3)

# === RIGHT PANEL: Chat ===
chat_x = 127
pdf.set_draw_color(200, 200, 200)
pdf.rect(chat_x, main_top, 70, 92, style="D")

pdf.draw_panel_label(chat_x, main_top, 70, "Chat with your data (powered by Claude)")

chat_start = main_top + 8

# Chat bubbles
cy = chat_start + 2
cy += pdf.draw_chat_bubble(chat_x + 2, cy, 66, "How much did I spend on dining in March?", True) + 2
cy += pdf.draw_chat_bubble(chat_x + 2, cy, 66, "You spent $780 on Dining Out in March -- $280 over your $500 budget (156%). Want to see the breakdown?", False) + 2
cy += pdf.draw_chat_bubble(chat_x + 2, cy, 66, "Show me trend vs last month", True) + 2
cy += pdf.draw_chat_bubble(chat_x + 2, cy, 66, "Dining out: Feb $650 -> Mar $780 (+20%). It's been rising for 3 months. Consider tightening the budget or checking for one-off events.", False, 6.5) + 2

# Input box
input_y = chat_start + 83
pdf.set_fill_color(255, 255, 255)
pdf.set_draw_color(200, 200, 200)
pdf.rect(chat_x + 2, input_y, 62, 7, style="DF")
pdf.set_xy(chat_x + 5, input_y + 1)
pdf.set_text_color(180, 180, 180)
pdf.set_font("Helvetica", "", 7)
pdf.cell(40, 4, "Type a question...")

# Send button
pdf.set_fill_color(41, 128, 185)
pdf.rect(chat_x + 58, input_y + 1, 8, 5, style="F")
pdf.set_xy(chat_x + 59, input_y + 1.5)
pdf.set_text_color(255, 255, 255)
pdf.set_font("Helvetica", "B", 6)
pdf.cell(6, 3, ">", align="C")

# ── BELOW MOCKUP: How it works ──
y = 155

# Three-mode diagram
y = pdf.header_block("Three Modes of AI Interaction", y + 2)

pdf.set_fill_color(248, 249, 250)
pdf.set_draw_color(200, 200, 200)

# Mode 1
pdf.rect(12, y + 2, 60, 42, style="DF")
pdf.set_xy(14, y + 4)
pdf.set_text_color(41, 128, 185)
pdf.set_font("Helvetica", "B", 9)
pdf.cell(56, 5, "[1] BUILD (now)", align="C")
pdf.set_text_color(33, 37, 41)
pdf.set_font("Helvetica", "", 8)
pd = (y + 11)
for t in ["Claude Code in VS Code", "Designs schema + API", "Writes dbt models", "Debugs errors live", "You: 'Add a table...'"]:
    pdf.set_xy(15, pd)
    pdf.cell(54, 4.5, f"-  {t}")
    pd += 4.5

# Mode 2
pdf.set_fill_color(225, 245, 255)
pdf.rect(75, y + 2, 60, 42, style="DF")
pdf.set_xy(77, y + 4)
pdf.set_text_color(41, 128, 185)
pdf.set_font("Helvetica", "B", 9)
pdf.cell(56, 5, "[2] OPERATE (future)", align="C")
pdf.set_font("Helvetica", "", 8)
pd = y + 11
for t in ["Web chat (customer)", "Claude API + tool calls", "Queries Supabase", "Answers in natural lang", "'How's my budget?'"]:
    pdf.set_xy(78, pd)
    pdf.cell(54, 4.5, f"-  {t}")
    pd += 4.5

# Mode 3
pdf.rect(138, y + 2, 60, 42, style="DF")
pdf.set_xy(140, y + 4)
pdf.set_text_color(41, 128, 185)
pdf.set_font("Helvetica", "B", 9)
pdf.cell(56, 5, "[3] VISUALIZE (future)", align="C")
pdf.set_font("Helvetica", "", 8)
pd = y + 11
for t in ["Power BI embedded", "Real-time dashboards", "Auto-refresh on upload", "Customer sees insights", "No data skills needed"]:
    pdf.set_xy(141, pd)
    pdf.cell(54, 4.5, f"-  {t}")
    pd += 4.5

y += 48

# -- Architecture --
y = pdf.header_block("Architecture: What Powers the Chat", y + 2)

# Draw simplified architecture boxes
boxes = [
    (12, "Web Browser", "Upload + Chat + Dashboard"),
    (62, "FastAPI", "/chat endpoint"),
    (112, "Claude API", "Tool calling"),
    (162, "Supabase", "PostgreSQL"),
]
bx_y = y + 4
for bx_x, title, desc in boxes:
    pdf.set_fill_color(248, 249, 250)
    pdf.set_draw_color(41, 128, 185)
    pdf.rect(bx_x, bx_y, 38, 18, style="DF")
    pdf.set_xy(bx_x, bx_y + 2)
    pdf.set_text_color(41, 128, 185)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(38, 5, title, align="C")
    pdf.set_xy(bx_x, bx_y + 10)
    pdf.set_text_color(108, 117, 125)
    pdf.set_font("Helvetica", "", 7)
    pdf.cell(38, 4, desc, align="C")

# Arrows between boxes
for ax in [52, 102, 152]:
    pdf.set_text_color(41, 128, 185)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_xy(ax, bx_y + 5)
    pdf.cell(10, 6, ">", align="C")

y = bx_y + 24

# Agent tools
y = pdf.header_block("agent_tools.py -- The Bridge Between Chat and Data", y + 2)
pdf.set_text_color(33, 37, 41)
pdf.set_font("Courier", "", 8)
tools_code = [
    "def get_monthly_summary(year, month):",
    '    """Return spending by category for a given month."""',
    "    # Queries Supabase v_monthly_summary",
    "",
    "def compare_months(month1, month2):",
    '    """Compare spending between two months side by side."""',
    "",
    "def get_budget_status(year, month):",
    '    """Check which categories are over/under budget."""',
    "",
    "def search_transactions(keyword):",
    '    """Search transactions by description keyword."""',
]
cy = y
for line in tools_code:
    pdf.set_xy(25, cy)
    if line.startswith("def "):
        pdf.set_text_color(41, 128, 185)
        pdf.set_font("Courier", "B", 8)
    elif line.startswith('    """'):
        pdf.set_text_color(108, 117, 125)
        pdf.set_font("Courier", "", 7)
    else:
        pdf.set_text_color(33, 37, 41)
        pdf.set_font("Courier", "", 8)
    pdf.cell(160, 3.8, line)
    cy += 3.8

# Same as Databricks callout
pdf.set_xy(20, cy + 4)
pdf.set_fill_color(225, 245, 255)
pdf.set_text_color(41, 128, 185)
pdf.set_font("Helvetica", "B", 8)
pdf.cell(170, 7, "Same pattern as your Databricks agent!  Unity Catalog functions -> Python functions.  Databricks serving endpoint -> FastAPI /chat.", fill=True, align="C")

# -- Footnote --
pdf.set_text_color(108, 117, 125)
pdf.set_font("Helvetica", "I", 8)
pdf.set_xy(0, 288)
pdf.cell(210, 5, "github.com/xinxu-work/DS  |  Built with Claude AI  |  From personal tracker -> AI SaaS", align="C")

output_path = "c:/Users/XinXu/iCloudDrive/Xin_Xin_File/DS/Learning/AI_Practice/expense_tracker/Expense_Tracker_Key_Takeaways.pdf"
pdf.output(output_path)
print(f"PDF saved to: {output_path}")
