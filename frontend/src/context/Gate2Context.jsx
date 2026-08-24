import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';
import {
  acceptPlan,
  fastForwardDemoWeek,
  generatePlan,
  generatePlanFromReflection,
  getDemoState,
  resetDemo,
  saveReflection,
  updatePlanTaskStatus,
} from '../lib/api';

/**
 * The single canonical client-side state for the Gate-2 student slice.
 *
 * Every student screen (Dashboard, Planner, Reflection, Cursus Assistant) reads and
 * writes through this provider, which talks to the real backend — there is
 * deliberately no per-component mock. A task completed on the Dashboard is
 * the same record the Planner and the Reflection evidence summary see,
 * because all three re-read `GET /student/demo/state` after a mutation.
 */
const Gate2Context = createContext(null);

const EMPTY_STATE = {
  student: null,
  course: null,
  assignment: null,
  weekNumber: null,
  currentPlan: null,
  nextPlan: null,
  reflections: [],
  deferReasons: [],
  fixtureVersion: null,
};

export function Gate2Provider({ children }) {
  const [state, setState] = useState(EMPTY_STATE);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [mutating, setMutating] = useState(false);

  const load = useCallback(async ({ silent = false } = {}) => {
    if (!silent) setLoading(true);
    setError(null);
    try {
      const data = await getDemoState();
      setState({ ...EMPTY_STATE, ...data });
      return data;
    } catch (err) {
      setError(err);
      throw err;
    } finally {
      if (!silent) setLoading(false);
    }
  }, []);

  useEffect(() => {
    load().catch(() => {
      /* error surfaced through `error` */
    });
  }, [load]);

  /** Run a mutation, then re-read the canonical state so no screen can drift. */
  const mutate = useCallback(
    async (fn) => {
      setMutating(true);
      try {
        const result = await fn();
        await load({ silent: true });
        return result;
      } finally {
        setMutating(false);
      }
    },
    [load],
  );

  const actions = useMemo(
    () => ({
      reload: load,
      createPlan: (options) => mutate(() => generatePlan(options)),
      confirmPlan: (planId) => mutate(() => acceptPlan(planId)),
      startTask: (taskId) => mutate(() => updatePlanTaskStatus(taskId, 'IN_PROGRESS')),
      completeTask: (taskId, actualMinutes = null) =>
        mutate(() => updatePlanTaskStatus(taskId, 'COMPLETED', actualMinutes)),
      // The backend rejects a defer with no reason code — the dialog must
      // collect one before calling this.
      deferTask: (taskId, reasonCode, reasonNote = null) =>
        mutate(() =>
          updatePlanTaskStatus(taskId, 'DEFERRED', null, { reasonCode, reasonNote }),
        ),
      submitReflection: (payload) => mutate(() => saveReflection(payload)),
      buildNextWeekPlan: (payload) => mutate(() => generatePlanFromReflection(payload)),
      resetDemoState: () => mutate(() => resetDemo()),
      fastForward: () => mutate(() => fastForwardDemoWeek()),
    }),
    [load, mutate],
  );

  const derived = useMemo(() => {
    const plan = state.currentPlan;
    const tasks = plan?.tasks ?? [];
    const completed = tasks.filter((task) => task.status === 'COMPLETED');
    const openTasks = tasks.filter((task) => task.status !== 'COMPLETED');

    // "Next best action": earliest scheduled open task, highest priority first.
    const priorityRank = { HIGH: 0, MEDIUM: 1, LOW: 2 };
    const nextBestAction = [...openTasks].sort((a, b) => {
      const dateDiff = String(a.scheduledDate ?? '').localeCompare(String(b.scheduledDate ?? ''));
      if (dateDiff !== 0) return dateDiff;
      return (priorityRank[a.priority] ?? 3) - (priorityRank[b.priority] ?? 3);
    })[0] ?? null;

    const confirmedReflection = state.reflections.find((item) => item.studentConfirmed) ?? null;

    // Which step of Plan → Do → Reflect the student is actually on.
    let phase = 'plan';
    if (plan && plan.status === 'DRAFT') phase = 'plan';
    else if (plan && completed.length < tasks.length) phase = 'do';
    else if (plan) phase = 'reflect';
    if (confirmedReflection && state.nextPlan) phase = 'next-plan';

    return {
      tasks,
      completedCount: completed.length,
      totalCount: tasks.length,
      progressPct: tasks.length ? Math.round((completed.length / tasks.length) * 100) : 0,
      nextBestAction,
      confirmedReflection,
      phase,
    };
  }, [state]);

  const value = useMemo(
    () => ({ ...state, ...derived, loading, error, mutating, ...actions }),
    [state, derived, loading, error, mutating, actions],
  );

  return <Gate2Context.Provider value={value}>{children}</Gate2Context.Provider>;
}

export function useGate2() {
  const context = useContext(Gate2Context);
  if (!context) {
    throw new Error('useGate2 must be used within a Gate2Provider');
  }
  return context;
}
