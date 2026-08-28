import { describe, test, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, within, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import CursusChat from './CursusChat';

/**
 * Covers the 4 chat-widget fixes with the network layer mocked out:
 *  1. citations render as unique pills (backend already dedups; this guards
 *     the render path never re-introduces duplicates for a given payload)
 *  2. FAQ/quick-reply chips show at the welcome screen AND again once a
 *     reply has finished
 *  3. assistant text is revealed gradually (typewriter), not all at once
 *  4. the source drawer opens with a higher stacking order than the chat
 *     panel (regression guard for the panel-behind-drawer bug)
 */

const apiMocks = vi.hoisted(() => ({
  streamCursusChat: vi.fn(),
  pingBackendHealth: vi.fn(),
  getCursusBriefing: vi.fn(),
  dismissCursusBriefing: vi.fn(),
  getCursusConversations: vi.fn(),
  getCursusConversationMessages: vi.fn(),
  exportCursusHistory: vi.fn(),
  deleteCursusHistory: vi.fn(),
  confirmCursusAction: vi.fn(),
  cancelCursusAction: vi.fn(),
  getSourceChunk: vi.fn(),
}));

vi.mock('../../lib/api', () => apiMocks);

const STUDENT_USER = { role: 'student', id: 'student-1' };

function renderChat() {
  return render(
    <MemoryRouter>
      <CursusChat user={STUDENT_USER} />
    </MemoryRouter>,
  );
}

async function openPanel(user) {
  await user.click(screen.getByRole('button', { name: 'Mở Cursus' }));
  return screen.getByRole('complementary', { name: 'Cursus chat' });
}

beforeEach(() => {
  apiMocks.pingBackendHealth.mockResolvedValue(true);
  apiMocks.getCursusBriefing.mockResolvedValue({ show: false });
  apiMocks.dismissCursusBriefing.mockResolvedValue({ ok: true });
  apiMocks.getCursusConversations.mockResolvedValue({ items: [] });
  apiMocks.streamCursusChat.mockReset();
});

afterEach(() => {
  vi.useRealTimers();
  vi.clearAllMocks();
});

describe('CursusChat', () => {
  test('shows FAQ quick-reply chips before any message is sent', async () => {
    const user = userEvent.setup();
    renderChat();
    const panel = await openPanel(user);
    expect(within(panel).getByRole('button', { name: /Hôm nay mình nên học gì trước/i })).toBeInTheDocument();
  });

  test('reveals the assistant reply progressively, dedupes citation pills, and re-shows the FAQ once done', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });

    const fullReply = 'Đây là câu trả lời khá dài để kiểm tra hiệu ứng gõ chữ từng ký tự một cách rõ ràng.';
    const citations = [
      { id: 'chunk-1', chunkId: 'chunk-1', title: 'Syllabus CSI106', document: 'Syllabus CSI106', section: 'Phần 1', isMock: false },
      { id: 'chunk-2', chunkId: 'chunk-2', title: 'Syllabus PRF192', document: 'Syllabus PRF192', section: 'Phần 1', isMock: false },
    ];
    apiMocks.streamCursusChat.mockImplementation(async ({ onEvent }) => {
      onEvent('meta', { conversationId: 'conv-1' });
      onEvent('delta', { text: fullReply });
      onEvent('citation', { items: citations });
    });

    renderChat();
    const panel = await openPanel(user);
    const textarea = within(panel).getByPlaceholderText('Hỏi Cursus…');
    await user.type(textarea, 'Tóm tắt môn học giúp mình');
    await user.keyboard('{Enter}');

    // Right after the delta arrives, the full text must NOT be on screen yet
    // -- it should still be mid-reveal (typewriter, not instant paste-in).
    await act(async () => {
      await vi.advanceTimersByTimeAsync(40); // a couple of 20ms ticks, 2 chars each
    });
    expect(screen.queryByText(fullReply)).not.toBeInTheDocument();

    // Let the typewriter finish revealing the whole message.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(fullReply.length * 20);
    });
    expect(screen.getByText(fullReply)).toBeInTheDocument();

    // Citations: exactly one pill per document, no duplicates.
    const citationButtons = screen.getAllByTitle(/^Mở nguồn:/);
    expect(citationButtons).toHaveLength(2);
    const labels = citationButtons.map((btn) => btn.getAttribute('title'));
    expect(new Set(labels).size).toBe(labels.length);

    // FAQ chips reappear now that the reply is fully typed out.
    expect(within(panel).getByRole('button', { name: /Hôm nay mình nên học gì trước/i })).toBeInTheDocument();
  });

  test('clicking a citation opens the source drawer with a higher stacking order than the chat panel', async () => {
    apiMocks.getSourceChunk.mockResolvedValue({ document: 'Syllabus CSI106', section: 'Phần 1', excerpt: 'Nội dung trích dẫn.' });
    apiMocks.streamCursusChat.mockImplementation(async ({ onEvent }) => {
      onEvent('delta', { text: 'Trả lời ngắn.' });
      onEvent('citation', { items: [{ id: 'chunk-1', chunkId: 'chunk-1', title: 'Syllabus CSI106', document: 'Syllabus CSI106', section: 'Phần 1', isMock: false }] });
    });

    const user = userEvent.setup();
    renderChat();
    const panel = await openPanel(user);
    // The chat <aside> panel uses z-[100] (see CursusChat.jsx) -- the drawer
    // must render above it, not behind it (the original bug).
    expect(panel.className).toMatch(/z-\[100\]/);

    const textarea = within(panel).getByPlaceholderText('Hỏi Cursus…');
    await user.type(textarea, 'Hỏi gì đó');
    await user.keyboard('{Enter}');

    const citationButton = await screen.findByTitle(/^Mở nguồn:/);
    await user.click(citationButton);

    const drawer = await screen.findByRole('dialog', { name: 'Nguồn trích dẫn' });
    const drawerZIndexMatch = drawer.className.match(/z-\[(\d+)\]/);
    const panelZIndexMatch = panel.className.match(/z-\[(\d+)\]/);
    expect(drawerZIndexMatch).not.toBeNull();
    expect(panelZIndexMatch).not.toBeNull();
    expect(Number(drawerZIndexMatch[1])).toBeGreaterThan(Number(panelZIndexMatch[1]));
  });
});
