import { createContext, useContext, useMemo, useState } from "react";

interface TutorialContextValue {
  isOpen: boolean;
  openTutorial: () => void;
  closeTutorial: () => void;
}

const TUTORIAL_STORAGE_KEY = "lawflow_tutorial_seen";

const TutorialContext = createContext<TutorialContextValue | undefined>(undefined);

export function TutorialProvider({ children }: { children: React.ReactNode }) {
  const [isOpen, setIsOpen] = useState<boolean>(() => {
    return localStorage.getItem(TUTORIAL_STORAGE_KEY) !== "1";
  });

  const value = useMemo(
    () => ({
      isOpen,
      openTutorial: () => setIsOpen(true),
      closeTutorial: () => {
        localStorage.setItem(TUTORIAL_STORAGE_KEY, "1");
        setIsOpen(false);
      },
    }),
    [isOpen]
  );

  return <TutorialContext.Provider value={value}>{children}</TutorialContext.Provider>;
}

export function useTutorial() {
  const ctx = useContext(TutorialContext);
  if (!ctx) {
    throw new Error("useTutorial must be used within TutorialProvider");
  }
  return ctx;
}
