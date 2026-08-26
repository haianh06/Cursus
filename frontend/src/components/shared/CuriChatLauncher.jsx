import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { X, Trash2, Shield, ArrowRight, BookOpen, ArrowUp, ShieldAlert } from 'lucide-react';
import CursusMascot from './CursusMascot';
import { useLanguage } from '../../context/LanguageContext';
import { useCursus } from '../../context/CursusContext';
import { askQuestion, getStudentCourses } from '../../lib/api';

export default function CuriChatLauncher() {
  const navigate = useNavigate();
  const location = useLocation();
  const { lang } = useLanguage();
  const { showMascot, toggleMascot } = useCursus();

  // Route Guard: the public marketing/onboarding pages keep the scripted
  // FAQ (no login yet, nothing to call). `/student/*` is the other branch —
  // there the widget calls the real `POST /qa` pipeline (same one
  // `CuriContextPanel` uses on Student Overview) instead of canned copy, so
  // a student gets one consistent Cursus Assistant wherever they are, not a
  // fake-chat toy on some pages and the real thing on others. Instructor/
  // Admin dashboards are still out of scope — Cursus Assistant's Q&A is a
  // student study tool (mục 1/6.2), there's no "which course" context on
  // those roles' pages to scope a real answer to.
  const visibleRoutes = ['/', '/login', '/accept-invite', '/request-access', '/demo/select-role', '/forgot-password'];
  const isStudentRoute = location.pathname.startsWith('/student');
  const isVisibleRoute = visibleRoutes.includes(location.pathname) || isStudentRoute;

  // ALT + C Global Keyboard Shortcut to Toggle Mascot Visibility
  useEffect(() => {
    const handleGlobalKeyDown = (e) => {
      if (e.altKey && (e.key === 'c' || e.key === 'C')) {
        e.preventDefault();
        toggleMascot();
      }
    };
    window.addEventListener('keydown', handleGlobalKeyDown);
    return () => window.removeEventListener('keydown', handleGlobalKeyDown);
  }, [toggleMascot]);

  const [isOpen, setIsOpen] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [showWelcomeTip, setShowWelcomeTip] = useState(false); // Disabled auto-open
  const [showPrivacy, setShowPrivacy] = useState(false);
  const [messages, setMessages] = useState([]);
  const [isThinking, setIsThinking] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0); 
  const [showTooltip, setShowTooltip] = useState(false);
  const [mascotState, setMascotState] = useState('idle');
  const [isPressed, setIsPressed] = useState(false);
  const [confirmingClear, setConfirmingClear] = useState(false);
  const [inputValue, setInputValue] = useState('');
  const clearTriggerRef = useRef(null);
  const confirmCancelRef = useRef(null);
  const textInputRef = useRef(null);

  // Real-answer mode (`/student/*` only) — which course an "ask about the
  // course" question is scoped to. Loaded lazily so public-route visitors
  // never trigger an authenticated request.
  const [courses, setCourses] = useState([]);
  const [subjectCode, setSubjectCode] = useState('');
  const [coursesLoaded, setCoursesLoaded] = useState(false);

  useEffect(() => {
    if (!isStudentRoute || coursesLoaded) return;
    let cancelled = false;
    getStudentCourses()
      .then((list) => {
        if (cancelled) return;
        // Seed/demo enrollments can list the same course code across more
        // than one section (pre-existing data artifact, not this widget's
        // concern to fix) — dedupe by code so the picker doesn't show the
        // same course twice.
        const seen = new Set();
        const deduped = (list || []).filter((c) => (seen.has(c.code) ? false : seen.add(c.code)));
        setCourses(deduped);
        if (deduped.length) setSubjectCode((prev) => prev || deduped[0].code);
      })
      .catch(() => {})
      .finally(() => !cancelled && setCoursesLoaded(true));
    return () => {
      cancelled = true;
    };
  }, [isStudentRoute, coursesLoaded]);

  // The widget instance is mounted once for the whole app (App.jsx), so its
  // message history otherwise survives login — leaving stale scripted-FAQ
  // replies sitting next to real backend answers the moment a visitor logs
  // in and lands on /student/*. Reset on that one transition only, so an
  // in-progress real conversation isn't wiped by ordinary navigation between
  // student pages (isStudentRoute stays true there).
  const prevIsStudentRoute = useRef(isStudentRoute);
  useEffect(() => {
    if (isStudentRoute && !prevIsStudentRoute.current) {
      setMessages([]);
    }
    prevIsStudentRoute.current = isStudentRoute;
  }, [isStudentRoute]);

  // Keep keyboard focus inside the inline confirm row once it appears
  useEffect(() => {
    if (confirmingClear) confirmCancelRef.current?.focus();
  }, [confirmingClear]);

  const closeConfirm = () => {
    setConfirmingClear(false);
    clearTriggerRef.current?.focus();
  };

  // Handle Mascot restoration happy blink animation
  useEffect(() => {
    if (showMascot) {
      setMascotState('celebrate');
      const timer = setTimeout(() => {
        setMascotState('idle');
      }, 1200);
      return () => clearTimeout(timer);
    }
  }, [showMascot]);

  // Wave greeting exactly once per session
  useEffect(() => {
    const greeted = sessionStorage.getItem('curi_greeted');
    if (!greeted && showMascot && isVisibleRoute) {
      setMascotState('greeting');
      sessionStorage.setItem('curi_greeted', 'true');

      const timer = setTimeout(() => {
        setMascotState('idle');
      }, 1600);
      return () => clearTimeout(timer);
    }
  }, [showMascot, isVisibleRoute]);

  // Sync Cursus Assistant's facial expression state
  useEffect(() => {
    if (isThinking) {
      setMascotState('thinking');
    } else if (isOpen) {
      setMascotState('listening');
    } else {
      const greeted = sessionStorage.getItem('curi_greeted');
      if (greeted && mascotState === 'greeting') return;
      setMascotState('idle');
    }
  }, [isThinking, isOpen]);

  const handleMouseEnter = () => {
    setShowTooltip(true);
    if (mascotState === 'idle') {
      setMascotState('hover');
    }
  };

  const handleMouseLeave = () => {
    setShowTooltip(false);
    if (mascotState === 'hover') {
      setMascotState(isOpen ? 'listening' : 'idle');
    }
  };

  const [isMobile, setIsMobile] = useState(false);
  // On the landing page only: stay out of the hero's cinematic frame while
  // it's still in view, so the launcher doesn't compete with it for
  // attention. Everywhere else (auth pages, once scrolled past hero) it
  // behaves exactly as before.
  const [withinHero, setWithinHero] = useState(location.pathname === '/');
  const isLandingRoute = location.pathname === '/';

  const launcherRef = useRef(null);
  const panelRef = useRef(null);
  const messagesEndRef = useRef(null);
  const prevMessagesCount = useRef(messages.length);
  const prevIsThinking = useRef(isThinking);

  // Track viewport size for mobile layout
  useEffect(() => {
    const checkMobile = () => setIsMobile(window.innerWidth < 640);
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  useEffect(() => {
    if (location.pathname !== '/') {
      setWithinHero(false);
      return undefined;
    }
    const heroEl = document.querySelector('.landing-main > section');
    const checkScroll = () => {
      const heroBottom = heroEl ? heroEl.getBoundingClientRect().bottom : 0;
      setWithinHero(heroBottom > 120);
    };
    checkScroll();
    window.addEventListener('scroll', checkScroll, { passive: true });
    return () => window.removeEventListener('scroll', checkScroll);
  }, [location.pathname]);

  // Sync scroll to bottom of messages — only when a message was actually
  // added or thinking just started, never on mount/re-run with unchanged
  // state. See the identical fix in LandingSandbox.jsx: a plain "first
  // render" boolean isn't safe here because React StrictMode's dev-only
  // double-invoke of effects re-runs this after the flag already flipped.
  useEffect(() => {
    const grew = messages.length > prevMessagesCount.current;
    const startedThinking = isThinking && !prevIsThinking.current;
    prevMessagesCount.current = messages.length;
    prevIsThinking.current = isThinking;
    if ((grew || startedThinking) && messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }, [messages, isThinking]);

  // Handle focus trapping and Escape key — Escape cancels the inline
  // "clear conversation" confirm first (if open), a second press then
  // closes the whole panel.
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        if (confirmingClear) {
          closeConfirm();
          return;
        }
        closeChat();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, confirmingClear]);

  const openChat = () => {
    setIsOpen(true);
    setIsMinimized(false);
    setShowWelcomeTip(false);
    setUnreadCount(0);
    window.dispatchEvent(new CustomEvent('curi-chat-toggle', { detail: { open: true } }));
    
    // Initialize welcome message if empty
    if (messages.length === 0) {
      setMessages([
        {
          id: 'welcome',
          role: 'assistant',
          text: isStudentRoute
            ? (lang === 'vi'
                ? 'Chào bạn! Hỏi mình về nội dung môn học — mình sẽ trả lời dựa trên tài liệu môn thật, kèm nguồn trích dẫn.'
                : "Hi! Ask me about your coursework — I'll answer from the real course materials, with citations.")
            : (lang === 'vi'
                ? 'Chào bạn! Mình là Trợ lý Cursus. Trước khi đăng nhập, mình có thể hướng dẫn bạn về các tính năng, đăng ký tài khoản hoặc bảo mật thông tin.'
                : 'Hi! I\'m Cursus Assistant. Before logging in, I can guide you on product features, registration, or privacy information.'),
          isWelcome: true
        }
      ]);
    }
    
    setTimeout(() => {
      if (textInputRef.current) {
        textInputRef.current.focus();
      } else if (panelRef.current) {
        panelRef.current.focus();
      }
    }, 100);
  };

  const closeChat = () => {
    setIsOpen(false);
    window.dispatchEvent(new CustomEvent('curi-chat-toggle', { detail: { open: false } }));
    if (launcherRef.current) {
      launcherRef.current.focus();
    }
  };

  const clearChat = () => {
    setMessages([
      {
        id: 'welcome',
        role: 'assistant',
        text: isStudentRoute
          ? (lang === 'vi'
              ? 'Hỏi mình về nội dung môn học — mình sẽ trả lời dựa trên tài liệu môn thật, kèm nguồn trích dẫn.'
              : "Ask me about your coursework — I'll answer from the real course materials, with citations.")
          : (lang === 'vi'
              ? 'Chào bạn! Tôi là Trợ lý Cursus. Trước khi đăng nhập, tôi có thể hướng dẫn bạn về các tính năng, đăng ký tài khoản hoặc bảo mật thông tin.'
              : 'Hi! I\'m Cursus Assistant. Before logging in, I can guide you on product features, registration, or privacy information.'),
        isWelcome: true
      }
    ]);
  };

  // Real-backend path for `/student/*` routes — calls the same `POST /qa`
  // pipeline as `CuriContextPanel`, pushes both the user message and the
  // real (possibly blocked/guardrailed) answer. No scripted intent matching
  // involved here — whatever the backend actually decided is what renders.
  const sendRealQuestion = async (rawQuestion) => {
    const question = (rawQuestion ?? '').trim();
    if (!question || isThinking) return;
    const id = `u-${Date.now()}`;
    setMessages((prev) => [...prev, { id, role: 'user', text: question }]);
    setIsThinking(true);
    setMascotState('thinking');
    try {
      const result = await askQuestion({ subjectCode, question });
      setMessages((prev) => [...prev, { id: `${id}-a`, role: 'assistant', real: true, ...result }]);
      setMascotState('answering');
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: `${id}-e`,
          role: 'assistant',
          real: true,
          failed: true,
          answer: lang === 'vi'
            ? 'Không hỏi được Trợ lý Cursus lúc này. Kiểm tra kết nối rồi thử lại — câu hỏi của bạn vẫn còn ở ô nhập.'
            : 'Could not reach Cursus Assistant. Check your connection and try again.',
        },
      ]);
      setInputValue(question);
    } finally {
      setIsThinking(false);
      setTimeout(() => setMascotState(isOpen ? 'listening' : 'idle'), 1200);
    }
  };

  // Shared by both the preset chips and free-text input, so a typed
  // question that matches one of the 5 known intents gets the exact same
  // answer as clicking its chip — one source of truth for the reply content.
  const getReplyForKey = (key) => {
    if (key === 'features') {
      return {
        replyText: lang === 'vi'
          ? 'Cursus giúp bạn chuyển hoá syllabus và assignment thành kế hoạch học tập tuần chủ động (PLAN), học tập liêm chính có đối thoại trích dẫn nguồn (DO) và nhật ký phản tư tuần (REFLECT).'
          : 'Cursus turns your course syllabus and assignments into an actionable weekly study plan (PLAN), grounded Q&A with citations (DO), and structured weekly reflections (REFLECT).',
        citation: lang === 'vi' ? 'Giới thiệu Cursus' : 'Cursus Core Pillars',
      };
    }
    if (key === 'register') {
      return {
        replyText: lang === 'vi'
          ? 'Cursus không có đăng ký công khai — tài khoản do trường của bạn cấp (Học viên được nhập/mời, Giảng viên được Quản trị viên mời, Quản trị viên được cấp khi khởi tạo tổ chức). Muốn dùng thử trước? Trải nghiệm sandbox 3 vai trò miễn phí, không cần tài khoản.'
          : 'Cursus has no public sign-up — accounts are issued by your institution (Students imported/invited, Teachers invited by an Admin, Admins provisioned when the organization is set up). Want to try it first? Explore the 3-role sandbox for free, no account needed.',
        citation: lang === 'vi' ? 'Provisioning tài khoản' : 'Account Provisioning',
        ctaLink: '/demo/select-role',
        ctaText: lang === 'vi' ? 'Trải nghiệm sandbox' : 'Explore the sandbox',
      };
    }
    if (key === 'login') {
      return {
        replyText: lang === 'vi'
          ? 'Nhấn nút "Sign In" góc phải trên trang chủ để vào trang đăng nhập (/login). Hãy dùng email trường được cấp và mật khẩu đã tạo. Bạn cũng có thể liên kết đăng nhập an toàn bằng tài khoản Google.'
          : 'Click the "Sign In" button on the top-right of the home page to go to /login. Enter your university email and password, or quickly sign in using Google OAuth.',
        citation: lang === 'vi' ? 'Hướng dẫn Đăng nhập' : 'Login Guidelines',
        ctaLink: '/login',
        ctaText: lang === 'vi' ? 'Đăng nhập ngay' : 'Sign In Now',
      };
    }
    if (key === 'privacy') {
      return {
        replyText: lang === 'vi'
          ? 'Cursus cam kết bảo vệ dữ liệu: Các đoạn hội thoại riêng tư giữa Học viên và Trợ lý Cursus không bao giờ hiển thị trực tiếp cho Giảng viên. Giảng viên chỉ nhận báo cáo KPI hoặc cảnh báo nguy cơ học tập để hỗ trợ kịp thời.'
          : 'Cursus prioritizes privacy: private conversations between students and Cursus Assistant are never exposed to instructors. Faculty members only see aggregated KPI metrics and at-risk alerts to offer timely support.',
        citation: lang === 'vi' ? 'Hiến chương Bảo mật Cursus' : 'Cursus Privacy Charter',
      };
    }
    if (key === 'integrity') {
      return {
        replyText: lang === 'vi'
          ? 'Để đảm bảo liêm chính học thuật, Trợ lý Cursus không bao giờ viết code, viết luận hay làm bài hộ bạn. Mọi yêu cầu làm hộ bài sẽ bị chặn và chuyển hướng sang gợi ý các bước logic tự làm.'
          : 'To protect academic integrity, Cursus Assistant never writes code, drafts essays, or solves assignments on your behalf. Any direct solving requests will be blocked and redirected to step-by-step hints.',
        citation: lang === 'vi' ? 'Liêm chính Học thuật' : 'Academic Integrity Engine',
      };
    }
    // Unmatched free-text: this widget only knows 5 fixed intents (it's a
    // scripted FAQ menu wearing chat clothing, not a real LLM backend — see
    // "Dữ liệu minh họa" in the header) — say so plainly instead of
    // pretending to understand, and point back at what it *can* answer.
    return {
      replyText: lang === 'vi'
        ? 'Mình chưa được huấn luyện để trả lời câu hỏi mở như thế này. Bạn thử chọn 1 trong các gợi ý bên dưới, hoặc liên hệ đội ngũ Cursus để được hỗ trợ trực tiếp nhé.'
        : "I'm not trained to answer open-ended questions like this yet. Try one of the suggestions below, or contact the Cursus team directly for help.",
      citation: null,
    };
  };

  // Bilingual, diacritic-insensitive keyword matching against the 5 known
  // intents — good enough for a scripted FAQ widget with no real NLU behind
  // it. Falls through to the "not trained for this" reply otherwise.
  const normalize = (s) => s
    .toLowerCase()
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '');

  // Order matters: checked top-to-bottom, first match wins. "login" must be
  // checked before "register" — a typed "không đăng nhập được vào tài
  // khoản" contains both "tài khoản" and "đăng nhập", and a bare
  // account/tài-khoản keyword on "register" would shadow the more specific
  // login complaint (caught by real testing: this exact phrase used to
  // wrongly return the registration answer).
  const INTENT_KEYWORDS = {
    login: ['dang nhap', 'log in', 'login', 'sign in', 'khong vao duoc', 'khong dang nhap', "can't log in", 'cant log in'],
    register: ['dang ky', 'sign up', 'signup', 'register', 'tao tai khoan', 'co tai khoan', 'invite', 'moi vao'],
    privacy: ['bao mat', 'rieng tu', 'privacy', 'data', 'du lieu'],
    integrity: ['liem chinh', 'gian lan', 'integrity', 'cheat', 'lam ho', 'guardrail', 'academic'],
    features: ['tinh nang', 'feature', 'lam duoc gi', 'what can', 'gioi thieu'],
  };

  const matchIntent = (text) => {
    const normalized = normalize(text);
    for (const [key, keywords] of Object.entries(INTENT_KEYWORDS)) {
      if (keywords.some((kw) => normalized.includes(normalize(kw)))) return key;
    }
    return null;
  };

  const respondTo = (key, replySettleDelay = true) => {
    setIsThinking(true);
    setTimeout(() => {
      setIsThinking(false);
      const { replyText, citation, ctaLink, ctaText } = getReplyForKey(key);

      setMessages(prev => [...prev, {
        id: `c-${Date.now()}`,
        role: 'assistant',
        text: replyText,
        citation,
        ctaLink,
        ctaText
      }]);

      setMascotState('answering');
      if (replySettleDelay && (key === 'features' || key === 'privacy')) {
        setTimeout(() => {
          setMascotState('success');
          setTimeout(() => {
            setMascotState(isOpen ? 'listening' : 'idle');
          }, 1000);
        }, 1400);
      } else {
        setTimeout(() => {
          setMascotState(isOpen ? 'listening' : 'idle');
        }, 1650);
      }
    }, 1000);
  };

  const handlePrompt = (key, label) => {
    const userMsgId = `u-${Date.now()}`;
    setMessages(prev => [...prev, { id: userMsgId, role: 'user', text: label }]);
    respondTo(key);
  };

  const handleFreeTextSubmit = (e) => {
    e.preventDefault();
    const text = inputValue.trim();
    if (!text || isThinking) return;
    setInputValue('');
    if (isStudentRoute) {
      sendRealQuestion(text);
      return;
    }
    setMessages(prev => [...prev, { id: `u-${Date.now()}`, role: 'user', text }]);
    respondTo(matchIntent(text) || 'fallback');
  };

  const handleMascotClick = () => {
    setIsPressed(true);
    setMascotState('happy');

    setTimeout(() => {
      setIsPressed(false);
      setMascotState(isOpen ? 'idle' : 'listening');
      if (isOpen) {
        closeChat();
      } else {
        openChat();
      }
    }, 180);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      if (isOpen) {
        closeChat();
      } else {
        openChat();
      }
    }
  };

  const PRESET_OPTIONS = [
    { key: 'features', label: lang === 'vi' ? 'Tính năng của Cursus' : 'Cursus Core Features' },
    { key: 'register', label: lang === 'vi' ? 'Làm sao để có tài khoản?' : 'How do I get an account?' },
    { key: 'login', label: lang === 'vi' ? 'Tôi không đăng nhập được' : 'I can\'t log in' },
    { key: 'privacy', label: lang === 'vi' ? 'Bảo mật thông tin thế nào?' : 'How is my data protected?' },
    { key: 'integrity', label: lang === 'vi' ? 'Quy tắc Liêm chính Học thuật' : 'Academic Integrity Charter' }
  ];

  // Real-mode suggestions — plain example questions (not fixed intents),
  // sent verbatim to /qa exactly like typing them in.
  const STUDENT_SUGGESTED_QUESTIONS = [
    lang === 'vi' ? 'Điều kiện qua môn này là gì?' : 'What are the passing requirements for this course?',
    lang === 'vi' ? 'Em nên bắt đầu từ đâu?' : 'Where should I start?',
    lang === 'vi' ? 'Tuần này có tài liệu nào cần đọc?' : 'What should I read this week?',
  ];

  if (!isVisibleRoute) return null;

  return (
    <div
      className={`fixed z-[85] transition-all duration-300 ease-out ${
        showMascot && !(withinHero && !isOpen) ? 'opacity-100 scale-100' : 'opacity-0 scale-90 pointer-events-none'
      }`}
      style={{
        bottom: isMobile ? 'calc(16px + env(safe-area-inset-bottom))' : '24px',
        right: '24px',
      }}
    >
      {/* Welcome Tip */}
      {showWelcomeTip && !isOpen && showMascot && (
        <div className="absolute bottom-16 right-0 w-64 p-3 rounded-[var(--radius-md)] bg-surface-card border border-line shadow-panel animate-scale-in text-xs font-semibold text-fg-secondary text-left leading-relaxed select-none">
          <div className="flex justify-between items-start gap-1">
            <span className="text-accent-text-safe font-bold">{lang === 'vi' ? 'Hướng dẫn từ Trợ lý Cursus' : 'Cursus Assistant Guide'}</span>
            <button 
              type="button" 
              onClick={() => setShowWelcomeTip(false)}
              className="p-0.5 text-fg-muted hover:text-fg rounded"
              aria-label="Close welcome tooltip"
            >
              <X size={12} />
            </button>
          </div>
          <p className="mt-1">
            {lang === 'vi' 
              ? 'Xin chào! Tôi có thể hướng dẫn bạn về Cursus. Nhấn vào đây nhé!' 
              : 'Hi there! I can guide you through Cursus. Click here to chat!'}
          </p>
          <div className="absolute right-6 -bottom-1.5 w-3 h-3 rotate-45 bg-surface-card border-r border-b border-line" />
        </div>
      )}

      {/* Non-permanent Tooltip */}
      {showTooltip && !isMobile && !isOpen && showMascot && (
        <div
          id="curi-launcher-tooltip"
          role="tooltip"
          className="absolute right-16 top-1/2 -translate-y-1/2 px-3 py-1.5 rounded-lg bg-slate-900 text-white text-[11px] font-bold shadow-md whitespace-nowrap animate-scale-in z-20 pointer-events-none"
        >
          {lang === 'vi' ? "Hỏi Cursus" : "Ask Cursus"}
          <div className="absolute top-1/2 -translate-y-1/2 -right-1 w-2 h-2 rotate-45 bg-slate-900" />
        </div>
      )}

      {/* Mascot Bubble — the landing page uses a neutral/Cursus Assistant-sky-blue glow
          (Cursus Assistant's single intelligence signal) instead of the product's warm
          amber halo, so it doesn't compete with the monochrome brand system
          there. Every other page (auth screens) keeps the original amber
          styling untouched.
          The grounding shadow (rgba(15,23,42,…), a near-black navy) reads as
          real elevation on a light surface but nearly disappears once the
          page background is itself dark — screenshot-verified: the bubble
          went from "floating with a soft glow" to "flat cutout" in dark
          mode. The dark: variants below don't add a dark contact-shadow
          (there's nothing darker than the page to cast one against) — they
          widen and intensify the same hue-matched glow instead, which is
          the actual working depth cue once the backdrop is dark.
          rgba(36,104,201,…) below = --brand-blue's own RGB (18/08/2026
          consolidation — this glow used to hardcode sky-400/old-accent-light
          rgba(56,189,248,…)/rgba(47,128,237,…), two more near-duplicate
          blues; kept as literals here rather than var() since Tailwind
          arbitrary-value shadow utilities can't cleanly reference a
          different alpha per state via a single CSS custom property). */}
      {showMascot && (
        <button
          ref={launcherRef}
          type="button"
          onClick={handleMascotClick}
          onKeyDown={handleKeyDown}
          onMouseEnter={handleMouseEnter}
          onMouseLeave={handleMouseLeave}
          className={`
            group rounded-full flex items-center justify-center relative select-none cursor-pointer outline-none border-none transition-all duration-300 ease-out z-10
            border-0
            hover:-translate-y-1.5 hover:scale-[1.18]
            active:scale-[1.08]
            focus-visible:ring-3 focus-visible:ring-offset-2
            ${isLandingRoute ? 'w-12 h-12' : 'w-14 h-14'}
              // Solid navy circle (not a washed-out white-dominant tint) —
              // the same rgba(20,49,92,…) navy used everywhere the mascot
              // appears (auth screens, App.jsx boot loader), now as the
              // actual fill instead of a faint gradient stop. A pale tinted
              // background read as "grey" rather than "blue" and the added
              // pulsing halo read as muddy/cluttered — both removed per
              // direct feedback in favor of one clean, confident color,
              // closer to how Intercom/Crisp/Drift render their launcher
              // (a solid brand-color disc, not a subtle wash).
              // Soft, wide, low-contrast shadow (large blur, low opacity)
              // instead of a tight/dark one — a tight dark shadow under a
              // small circle reads as a hard graphic cutout; a wide soft one
              // reads as an object actually floating above the page, which
              // is the difference between "looks hand-tuned" and "looks
              // machine-generated default".
              shadow-[0_10px_34px_-4px_rgba(20,49,92,0.3),0_4px_14px_-2px_rgba(15,23,42,0.08)] hover:shadow-[0_18px_44px_-4px_rgba(20,49,92,0.4),0_10px_22px_-4px_rgba(15,23,42,0.12)] active:shadow-[0_6px_18px_-4px_rgba(20,49,92,0.28)] focus-visible:ring-accent/40 dark:focus-visible:ring-offset-slate-900 dark:shadow-[0_12px_38px_-4px_rgba(20,49,92,0.5),0_2px_10px_rgba(0,0,0,0.4)] dark:hover:shadow-[0_20px_48px_-4px_rgba(20,49,92,0.6),0_10px_24px_-4px_rgba(0,0,0,0.45)] dark:active:shadow-[0_6px_20px_-4px_rgba(20,49,92,0.45)]
          `}
          style={{
            background: 'radial-gradient(circle at 32% 26%, #3A6BA5 0%, #234D80 45%, #142F58 100%)',
          }}
          aria-expanded={isOpen}
          aria-controls="curi-chat-panel"
          aria-label={isOpen ? "Đóng Trợ lý Cursus" : "Mở Trợ lý Cursus"}
        >
          {/* Soft, wide, heavily-blurred highlight instead of a crisp
              diagonal streak — a sharp white bar reads as a stock "glossy
              button" cliché; a big soft blob of light reads as an actual
              light source catching a rounded surface, closer to how a
              designer would actually shade a sphere by hand. */}
          <div className="absolute top-[2%] left-[6%] w-[55%] h-[45%] bg-white/25 rounded-full pointer-events-none filter blur-[10px] z-10" />
          {/* Soft sphere shading — wide blur radii on both the light-catch
              (top-left) and the deepening shadow (bottom-right) so they
              melt into the base color gradually instead of showing a
              visible hard-edged band/ring, which was the "looks a bit
              rough/AI-ish" complaint. */}
          <div
            className="absolute inset-0 rounded-full pointer-events-none z-10"
            style={{ boxShadow: 'inset 4px 6px 14px rgba(255,255,255,0.14), inset -6px -8px 18px rgba(0,0,0,0.22)' }}
          />

          <div className="relative w-full h-full flex items-center justify-center pointer-events-none z-10">
            <div 
              className={`absolute w-[76%] h-[76%] flex items-center justify-center transition-all duration-200 ease-out ${
                isPressed ? 'scale-[0.96]' : (mascotState === 'hover') ? 'scale-[1.10]' : 'scale-100'
              }`}
            >
              <CursusMascot size="launcher" className="w-full h-full" state={mascotState} />
            </div>
          </div>

          {!isOpen && (
            <span 
              className="absolute bottom-[2px] right-[2px] w-[11.5px] h-[11.5px] bg-[#22C55E] rounded-full ring-2 ring-white dark:ring-[#141828] z-20 pointer-events-none status-pulse-once shadow-[0_0_8px_#22C55E]" 
            />
          )}

          {unreadCount > 0 && !isOpen && (
            <span className="absolute -top-1 -right-1 flex h-5 min-w-[20px] items-center justify-center rounded-full bg-danger px-1 text-[10px] font-bold text-white shadow-sm ring-2 ring-white dark:ring-[#141828] z-20 pointer-events-none">
              {unreadCount > 9 ? '9+' : unreadCount}
            </span>
          )}
        </button>
      )}

      {/* Expanded Chat panel */}
      <div
        id="curi-chat-panel"
        ref={panelRef}
        tabIndex="-1"
        inert={!isOpen}
        className={`
          absolute z-[85] bg-surface-card border border-line shadow-panel overflow-hidden flex flex-col outline-none
          transition-all duration-300 ease-out origin-bottom-right
          ${isOpen ? 'opacity-100 translate-y-0 scale-100 pointer-events-auto' : 'opacity-0 translate-y-3 scale-[0.98] pointer-events-none'}
          ${isMinimized ? 'sm:h-[56px] sm:w-[300px] bottom-0 right-16 rounded-[var(--radius-md)]' : 'bottom-16 right-0 rounded-[var(--radius-lg)]'}
          max-sm:fixed max-sm:bottom-0 max-sm:right-0 max-sm:w-full max-sm:h-[80vh] max-sm:rounded-t-[var(--radius-lg)] max-sm:rounded-b-none
          ${!isMinimized ? 'sm:h-[500px] sm:w-[380px]' : ''}
        `}
      >
        {/* Header */}
        <div className="h-[56px] px-4 border-b border-line flex items-center justify-between bg-surface-elevated shrink-0 select-none">
          <div className="flex items-center gap-2 pointer-events-none">
            <CursusMascot size={24} state={mascotState} />
            <div className="text-left">
              <span className="block text-xs font-bold text-fg">{lang === 'vi' ? 'Trợ lý Cursus' : 'Cursus Assistant'}</span>
              <span className="block text-[9px] text-fg-muted font-bold uppercase tracking-wider">
                {isStudentRoute
                  ? (subjectCode
                      ? `${lang === 'vi' ? 'Ngữ cảnh môn' : 'Course context'}: ${subjectCode}`
                      : (lang === 'vi' ? 'Trả lời có trích dẫn nguồn thật' : 'Answers with real citations'))
                  : (lang === 'vi' ? 'Trợ lý học tập của Cursus · Dữ liệu minh họa' : "Cursus's learning assistant · Sample data")}
              </span>
            </div>
          </div>
          
          <div className="flex items-center gap-1">
            {/* Privacy policy */}
            <button
              type="button"
              onClick={() => setShowPrivacy(true)}
              className="p-1.5 rounded-lg text-fg-muted hover:text-accent hover:bg-surface-card transition-colors cursor-pointer outline-none focus-visible:ring-2 focus-visible:ring-accent"
              title={lang === 'vi' ? 'Chính sách bảo mật' : 'Privacy policy'}
              aria-label={lang === 'vi' ? 'Chính sách bảo mật' : 'Privacy policy'}
            >
              <Shield size={15} />
            </button>

            {/* Clear conversation, with an inline confirm popover */}
            <div className="relative">
              <button
                ref={clearTriggerRef}
                type="button"
                onClick={() => setConfirmingClear((v) => !v)}
                className={`p-1.5 rounded-lg transition-colors cursor-pointer outline-none focus-visible:ring-2 focus-visible:ring-red-500 ${confirmingClear ? 'text-red-500 bg-red-50 dark:bg-red-500/10' : 'text-fg-muted hover:text-red-500 hover:bg-surface-card'}`}
                title={lang === 'vi' ? 'Xóa cuộc hội thoại' : 'Clear conversation'}
                aria-label={lang === 'vi' ? 'Xóa cuộc hội thoại' : 'Clear conversation'}
                aria-expanded={confirmingClear}
              >
                <Trash2 size={15} />
              </button>

              {confirmingClear && (
                <>
                  <div className="fixed inset-0 z-40" onClick={closeConfirm} />
                  <div className="absolute right-0 mt-1 z-50 flex items-center gap-2 px-2.5 py-2 rounded-lg bg-surface-card border border-line shadow-lg animate-scale-in whitespace-nowrap">
                    <span className="text-[11px] font-bold text-red-600 dark:text-red-400">
                      {lang === 'vi' ? 'Xóa hẳn?' : 'Clear it?'}
                    </span>
                    <button
                      ref={confirmCancelRef}
                      type="button"
                      onClick={closeConfirm}
                      className="px-2 py-1 rounded-md text-[10px] font-bold text-fg-secondary bg-surface border border-line hover:bg-surface-elevated cursor-pointer outline-none focus-visible:ring-1 focus-visible:ring-accent"
                    >
                      {lang === 'vi' ? 'Hủy' : 'Cancel'}
                    </button>
                    <button
                      type="button"
                      onClick={() => { clearChat(); closeConfirm(); }}
                      className="px-2 py-1 rounded-md text-[10px] font-bold text-white bg-danger hover:opacity-90 cursor-pointer outline-none focus-visible:ring-1 focus-visible:ring-danger"
                    >
                      {lang === 'vi' ? 'Xóa' : 'Clear'}
                    </button>
                  </div>
                </>
              )}
            </div>

            {/* Close */}
            <button
              type="button"
              onClick={closeChat}
              className="p-1.5 text-fg-muted hover:text-fg rounded-lg transition-colors hover:bg-surface-card"
              aria-label="Close Cursus Assistant helper"
            >
              <X size={15} />
            </button>
          </div>
        </div>

        {/* Body */}
        {!isMinimized && (
          <div className="flex-1 flex flex-col min-h-0 bg-surface">
            {showPrivacy ? (
              <div className="flex-1 overflow-y-auto p-5 text-left space-y-4 animate-scale-in">
                <h3 className="font-display text-sm font-bold text-fg flex items-center gap-1.5">
                  <Shield size={16} className="text-accent" />
                  {lang === 'vi' ? 'Cam kết Bảo mật Quyền riêng tư' : 'Privacy Protection Policy'}
                </h3>
                <div className="text-xs text-fg-secondary leading-relaxed space-y-3">
                  <p>
                    {lang === 'vi'
                      ? '1. Lịch sử trò chuyện giữa Học viên và Trợ lý Cursus mang tính học tập bảo mật, không hiển thị trực tiếp cho Giảng viên.'
                      : '1. Chat history with Cursus Assistant is strictly confidential and not directly visible to your course instructors.'}
                  </p>
                  <p>
                    {lang === 'vi'
                      ? '2. Chúng tôi chỉ tổng hợp các chỉ số KPI tiến độ và mức độ nguy cơ trễ hạn để gửi cảnh báo học tập sớm (HITL) cho Advisor.'
                      : '2. We only aggregate weekly checklist status and coursework risks to generate early alerts for your Advisor.'}
                  </p>
                  <p>
                    {lang === 'vi'
                      ? '3. Trợ lý Cursus tuân thủ nguyên tắc không lưu trữ mật khẩu, OTP, hay thông tin thẻ tín dụng của người dùng.'
                      : '3. Mascot Cursus Assistant does not collect, record, or request passwords, OTP tokens, or credentials.'}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setShowPrivacy(false)}
                  className="w-full mt-4 h-9 rounded-lg bg-surface-card border border-line text-xs font-bold text-fg hover:bg-surface-elevated transition-colors cursor-pointer"
                >
                  {lang === 'vi' ? 'Quay lại trợ giúp' : 'Back to Guide'}
                </button>
              </div>
            ) : (
              <>
                <div className="flex-grow overflow-y-auto p-4 space-y-4 text-left">
                  {messages.map((m) => (
                    <div key={m.id} className={`flex flex-col ${m.role === 'user' ? 'items-end' : 'items-start'}`}>
                      {m.real && m.blocked && (
                        <span className="self-start mb-1 inline-flex items-center gap-1 text-[9px] font-bold px-1.5 py-0.5 rounded-full bg-warning-soft text-warning">
                          <ShieldAlert size={9} />
                          {lang === 'vi' ? 'Hướng dẫn học tập — không làm hộ' : 'Study guidance — not doing it for you'}
                        </span>
                      )}
                      {m.real && !m.blocked && m.block_reason === 'out_of_scope' && (
                        <span className="self-start mb-1 inline-flex items-center gap-1 text-[9px] font-bold px-1.5 py-0.5 rounded-full bg-surface text-fg-muted">
                          {lang === 'vi' ? 'Ngoài phạm vi tài liệu môn' : 'Outside course sources'}
                        </span>
                      )}
                      <div
                        className={`
                          max-w-[85%] p-3.5 text-xs leading-relaxed font-medium rounded-2xl
                          ${m.role === 'user'
                            ? 'bg-accent-cta text-white rounded-br-none'
                            : `bg-surface-card border border-line rounded-bl-none ${m.failed ? 'text-danger' : 'text-fg-secondary'}`}
                        `}
                      >
                        {m.real ? m.answer : m.text}
                        {m.real && m.guidance?.concept && (
                          <p className="mt-2 pt-2 border-t border-line text-[11px] text-fg-muted">
                            {m.guidance.concept}
                          </p>
                        )}
                        {m.citation && (
                          <div className="mt-2.5 pt-2 border-t border-line flex items-center gap-1.5 text-[10px] text-accent-text-safe font-bold">
                            <BookOpen size={11} />
                            <span>{m.citation}</span>
                          </div>
                        )}
                        {m.real && m.citations?.length > 0 && (
                          <div className="mt-2.5 pt-2 border-t border-line flex flex-wrap gap-x-3 gap-y-1">
                            {m.citations.map((c) => (
                              <div key={c.chunkId ?? c.sourceLabel} className="flex items-center gap-1 text-[10px] text-accent-text-safe font-bold">
                                <BookOpen size={11} />
                                <span>{c.sourceLabel ?? c.source_label}</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                      {m.ctaLink && (
                        <button
                          type="button"
                          onClick={() => { closeChat(); navigate(m.ctaLink); }}
                          className="mt-2 px-3 py-1.5 bg-accent-cta hover:bg-accent-cta-hover text-white rounded-lg text-[10px] font-bold flex items-center gap-1 transition-all"
                        >
                          {m.ctaText}
                          <ArrowRight size={10} />
                        </button>
                      )}
                    </div>
                  ))}

                  {isThinking && (
                    <div className="flex items-center gap-1.5 p-3 bg-surface-card border border-line rounded-2xl rounded-bl-none w-fit">
                      <span className="w-1.5 h-1.5 rounded-full bg-fg-muted animate-pulse" />
                      <span className="w-1.5 h-1.5 rounded-full bg-fg-muted animate-pulse delay-75" />
                      <span className="w-1.5 h-1.5 rounded-full bg-fg-muted animate-pulse delay-150" />
                    </div>
                  )}

                  <div ref={messagesEndRef} />
                </div>

                <div className="p-3 border-t border-line bg-surface-elevated shrink-0 text-left">
                  {isStudentRoute && courses.length > 1 && (
                    <label className="block mb-2">
                      <span className="sr-only">{lang === 'vi' ? 'Chọn môn học' : 'Select course'}</span>
                      <select
                        className="input text-[10px] w-full truncate"
                        style={{ height: '28px', paddingTop: '2px', paddingBottom: '2px', lineHeight: '1.2' }}
                        value={subjectCode}
                        onChange={(e) => setSubjectCode(e.target.value)}
                      >
                        {courses.map((c) => (
                          <option key={c.code} value={c.code}>{c.code} — {c.name}</option>
                        ))}
                      </select>
                    </label>
                  )}

                  <p className="text-[10px] text-fg-muted font-bold mb-2 uppercase tracking-wide">
                    {isStudentRoute
                      ? (lang === 'vi' ? 'Gợi ý câu hỏi:' : 'Suggested questions:')
                      : (lang === 'vi' ? 'Hãy hỏi Trợ lý Cursus về:' : 'Ask Cursus Assistant about:')}
                  </p>
                  <div className="flex flex-wrap gap-1.5 max-h-[120px] overflow-y-auto">
                    {(isStudentRoute
                      ? STUDENT_SUGGESTED_QUESTIONS.map((q) => ({ key: q, label: q }))
                      : PRESET_OPTIONS
                    ).map((opt) => (
                      <button
                        key={opt.key}
                        type="button"
                        onClick={() => (isStudentRoute ? sendRealQuestion(opt.label) : handlePrompt(opt.key, opt.label))}
                        disabled={isStudentRoute && (isThinking || !subjectCode)}
                        className="px-2.5 py-1.5 rounded-lg border border-line bg-surface-card hover:bg-surface text-[10px] font-bold text-fg-secondary transition-all hover:text-fg cursor-pointer text-left focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-accent disabled:opacity-40 disabled:cursor-not-allowed"
                      >
                        {opt.label}
                      </button>
                    ))}
                  </div>
                  {isStudentRoute && coursesLoaded && !subjectCode && (
                    <p className="mt-2 text-[10px] text-fg-muted">
                      {lang === 'vi' ? 'Bạn chưa có môn học nào được ghi danh.' : 'You are not enrolled in any course yet.'}
                    </p>
                  )}

                  <form onSubmit={handleFreeTextSubmit} className="mt-2.5 flex items-center gap-2">
                    <input
                      ref={textInputRef}
                      type="text"
                      value={inputValue}
                      onChange={(e) => setInputValue(e.target.value)}
                      placeholder={lang === 'vi' ? 'Nhập câu hỏi của bạn…' : 'Type your question…'}
                      aria-label={lang === 'vi' ? 'Nhập câu hỏi cho Trợ lý Cursus' : 'Message Cursus Assistant'}
                      disabled={isThinking || (isStudentRoute && !subjectCode)}
                      className="flex-1 min-w-0 h-9 px-3 rounded-lg border border-line bg-surface-card text-xs font-medium text-fg placeholder:text-fg-muted placeholder:font-normal outline-none focus-visible:ring-2 focus-visible:ring-accent disabled:opacity-60"
                    />
                    <button
                      type="submit"
                      disabled={!inputValue.trim() || isThinking || (isStudentRoute && !subjectCode)}
                      aria-label={lang === 'vi' ? 'Gửi tin nhắn' : 'Send message'}
                      className="shrink-0 w-9 h-9 flex items-center justify-center rounded-lg bg-accent-cta text-white transition-all hover:bg-accent-cta-hover disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
                    >
                      <ArrowUp size={16} />
                    </button>
                  </form>
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
