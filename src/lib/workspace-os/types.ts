export type WorkspaceNavItem = {
  id: string;
  label: string;
  href: string;
  icon: string;
};

export type WorkspaceMission = {
  id: string;
  title: string;
  status: string;
  progress: number;
  currentMilestone: string;
  nextStep: string;
};

export type WorkspaceFocus = {
  title: string;
  reason: string;
  estimatedTime: string;
  linkedItems: string[];
};

export type WorkspaceAgent = {
  id: string;
  name: string;
  goal: string;
  status: string;
  recentActivity: string[];
  plannedNextSteps: string[];
  approvalsAwaitingUser: string[];
};

export type WorkspaceApproval = {
  id: string;
  title: string;
  requestedBy: string;
  riskLevel: string;
  preview: string;
  status: string;
};

export type WorkspaceKnowledge = {
  id: string;
  title: string;
  kind: string;
  summary: string;
  source: string;
  updatedAt: string;
};

export type WorkspaceOpportunity = {
  id: string;
  title: string;
  expectedImpact: number;
  confidence: number;
  suggestedAction: string;
};

export type WorkspaceOpenLoop = {
  id: string;
  title: string;
  owner: string;
  dueLabel: string;
  urgency: string;
};

export type WorkspaceBrief = {
  headline: string;
  whatChanged: string[];
  reminders: string[];
  recommendedNextAction: string;
};

export type WorkspaceSearchResult = {
  id: string;
  type: string;
  title: string;
  snippet: string;
  href: string;
  source: string;
  updatedAt: string;
  tags: string[];
};

export type WorkspaceCommand = {
  id: string;
  title: string;
  description: string;
  category: string;
  shortcut?: string;
  requiresInput: boolean;
};

export type WorkspaceOSData = {
  generatedAt: string;
  navigation: WorkspaceNavItem[];
  home: {
    currentMission: WorkspaceMission;
    todaysFocus: WorkspaceFocus[];
    activeAgents: WorkspaceAgent[];
    pendingApprovals: WorkspaceApproval[];
    recentKnowledge: WorkspaceKnowledge[];
    opportunities: WorkspaceOpportunity[];
    openLoops: WorkspaceOpenLoop[];
    dailyBrief: WorkspaceBrief;
  };
  searchIndex: WorkspaceSearchResult[];
  commands: WorkspaceCommand[];
  agents: WorkspaceAgent[];
  designPrinciples: string[];
};
