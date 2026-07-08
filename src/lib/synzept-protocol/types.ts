export type ProtocolResourceType =
  | "profile"
  | "goals"
  | "missions"
  | "projects"
  | "decisions"
  | "knowledge"
  | "memories"
  | "relationships"
  | "preferences";

export type ProtocolResource = {
  id: string;
  type: ProtocolResourceType;
  version: string;
  owner: "user";
  title: string;
  summary: string;
  updatedAt: string;
  schemaUrl: string;
  data: Record<string, string | number | boolean | string[]>;
};

export type ProtocolPermissionGrant = {
  id: string;
  appId: string;
  appName: string;
  resourceType: ProtocolResourceType;
  scopes: string[];
  status: "active" | "pending_user_approval" | "revoked";
  grantedAt: string;
  expiresAt: string | null;
  purpose: string;
};

export type ProtocolSubscription = {
  id: string;
  appId: string;
  resourceType: ProtocolResourceType;
  eventTypes: string[];
  callbackUrl: string;
  status: "active" | "paused";
  createdAt: string;
};

export type ProtocolAuditLog = {
  id: string;
  appId: string;
  appName: string;
  action: string;
  resourceType: ProtocolResourceType;
  scopes: string[];
  timestamp: string;
  result: string;
  userVisibleSummary: string;
};

export type ProtocolApp = {
  id: string;
  name: string;
  description: string;
  redirectUris: string[];
  allowedScopes: string[];
  sampleUseCase: string;
};

export type ProtocolSdk = {
  language: string;
  packageName: string;
  installCommand: string;
  modules: string[];
  example: string;
};

export type ProtocolAuthFlow = {
  flow: string;
  steps: string[];
  tokenRules: string[];
};

export type SynzeptProtocolData = {
  version: string;
  generatedAt: string;
  principles: string[];
  resourceTypes: ProtocolResourceType[];
  resources: ProtocolResource[];
  permissionGrants: ProtocolPermissionGrant[];
  subscriptions: ProtocolSubscription[];
  auditLogs: ProtocolAuditLog[];
  apps: ProtocolApp[];
  sdks: ProtocolSdk[];
  authFlow: ProtocolAuthFlow;
};
