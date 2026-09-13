# Báo cáo nghiệm thu Lab 3 — Trợ lý tư vấn sức khỏe Vinmec

- **Học viên:** Nguyễn Văn Hồng
- **Mã học viên:** 2A202602800
- **Chủ đề:** Tra cứu lịch và đặt lịch khám Vinmec

## 1. Agentic Fit Scoring Matrix

| Tiêu chí | Điểm (1–5) | Bằng chứng |
|---|---:|---|
| Multi-step Reasoning | 5/5 | Agent đọc Observation và tiếp tục vòng ReAct khi cần. |
| Tool Interaction | 5/5 | Native Tool Calling gọi hai Tool Vinmec qua MCP. |
| Dynamic Decision | 5/5 | Xử lý SUCCESS, NOT_FOUND, nhiều bác sĩ/slot và ngày cụ thể. |
| Long Horizon Goal | 4/5 | Hỗ trợ tra cứu → chọn slot → xác nhận → đặt lịch trong Interactive. |
| **Tổng** | **19/20** | Chủ đề phù hợp Agentic System. |

## 2. Tool Schema và test cases

`src/tools.py` khai báo JSON Schema chuẩn cho `doctor_schedule_query` và `book_medical_appointment`. Tên bác sĩ tùy chọn ở Tool tra cứu để hỗ trợ “bác sĩ bất kỳ”; thông tin đặt lịch vẫn bắt buộc đầy đủ.

`config/test_cases.json` có 5 ca: hỏi thông tin chung, tra cứu, đặt lịch, tra cứu không tìm thấy và xử lý edge case.

## 3. ReAct và Native Tool Calling

```text
Thought → Action (Native Tool Call) → MCP → Observation
       → gửi Observation lại LLM → Tool tiếp theo hoặc Final Answer
```

`src/app.py` giữ `MAX_ITERATIONS`, MCP dispatch và trace contract. Sau mỗi Tool Execution, Observation được đưa lại vào prompt ở vòng kế tiếp. Khi LLM trả `type=text`, Agent ghi Final Answer và dừng.

Khi nghiệm thu API thật, console phải có `LLM Provider: GeminiProvider`; không dùng fallback Mock làm bằng chứng API thật.

## 4. Waterfall Trace

Artifact chính là `docs/trace_waterfall.json`. Sự kiện Tool ghi `step`, `query`, `action_type`, `tool_name`, `arguments`, `observation`, `latency_ms`; Final Answer ghi `thought`, `output`, `latency_ms`.

TC01 không gọi Tool; TC02, TC04, TC05 gọi `doctor_schedule_query`; TC03 gọi `book_medical_appointment`. Số lượt Tool tối thiểu của bộ test là **4**, được đếm theo số sự kiện `action_type=TOOL_EXECUTION` thực tế trong trace.

## 5. Kết quả nghiệm thu

- **Test cases:** 5/5 đã cấu hình.
- **Tool schema:** hoàn chỉnh.
- **MCP dispatch:** hoàn chỉnh.
- **Trace artifact:** `docs/trace_waterfall.json`.
- **API thật:** xác nhận bằng log `GeminiProvider` ở lần chạy nộp bài cuối.

```powershell
python -m compileall -q src
python src/app.py --all
```

Chạy `--all` cuối cùng để không ghi đè trace bằng phiên Interactive.
