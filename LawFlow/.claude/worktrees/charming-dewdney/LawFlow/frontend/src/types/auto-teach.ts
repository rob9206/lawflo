export interface Mnemonic {
  acronym: string;
  expansion: string;
}

export interface Requirement {
  label: string;
  detail: string;
}

export interface CaseExample {
  name: string;
  court?: string;
  facts: string;
  holding: string;
  significance?: string;
}

export interface ExamTrap {
  trap: string;
  detail: string;
}

export interface RecognitionPattern {
  trigger: string;
  response: string;
}

export interface PracticeChoice {
  id: string;
  text: string;
}

export interface PracticeQuestion {
  stem: string;
  choices: PracticeChoice[];
  correct: string;
  explanation: string;
}

export interface AdditionalNote {
  heading: string;
  items: { label: string; detail: string }[];
}

export interface AutoTeachLesson {
  title: string;
  subtitle: string;
  category: string;
  level: string;
  topicKey: string;
  definition: string;
  mnemonic: Mnemonic;
  requirements: Requirement[];
  practiceQuestions: PracticeQuestion[];
  caseExample?: CaseExample;
  examTraps?: ExamTrap[];
  recognitionPattern?: RecognitionPattern;
  additionalNotes?: AdditionalNote[];
}
