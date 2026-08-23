'use client';

import { Cpu } from 'lucide-react';

export type SalesAiActionRow = {
  action?: string;
  status?: string;
  nba?: string;
  note?: string;
  error?: string;
  delivery?: string;
};

export type SalesAiResult = {
  mode?: string;
  applied?: boolean;
  recommendation?: { action?: string; rationale?: string; missing_fields?: string[] };
  scores?: {
    conversion_probability?: number;
    lead_temperature?: string;
    engagement_score?: number;
    urgency_level?: string;
    confidence_score?: number;
  };
  scores_before?: {
    conversion_probability?: number | null;
    lead_temperature?: string | null;
  };
  scores_unchanged?: boolean;
  assigned_agent?: string | null;
  funnel_stage?: string | null;
  stage_before?: string | null;
  proposed_stage?: string | null;
  crm_sync?: unknown;
  actions_executed?: SalesAiActionRow[];
  note?: string;
  test_mode?: boolean;
};

type Props = {
  result: SalesAiResult;
  isExecuting?: boolean;
  error?: string | null;
  onCancel: () => void;
  onConfirm: () => void;
};

function actionLabel(row: SalesAiActionRow): string {
  const a = row.action || 'action';
  const map: Record<string, string> = {
    notify_agent: 'Notified agent',
    create_task: 'Task created',
    send_whatsapp: 'WhatsApp / brochure',
    schedule_visit: 'Site visit scheduled',
    request_info: 'Request info (no AE)',
    nurture_followup: 'Nurture follow-up (no AE)',
    assign_agent: 'Assign agent (no AE)',
    deal_closed: 'Deal closed — no outbound',
  };
  return map[a] || a.replace(/_/g, ' ');
}

export default function SalesAiModal({ result, isExecuting, error, onCancel, onConfirm }: Props) {
  const conf =
    result.scores?.conversion_probability ??
    result.scores?.confidence_score ??
    null;
  const confBefore = result.scores_before?.conversion_probability;
  const actions = result.actions_executed || [];
  const stageChanged =
    result.applied &&
    result.stage_before &&
    result.funnel_stage &&
    result.stage_before !== result.funnel_stage;
  const scoreChanged =
    confBefore != null && conf != null && Number(confBefore) !== Number(conf);

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-[#13131a] border border-gray-800 rounded-2xl p-6 max-w-lg w-full shadow-2xl max-h-[90vh] overflow-y-auto">
        <h3 className="text-xl font-bold text-white mb-2 flex items-center gap-2">
          <Cpu className="w-5 h-5 text-indigo-400" />
          {result.applied ? 'Applied Next Best Action' : 'Preview Next Best Action'}
        </h3>
        <p className="text-xs text-gray-500 mb-4 leading-relaxed">
          {result.note ||
            (result.applied
              ? 'Lead row updated. Scores use chat-aligned floors and do not drop a higher stored conversion while the lead stays complete.'
              : 'Preview only — Confirm saves to the lead and may run outbound actions.')}
        </p>
        <p className="mb-4 text-[11px] text-gray-600 leading-snug">
          Sales AI rescore matches chat visit/full-qualify boosts; it will not yank a high chat
          score down on Confirm when fields are still filled.
        </p>
        {result.test_mode && (
          <p className="mb-4 rounded-lg border border-amber-800/50 bg-amber-950/40 px-3 py-2 text-xs text-amber-200">
            TEST_MODE is on — brochure/WhatsApp will not be delivered to a real phone.
          </p>
        )}

        <div className="space-y-4 mb-6">
          <div className="bg-[#0f0f13] p-4 rounded-xl border border-gray-800">
            <span className="text-xs text-gray-500 uppercase font-bold tracking-wider block mb-1">
              Recommended Action
            </span>
            <span className="text-indigo-400 font-semibold">
              {result.recommendation?.action || '—'}
            </span>
          </div>

          <div className="bg-[#0f0f13] p-4 rounded-xl border border-gray-800">
            <span className="text-xs text-gray-500 uppercase font-bold tracking-wider block mb-1">
              Rationale
            </span>
            <p className="text-sm text-gray-300">{result.recommendation?.rationale || '—'}</p>
            {!!result.recommendation?.missing_fields?.length && (
              <p className="text-xs text-amber-400/90 mt-2">
                Missing: {result.recommendation.missing_fields.join(', ')}
              </p>
            )}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="bg-[#0f0f13] p-4 rounded-xl border border-gray-800">
              <span className="text-xs text-gray-500 uppercase font-bold tracking-wider block mb-1">
                Conversion
              </span>
              <span className="text-white font-bold">{conf != null ? `${conf}%` : '—'}</span>
              {!result.applied && confBefore != null && conf != null && scoreChanged && (
                <p className="text-[10px] text-gray-400 mt-1">
                  Stored in DB: {confBefore}% (Preview not saved yet)
                </p>
              )}
              {result.applied && scoreChanged && (
                <p className="text-[10px] text-emerald-400 mt-1">
                  Stored was {confBefore}% → now {conf}%
                </p>
              )}
              {result.applied && result.scores_unchanged && (
                <p className="text-[10px] text-gray-500 mt-1">Recalculated · unchanged</p>
              )}
            </div>
            <div className="bg-[#0f0f13] p-4 rounded-xl border border-gray-800">
              <span className="text-xs text-gray-500 uppercase font-bold tracking-wider block mb-1">
                Assigned To
              </span>
              <span className="text-white font-bold">{result.assigned_agent || 'Unassigned'}</span>
            </div>
            <div className="bg-[#0f0f13] p-4 rounded-xl border border-gray-800">
              <span className="text-xs text-gray-500 uppercase font-bold tracking-wider block mb-1">
                Funnel Stage
              </span>
              <span className="text-white font-bold">{result.funnel_stage || '—'}</span>
              {stageChanged && (
                <p className="text-[10px] text-emerald-400 mt-1">
                  {result.stage_before} → {result.funnel_stage}
                </p>
              )}
              {!result.applied && result.proposed_stage && (
                <p className="text-[10px] text-indigo-300 mt-1">
                  On confirm may become: {result.proposed_stage}
                </p>
              )}
              {result.applied && !stageChanged && (
                <p className="text-[10px] text-gray-500 mt-1">Stage unchanged (policy)</p>
              )}
            </div>
            <div className="bg-[#0f0f13] p-4 rounded-xl border border-gray-800">
              <span className="text-xs text-gray-500 uppercase font-bold tracking-wider block mb-1">
                Temperature
              </span>
              <span className="text-white font-bold capitalize">
                {result.scores?.lead_temperature || '—'}
              </span>
              {result.applied &&
                result.scores_before?.lead_temperature &&
                result.scores_before.lead_temperature !== result.scores?.lead_temperature && (
                  <p className="text-[10px] text-emerald-400 mt-1 capitalize">
                    Stored was {result.scores_before.lead_temperature} → now{' '}
                    {result.scores?.lead_temperature}
                  </p>
                )}
            </div>
          </div>

          {result.applied && actions.length > 0 && (
            <div className="bg-[#0f0f13] p-4 rounded-xl border border-indigo-900/40">
              <span className="text-xs text-gray-500 uppercase font-bold tracking-wider block mb-2">
                Actions Executed
              </span>
              <ul className="space-y-2">
                {actions.map((row, i) => (
                  <li key={`${row.action}-${i}`} className="text-sm">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-gray-200">{actionLabel(row)}</span>
                      <span
                        className={
                          row.status === 'ok'
                            ? 'text-emerald-400 text-xs font-semibold'
                            : row.status === 'skipped'
                              ? 'text-amber-400 text-xs font-semibold'
                              : 'text-red-400 text-xs font-semibold'
                        }
                      >
                        {(row.status || '—').toUpperCase()}
                      </span>
                    </div>
                    {row.note && (
                      <p className="mt-1 text-[11px] leading-snug text-gray-500">{row.note}</p>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {error && (
            <p className="text-sm text-red-400 bg-red-950/30 border border-red-900/40 rounded-lg px-3 py-2">
              {error}
            </p>
          )}
        </div>

        <div className="flex justify-end gap-3">
          <button
            type="button"
            onClick={onCancel}
            disabled={isExecuting}
            className="px-4 py-2 rounded-lg text-sm font-medium text-gray-400 hover:text-white hover:bg-gray-800 transition-colors disabled:opacity-50"
          >
            {result.applied ? 'Close' : 'Cancel'}
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={isExecuting || result.applied === true}
            className="px-4 py-2 rounded-lg text-sm font-medium bg-indigo-600 text-white hover:bg-indigo-700 transition-colors disabled:opacity-50"
          >
            {isExecuting ? 'Applying…' : result.applied ? 'Applied' : 'Confirm & Apply'}
          </button>
        </div>
      </div>
    </div>
  );
}
