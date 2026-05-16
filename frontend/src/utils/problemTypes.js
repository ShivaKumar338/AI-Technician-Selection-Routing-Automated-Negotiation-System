import { Hammer, Paintbrush, Snowflake, Wrench, Zap } from "lucide-react";

export const PROBLEM_TYPES = [
  { value: "AC", label: "AC Repair", icon: Snowflake },
  { value: "plumbing", label: "Plumbing", icon: Wrench },
  { value: "electrical", label: "Electrical", icon: Zap },
  { value: "carpentry", label: "Carpentry", icon: Hammer },
  { value: "painting", label: "Painting", icon: Paintbrush },
];

export const SKILL_FILTERS = PROBLEM_TYPES.map((item) => item.value);
