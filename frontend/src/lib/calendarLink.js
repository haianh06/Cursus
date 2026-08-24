/**
 * F11 — "Đặt lịch gặp" thành nút thật, không cần OAuth/tích hợp Google gì cả.
 * Google hỗ trợ sẵn URL "render" điền trước 1 sự kiện — mở ra là một trang
 * Google Calendar thật, GV tự xem lại và bấm Lưu. Đúng tinh thần HITL: hệ
 * thống chỉ hỗ trợ thao tác, GV vẫn là người quyết định gửi lời mời hay không.
 */
function toGoogleCalendarStamp(date) {
  return date.toISOString().replace(/[-:]/g, '').replace(/\.\d{3}Z$/, 'Z');
}

/**
 * Mặc định 15:00–15:30 ngày làm việc kế tiếp — không có deadline cụ thể nào
 * để bám vào (suggested_action chỉ là gợi ý hành động, không có giờ hẹn),
 * nên chọn một khung giờ trung tính GV tự đổi lại trên Google Calendar.
 */
export function buildMeetingCalendarUrl({ studentName, note }) {
  const start = new Date();
  start.setDate(start.getDate() + 1);
  start.setHours(15, 0, 0, 0);
  const end = new Date(start.getTime() + 30 * 60 * 1000);

  const params = new URLSearchParams({
    action: 'TEMPLATE',
    text: `Gặp ${studentName || 'sinh viên'} — trao đổi học tập`,
    dates: `${toGoogleCalendarStamp(start)}/${toGoogleCalendarStamp(end)}`,
    details: note || 'Trao đổi về tiến độ học tập trên Cursus.',
  });

  return `https://calendar.google.com/calendar/render?${params.toString()}`;
}
