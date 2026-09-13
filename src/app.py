"""
🚀 CORE AGENT APPLICATION (DAY 03: CHATBOT VS REACT AGENT)
Thực thi so sánh giữa Chatbot Baseline (Cấp 2) và ReAct Agent kết nối MCP Server (Cấp 3).
"""

import json
import os
import sys
import time
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from mcp_server import MCPAcademicServer
from prompts import (
    CHATBOT_BASELINE_PROMPT,
    REACT_AGENT_SYSTEM_PROMPT,
    MAX_ITERATIONS
)
from providers import get_llm_provider

load_dotenv()

def load_test_cases():
    """Tải danh sách 5 test cases từ config/test_cases.json hoặc config/test_cases.example.json"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, "config", "test_cases.json")
    if not os.path.exists(config_path):
        example_path = os.path.join(base_dir, "config", "test_cases.example.json")
        if os.path.exists(example_path):
            print("⚠️ [CONFIG NOTICE]: Chưa thấy file 'config/test_cases.json'. Đang dùng mẫu 'config/test_cases.example.json'.")
            print("👉 Hãy chạy: copy config/test_cases.example.json config/test_cases.json và viết test cases theo đề tài của bạn!\n")
            config_path = example_path
        else:
            config_path = "test_cases.json"
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_waterfall_trace(trace_data: list):
    """Ghi vết log Waterfall Trace Log ra file docs/trace_waterfall.json"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    docs_dir = os.path.join(base_dir, "docs")
    os.makedirs(docs_dir, exist_ok=True)
    trace_path = os.path.join(docs_dir, "trace_waterfall.json")
    with open(trace_path, "w", encoding="utf-8") as f:
        json.dump(trace_data, f, ensure_ascii=False, indent=2)
    print(f"📊 [OBSERVABILITY]: Đã lưu {len(trace_data)} sự kiện Waterfall Trace tại '{trace_path}'!")


def run_baseline_chatbot(user_query: str, provider):
    """Chạy Chatbot gốc (Cấp 2) không có công cụ gọi Tool"""
    print(f"\n💬 [CHATBOT BASELINE] Câu hỏi: {user_query}")
    response = provider.generate(user_query, system_prompt=CHATBOT_BASELINE_PROMPT)
    print(f"🤖 Chatbot phản hồi:\n{response}")


def run_react_agent(user_query: str, provider, mcp_server: MCPAcademicServer, conversation_history: list = None) -> list:
    """
    [REACT AGENT LOOP] Thực thi vòng lặp Thought -> Action -> Observation với MCP Server.
    conversation_history chỉ bổ sung ngữ cảnh cho chế độ interactive; contract ReAct cũ vẫn giữ nguyên.
    """
    print(f"\n🤖 [REACT AGENT] Câu hỏi: {user_query}")
    history_text = ""
    if conversation_history:
        history_text = "\n\nLỊCH SỬ HỘI THOẠI TRƯỚC ĐÓ:\n" + "\n".join(conversation_history)
    agent_prompt = user_query + history_text
    working_prompt = agent_prompt

    step = 0
    trace_logs = []
    tools_list = mcp_server.list_tools()
    
    while step < MAX_ITERATIONS:
        step += 1
        step_start_time = time.time()
        print(f"\n--- 🔄 Vòng lặp ReAct Loop (Step {step}/{MAX_ITERATIONS}) ---")
        
        # Gọi LLM với Native Tool Calling Specs
        llm_response = provider.generate_with_tools(working_prompt, tools_list, system_prompt=REACT_AGENT_SYSTEM_PROMPT)
        latency_ms = round((time.time() - step_start_time) * 1000, 2)
        
        thought = llm_response.get("thought", "Đang suy luận...")
        print(f"🧠 [Thought]: {thought}")
        
        # Trường hợp 1: LLM quyết định trả lời bằng văn bản trực tiếp
        if llm_response.get("type") == "text":
            final_content = llm_response.get("content", "")
            print(f"🏁 [Final Answer]: {final_content}")
            trace_logs.append({
                "step": step,
                "query": user_query,
                "action_type": "FINAL_ANSWER",
                "thought": thought,
                "output": final_content,
                "latency_ms": latency_ms
            })
            break
            
        # Trường hợp 2: LLM đề xuất gọi Tool (Action)
        elif llm_response.get("type") == "tool_call":
            tool_name = llm_response.get("tool_name")
            arguments = llm_response.get("arguments", {})
            
            print(f"🛠️ [Action Proposed]: {tool_name}({arguments})")
            
            # Thực thi Tool qua MCP Server
            mcp_result = mcp_server.call_tool(tool_name, arguments)
            obs_data = mcp_result.get("result", {})
            
            if not obs_data:
                print(f"👁️ [Observation từ MCP Server]: {{}}")
                print(f"⚠️ [CHÚ Ý]: MCP Server trả về kết quả rỗng! Học viên cần hoàn thành TODO 2.1 trong 'src/mcp_server.py'.")
                final_answer = "Chưa thể trả lời chi tiết do chưa nhận được dữ liệu từ MCP Server (hãy hoàn thành TODO 2.1)."
            else:
                obs_str = json.dumps(obs_data, ensure_ascii=False)
                print(f"👁️ [Observation từ MCP Server]: {obs_str}")
                
                # Tổng hợp Final Answer từ kết quả Observation thực tế
                if obs_data.get("status") == "SUCCESS":
                    if "message" in obs_data:
                        final_answer = obs_data["message"]
                    elif "data" in obs_data:
                        d = obs_data["data"]
                        if isinstance(d, list) and d and "available_slots" in d[0]:
                            entries = []
                            for item in d:
                                slots = ", ".join(item.get("available_slots", [])) or "chưa có khung giờ trống"
                                entries.append(
                                    f"{item.get('doctor_name', '')} ({item.get('specialty', '')}, "
                                    f"{item.get('facility', '')}): {slots}"
                                )
                            final_answer = "Các lịch trống phù hợp: " + "; ".join(entries) + "."
                        elif isinstance(d, dict) and "available_slots" in d:
                            slots = ", ".join(d.get("available_slots", [])) or "chưa có khung giờ trống"
                            final_answer = (
                                f"Lịch làm việc của bác sĩ {d.get('doctor_name', '')}, "
                                f"chuyên khoa {d.get('specialty', '')} tại {d.get('facility', '')} "
                                f"trong khoảng {d.get('date_range', '')}: {slots}."
                            )
                        elif isinstance(d, dict) and "full_name" in d:
                            final_answer = (
                                f"Kết quả tra cứu cho sinh viên {obs_data.get('student_id', '')} ({d.get('full_name', '')}): "
                                f"Lớp {d.get('class', '')}, GPA: {d.get('gpa', '')}, Email: {d.get('email', '')}, "
                                f"Trạng thái: {d.get('status', '')}, Cố vấn: {d.get('advisor', '')}."
                            )
                        else:
                            final_answer = json.dumps(d, ensure_ascii=False)
                    else:
                        final_answer = f"Đã hoàn tất xử lý qua MCP Server: {json.dumps(obs_data, ensure_ascii=False)}"
                elif obs_data.get("status") == "NOT_FOUND":
                    final_answer = obs_data.get("message", "Không tìm thấy thông tin sinh viên yêu cầu.")
                else:
                    final_answer = f"Phản hồi từ công cụ: {json.dumps(obs_data, ensure_ascii=False)}"
            
            trace_logs.append({
                "step": step,
                "query": user_query,
                "action_type": "TOOL_EXECUTION",
                "tool_name": tool_name,
                "arguments": arguments,
                "observation": obs_data,
                "latency_ms": latency_ms
            })
            
            # Đưa Observation trở lại LLM để thực hiện bước ReAct tiếp theo.
            # Chỉ kết thúc khi LLM trả lời text hoặc hết MAX_ITERATIONS.
            working_prompt = (
                f"{agent_prompt}\n\n"
                f"OBSERVATION TỪ TOOL {tool_name}: {json.dumps(obs_data, ensure_ascii=False)}\n"
                "Hãy tiếp tục suy luận theo quy tắc: nếu cần dữ liệu/hành động tiếp theo thì gọi Tool; "
                "nếu đã đủ thông tin thì trả lời text cho người dùng."
            )
            if step >= MAX_ITERATIONS:
                final_answer = final_answer or "Đã đạt giới hạn số bước xử lý; vui lòng xác nhận lại yêu cầu."
                print(f"🏁 [Final Answer]: {final_answer}")
                trace_logs.append({
                    "step": step + 1,
                    "query": user_query,
                    "action_type": "FINAL_ANSWER",
                    "thought": "Đạt giới hạn MAX_ITERATIONS sau khi nhận Observation.",
                    "output": final_answer,
                    "latency_ms": 0.0
                })
                break

            print(f"🧠 [Thought]: Đã nhận Observation; tiếp tục vòng ReAct kế tiếp.")

    return trace_logs


if __name__ == "__main__":
    print("==========================================================")
    print("🏫 VINUNI AI COURSE - DAY 03 LAB: CHATBOT VS REACT AGENT")
    print("==========================================================")
    
    provider = get_llm_provider()
    mcp_server = MCPAcademicServer()
    
    print(f"🔌 LLM Provider: {provider.__class__.__name__}")
    print(f"🌐 MCP Server: {mcp_server.server_name}\n")
    
    tests = load_test_cases()
    print(f"✅ Đã tải thành công {len(tests)} Test Cases thử nghiệm.\n")
    
    if "--interactive" in sys.argv:
        print("🎮 [INTERACTIVE MODE] Trò chuyện trực tiếp với ReAct Agent:")
        print("💡 Gợi ý câu hỏi thử nghiệm:")
        print("   - Câu hỏi chung: 'Vinmec hỗ trợ những dịch vụ gì?'")
        print("   - Tra cứu lịch: 'Hãy tra cứu lịch bác sĩ Nguyễn Văn An tại Vinmec Times City'")
        print("   - Đặt lịch: 'Hãy đặt lịch khám tại Vinmec Times City vào 14:00 15/09/2026'")
        print("   - Gõ 'exit' hoặc 'quit' để kết thúc phiên trò chuyện.\n")
        conversation_history = []
        while True:
            try:
                user_input = input("👤 Sinh viên hỏi: ").strip()
                if not user_input or user_input.lower() in ["exit", "quit"]:
                    print("👋 Tạm biệt! Kết thúc phiên trò chuyện.")
                    break
                logs = run_react_agent(user_input, provider, mcp_server, conversation_history)
                save_waterfall_trace(logs)
                conversation_history.append(f"Người dùng: {user_input}")
                final_events = [event for event in logs if event.get("action_type") == "FINAL_ANSWER"]
                if final_events:
                    conversation_history.append(f"Trợ lý: {final_events[-1].get('output', '')}")
            except (KeyboardInterrupt, EOFError):
                print("\n👋 Đã thoát phiên tương tác.")
                break
    elif "--all" in sys.argv:
        print("🚀 [TEST SUITE MODE] Kiểm tra 5 Test Cases:")
        completed_count = 0
        todo_count = 0
        all_traces = []
        
        for tc in tests:
            print(f"\n==================================================")
            print(f"🧪 [{tc['id']}] Loại test: {tc['type']} (Độ phức tạp: {tc['complexity']})")
            print(f"📌 Kỳ vọng: {tc['expected_behavior']}")
            
            if tc["question"].strip().startswith("TODO"):
                print(f"⏸️ [CHƯA KÍCH HOẠT - ĐANG LÀ TODO]:")
                print(f"   {tc['question']}")
                print(f"   👉 Hãy mở file 'config/test_cases.json' để viết câu hỏi thực tế cho Test Case này!")
                todo_count += 1
            else:
                logs = run_react_agent(tc["question"], provider, mcp_server)
                all_traces.extend(logs)
                completed_count += 1
                
        print(f"\n==================================================")
        print(f"📊 [KẾT QUẢ TEST SUITE]: Đã thực thi {completed_count}/{len(tests)} Test Cases | {todo_count} Test Cases đang chờ điền câu hỏi (TODO)")
        if all_traces:
            save_waterfall_trace(all_traces)
        print(f"💡 Để trò chuyện trực tiếp từng câu: Chạy 'python src/app.py --interactive'")
    else:
        # Chế độ mặc định khi chỉ gõ 'python src/app.py'
        print("ℹ️ HƯỚNG DẪN SỬ DỤNG CHƯƠNG TRÌNH:")
        print("  1. Chat trực tiếp liên tục:   python src/app.py --interactive")
        print("  2. Chạy toàn bộ Test Cases:    python src/app.py --all\n")
        
        sample_query = tests[1]["question"]
        print(f"--- 🏁 DEMO CHẠY THỬ 1 TEST CASE MẪU (TC02: Tra cứu học vụ) ---")
        logs = run_react_agent(sample_query, provider, mcp_server)
        save_waterfall_trace(logs)
        print("\n💡 Hãy thử ngay lệnh: python src/app.py --interactive để chat trực tiếp!")
