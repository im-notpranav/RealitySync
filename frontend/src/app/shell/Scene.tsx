/** Fixed background layer behind all glass (06 §2.4). Static on purpose: animating it under backdrop blur is expensive. */
export function Scene() {
  return <div aria-hidden="true" className="scene pointer-events-none fixed inset-0 -z-10" />;
}
