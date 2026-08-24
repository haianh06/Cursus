"""Sinh dữ liệu SV mô phỏng cho demo Mốc 1 — đủ để Dashboard GV/Admin có số liệu thật.
Áp đúng rule alert đã chốt trong PRD: trễ >=2 deadline liên tiếp trong 2 tuần gần nhất
HOAC hoan thanh <50% task trong 3 tuan lien tiep.
"""
import json

NAMES = ["Đăng","Linh","Huy","Mai","Khoa","Trang","Phúc","An","Bảo","Chi","Vinh","Ngọc"]
SUBJECT = "SSA101"

# (tasks_total, tasks_completed, deadline_missed) mỗi tuần, 4 tuần/SV — tự tay chọn để có
# đúng 3 SV rơi vào ngưỡng cảnh báo, còn lại bình thường -> demo GV có gì để bấm vào.
PATTERNS = {
    "Đăng":  [(5,5,0),(5,4,0),(5,5,0),(5,4,0)],   # ổn định
    "Linh":  [(5,5,0),(5,5,0),(5,4,0),(5,5,0)],   # tốt
    "Huy":   [(5,3,1),(5,2,1),(5,1,1),(5,2,1)],   # <50% 3 tuần liên tiếp -> ALERT
    "Mai":   [(5,5,0),(5,4,0),(4,1,1),(4,0,1)],   # trễ 2 deadline liên tiếp -> ALERT
    "Khoa":  [(5,4,0),(5,5,0),(5,4,0),(5,5,0)],
    "Trang": [(5,5,0),(5,3,0),(5,4,0),(5,5,0)],
    "Phúc":  [(4,4,0),(4,3,0),(4,2,1),(4,1,1)],   # trễ liên tiếp cuối kỳ -> ALERT
    "An":    [(5,5,0),(5,5,0),(5,5,0),(5,4,0)],
    "Bảo":   [(5,4,0),(5,3,0),(5,4,0),(5,3,0)],
    "Chi":   [(5,5,0),(5,4,0),(5,5,0),(5,5,0)],
    "Vinh":  [(4,3,0),(4,3,0),(4,4,0),(4,3,0)],
    "Ngọc":  [(5,4,0),(5,5,0),(5,3,0),(5,4,0)],
}

def compute_alert(weeks):
    # >=2 deadline_missed liên tiếp ở 2 tuần gần nhất
    last2 = weeks[-2:]
    if all(w[2] >= 1 for w in last2):
        return "TRE_LIEN_TIEP", "Trễ deadline liên tiếp 2 tuần gần nhất"
    # <50% completion 3 tuần liên tiếp
    last3 = weeks[-3:]
    if all((w[1] / w[0]) < 0.5 for w in last3):
        return "HOAN_THANH_THAP", "Tỷ lệ hoàn thành <50% trong 3 tuần liên tiếp"
    return None, None

students = []
for i, name in enumerate(NAMES, start=1):
    weeks = PATTERNS[name]
    weekly = []
    for w_idx, (total, done, missed) in enumerate(weeks, start=1):
        weekly.append({
            "week": w_idx,
            "tasks_total": total,
            "tasks_completed": done,
            "on_time_rate": round(done / total, 2),
            "deadline_missed_this_week": missed,
        })
    alert_type, alert_reason = compute_alert(weeks)
    students.append({
        "student_id": f"sv{i:02d}",
        "name": name,
        "subject_code": SUBJECT,
        "weekly": weekly,
        "avg_completion_4weeks": round(sum(w["on_time_rate"] for w in weekly) / 4, 2),
        "alert": {
            "triggered": alert_type is not None,
            "type": alert_type,
            "reason": alert_reason,
            "status": "pending_review" if alert_type else None,
        },
    })

class_summary = {
    "subject_code": SUBJECT,
    "class_size": len(students),
    "students_with_alert": sum(1 for s in students if s["alert"]["triggered"]),
    "class_avg_completion_by_week": [
        round(sum(s["weekly"][w]["on_time_rate"] for s in students) / len(students), 2)
        for w in range(4)
    ],
}

# ---- Kịch bản baseline "không dùng Cursus" — độc lập, không suy ra từ nhóm trên,
# để tránh thiên vị khi so sánh (đúng lưu ý đã ghi trong PRD mục 6) ----
BASELINE_PATTERNS = {
    "Đăng":[(5,3,1),(5,2,1),(5,3,1),(5,2,1)], "Linh":[(5,4,0),(5,3,1),(5,3,0),(5,2,1)],
    "Huy":[(5,2,1),(5,1,1),(5,1,1),(5,0,1)], "Mai":[(5,3,0),(5,2,1),(4,1,1),(4,0,1)],
    "Khoa":[(5,3,0),(5,3,1),(5,2,1),(5,3,0)], "Trang":[(5,3,0),(5,2,1),(5,3,0),(5,2,0)],
    "Phúc":[(4,2,0),(4,2,1),(4,1,1),(4,0,1)], "An":[(5,4,0),(5,3,0),(5,3,1),(5,2,0)],
    "Bảo":[(5,2,1),(5,2,0),(5,2,1),(5,1,1)], "Chi":[(5,4,0),(5,3,0),(5,3,0),(5,2,1)],
    "Vinh":[(4,2,0),(4,2,1),(4,1,1),(4,1,0)], "Ngọc":[(5,3,0),(5,3,1),(5,2,0),(5,2,1)],
}
baseline_by_week = [
    round(sum(v[w][1] / v[w][0] for v in BASELINE_PATTERNS.values()) / len(BASELINE_PATTERNS), 2)
    for w in range(4)
]

kpi_comparison = {
    "with_cursus_avg_by_week": class_summary["class_avg_completion_by_week"],
    "baseline_no_cursus_avg_by_week": baseline_by_week,
    "with_cursus_overall": round(sum(class_summary["class_avg_completion_by_week"]) / 4, 2),
    "baseline_overall": round(sum(baseline_by_week) / 4, 2),
    "note": "2 kịch bản sinh độc lập, không dùng chung nguồn ngẫu nhiên — tránh thiên vị khi so sánh A/B mô phỏng.",
}

output = {"class_summary": class_summary, "students": students, "kpi_comparison": kpi_comparison}
with open("/mnt/user-data/outputs/seed_students_SSA101.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print("students with alert:", [s["name"] for s in students if s["alert"]["triggered"]])
print("class_avg_completion_by_week (with Cursus):", class_summary["class_avg_completion_by_week"])
print("baseline (no Cursus):", baseline_by_week)
print("overall with vs baseline:", kpi_comparison["with_cursus_overall"], "vs", kpi_comparison["baseline_overall"])
