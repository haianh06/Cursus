import React from 'react';
import AdminGuardrailRules from './AdminGuardrailRules';
import AdminRiskPolicy from './AdminRiskPolicy';

/** mục 6.5 "Chính sách AI" tab — guardrail rule toggles + risk-policy
 * versioning. Two independent backends/cards, shown together because the
 * spec groups them under one Admin Console section. */
export default function AdminAiPolicy() {
  return (
    <div className="space-y-6">
      <AdminGuardrailRules />
      <AdminRiskPolicy />
    </div>
  );
}
