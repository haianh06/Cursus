import React, { useEffect, useState } from 'react';
import { Sprout, Leaf, TreeDeciduous, Flower2 } from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';
import { getStudentReflections } from '../../lib/api';

/**
 * F14 — Vườn tiến độ: thay thế cho streak kiểu Duolingo (đếm chuỗi ngày,
 * "mất chuỗi" gây tội lỗi). Mỗi tuần đã có phản tư thì hiện 1 biểu tượng lớn
 * dần theo % hoàn thành — tuần chưa có dữ liệu thì đơn giản không hiện gì,
 * không có icon "khô héo"/cảnh báo mất chuỗi nào cả.
 *
 * Dữ liệu lấy lại từ GET /student/reflections đã có sẵn (mỗi tuần phản tư
 * lưu kèm metrics.completionRate) — không cần endpoint mới.
 */
function stageFor(rate) {
  if (rate >= 90) return { Icon: Flower2, className: 'text-[#7c3aed] dark:text-[#a78bfa]' };
  if (rate >= 75) return { Icon: TreeDeciduous, className: 'text-success-ink dark:text-emerald-400' };
  if (rate >= 50) return { Icon: Leaf, className: 'text-brand' };
  return { Icon: Sprout, className: 'text-slate-400 dark:text-slate-500' };
}

export default function ProgressGarden() {
  const { t } = useLanguage();
  const [weeks, setWeeks] = useState([]);

  useEffect(() => {
    let cancelled = false;
    getStudentReflections()
      .then((data) => {
        if (cancelled) return;
        const withRate = data
          .filter((item) => Number.isFinite(item.completion_rate))
          .sort((a, b) => a.week_number - b.week_number);
        setWeeks(withRate);
      })
      .catch(() => {
        // Widget trang trí — im lặng ẩn đi nếu không tải được, không chiếm
        // chỗ bằng thông báo lỗi cho một tính năng không thiết yếu.
        if (!cancelled) setWeeks([]);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (weeks.length === 0) return null;

  return (
    <div className="cursus-card rounded-3xl p-5 shadow-sm space-y-3">
      <div className="flex items-center gap-2">
        <Flower2 className="w-4 h-4 text-brand" />
        <h2 className="text-sm font-black text-[#15181C] dark:text-white font-serif-heading">
          {t('studentHome.gardenTitle')}
        </h2>
      </div>
      <p className="text-[11px] text-slate-500 dark:text-slate-400 font-medium">
        {t('studentHome.gardenSubtitle')}
      </p>
      <div className="flex flex-wrap items-end gap-3 pt-1">
        {weeks.map(({ week_number: week, completion_rate: rate }) => {
          const { Icon, className } = stageFor(rate);
          return (
            <div key={week} className="flex flex-col items-center gap-1" title={`W${week} — ${rate}%`}>
              <Icon className={`w-7 h-7 ${className}`} />
              <span className="text-[10px] font-bold text-slate-500 dark:text-slate-500 font-mono-code">
                W{week}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
