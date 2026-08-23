// src/lib/api/mockService.ts
// Dev-only chart shapes. Live KPIs must use /api/v1/predictions/* (P4-6).
// Do not import mockForecastData as sole production forecast source.

/** @deprecated Prefer live predictions API — kept for illustrative chart series only */
export const mockForecastData = {
  status: "success",
  forecast: {
    timeframe: "monthly",
    projected_revenue: 4200000.00,
    confidence_interval: {
      lower_bound: 3800000.00,
      upper_bound: 4500000.00
    },
    key_drivers: [
      { factor: "High volume of Site Visits in Week 2", impact_weight: 0.4 },
      { factor: "3 bulk deals in advanced negotiation", impact_weight: 0.35 }
    ]
  }
};

export const mockChartData = [
  { name: 'Week 1', actual: 800000, forecast: 850000 },
  { name: 'Week 2', actual: 1200000, forecast: 1100000 },
  { name: 'Week 3', actual: 950000, forecast: 1050000 },
  { name: 'Week 4', actual: 0, forecast: 1200000 }, // Future
];

export const mockAlerts = [
  { id: 1, type: 'critical', message: '3 High-value payments overdue in Tower B', timestamp: '10 mins ago' },
  { id: 2, type: 'warning', message: 'Lead velocity dropped 15% in last 24hrs', timestamp: '1 hr ago' },
  { id: 3, type: 'info', message: 'Agent Anohita successfully closed Unit A-402', timestamp: '2 hrs ago' },
];

export const mockKPIs = {
  totalRevenue: 2950000,
  pipelineValue: 12400000,
  activeAgents: 14,
  leadVelocity: 85 // Leads per day
};

