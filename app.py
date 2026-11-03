"""หน้าแรกของ UBE SafetyTalk สำหรับการอบรมภายในเครื่อง"""

import base64
import hashlib
import json
import os
import re
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from src.approval_service import ApprovalService, ApprovalStatus
from src.approval_queue import (
    ALL_FILTER_VALUE as ALL_APPROVAL_FILTER,
    build_pending_queue,
    filter_pending_queue,
)
from src.dashboard import (
    ALL_FILTER_VALUE,
    THAI_MONTH_NAMES,
    calculate_dashboard_metrics,
    calculate_monthly_activity,
    filter_dashboard_data,
    get_department_options,
    get_month_options,
    get_year_options,
)
from src.data_access import MigrationRiskError, SafetyTalkDataAccess
from src.demo_users import (
    DEMO_USERS,
    is_localhost_url,
    render_demo_user_panel,
)
from src.excel_export import (
    EXCEL_MIME_TYPE,
    report_excel_download_filename,
    report_history_to_excel_bytes,
)
from src.history import (
    ALL_COMPANIES,
    report_download_filename,
    report_history_to_csv_bytes,
)
from src.permissions import Permission, has_permission, require_permission
from src.report_history_service import ReportHistoryService
from src.storage import CSV_COLUMNS
from src.uploads import (
    evidence_files_to_json,
    save_evidence_files,
    validate_evidence_files,
)
from src.validation import validate_report


BASE_DIR = Path(__file__).resolve().parent
DEPARTMENTS_PATH = BASE_DIR / "config" / "departments.json"
REPORTS_PATH = BASE_DIR / "data" / "reports.csv"
SAMPLE_REPORTS_PATH = BASE_DIR / "data" / "sample_safety_talk.csv"
WORKFLOW_PATH = BASE_DIR / "data" / "approval_workflow.json"
DATABASE_PATH = Path(
    os.environ.get("UBE_SAFETY_DB_PATH", BASE_DIR / "data" / "safety_talk.db")
)
SUPPORTED_EVIDENCE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf"}
MENU_ITEMS = (
    (
        "บันทึก Safety Talk",
        "nav_report",
        ":material/edit_note:",
        Permission.CREATE_REPORT,
    ),
    (
        "Dashboard",
        "nav_dashboard",
        ":material/dashboard:",
        Permission.VIEW_DASHBOARD,
    ),
    (
        "ประวัติรายงาน",
        "nav_history",
        ":material/history:",
        Permission.VIEW_DASHBOARD,
    ),
    (
        "ส่งขออนุมัติ",
        "nav_submit_approval",
        ":material/send:",
        Permission.VIEW_DASHBOARD,
    ),
    (
        "Approval Queue",
        "nav_approval_queue",
        ":material/approval:",
        Permission.APPROVE_REPORT,
    ),
    (
        "Demo Admin",
        "nav_admin",
        ":material/admin_panel_settings:",
        Permission.VIEW_ADMIN,
    ),
)
PAGE_PERMISSIONS = {item[0]: item[3] for item in MENU_ITEMS}
PAGE_PERMISSIONS["รายละเอียดรายงาน"] = Permission.VIEW_DASHBOARD
PAGE_HEROES = {
    "บันทึก Safety Talk": {
        "image": BASE_DIR / "Picture" / "safety-talk-report.png",
        "eyebrow": "SAFETY TALK · WORKSHOP DAY 1",
        "title": "บันทึก Safety Talk",
        "description": "สร้างรายงานกิจกรรมความปลอดภัย พร้อมแนบหลักฐานภายในเครื่อง",
    },
    "Dashboard": {
        "image": BASE_DIR / "Picture" / "safety-talk-dashboard.png",
        "eyebrow": "SAFETY PERFORMANCE OVERVIEW",
        "title": "Dashboard",
        "description": "ติดตามภาพรวมรายงาน ผู้เข้าร่วม และกิจกรรมของ UBE และ UBS",
    },
    "ประวัติรายงาน": {
        "image": BASE_DIR / "Picture" / "safety-talk-history.png",
        "eyebrow": "REPORT ARCHIVE",
        "title": "ประวัติรายงาน",
        "description": "ค้นหา ตรวจสอบ และส่งออกข้อมูล Safety Talk ที่บันทึกไว้",
    },
    "รายละเอียดรายงาน": {
        "image": BASE_DIR / "Picture" / "safety-talk-history.png",
        "eyebrow": "REPORT DETAIL · AUDIT TRAIL",
        "title": "รายละเอียดรายงาน",
        "description": "ตรวจสอบข้อมูล Safety Talk และประวัติการดำเนินการอนุมัติ",
    },
    "ส่งขออนุมัติ": {
        "image": BASE_DIR / "Picture" / "safety-talk-history.png",
        "eyebrow": "SUBMIT FOR APPROVAL · DEMO SESSION",
        "title": "ส่งขออนุมัติ",
        "description": "ส่งรายงาน Draft ที่เป็นเจ้าของเข้าสู่ขั้นตอนอนุมัติ",
    },
    "Approval Queue": {
        "image": BASE_DIR / "Picture" / "safety-talk-history.png",
        "eyebrow": "CORPORATE SAFETY WORKFLOW",
        "title": "Approval Queue",
        "description": "ตรวจสอบรายงาน Pending ก่อนตัดสินใจอนุมัติหรือปฏิเสธ",
    },
    "Demo Admin": {
        "image": BASE_DIR / "Picture" / "safety-talk-dashboard.png",
        "eyebrow": "DEMO ADMIN · NO AUTHENTICATION",
        "title": "Demo Admin",
        "description": "พื้นที่สาธิตสำหรับ ADMIN เท่านั้น ไม่ใช่ระบบผู้ดูแลจริง",
    },
}


def load_departments() -> dict[str, list[str]]:
    """โหลดรายชื่อหน่วยงาน UBE และ UBS จากไฟล์ตั้งค่าของโปรเจกต์"""
    with DEPARTMENTS_PATH.open(encoding="utf-8-sig") as config_file:
        departments = json.load(config_file)

    if not all(company in departments for company in ("UBE", "UBS")):
        raise ValueError("ไฟล์ departments.json ต้องมีรายชื่อหน่วยงาน UBE และ UBS")

    return departments


def sanitize_filename(filename: str) -> str:
    """คืนชื่อไฟล์ที่ปลอดภัยและยอมรับเฉพาะไฟล์หลักฐานที่รองรับ"""
    original_name = Path(filename).name
    extension = Path(original_name).suffix.lower()
    if extension not in SUPPORTED_EVIDENCE_EXTENSIONS:
        raise ValueError("รองรับเฉพาะไฟล์ JPG, JPEG, PNG และ PDF")

    safe_stem = re.sub(r"[^\w.-]+", "_", Path(original_name).stem, flags=re.UNICODE)
    safe_stem = safe_stem.strip("._") or "evidence"
    return f"{safe_stem}{extension}"


def submission_fingerprint(report: dict[str, object], evidence_files: list[object]) -> str:
    """สร้างลายเซ็นข้อมูลเพื่อกันการบันทึกรายการเดิมซ้ำระหว่าง rerun"""
    digest = hashlib.sha256(
        json.dumps(report, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    )
    for evidence_file in evidence_files:
        digest.update(str(evidence_file.name).encode("utf-8"))
        digest.update(evidence_file.getvalue())
    return digest.hexdigest()


st.set_page_config(
    page_title="UBE SafetyTalk",
    page_icon=":material/health_and_safety:",
    layout="wide",
)

st.html(
    """
    <style>
    .st-key-nav_report button,
    .st-key-nav_dashboard button,
    .st-key-nav_history button,
    .st-key-nav_submit_approval button,
    .st-key-nav_approval_queue button,
    .st-key-nav_admin button {
        min-height: 3.25rem;
        justify-content: flex-start;
        padding-inline: 1rem;
        font-weight: 600;
        letter-spacing: 0.01em;
        box-shadow: 0 8px 20px rgba(8, 39, 24, 0.12);
    }
    .safety-hero {
        min-height: 280px;
        display: flex;
        align-items: flex-end;
        padding: clamp(1.5rem, 4vw, 3.25rem);
        border: 1px solid rgba(255, 255, 255, 0.22);
        border-radius: 1.5rem;
        background-position: center;
        background-size: cover;
        box-shadow: 0 24px 55px rgba(14, 62, 39, 0.20);
        overflow: hidden;
        color: #ffffff;
    }
    .safety-hero__content {
        max-width: 720px;
        text-shadow: 0 2px 18px rgba(0, 0, 0, 0.32);
    }
    .safety-hero__eyebrow {
        margin: 0 0 0.6rem;
        color: #ffb15c;
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.14em;
    }
    .safety-hero h1 {
        margin: 0;
        color: #ffffff;
        font-size: clamp(2rem, 5vw, 3.5rem);
        line-height: 1.08;
    }
    .safety-hero__description {
        margin: 0.85rem 0 0;
        color: rgba(255, 255, 255, 0.90);
        font-size: clamp(1rem, 2vw, 1.15rem);
        line-height: 1.65;
    }
    .st-key-approval_queue_filters,
    .st-key-approval_queue_actions,
    .st-key-report_history_filters,
    .st-key-report_detail_card,
    .st-key-report_history_results {
        border-color: rgba(13, 148, 136, 0.38);
        background: linear-gradient(135deg, rgba(7, 27, 54, 0.04), rgba(13, 148, 136, 0.08));
        box-shadow: 0 12px 30px rgba(7, 27, 54, 0.08);
    }
    </style>
    """
)


@st.cache_data(show_spinner=False)
def image_data_uri(image_path: Path, modified_at_ns: int) -> str:
    """อ่านภาพในโปรเจกต์เป็น data URI และรีเฟรช cache เมื่อไฟล์เปลี่ยน"""
    del modified_at_ns
    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def select_menu(menu_label: str) -> None:
    """เปลี่ยนหน้าที่เลือกจากปุ่มเมนูด้านข้าง"""
    st.session_state["selected_menu"] = menu_label


def reset_dashboard_department() -> None:
    """ล้างหน่วยงานเดิมทันทีเมื่อผู้ใช้สลับบริษัท"""
    st.session_state["dashboard_department"] = ALL_FILTER_VALUE


def reset_dashboard_month() -> None:
    """ล้างเดือนเดิมเมื่อปีเปลี่ยน เพื่อไม่ให้ค่าเก่าค้างนอกตัวเลือก"""
    st.session_state["dashboard_month"] = ALL_FILTER_VALUE


def reset_approval_department() -> None:
    """ล้างหน่วยงานของ Approval Queue เมื่อสลับบริษัท"""
    st.session_state["approval_queue_department"] = ALL_APPROVAL_FILTER


def reset_history_department() -> None:
    """ล้างหน่วยงานของ Report History เมื่อสลับบริษัท"""
    st.session_state["history_department"] = ALL_COMPANIES


def open_report_detail(report_id: str) -> None:
    st.session_state["selected_report_id"] = report_id
    st.session_state["selected_menu"] = "รายละเอียดรายงาน"


def render_page_hero(menu_label: str) -> None:
    """แสดงภาพพื้นหลังและข้อความนำของหน้าที่เลือก"""
    hero = PAGE_HEROES[menu_label]
    image_path = hero["image"]
    image_uri = image_data_uri(image_path, image_path.stat().st_mtime_ns)
    if menu_label in {"ประวัติรายงาน", "รายละเอียดรายงาน", "Approval Queue"}:
        gradient = (
            "linear-gradient(90deg, rgba(7, 27, 54, 0.98) 0%, "
            "rgba(8, 77, 86, 0.88) 48%, rgba(13, 148, 136, 0.18) 82%)"
        )
    else:
        gradient = (
            "linear-gradient(90deg, rgba(5, 48, 34, 0.96) 0%, "
            "rgba(5, 48, 34, 0.72) 42%, rgba(5, 48, 34, 0.12) 78%)"
        )
    st.html(
        f"""
        <section
            class="safety-hero"
            style="background-image:
                {gradient},
                url('{image_uri}');"
        >
            <div class="safety-hero__content">
                <p class="safety-hero__eyebrow">{hero['eyebrow']}</p>
                <h1>{hero['title']}</h1>
                <p class="safety-hero__description">{hero['description']}</p>
            </div>
        </section>
        """
    )


st.session_state.setdefault("selected_menu", "บันทึก Safety Talk")
st.session_state.setdefault("last_saved_submission_fingerprint", None)
st.session_state.setdefault("last_saved_report_id", None)
data_access = SafetyTalkDataAccess(DATABASE_PATH)
try:
    data_access.bootstrap_from_legacy(REPORTS_PATH, WORKFLOW_PATH)
except MigrationRiskError as error:
    st.error(
        str(error),
        title="หยุดการย้ายข้อมูลเพื่อป้องกันข้อมูลเดิม",
        icon=":material/database_off:",
    )
    st.stop()
st.session_state["approval_records"] = data_access.load_approval_records()

with st.sidebar:
    st.title("UBE Safety Talk", icon=":material/health_and_safety:")
    st.caption("ระบบบันทึกกิจกรรมความปลอดภัย")
    render_demo_user_panel(is_localhost_url(st.context.url))
    current_role = DEMO_USERS[st.session_state["current_demo_user"]]
    st.space("small")
    st.markdown("**เมนูหลัก**")

    for menu_label, button_key, button_icon, required_permission in MENU_ITEMS:
        if not has_permission(current_role, required_permission):
            continue
        st.button(
            menu_label,
            key=button_key,
            icon=button_icon,
            type=(
                "primary"
                if st.session_state["selected_menu"] == menu_label
                else "secondary"
            ),
            width="stretch",
            on_click=select_menu,
            args=(menu_label,),
        )

    st.space("small")
    st.caption("UBE Safety Talk · Workshop Day 1")
    st.caption("ระบบสาธิตภายในเครื่อง · ไม่มีระบบ Login")

selected_menu = st.session_state["selected_menu"]
current_actor = st.session_state["current_demo_user"]
approval_service = ApprovalService(
    st.session_state["approval_records"],
    on_change=data_access.save_approval_records,
)
report_history_service = ReportHistoryService(
    data_access,
    viewer_user_id=current_actor,
    viewer_role=current_role,
)
required_page_permission = PAGE_PERMISSIONS.get(selected_menu)
page_authorized = required_page_permission is not None and has_permission(
    current_role,
    required_page_permission,
)
if page_authorized:
    render_page_hero(selected_menu)
    st.space("small")

if not page_authorized:
    st.subheader("ไม่สามารถเข้าถึงหน้านี้", icon=":material/block:")
    st.error(
        f"Role {current_role} ไม่มีสิทธิ์เข้าถึง {selected_menu}",
        title="ไม่มีสิทธิ์",
        icon=":material/lock:",
    )
    st.info("เลือกเมนูที่แสดงอยู่ใน Sidebar เพื่อดำเนินการต่อ")

elif selected_menu == "บันทึก Safety Talk":
    st.subheader("แบบฟอร์มบันทึกรายงาน", icon=":material/edit_note:")
    st.warning(
        "ใช้ข้อมูลและไฟล์ทดสอบเท่านั้น ห้ามอัปโหลดข้อมูลส่วนบุคคล "
        "เอกสารลับ หรือข้อมูลจริงของบริษัท",
        title="ข้อมูลทดสอบเท่านั้น",
        icon=":material/warning:",
    )

    departments = load_departments()
    with st.container(border=True):
        company = st.selectbox(
            "บริษัท",
            ("UBE", "UBS"),
            key="safety_company",
            help="เลือกบริษัทเพื่อแสดงรายชื่อหน่วยงานที่เกี่ยวข้อง",
        )

        with st.form("safety_talk_form"):
            talk_date = st.date_input(
                "วันที่สื่อสาร Safety Talk",
                value=date.today(),
                key="safety_talk_date",
            )
            department = st.selectbox(
                "หน่วยงาน",
                departments[company],
                index=None,
                key=f"safety_department_{company}",
                placeholder="เลือกหน่วยงาน",
            )
            reporter = st.text_input(
                "ชื่อผู้รายงาน",
                key="safety_reporter",
                placeholder="ระบุชื่อผู้รายงาน",
            )
            topic = st.text_area(
                "หัวข้อ Safety Talk",
                key="safety_topic",
                placeholder="ระบุหัวข้อที่สื่อสาร",
            )
            participants = st.number_input(
                "จำนวนผู้เข้าร่วม",
                min_value=0,
                value=0,
                step=1,
                key="safety_participants",
            )
            evidence_files = st.file_uploader(
                "ไฟล์หลักฐาน (ไม่บังคับ)",
                type=["jpg", "jpeg", "png", "pdf"],
                accept_multiple_files=True,
                max_upload_size=5,
                key="safety_evidence_files",
                help="รองรับ JPG, JPEG, PNG และ PDF ขนาดไม่เกิน 5 MB ต่อไฟล์",
            )
            submitted = st.form_submit_button(
                "บันทึกรายงาน",
                icon=":material/save:",
                type="primary",
            )

        st.caption("รายชื่อหน่วยงานโหลดจาก config/departments.json")

    display_report_id = st.session_state.get("last_saved_report_id")
    if submitted:
        report = {
            "talk_date": talk_date,
            "company": company,
            "department": department,
            "reporter": reporter,
            "topic": topic,
            "participants": participants,
        }
        errors = validate_report(report, departments)
        errors.extend(validate_evidence_files(evidence_files))

        if errors:
            display_report_id = None
            for error in errors:
                st.error(error, icon=":material/error:")
        else:
            try:
                require_permission(current_role, Permission.SUBMIT_REPORT)
            except PermissionError as error:
                display_report_id = None
                st.error(str(error), title="ไม่มีสิทธิ์ส่งรายงาน")
            else:
                fingerprint = submission_fingerprint(report, evidence_files)
                if fingerprint != st.session_state["last_saved_submission_fingerprint"]:
                    report_id = data_access.generate_report_id(talk_date)
                    saved_filenames = save_evidence_files(evidence_files, report_id)
                    data_access.create_report(
                        {
                            "report_id": report_id,
                            "talk_date": talk_date.isoformat(),
                            "company": company,
                            "department": department,
                            "reporter": reporter.strip(),
                            "topic": topic.strip(),
                            "participants": participants,
                            "evidence_files": evidence_files_to_json(saved_filenames),
                            "created_at": datetime.now()
                            .astimezone()
                            .isoformat(timespec="seconds"),
                        },
                        owner_id=current_actor,
                    )
                    st.session_state["last_saved_submission_fingerprint"] = fingerprint
                    st.session_state["last_saved_report_id"] = report_id
                    approval_service.register_report(
                        report_id,
                        owner=current_actor,
                    )

                display_report_id = st.session_state["last_saved_report_id"]

    if display_report_id:
        st.success(f"บันทึกรายงานเรียบร้อยแล้ว · Report ID: {display_report_id}")
        saved_approval_record = st.session_state["approval_records"].get(
            display_report_id
        )
        if saved_approval_record is None:
            saved_approval_record = approval_service.register_report(
                display_report_id,
                owner=current_actor,
            )

        if (
            saved_approval_record.status is ApprovalStatus.DRAFT
            and saved_approval_record.owner == current_actor
            and has_permission(current_role, Permission.SUBMIT_REPORT)
        ):
            if st.button(
                "ส่งขออนุมัติ",
                key="form_send_for_approval",
                icon=":material/send:",
                type="primary",
            ):
                try:
                    approval_service.submit(
                        display_report_id,
                        role=current_role,
                        actor=current_actor,
                    )
                except (PermissionError, ValueError, KeyError) as error:
                    st.error(str(error), title="ไม่สามารถส่งขออนุมัติได้")
                else:
                    st.success(
                        "ส่งขออนุมัติสำเร็จ · "
                        f"Report ID: {display_report_id} · สถานะ Pending"
                    )
        elif saved_approval_record.status is ApprovalStatus.PENDING:
            st.info(
                f"Report ID: {display_report_id} อยู่ใน Approval Queue แล้ว"
            )

elif selected_menu == "Dashboard":
    st.subheader("ภาพรวม Safety Talk", icon=":material/dashboard:")
    dashboard_data, is_demo = data_access.load_dashboard_data(SAMPLE_REPORTS_PATH)

    if is_demo:
        st.warning(
            "ยังไม่มีรายงานจริงใน data/reports.csv จึงใช้ "
            "data/sample_safety_talk.csv เพื่อแสดงตัวอย่างเท่านั้น",
            title="DEMO · ข้อมูลตัวอย่าง",
            icon=":material/science:",
        )
    else:
        st.caption("ข้อมูลจริงจาก SQLite")

    with st.container(border=True):
        st.markdown("**ตัวกรอง Dashboard**")
        company_column, department_column, year_column, month_column = st.columns(
            [1.25, 2.5, 1, 1],
            vertical_alignment="bottom",
        )

        with company_column:
            dashboard_company = st.segmented_control(
                "บริษัท",
                options=(ALL_FILTER_VALUE, "UBE", "UBS"),
                default=ALL_FILTER_VALUE,
                required=True,
                key="dashboard_company",
                on_change=reset_dashboard_department,
                width="stretch",
            )

        department_options = [
            ALL_FILTER_VALUE,
            *get_department_options(dashboard_data, dashboard_company),
        ]
        if st.session_state.get("dashboard_department") not in department_options:
            st.session_state["dashboard_department"] = ALL_FILTER_VALUE
        with department_column:
            dashboard_department = st.selectbox(
                "หน่วยงาน",
                options=department_options,
                key="dashboard_department",
            )

        year_options = [ALL_FILTER_VALUE, *get_year_options(dashboard_data)]
        if st.session_state.get("dashboard_year") not in year_options:
            st.session_state["dashboard_year"] = ALL_FILTER_VALUE
        with year_column:
            dashboard_year = st.selectbox(
                "ปี",
                options=year_options,
                key="dashboard_year",
                on_change=reset_dashboard_month,
            )

        month_options = [
            ALL_FILTER_VALUE,
            *get_month_options(dashboard_data, dashboard_year),
        ]
        if st.session_state.get("dashboard_month") not in month_options:
            st.session_state["dashboard_month"] = ALL_FILTER_VALUE
        with month_column:
            dashboard_month = st.selectbox(
                "เดือน",
                options=month_options,
                format_func=lambda value: (
                    value
                    if value == ALL_FILTER_VALUE
                    else THAI_MONTH_NAMES[int(value)]
                ),
                key="dashboard_month",
            )

    filtered_dashboard_data = filter_dashboard_data(
        dashboard_data,
        company=dashboard_company,
        department=dashboard_department,
        year=dashboard_year,
        month=dashboard_month,
    )
    dashboard_metrics = calculate_dashboard_metrics(filtered_dashboard_data)
    monthly_activity = calculate_monthly_activity(filtered_dashboard_data)
    st.caption(
        f"ข้อมูลหลังกรอง {len(filtered_dashboard_data):,} จาก {len(dashboard_data):,} รายงาน"
    )

    with st.container(horizontal=True):
        st.metric(
            "จำนวนรายงาน Safety Talk",
            f"{dashboard_metrics['report_count']:,}",
            border=True,
        )
        st.metric(
            "ผลรวมจำนวนผู้เข้าร่วม",
            f"{dashboard_metrics['participant_count']:,}",
            border=True,
        )
        st.metric(
            "จำนวนรายงาน UBE",
            f"{dashboard_metrics['ube_report_count']:,}",
            border=True,
        )
        st.metric(
            "จำนวนรายงาน UBS",
            f"{dashboard_metrics['ubs_report_count']:,}",
            border=True,
        )

    with st.container(border=True):
        st.subheader(
            "จำนวนกิจกรรม Safety Talk รายเดือน",
            icon=":material/calendar_month:",
        )
        if monthly_activity.empty:
            st.info(
                "ยังไม่มีข้อมูลวันที่ที่ถูกต้องสำหรับแสดงกิจกรรมรายเดือน",
                icon=":material/info:",
            )
        else:
            st.bar_chart(
                monthly_activity,
                x="month",
                y="activity_count",
                x_label="เดือน",
                y_label="จำนวนกิจกรรม",
                sort=False,
                alt="จำนวนกิจกรรม Safety Talk ที่บันทึกในแต่ละเดือน",
            )

elif selected_menu == "ประวัติรายงาน":
    st.subheader("รายการรายงาน", icon=":material/history:")
    visible_reports = report_history_service.search_reports()

    if not visible_reports:
        st.info(
            "ยังไม่มีรายงานที่ผู้ใช้ปัจจุบันมีสิทธิ์ดู "
            "เมื่อมีรายงานที่เป็นเจ้าของหรือได้รับสิทธิ์ รายการจะแสดงที่นี่",
            title="ไม่พบรายงานในขอบเขตสิทธิ์",
            icon=":material/folder_off:",
        )
    else:
        with st.container(border=True, key="report_history_filters"):
            st.markdown("**ค้นหาและกรองรายงาน**")
            search_column, company_column, status_column = st.columns(
                [2.2, 1.2, 1.2],
                vertical_alignment="bottom",
            )
            with search_column:
                history_search = st.text_input(
                    "ค้นหา Report ID, หัวข้อ หรือผู้รายงาน",
                    key="history_search",
                    type="search",
                    icon=":material/search:",
                    placeholder="พิมพ์ข้อความที่ต้องการค้นหา",
                )
            with company_column:
                history_company = st.segmented_control(
                    "บริษัท",
                    options=(ALL_COMPANIES, "UBE", "UBS"),
                    default=ALL_COMPANIES,
                    required=True,
                    key="history_company",
                    on_change=reset_history_department,
                    width="stretch",
                )
            with status_column:
                history_status = st.selectbox(
                    "สถานะ",
                    options=(ALL_COMPANIES, *tuple(ApprovalStatus)),
                    format_func=lambda value: (
                        value if value == ALL_COMPANIES else value.value
                    ),
                    key="history_status",
                )

            department_options = [
                ALL_COMPANIES,
                *report_history_service.list_departments(
                    company=(
                        history_company
                        if history_company in {"UBE", "UBS"}
                        else None
                    )
                ),
            ]
            if st.session_state.get("history_department") not in department_options:
                st.session_state["history_department"] = ALL_COMPANIES
            department_column, date_column = st.columns(
                [1.5, 1],
                vertical_alignment="bottom",
            )
            with department_column:
                history_department = st.selectbox(
                    "หน่วยงาน",
                    options=department_options,
                    key="history_department",
                )
            with date_column:
                history_dates = st.date_input(
                    "ช่วงวันที่ Safety Talk",
                    value=(),
                    key="history_dates",
                    help="ไม่เลือกวันที่เพื่อแสดงทุกช่วงเวลา",
                )

        date_from = None
        date_to = None
        if isinstance(history_dates, tuple):
            if len(history_dates) == 1:
                date_from = date_to = history_dates[0]
            elif len(history_dates) >= 2:
                date_from, date_to = history_dates[:2]
        elif history_dates:
            date_from = date_to = history_dates

        filtered_reports = report_history_service.search_reports(
            search_text=history_search,
            company=(history_company if history_company in {"UBE", "UBS"} else None),
            department=(
                history_department
                if history_department != ALL_COMPANIES
                else None
            ),
            date_from=date_from,
            date_to=date_to,
            approval_status=(
                history_status if history_status != ALL_COMPANIES else None
            ),
        )
        filtered_history = pd.DataFrame(filtered_reports)
        st.caption(
            f"แสดง {len(filtered_history):,} จาก {len(visible_reports):,} รายงานที่มีสิทธิ์ดู"
        )
        export_history = filtered_history.reindex(columns=CSV_COLUMNS)
        with st.container(horizontal=True):
            st.download_button(
                "ดาวน์โหลด CSV ที่กรองแล้ว",
                data=report_history_to_csv_bytes(export_history),
                file_name=report_download_filename(date.today()),
                mime="text/csv; charset=utf-8",
                key="download_filtered_history",
                on_click="ignore",
                icon=":material/download:",
                disabled=filtered_history.empty,
            )
            st.download_button(
                "ดาวน์โหลด Excel ที่กรองแล้ว",
                data=lambda: report_history_to_excel_bytes(export_history),
                file_name=report_excel_download_filename(date.today()),
                mime=EXCEL_MIME_TYPE,
                key="download_filtered_history_excel",
                on_click="ignore",
                icon=":material/table_view:",
                disabled=filtered_history.empty,
            )

        if filtered_history.empty:
            st.info(
                "ลองล้างคำค้นหา เปลี่ยนตัวกรอง หรือเลือกช่วงวันที่ใหม่",
                title="ไม่พบรายงานที่ตรงกับเงื่อนไข",
                icon=":material/search_off:",
            )
        else:
            with st.container(border=True, key="report_history_results"):
                st.dataframe(
                    filtered_history.loc[
                        :,
                        [
                            "report_id",
                            "talk_date",
                            "company",
                            "department",
                            "topic",
                            "reporter",
                            "approval_status",
                        ],
                    ],
                    hide_index=True,
                    width="stretch",
                    column_config={
                        "report_id": "Report ID",
                        "talk_date": "วันที่",
                        "company": "บริษัท",
                        "department": "หน่วยงาน",
                        "topic": "หัวข้อ",
                        "reporter": "ผู้รายงาน",
                        "approval_status": "สถานะ",
                    },
                    alt="รายงาน Safety Talk ที่ผู้ใช้มีสิทธิ์ดูและตรงกับตัวกรอง",
                )
                detail_column, button_column = st.columns(
                    [3, 1],
                    vertical_alignment="bottom",
                )
                with detail_column:
                    detail_report_id = st.selectbox(
                        "เลือกรายงานเพื่อดูรายละเอียด",
                        options=filtered_history["report_id"].tolist(),
                        key="history_detail_report_id",
                    )
                with button_column:
                    st.button(
                        "เปิดรายละเอียด",
                        key="history_open_detail",
                        icon=":material/open_in_new:",
                        type="primary",
                        width="stretch",
                        on_click=open_report_detail,
                        args=(detail_report_id,),
                    )

elif selected_menu == "รายละเอียดรายงาน":
    st.button(
        "กลับไปประวัติรายงาน",
        key="report_detail_back",
        icon=":material/arrow_back:",
        on_click=select_menu,
        args=("ประวัติรายงาน",),
    )
    selected_report_id = st.session_state.get("selected_report_id")
    if not selected_report_id:
        st.info(
            "กลับไปหน้า Report History แล้วเลือกรายงานที่ต้องการตรวจสอบ",
            title="ยังไม่ได้เลือกรายงาน",
            icon=":material/info:",
        )
    else:
        try:
            report_detail = report_history_service.get_report_detail(
                selected_report_id
            )
        except PermissionError as error:
            st.error(str(error), title="ไม่สามารถเปิดรายละเอียดได้")
        else:
            report = report_detail.report
            status_colors = {
                "Draft": "gray",
                "Pending": "orange",
                "Approved": "green",
                "Rejected": "red",
            }
            with st.container(border=True, key="report_detail_card"):
                with st.container(horizontal=True, vertical_alignment="center"):
                    st.subheader(
                        report["report_id"],
                        icon=":material/description:",
                    )
                    st.badge(
                        report["approval_status"],
                        color=status_colors[report["approval_status"]],
                    )
                st.table(
                    {
                        "วันที่ Safety Talk": report["talk_date"],
                        "บริษัท": report["company"],
                        "หน่วยงาน": report["department"],
                        "ผู้รายงาน": report["reporter"],
                        "หัวข้อ": report["topic"],
                        "จำนวนผู้เข้าร่วม": report["participants"],
                        "เจ้าของรายงาน": report["owner_id"],
                        "บันทึกเมื่อ": report["created_at"],
                    },
                    border="horizontal",
                    width="stretch",
                    alt=f"รายละเอียดรายงาน {report['report_id']}",
                )

            st.subheader("Approval History", icon=":material/history:")
            if not report_detail.approval_history:
                st.info(
                    "รายงานนี้ยังไม่มีการส่ง อนุมัติ ปฏิเสธ หรือแก้ไขสถานะ",
                    title="ยังไม่มี Approval History",
                    icon=":material/history_toggle_off:",
                )
            else:
                st.dataframe(
                    pd.DataFrame(report_detail.approval_history),
                    hide_index=True,
                    width="stretch",
                    column_config={
                        "actor": "ผู้ดำเนินการ",
                        "timestamp": "เวลา",
                        "old_status": "สถานะเดิม",
                        "new_status": "สถานะใหม่",
                        "action": "Action",
                        "comment": "ความคิดเห็น",
                    },
                    alt=f"ประวัติการอนุมัติของ {report['report_id']}",
                )

elif selected_menu == "ส่งขออนุมัติ":
    st.subheader("รายงานของฉัน", icon=":material/send:")
    st.warning(
        "เจ้าของ สถานะ และ Action History เก็บใน SQLite ภายในเครื่อง "
        "โดยยังเป็น Demo Workflow ที่ไม่มี Authentication จริง",
        title="DEMO WORKFLOW · NO AUTHENTICATION",
        icon=":material/science:",
    )
    stored_reports = data_access.list_reports()

    owned_report_ids = [
        stored_report["report_id"]
        for stored_report in stored_reports
        if approval_service.get_record(stored_report["report_id"]).owner
        == current_actor
    ]

    if not owned_report_ids:
        st.info("ยังไม่มีรายงานที่ผู้ใช้จำลองคนนี้เป็นเจ้าของ")
    else:
        selected_report_id = st.selectbox(
            "Report ID ของฉัน",
            options=owned_report_ids,
            key="demo_approval_report_id",
        )
        approval_record = approval_service.get_record(selected_report_id)
        st.markdown(
            f"**สถานะของ {approval_record.report_id}:** "
            f"`{approval_record.status.value}`"
        )
        st.caption(f"เจ้าของรายงาน: {approval_record.owner}")
        action_comment = st.text_area(
            "ความคิดเห็นประกอบการส่งหรือแก้ไข",
            key="demo_approval_comment",
        )

        try:
            if (
                approval_record.status is ApprovalStatus.DRAFT
                and has_permission(current_role, Permission.SUBMIT_REPORT)
                and st.button(
                    "ส่งขออนุมัติ",
                    key="demo_submit_action",
                    icon=":material/send:",
                    type="primary",
                )
            ):
                approval_service.submit(
                    selected_report_id,
                    role=current_role,
                    actor=current_actor,
                    comment=action_comment,
                )
                st.success(
                    f"ส่งขออนุมัติสำเร็จ · Report ID: {selected_report_id}"
                )

            elif (
                approval_record.status is ApprovalStatus.REJECTED
                and has_permission(current_role, Permission.CREATE_REPORT)
                and st.button(
                    "Revise: Rejected → Draft",
                    key="demo_revise_action",
                    icon=":material/edit:",
                    type="primary",
                )
            ):
                approval_service.revise(
                    selected_report_id,
                    role=current_role,
                    actor=current_actor,
                    comment=action_comment,
                )
                st.success(f"ส่ง {selected_report_id} กลับเป็น Draft แล้ว")
        except (PermissionError, ValueError, KeyError) as error:
            st.error(str(error), title="ไม่สามารถเปลี่ยนสถานะได้")

        if approval_record.status is ApprovalStatus.PENDING:
            st.info("รายงานนี้อยู่ใน Approval Queue และกำลังรอผู้อนุมัติดำเนินการ")
        elif approval_record.status is ApprovalStatus.APPROVED:
            st.info("รายงานนี้อนุมัติแล้ว")

        st.markdown("**Action History**")
        if approval_record.history:
            st.dataframe(
                [event.to_dict() for event in approval_record.history],
                hide_index=True,
                width="stretch",
                alt=f"Action History ของ {approval_record.report_id}",
            )
        else:
            st.caption("ยังไม่มี Action History — รายงานเริ่มต้นที่สถานะ Draft")

elif selected_menu == "Approval Queue":
    st.subheader("รายการรออนุมัติ", icon=":material/approval:")
    if flash_message := st.session_state.pop("approval_queue_flash", None):
        st.success(flash_message)

    pending_queue = build_pending_queue(
        data_access.list_reports(),
        st.session_state["approval_records"],
    )

    with st.container(border=True, key="approval_queue_filters"):
        st.markdown("**ค้นหาและกรองรายงาน Pending**")
        search_column, company_column, department_column = st.columns(
            [2.2, 1, 2],
            vertical_alignment="bottom",
        )
        with search_column:
            approval_search = st.text_input(
                "ค้นหา Report ID, หัวข้อ หรือผู้ส่ง",
                key="approval_queue_search",
                icon=":material/search:",
            )
        with company_column:
            approval_company = st.segmented_control(
                "บริษัท",
                options=(ALL_APPROVAL_FILTER, "UBE", "UBS"),
                default=ALL_APPROVAL_FILTER,
                required=True,
                key="approval_queue_company",
                on_change=reset_approval_department,
                width="stretch",
            )

        department_source = pending_queue
        if approval_company in {"UBE", "UBS"}:
            department_source = department_source.loc[
                department_source["company"].astype("string").eq(approval_company)
            ]
        approval_departments = [
            ALL_APPROVAL_FILTER,
            *sorted(
                department_source["department"]
                .dropna()
                .astype(str)
                .str.strip()
                .loc[lambda values: values.ne("")]
                .unique()
                .tolist()
            ),
        ]
        if st.session_state.get("approval_queue_department") not in approval_departments:
            st.session_state["approval_queue_department"] = ALL_APPROVAL_FILTER
        with department_column:
            approval_department = st.selectbox(
                "หน่วยงาน",
                options=approval_departments,
                key="approval_queue_department",
            )

    filtered_queue = filter_pending_queue(
        pending_queue,
        search_text=approval_search,
        company=approval_company,
        department=approval_department,
    )
    with st.container(horizontal=True):
        st.metric("Pending ทั้งหมด", len(pending_queue), border=True)
        st.metric("ผลลัพธ์หลังกรอง", len(filtered_queue), border=True)
        st.badge("APPROVER / ADMIN", color="blue", icon=":material/verified_user:")

    if filtered_queue.empty:
        st.info(
            "ไม่พบรายงาน Pending ที่ตรงกับเงื่อนไข หากยังไม่ได้ส่งคำขอ "
            "ให้สลับเป็น demo_user แล้วกด ‘ส่งขออนุมัติ’ ก่อน"
        )
    else:
        st.dataframe(
            filtered_queue,
            hide_index=True,
            width="stretch",
            column_config={
                "report_id": "Report ID",
                "talk_date": "วันที่",
                "company": "บริษัท",
                "department": "หน่วยงาน",
                "topic": "หัวข้อ",
                "sender": "ผู้ส่ง",
                "status": "สถานะ",
            },
            alt="รายงาน Safety Talk สถานะ Pending ที่รอการอนุมัติ",
        )

        with st.container(border=True, key="approval_queue_actions"):
            st.markdown("**ดำเนินการกับรายงาน**")
            action_report_id = st.selectbox(
                "Report ID",
                options=filtered_queue["report_id"].tolist(),
                key="approval_queue_report_id",
            )
            approval_comment = st.text_area(
                "ความคิดเห็น / เหตุผล (ต้องระบุเมื่อ Reject)",
                key="approval_queue_comment",
            )
            approve_column, reject_column = st.columns(2)
            with approve_column:
                approve_clicked = st.button(
                    "อนุมัติ",
                    key="approval_queue_approve",
                    icon=":material/check_circle:",
                    type="primary",
                    width="stretch",
                )
            with reject_column:
                reject_clicked = st.button(
                    "ปฏิเสธ",
                    key="approval_queue_reject",
                    icon=":material/cancel:",
                    width="stretch",
                )

            try:
                if approve_clicked:
                    approval_service.approve(
                        action_report_id,
                        role=current_role,
                        actor=current_actor,
                        comment=approval_comment,
                    )
                    st.session_state["approval_queue_flash"] = (
                        f"อนุมัติสำเร็จ · Report ID: {action_report_id}"
                    )
                    st.rerun()
                elif reject_clicked:
                    approval_service.reject(
                        action_report_id,
                        role=current_role,
                        actor=current_actor,
                        comment=approval_comment,
                    )
                    st.session_state["approval_queue_flash"] = (
                        f"ปฏิเสธสำเร็จ · Report ID: {action_report_id}"
                    )
                    st.rerun()
            except (PermissionError, ValueError, KeyError) as error:
                st.error(str(error), title="ไม่สามารถดำเนินการได้")

elif selected_menu == "Demo Admin":
    st.subheader("Demo Admin Console", icon=":material/admin_panel_settings:")
    st.warning(
        "หน้านี้เป็นพื้นที่สาธิตสำหรับ ADMIN และไม่มี Authentication จริง",
        title="DEMO ADMIN",
        icon=":material/science:",
    )
    with st.container(border=True):
        st.markdown("**สิทธิ์ของ ADMIN ใน Demo นี้**")
        for permission in Permission:
            st.markdown(f"- `{permission.value}`")
        st.caption("ไม่มีการแก้ไขผู้ใช้ หน่วยงาน หรือ CSV จากหน้านี้")

st.caption("ใช้ข้อมูลตัวอย่างเท่านั้น · ไม่ใช่ระบบ Production")
