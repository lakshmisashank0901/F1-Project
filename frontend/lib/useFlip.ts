"use client";

import { useLayoutEffect, useRef } from "react";

export function useFlip(ids: string[]) {
  const nodes = useRef(new Map<string, HTMLElement>());
  const previous = useRef(new Map<string, number>());

  useLayoutEffect(() => {
    const next = new Map<string, number>();
    for (const id of ids) {
      const node = nodes.current.get(id);
      if (!node) continue;
      const top = node.getBoundingClientRect().top;
      const last = previous.current.get(id);
      if (last !== undefined && Math.abs(last - top) > 1) {
        node.animate(
          [{ transform: `translateY(${last - top}px)` }, { transform: "translateY(0)" }],
          { duration: 520, easing: "cubic-bezier(.2,.8,.2,1)" },
        );
      }
      next.set(id, top);
    }
    previous.current = next;
  }, [ids]);

  return nodes;
}
