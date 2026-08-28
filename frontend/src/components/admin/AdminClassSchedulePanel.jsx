import React, { useEffect, useState } from 'react';
import { CalendarClock, Plus } from 'lucide-react';
import { createAdminStudySlot, createFixedClassSchedule, getActiveAcademicTerm, getAdminSections, getAdminStudySlots } from '../../lib/api';

const DEFAULT_FROM = '2026-08-10';
const DEFAULT_TO = '2026-10-18';

export default function AdminClassSchedulePanel() {
  const [term, setTerm] = useState('Fall2026');
  const [slots, setSlots] = useState([]);
  const [sections, setSections] = useState([]);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [slot, setSlot] = useState({ name: '', start_minute: 480, end_minute: 600, display_order: 1, is_active: true });
  const [meeting, setMeeting] = useState({ section_id: '', slot_id: '', weekday: 0, room: '', note: '', effective_from: DEFAULT_FROM, effective_to: DEFAULT_TO });
  const load = async (termName = term) => {
    try {
      const [active, slotData, sectionData] = await Promise.all([getActiveAcademicTerm().catch(() => null), getAdminStudySlots(termName), getAdminSections()]);
      if (active?.name && active.name !== termName) { setTerm(active.name); return load(active.name); }
      setSlots(slotData.items || []); setSections(sectionData.items || []);
    } catch (err) { setError(err.message || 'Không tải được lịch lớp.'); }
  };
  useEffect(() => { load(); }, []); // initial term is stable
  const addSlot = async (event) => { event.preventDefault(); setSaving(true); setError(''); try { await createAdminStudySlot({ ...slot, term_name: term }); setSlot({ ...slot, name: '' }); await load(); } catch (err) { setError(err.message); } finally { setSaving(false); } };
  const addMeeting = async (event) => { event.preventDefault(); setSaving(true); setError(''); try { await createFixedClassSchedule(meeting); setMeeting((x) => ({ ...x, room: '', note: '' })); } catch (err) { setError(err.message); } finally { setSaving(false); } };
  return <section className="card p-5 space-y-5 text-left" aria-labelledby="class-schedule-title">
    <div><div className="flex items-center gap-2"><CalendarClock size={18} className="text-accent" /><h2 id="class-schedule-title" className="text-sm font-bold text-fg">Lịch lớp cố định</h2></div><p className="mt-1 text-xs text-fg-secondary">Ca học được snapshot vào từng lịch; sinh viên chỉ xem, không thể chỉnh sửa.</p></div>
    {error && <p className="text-xs text-danger" role="alert">{error}</p>}
    <div className="grid gap-5 lg:grid-cols-2">
      <form onSubmit={addSlot} className="rounded-lg border border-line p-4 space-y-3"><h3 className="text-xs font-bold text-fg">Ca học · {term}</h3><div className="grid grid-cols-3 gap-2"><input required className="input text-xs col-span-3" placeholder="Tên ca (VD: Ca 1)" value={slot.name} onChange={e => setSlot({ ...slot, name: e.target.value })} /><input type="number" className="input text-xs" value={slot.start_minute} onChange={e => setSlot({ ...slot, start_minute: Number(e.target.value) })} /><input type="number" className="input text-xs" value={slot.end_minute} onChange={e => setSlot({ ...slot, end_minute: Number(e.target.value) })} /><input type="number" className="input text-xs" value={slot.display_order} onChange={e => setSlot({ ...slot, display_order: Number(e.target.value) })} /></div><p className="text-[11px] text-fg-muted">Nhập phút tính từ 00:00 (480 = 08:00).</p><button disabled={saving} className="btn btn-accent px-3 py-2 text-xs"><Plus size={14}/> Thêm ca</button><div className="space-y-1 text-xs">{slots.map(item => <p key={item.id} className="font-mono text-fg-secondary">{item.name}: {String(Math.floor(item.startMinute / 60)).padStart(2,'0')}:{String(item.startMinute % 60).padStart(2,'0')}–{String(Math.floor(item.endMinute / 60)).padStart(2,'0')}:{String(item.endMinute % 60).padStart(2,'0')}</p>)}</div></form>
      <form onSubmit={addMeeting} className="rounded-lg border border-line p-4 space-y-3"><h3 className="text-xs font-bold text-fg">Xếp lịch lớp</h3><select required className="input text-xs" value={meeting.section_id} onChange={e => setMeeting({ ...meeting, section_id: e.target.value })}><option value="">Chọn lớp-môn</option>{sections.map(s => <option key={s.id} value={s.id}>{s.sectionCode || s.section_code} · {s.courseCode || s.course_code}</option>)}</select><div className="grid grid-cols-2 gap-2"><select required className="input text-xs" value={meeting.slot_id} onChange={e => setMeeting({ ...meeting, slot_id: e.target.value })}><option value="">Chọn ca</option>{slots.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}</select><select className="input text-xs" value={meeting.weekday} onChange={e => setMeeting({ ...meeting, weekday: Number(e.target.value) })}>{['Thứ 2','Thứ 3','Thứ 4','Thứ 5','Thứ 6','Thứ 7','CN'].map((d,i)=><option key={d} value={i}>{d}</option>)}</select></div><input className="input text-xs" placeholder="Phòng học" value={meeting.room} onChange={e => setMeeting({ ...meeting, room: e.target.value })}/><div className="grid grid-cols-2 gap-2"><input type="date" className="input text-xs" value={meeting.effective_from} onChange={e=>setMeeting({...meeting,effective_from:e.target.value})}/><input type="date" className="input text-xs" value={meeting.effective_to} onChange={e=>setMeeting({...meeting,effective_to:e.target.value})}/></div><button disabled={saving} className="btn btn-accent px-3 py-2 text-xs">Lưu lịch cố định</button></form>
    </div>
  </section>;
}
