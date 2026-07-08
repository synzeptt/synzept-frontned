from pydantic import BaseModel, Field


class ProtocolResourceOut(BaseModel):
    id: str
    type: str
    version: str
    owner: str
    title: str
    summary: str
    updatedAt: str
    schemaUrl: str
    data: dict[str, str | int | float | bool | list[str]]


class ProtocolPermissionGrantOut(BaseModel):
    id: str
    appId: str
    appName: str
    resourceType: str
    scopes: list[str] = Field(default_factory=list)
    status: str
    grantedAt: str
    expiresAt: str | None = None
    purpose: str


class ProtocolPermissionRequestIn(BaseModel):
    appId: str
    appName: str
    resourceType: str
    scopes: list[str]
    purpose: str


class ProtocolSubscriptionOut(BaseModel):
    id: str
    appId: str
    resourceType: str
    eventTypes: list[str] = Field(default_factory=list)
    callbackUrl: str
    status: str
    createdAt: str


class ProtocolSubscriptionIn(BaseModel):
    appId: str
    resourceType: str
    eventTypes: list[str]
    callbackUrl: str


class ProtocolAuditLogOut(BaseModel):
    id: str
    appId: str
    appName: str
    action: str
    resourceType: str
    scopes: list[str] = Field(default_factory=list)
    timestamp: str
    result: str
    userVisibleSummary: str


class ProtocolAppOut(BaseModel):
    id: str
    name: str
    description: str
    redirectUris: list[str] = Field(default_factory=list)
    allowedScopes: list[str] = Field(default_factory=list)
    sampleUseCase: str


class ProtocolSdkOut(BaseModel):
    language: str
    packageName: str
    installCommand: str
    modules: list[str] = Field(default_factory=list)
    example: str


class ProtocolAuthFlowOut(BaseModel):
    flow: str
    steps: list[str] = Field(default_factory=list)
    tokenRules: list[str] = Field(default_factory=list)


class SynzeptProtocolOut(BaseModel):
    version: str
    generatedAt: str
    principles: list[str] = Field(default_factory=list)
    resourceTypes: list[str] = Field(default_factory=list)
    resources: list[ProtocolResourceOut] = Field(default_factory=list)
    permissionGrants: list[ProtocolPermissionGrantOut] = Field(default_factory=list)
    subscriptions: list[ProtocolSubscriptionOut] = Field(default_factory=list)
    auditLogs: list[ProtocolAuditLogOut] = Field(default_factory=list)
    apps: list[ProtocolAppOut] = Field(default_factory=list)
    sdks: list[ProtocolSdkOut] = Field(default_factory=list)
    authFlow: ProtocolAuthFlowOut
