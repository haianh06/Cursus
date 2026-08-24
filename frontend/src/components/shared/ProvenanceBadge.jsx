import React from 'react';
import { BookOpen, FlaskConical, Sparkles, User, Calculator } from 'lucide-react';

/**
 * Renders the Data-Contract §3 provenance of a value.
 *
 * This is the component that keeps the product honest: an AI-invented
 * duration must read "Ước tính của Trợ lý Cursus", a syllabus fact must read
 * "Theo syllabus", and a made-up sandbox-only deadline must read "Dữ liệu
 * minh họa". Never render a number that could be mistaken for a fact
 * without one.
 */
const CONFIG = {
  official_document: {
    icon: BookOpen,
    vi: 'Theo syllabus',
    en: 'From syllabus',
    color: 'var(--citation)',
    bg: 'var(--accent-soft)',
  },
  simulated: {
    icon: FlaskConical,
    vi: 'Dữ liệu minh họa',
    en: 'Sample data',
    color: 'var(--gold)',
    bg: 'var(--gold-soft)',
  },
  user_entered: {
    icon: User,
    vi: 'Do bạn cung cấp',
    en: 'Provided by you',
    color: 'var(--text-secondary)',
    bg: 'var(--bg-elevated)',
  },
  system_derived: {
    icon: Calculator,
    vi: 'Hệ thống tính',
    en: 'System calculated',
    color: 'var(--do)',
    bg: 'var(--success-soft)',
  },
  ai_suggested: {
    icon: Sparkles,
    vi: 'Ước tính của Trợ lý Cursus',
    en: 'Cursus Assistant estimate',
    color: 'var(--ai-insight)',
    bg: 'var(--accent-soft)',
  },
};

export default function ProvenanceBadge({
  provenance,
  sourceType,
  lang = 'vi',
  label,
  title,
  size = 'sm',
}) {
  const type = sourceType || provenance?.source_type;
  const config = CONFIG[type];
  if (!config) return null;

  const Icon = config.icon;
  const text = label ?? (lang === 'vi' ? config.vi : config.en);
  const isXs = size === 'xs';

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full font-semibold whitespace-nowrap ${
        isXs ? 'text-[10px] px-1.5 py-0.5' : 'text-[11px] px-2 py-0.5'
      }`}
      style={{ color: config.color, background: config.bg }}
      title={title || `${text}${provenance?.source_id ? ` · ${provenance.source_id}` : ''}`}
    >
      <Icon size={isXs ? 9 : 10} aria-hidden="true" />
      {text}
    </span>
  );
}
