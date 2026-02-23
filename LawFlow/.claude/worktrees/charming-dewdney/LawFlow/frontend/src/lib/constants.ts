export const SUBJECT_LABELS: Record<string, string> = {
  con_law: "Constitutional Law",
  contracts: "Contracts",
  torts: "Torts",
  crim_law: "Criminal Law",
  civ_pro: "Civil Procedure",
  property: "Property",
  evidence: "Evidence",
  prof_responsibility: "Professional Responsibility",
};

export const SUBJECT_DESCRIPTIONS: Record<string, string> = {
  con_law: "Foundational principles of the U.S. Constitution.",
  contracts: "Formation, enforcement, and remedies for breach of contract.",
  torts: "Civil wrongs including negligence, intentional torts, and strict liability.",
  crim_law: "Principles of criminal liability, defenses, and specific crimes.",
  civ_pro: "Rules governing civil litigation including jurisdiction and discovery.",
  property: "Real and personal property rights, transfers, and land use.",
  evidence: "Rules governing admissibility of evidence at trial.",
  prof_responsibility: "Professional duties, ethics, and responsibilities of attorneys.",
};

export const SUBJECTS_FULL = [
  { value: "", label: "All Subjects" },
  { value: "con_law", label: "Constitutional Law" },
  { value: "contracts", label: "Contracts" },
  { value: "torts", label: "Torts" },
  { value: "crim_law", label: "Criminal Law" },
  { value: "civ_pro", label: "Civil Procedure" },
  { value: "property", label: "Property" },
  { value: "evidence", label: "Evidence" },
  { value: "prof_responsibility", label: "Professional Responsibility" },
] as const;

export const SUBJECTS_SHORT = [
  { value: "", label: "Any subject" },
  { value: "con_law", label: "Con Law" },
  { value: "contracts", label: "Contracts" },
  { value: "torts", label: "Torts" },
  { value: "crim_law", label: "Crim Law" },
  { value: "civ_pro", label: "Civ Pro" },
  { value: "property", label: "Property" },
  { value: "evidence", label: "Evidence" },
  { value: "prof_responsibility", label: "Prof. Resp." },
] as const;

/** Subjects without the "All" / empty option, for pickers that require a selection. */
export const SUBJECTS_REQUIRED = SUBJECTS_FULL.filter((s) => s.value !== "");

export const MODE_LABELS: Record<string, string> = {
  explain: "Explain",
  socratic: "Socratic",
  hypo: "Hypo Drill",
  issue_spot: "Issue Spot",
  irac: "IRAC",
  exam_strategy: "Exam Strategy",
};

export const AUTOTEACH_MODE_LABELS: Record<string, string> = {
  explain: "Learn",
  socratic: "Question",
  hypo: "Hypo Drill",
  issue_spot: "Issue Spot",
  irac: "IRAC",
  exam_strategy: "Exam Prep",
};

export const DOC_TYPES = [
  { value: "", label: "Auto-detect" },
  { value: "casebook", label: "Casebook / Textbook" },
  { value: "slides", label: "Lecture Slides" },
  { value: "outline", label: "Outline / Notes" },
  { value: "exam", label: "Past Exam" },
  { value: "supplement", label: "Supplement" },
] as const;

export const SUBJECTS_WITH_AUTODETECT = [
  { value: "", label: "Auto-detect" },
  ...SUBJECTS_REQUIRED,
] as const;

export const EXAM_FORMATS = [
  { value: "mixed", label: "Mixed (Essay + MC)", desc: "Realistic exam simulation" },
  { value: "essay", label: "Essay Only", desc: "IRAC-graded fact patterns" },
  { value: "mc", label: "Multiple Choice", desc: "MBE-style questions" },
  { value: "issue_spot", label: "Issue Spotting", desc: "Identify all legal issues" },
] as const;

export const CARD_TYPE_LABELS: Record<string, string> = {
  concept: "Concept",
  rule: "Rule",
  case_holding: "Case Holding",
  element_list: "Elements",
};

export const QUALITY_BUTTONS = [
  { label: "Again", quality: 1, color: "var(--red)", bg: "color-mix(in srgb, var(--red) 15%, transparent)" },
  { label: "Hard", quality: 2, color: "var(--orange)", bg: "color-mix(in srgb, var(--orange) 15%, transparent)" },
  { label: "Good", quality: 4, color: "var(--green)", bg: "color-mix(in srgb, var(--green) 15%, transparent)" },
  { label: "Easy", quality: 5, color: "var(--blue)", bg: "color-mix(in srgb, var(--blue) 15%, transparent)" },
] as const;
