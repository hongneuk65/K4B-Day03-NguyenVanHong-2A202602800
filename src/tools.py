"""
🛠️ TOOL DEFINITIONS & EXECUTION BACKEND
Mã nguồn chứa danh sách Tool Schemas (JSON Schema) và Execution Layer phục vụ cho MCP Server.
"""

import json
import re
from typing import Dict, Any


TOOLS_SCHEMA = [
    {
        "name": "doctor_schedule_query",
        "description": "Tra cứu lịch làm việc của bác sĩ chuyên khoa tại cơ sở Vinmec theo bác sĩ, chuyên khoa và khoảng thời gian.",
        "parameters": {
            "type": "object",
            "properties": {
                "doctor_name": {"type": "string", "description": "Tên bác sĩ cần tra cứu"},
                "specialty": {"type": "string", "description": "Chuyên khoa, ví dụ: Tim mạch hoặc Nội thần kinh"},
                "facility": {"type": "string", "description": "Cơ sở Vinmec cần tra cứu"},
                "date_range": {"type": "string", "description": "Khoảng thời gian cần tra cứu, ví dụ: 15/09/2026-21/09/2026"}
            },
            "required": ["specialty", "facility", "date_range"]
        }
    },
    {
        "name": "book_medical_appointment",
        "description": "Đặt lịch khám bệnh tại Vinmec sau khi người bệnh đã xác nhận bác sĩ, cơ sở và thời gian.",
        "parameters": {
            "type": "object",
            "properties": {
                "patient_name": {"type": "string", "description": "Họ tên người bệnh"},
                "phone": {"type": "string", "description": "Số điện thoại liên hệ của người bệnh"},
                "doctor_name": {"type": "string", "description": "Tên bác sĩ muốn đặt lịch"},
                "specialty": {"type": "string", "description": "Chuyên khoa khám"},
                "facility": {"type": "string", "description": "Cơ sở Vinmec"},
                "datetime_str": {"type": "string", "description": "Thời gian khám, ví dụ: 14:00 15/09/2026"}
            },
            "required": ["patient_name", "phone", "doctor_name", "specialty", "facility", "datetime_str"]
        }
    }
]


MOCK_DATABASE = {
    "Nguyễn Văn An|Nội tổng quát|Vinmec Times City": {
        "doctor_name": "Nguyễn Văn An",
        "specialty": "Nội tổng quát",
        "facility": "Vinmec Times City",
        "available_slots": ["14:00 15/09/2026", "09:00 17/09/2026"]
    },
    "Trần Minh An|Tim mạch|Vinmec Nha Trang": {
        "doctor_name": "Trần Minh An",
        "specialty": "Tim mạch",
        "facility": "Vinmec Nha Trang",
        "available_slots": []
    },
    "Lê Thị Mai|Tim mạch|Vinmec Times City": {
        "doctor_name": "Lê Thị Mai",
        "specialty": "Tim mạch",
        "facility": "Vinmec Times City",
        "available_slots": ["10:00 15/09/2026", "08:30 16/09/2026"]
    },
    "Phạm Minh Đức|Nội tổng quát|Vinmec Times City": {
        "doctor_name": "Phạm Minh Đức",
        "specialty": "Nội tổng quát",
        "facility": "Vinmec Times City",
        "available_slots": ["09:00 16/09/2026", "15:30 18/09/2026"]
    }
}


def execute_doctor_schedule_query(doctor_name: str = "", specialty: str = "", facility: str = "", date_range: str = "") -> str:
    """Tra cứu lịch theo các tiêu chí; cho phép bỏ trống tên để tìm bác sĩ bất kỳ."""
    requested_doctor = (doctor_name or "").strip().casefold()
    any_doctor = requested_doctor in {"", "*", "bất kỳ", "bác sĩ bất kỳ", "any"}
    requested_specialty = (specialty or "").strip().casefold()
    requested_facility = (facility or "").strip().casefold()

    matches = []
    for doctor in MOCK_DATABASE.values():
        if not doctor["available_slots"]:
            continue
        if not any_doctor and doctor["doctor_name"].casefold() != requested_doctor:
            continue
        if requested_specialty and doctor["specialty"].casefold() != requested_specialty:
            continue
        if requested_facility and doctor["facility"].casefold() != requested_facility:
            continue

        slots = doctor["available_slots"]
        requested_dates = set(re.findall(r"\d{2}/\d{2}/\d{4}", date_range or ""))
        if requested_dates:
            slots = [slot for slot in slots if any(day in slot for day in requested_dates)]
        if not slots:
            continue
        matches.append({**doctor, "available_slots": slots, "date_range": date_range})

    if not matches:
        doctor_label = "bất kỳ bác sĩ" if any_doctor else f"bác sĩ {doctor_name}"
        return json.dumps({
            "status": "NOT_FOUND",
            "message": f"Không tìm thấy lịch trống của {doctor_label} tại {facility} trong {date_range}."
        }, ensure_ascii=False)

    return json.dumps({"status": "SUCCESS", "data": matches}, ensure_ascii=False)


def execute_book_medical_appointment(patient_name: str, phone: str, doctor_name: str, specialty: str, facility: str, datetime_str: str) -> str:
    """Đặt lịch khám bệnh Vinmec từ dữ liệu đã xác nhận."""
    return json.dumps({
        "status": "SUCCESS", "booking_id": f"VM-{phone[-4:]}-99", "patient_name": patient_name,
        "phone": phone, "doctor_name": doctor_name, "specialty": specialty,
        "facility": facility, "datetime": datetime_str,
        "message": f"Đặt lịch khám thành công cho {patient_name} tại {facility} vào {datetime_str}."
    }, ensure_ascii=False)


# Router gọi tool thực tế
TOOL_ROUTER = {
    "doctor_schedule_query": execute_doctor_schedule_query,
    "book_medical_appointment": execute_book_medical_appointment
}

def dispatch_tool_call(tool_name: str, arguments: Dict[str, Any]) -> str:
    """Hàm trung chuyển thực thi tool"""
    if tool_name in TOOL_ROUTER:
        try:
            return TOOL_ROUTER[tool_name](**arguments)
        except Exception as e:
            return json.dumps({"status": "EXECUTION_ERROR", "error": str(e)}, ensure_ascii=False)
    return json.dumps({"status": "UNKNOWN_TOOL", "error": f"Tool '{tool_name}' không tồn tại!"}, ensure_ascii=False)
