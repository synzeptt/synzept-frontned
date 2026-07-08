from pydantic import BaseModel, Field


class SkillMarketplaceItemOut(BaseModel):
    id: str
    name: str
    description: str
    author: str
    version: str
    category: str
    rating: float
    reviews: int
    featured: bool = False
    trending: bool = False
    new: bool = False
    installed: bool = False
    enabled: bool = False
    permissions: list[str] = Field(default_factory=list)
    integrations: list[str] = Field(default_factory=list)
    screenshots: list[str] = Field(default_factory=list)
    documentation: str
    changelog: list[str] = Field(default_factory=list)


class SkillInstallActionOut(BaseModel):
    skillId: str
    action: str
    status: str
    message: str


class SkillDeveloperManifestOut(BaseModel):
    name: str
    version: str
    author: str
    category: str
    permissions: list[str] = Field(default_factory=list)
    integrations: list[str] = Field(default_factory=list)
    lifecycleHooks: list[str] = Field(default_factory=list)
