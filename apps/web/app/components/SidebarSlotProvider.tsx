"use client";

/**
 * SidebarSlotProvider — Context for injecting page-specific contextual
 * content into the AppShell sidebar rail.
 *
 * Issue #288 — merge dual sidebars into single AppShell sidebar.
 *
 * Usage:
 *   <SidebarContent>
 *     <GuidedSidebarSection label="CONTEXT">...</GuidedSidebarSection>
 *   </SidebarContent>
 *
 * The content renders inside the AppShell sidebar, not in the page DOM.
 * Automatically cleans up on unmount.
 */

import {
  createContext,
  useContext,
  useState,
  useEffect,
  type ReactNode,
} from "react";

type SidebarSlotContextValue = {
  content: ReactNode | null;
  setContent: (content: ReactNode | null) => void;
};

const SidebarSlotContext = createContext<SidebarSlotContextValue>({
  content: null,
  setContent: () => {},
});

export function SidebarSlotProvider({ children }: { children: ReactNode }) {
  const [content, setContent] = useState<ReactNode | null>(null);
  return (
    <SidebarSlotContext.Provider value={{ content, setContent }}>
      {children}
    </SidebarSlotContext.Provider>
  );
}

export function useSidebarSlot() {
  return useContext(SidebarSlotContext);
}

/**
 * Declarative component — renders nothing in the page DOM but injects
 * its children into the AppShell sidebar via context.
 */
export function SidebarContent({ children }: { children: ReactNode }) {
  const { setContent } = useSidebarSlot();

  useEffect(() => {
    setContent(children);
    return () => setContent(null);
  }, [children, setContent]);

  return null;
}
