import React from 'react';
import { useNavigate } from 'react-router-dom';
import ChatPanel from '../shared/ChatPanel';
import { useLanguage } from '../../context/LanguageContext';

/**
 * Full-page shell for the Cursus chat — one continuous conversation per
 * student (`/api/v1/student/chat*`), same `ChatPanel` the floating launcher
 * uses. No more per-course thread list: a course is just a per-message
 * context field now, picked from the dropdown inside `ChatPanel` itself.
 */
export default function StudentCompanionPage() {
  const { lang } = useLanguage();
  const navigate = useNavigate();

  return (
    <div className="flex flex-col gap-4 p-6 animate-fade-up max-w-4xl">
      <div className="border-b pb-4 border-line text-left">
        <h1 className="font-display text-xl font-bold text-fg">
          {lang === 'vi' ? 'Trợ lý Cursus' : 'Cursus Assistant'}
        </h1>
        <p className="text-xs text-fg-muted mt-1">
          {lang === 'vi'
            ? 'Hỏi về nội dung môn học, kế hoạch/rủi ro/phản tư của bạn, hoặc cách dùng Cursus — tất cả trong 1 cuộc trò chuyện.'
            : 'Ask about course content, your own plan/risk/reflection, or how to use Cursus — all in one conversation.'}
        </p>
      </div>
      <ChatPanel variant="full" navigate={navigate} />
    </div>
  );
}
