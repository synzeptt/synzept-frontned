export type SkillMarketplaceItem = {
  id: string;
  name: string;
  description: string;
  category: string;
  version: string;
  rating: number;
  installed: boolean;
  featured: boolean;
  updateAvailable: boolean;
  permissions: string[];
  integrations: string[];
};

export const skillMarketplaceItems: SkillMarketplaceItem[] = [
  {
    id: "skill-market-1",
    name: "Launch Planner",
    description: "Turn a product vision into a crisp launch plan.",
    category: "Startup",
    version: "1.2.0",
    rating: 4.8,
    installed: true,
    featured: true,
    updateAvailable: false,
    permissions: ["Memory access", "Tasks", "Projects"],
    integrations: ["Tasks", "Projects"],
  },
  {
    id: "skill-market-2",
    name: "Weekly Review",
    description: "Review the week and identify the biggest gain.",
    category: "Productivity",
    version: "1.0.0",
    rating: 4.6,
    installed: false,
    featured: false,
    updateAvailable: true,
    permissions: ["Calendar", "Tasks", "Memory access"],
    integrations: ["Calendar", "Tasks"],
  },
  {
    id: "skill-market-3",
    name: "Knowledge Graph Builder",
    description: "Connect notes, memories, and projects into a graph.",
    category: "Knowledge",
    version: "2.1.0",
    rating: 4.9,
    installed: true,
    featured: true,
    updateAvailable: false,
    permissions: ["Memory access", "Files", "Projects"],
    integrations: ["Files", "Projects"],
  },
];
