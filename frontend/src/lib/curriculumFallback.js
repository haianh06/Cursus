// SINH TU DONG - du lieu du phong khi backend chua co endpoint tuong ung.
// Nguon:
//   docs/planning/v2/data/courses_BIT_SE_K20D_K21A.json  (48 mon)
//   docs/planning/v2/data/seed_students_SSA101.json      (class_summary, kpi_comparison)
//   docs/planning/v2/data/chunks_*.json                  (mon nao da ingest)
// UI luon uu tien API that va chi dung file nay khi API chua co/that bai,
// dong thoi phai hien nhan bao dang chay bang du lieu seed.

export const CURRICULUM_FALLBACK = {
  "courses": [
    {
      "subject_code": "OTP101",
      "subject_name": "Orientation and General Training Program_Định hướng và Rèn luyện tập trung",
      "semester": "0",
      "ingest_status": "not_ingested",
      "chunk_count": 0
    },
    {
      "subject_code": "PEN",
      "subject_name": "Preparation English_Tiếng Anh chuẩn bị",
      "semester": "0",
      "ingest_status": "not_ingested",
      "chunk_count": 0
    },
    {
      "subject_code": "PHE_COM*1",
      "subject_name": "Physical Education 1_Giáo dục thể chất 1",
      "semester": "0",
      "ingest_status": "not_ingested",
      "chunk_count": 0
    },
    {
      "subject_code": "TMI_ELE",
      "subject_name": "Traditional musical instrument_Nhạc cụ truyền thống",
      "semester": "0",
      "ingest_status": "not_ingested",
      "chunk_count": 0
    },
    {
      "subject_code": "CEA201",
      "subject_name": "Computer Organization and Architecture_Tổ chức và Kiến trúc máy tính",
      "semester": "1",
      "ingest_status": "not_ingested",
      "chunk_count": 0
    },
    {
      "subject_code": "CSI106",
      "subject_name": "Introduction to Computer Science_Nhập môn khoa học máy tính",
      "semester": "1",
      "ingest_status": "not_ingested",
      "chunk_count": 0
    },
    {
      "subject_code": "MAE101",
      "subject_name": "Mathematics for Engineering_Toán cho ngành kỹ thuật",
      "semester": "1",
      "ingest_status": "not_ingested",
      "chunk_count": 0
    },
    {
      "subject_code": "PHE_COM*2",
      "subject_name": "Physical Education 2_Giáo dục thể chất 2",
      "semester": "1",
      "ingest_status": "not_ingested",
      "chunk_count": 0
    },
    {
      "subject_code": "PRF192",
      "subject_name": "Programming Fundamentals_Cơ sở lập trình",
      "semester": "1",
      "ingest_status": "not_ingested",
      "chunk_count": 0
    },
    {
      "subject_code": "SSA101",
      "subject_name": "Kỹ năng học thuật",
      "semester": "1",
      "ingest_status": "ingested",
      "chunk_count": 72
    },
    {
      "subject_code": "MAD101",
      "subject_name": "Discrete mathematics_Toán rời rạc",
      "semester": "2",
      "ingest_status": "not_ingested",
      "chunk_count": 0
    },
    {
      "subject_code": "NWC204",
      "subject_name": "Computer Networking_Mạng máy tính",
      "semester": "2",
      "ingest_status": "not_ingested",
      "chunk_count": 0
    },
    {
      "subject_code": "OSG202",
      "subject_name": "Operating Systems_Hệ điều hành",
      "semester": "2",
      "ingest_status": "not_ingested",
      "chunk_count": 0
    },
    {
      "subject_code": "PHE_COM*3",
      "subject_name": "Physical Education 3_Giáo dục thể chất 3",
      "semester": "2",
      "ingest_status": "not_ingested",
      "chunk_count": 0
    },
    {
      "subject_code": "PRO192",
      "subject_name": "Object-Oriented Programming_Lập trình hướng đối tượng",
      "semester": "2",
      "ingest_status": "not_ingested",
      "chunk_count": 0
    },
    {
      "subject_code": "WED201c",
      "subject_name": "Web Design_Thiết kế web",
      "semester": "2",
      "ingest_status": "not_ingested",
      "chunk_count": 0
    },
    {
      "subject_code": "DBI202",
      "subject_name": "Introduction to Databases_Các hệ cơ sở dữ liệu",
      "semester": "3",
      "ingest_status": "not_ingested",
      "chunk_count": 0
    },
    {
      "subject_code": "JPD113",
      "subject_name": "Elementary Japanese 1- A1.1_Tiếng Nhật sơ cấp 1-A1.1",
      "semester": "3",
      "ingest_status": "not_ingested",
      "chunk_count": 0
    },
    {
      "subject_code": "LAB211",
      "subject_name": "OOP with Java Lab_Thực hành OOP với Java",
      "semester": "3",
      "ingest_status": "not_ingested",
      "chunk_count": 0
    },
    {
      "subject_code": "MAS291",
      "subject_name": "Statistics & Probability_Xác suất thống kê",
      "semester": "3",
      "ingest_status": "not_ingested",
      "chunk_count": 0
    },
    {
      "subject_code": "SWE202c",
      "subject_name": "Introduction to Software Engineering_Nhập môn kĩ thuật phần mềm",
      "semester": "3",
      "ingest_status": "not_ingested",
      "chunk_count": 0
    },
    {
      "subject_code": "CSD201",
      "subject_name": "Data Structures and Algorithms_Cấu trúc dữ liệu và giải thuật",
      "semester": "4",
      "ingest_status": "not_ingested",
      "chunk_count": 0
    },
    {
      "subject_code": "IOT102",
      "subject_name": "Internet of Things_Internet vạn vật",
      "semester": "4",
      "ingest_status": "not_ingested",
      "chunk_count": 0
    },
    {
      "subject_code": "JPD123",
      "subject_name": "Elementary Japanese 1-A1.2_Tiếng Nhật sơ cấp 1-A1.2",
      "semester": "4",
      "ingest_status": "not_ingested",
      "chunk_count": 0
    },
    {
      "subject_code": "PRJ301",
      "subject_name": "Java Web Application Development_Phát triển ứng dụng Java web",
      "semester": "4",
      "ingest_status": "not_ingested",
      "chunk_count": 0
    },
    {
      "subject_code": "SWR302",
      "subject_name": "Software Requirement_Yêu cầu phần mềm",
      "semester": "4",
      "ingest_status": "not_ingested",
      "chunk_count": 0
    },
    {
      "subject_code": "SE_COM*1",
      "subject_name": "Subject 1 of Combo*_Học phần 1 của combo*",
      "semester": "5",
      "ingest_status": "not_ingested",
      "chunk_count": 0
    },
    {
      "subject_code": "SSG105",
      "subject_name": "Kỹ năng giao tiếp và cộng tác",
      "semester": "5",
      "ingest_status": "not_ingested",
      "chunk_count": 0
    },
    {
      "subject_code": "SWP391",
      "subject_name": "Software development project_Dự án phát triển phần mềm",
      "semester": "5",
      "ingest_status": "not_ingested",
      "chunk_count": 0
    },
    {
      "subject_code": "SWT301",
      "subject_name": "Software Testing_Kiểm thử phần mềm",
      "semester": "5",
      "ingest_status": "not_ingested",
      "chunk_count": 0
    },
    {
      "subject_code": "WDU203c",
      "subject_name": "UI/UX Design_Thiết kế trải nghiệm người dùng",
      "semester": "5",
      "ingest_status": "not_ingested",
      "chunk_count": 0
    },
    {
      "subject_code": "ENW493c",
      "subject_name": "Research Methods & Academic Writing Skills_Phương pháp nghiên cứu & Kỹ năng viết học thuật",
      "semester": "6",
      "ingest_status": "not_ingested",
      "chunk_count": 0
    },
    {
      "subject_code": "OJT202",
      "subject_name": "On-The-Job Training_Đào tạo trong môi trường thực tế",
      "semester": "6",
      "ingest_status": "not_ingested",
      "chunk_count": 0
    },
    {
      "subject_code": "EXE101",
      "subject_name": "Experiential Entrepreneurship 1_Trải nghiệm khởi nghiệp 1",
      "semester": "7",
      "ingest_status": "not_ingested",
      "chunk_count": 0
    },
    {
      "subject_code": "PMG201c",
      "subject_name": "Project Management",
      "semester": "7",
      "ingest_status": "not_ingested",
      "chunk_count": 0
    },
    {
      "subject_code": "SE_COM*2",
      "subject_name": "Subject 2 of Combo*_Học phần 2 của combo*",
      "semester": "7",
      "ingest_status": "not_ingested",
      "chunk_count": 0
    },
    {
      "subject_code": "SE_COM*3",
      "subject_name": "Subject 3 of Combo*_Học phần 3 của combo*",
      "semester": "7",
      "ingest_status": "not_ingested",
      "chunk_count": 0
    },
    {
      "subject_code": "SWD392",
      "subject_name": "Software Architecture and Design_Kiến trúc và thiết kế phần mềm",
      "semester": "7",
      "ingest_status": "not_ingested",
      "chunk_count": 0
    },
    {
      "subject_code": "EXE201",
      "subject_name": "Experiential Entrepreneurship 2_Trải nghiệm khởi nghiệp 2",
      "semester": "8",
      "ingest_status": "not_ingested",
      "chunk_count": 0
    },
    {
      "subject_code": "ITE302c",
      "subject_name": "Ethics in IT_Đạo đức trong CNTT",
      "semester": "8",
      "ingest_status": "not_ingested",
      "chunk_count": 0
    },
    {
      "subject_code": "MLN111",
      "subject_name": "Philosophy of Marxism – Leninism_Triết học Mác - Lê-nin",
      "semester": "8",
      "ingest_status": "not_ingested",
      "chunk_count": 0
    },
    {
      "subject_code": "MLN122",
      "subject_name": "Political economics of Marxism – Leninism_Kinh tế chính trị Mác - Lê-nin",
      "semester": "8",
      "ingest_status": "not_ingested",
      "chunk_count": 0
    },
    {
      "subject_code": "PRM393",
      "subject_name": "Mobile Programming_Lập trình di động",
      "semester": "8",
      "ingest_status": "not_ingested",
      "chunk_count": 0
    },
    {
      "subject_code": "SE_COM*4_ELE",
      "subject_name": "Học phần 4 của combo SE",
      "semester": "8",
      "ingest_status": "not_ingested",
      "chunk_count": 0
    },
    {
      "subject_code": "HCM202",
      "subject_name": "Ho Chi Minh Ideology_Tư tưởng Hồ Chí Minh",
      "semester": "9",
      "ingest_status": "not_ingested",
      "chunk_count": 0
    },
    {
      "subject_code": "MLN131",
      "subject_name": "Scientific socialism_Chủ nghĩa xã hội khoa học",
      "semester": "9",
      "ingest_status": "not_ingested",
      "chunk_count": 0
    },
    {
      "subject_code": "SE_GRA_ELE",
      "subject_name": "Graduation Elective - Software Engineering_Học phần lựa chọn Đồ án tốt nghiệp chuyên ngành Kỹ thuật phần mềm",
      "semester": "9",
      "ingest_status": "not_ingested",
      "chunk_count": 0
    },
    {
      "subject_code": "VNR202",
      "subject_name": "History of Communist Party of Vietnam_Lịch sử Đảng Cộng sản Việt Nam",
      "semester": "9",
      "ingest_status": "not_ingested",
      "chunk_count": 0
    }
  ],
  "kpi": {
    "with_cursus_overall": 0.78,
    "baseline_overall": 0.45,
    "method_note": "2 kịch bản sinh độc lập, không dùng chung nguồn ngẫu nhiên — tránh thiên vị khi so sánh A/B mô phỏng."
  },
  "class_summary": {
    "subject_code": "SSA101",
    "class_size": 12,
    "class_avg_completion_by_week": [
      0.9,
      0.79,
      0.73,
      0.7
    ]
  }
};
