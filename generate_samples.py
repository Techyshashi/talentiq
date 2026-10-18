"""Create fictional TalentIQ demo documents."""
from pathlib import Path

from docx import Document
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen.canvas import Canvas


ROOT = Path(__file__).parent
SAMPLE_DIR = ROOT / "sample_data"
CV_DIR = SAMPLE_DIR / "cvs"

JD_TEXT = """Northwind Retail Analytics (fictional)
Data Analyst
Bengaluru, hybrid
3 to 5 years of experience

Must-have: SQL including joins and window functions, Python with pandas and NumPy,
Power BI or Tableau, advanced Excel, statistics and A/B testing, stakeholder
communication.
Nice-to-have: Azure Synapse, Azure Data Factory, ETL, and retail domain experience.
Education: Bachelor's in Engineering, Statistics, Maths, or Computer Science.
"""

CVS = {
    "CV_Priya_Nair.docx": """Priya Nair
Data Analyst | Bengaluru
Experience: 4 years in retail analytics.
Built SQL models with joins and window functions, Python pipelines using pandas and NumPy,
Power BI dashboards, advanced Excel reporting, and A/B testing for merchandising teams.
Worked with Azure Synapse and Data Factory. Presented findings to business stakeholders.
B.Tech in Computer Science. priya.nair@example.com | +91 90000 00001""",
    "CV_Ananya_Das.docx": """Ananya Das
Analytics Specialist | Bengaluru
Experience: 5 years in product and retail analytics.
Writes T-SQL queries with joins and window functions. Builds Python dataframes and NumPy
analysis, plus Microsoft's business intelligence dashboard suite. Runs experiments,
statistical analysis, advanced spreadsheet models, and stakeholder reviews.
B.Sc. Statistics. ananya.das@example.com | +91 90000 00002""",
    "CV_Meera_Joshi.docx": """Meera Joshi
Data Analyst | Pune
Experience: 4 years.
Strong SQL, Python, Tableau, Excel, statistics, and ETL with SSIS. Built dashboards for
operations and communicated recommendations to managers.
B.E. Information Technology. meera.joshi@example.com | +91 90000 00003""",
    "CV_Rohan_Verma.pdf": """Rohan Verma
Data Analyst | Hyderabad
Experience: 3.5 years in reporting and analysis.
SQL, Tableau, advanced Excel, basic Python, descriptive statistics, and stakeholder
communication. Delivered weekly business dashboards.
B.Com. rohan.verma@example.com | +91 90000 00004""",
    "CV_Sneha_Iyer.docx": """Sneha Iyer
Reporting Analyst | Chennai
Experience: 2 years.
Advanced Excel, Power BI, basic SQL, and business reporting. No production Python
experience listed.
BBA. sneha.iyer@example.com | +91 90000 00005""",
    "CV_Vikram_Singh.pdf": """Vikram Singh
Junior Intern
Internship: 6 months, assisting with data entry and weekly reports.
Skills: SQL Python pandas NumPy Power BI Tableau Excel Azure Synapse Data Factory ETL
statistics A/B testing machine learning deep learning NLP Spark AWS GCP.
No project outcomes or work examples listed.
vikram.singh@example.com | +91 90000 00006""",
    "CV_Karthik_Reddy.pdf": """Karthik Reddy
Marketing Executive | Chennai
Experience: 1 year in campaign coordination and Google Analytics.
Uses Excel for campaign tracking. No SQL, Python, BI dashboard, or statistics project
experience listed.
karthik.reddy@example.com | +91 90000 00007""",
}


def write_pdf(path: Path, text: str) -> None:
    canvas = Canvas(str(path), pagesize=LETTER)
    y = 750
    for line in text.splitlines():
        canvas.drawString(54, y, line[:110])
        y -= 16
        if y < 54:
            canvas.showPage()
            y = 750
    canvas.save()


def write_docx(path: Path, text: str) -> None:
    document = Document()
    for line in text.splitlines():
        document.add_paragraph(line)
    document.save(path)


def main() -> None:
    CV_DIR.mkdir(parents=True, exist_ok=True)
    write_pdf(SAMPLE_DIR / "JD_Data_Analyst.pdf", JD_TEXT)
    for filename, text in CVS.items():
        path = CV_DIR / filename
        if filename.endswith(".pdf"):
            write_pdf(path, text)
        else:
            write_docx(path, text)
    print(f"Created JD and {len(CVS)} fictional CVs in {SAMPLE_DIR}")


if __name__ == "__main__":
    main()
